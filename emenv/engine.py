"""Numerical compute engine for EM environment estimation.

计算流程涵盖：
1. 构建观测网格（纬/经度单位 degree，高度单位米）
2. 过滤影响范围内的辐射源（距离单位 km）
3. 结合天线增益、传播损耗、功率密度与电场强度换算（瓦特、dBm、dBµV/m）

该模块的接口被 CLI、REST 服务以及可视化工具复用，因此注释中明确了输入输出约定，
便于未来将算法部署为长期运行的服务。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Dict, List

from pathlib import Path

import numpy as np

from .antenna import peak_gain_dBi
from .api_models import Band, ComputeRequest, Source
from .bands import bands_center_array
from .combine import (
    eirp_dBm_to_W,
    field_strength_dBuV_per_m,
    power_density_W_m2,
    sum_sources_and_topk,
)
from .config import ENGINE_CONFIG, EngineConfig
from .geo import EARTH_RADIUS_KM, elevation_angle_deg, forward_azimuth_deg, haversine_km
from .grid import GridDefinition, create_grid
from .propagation import propagation_additional_loss_dB


@dataclass
class BandResult:
    """Result container for a single frequency band.

    Attributes
    ----------
    name : str
        频段名称。
    center_freq_MHz : float
        频段中心频率 (MHz)。
    field_strength_dbuv_per_m : np.ndarray
        电场强度格网，单位 dBµV/m。
    power_density_W_m2 : np.ndarray
        功率密度格网，单位 W/m²。
    topk_indices : np.ndarray
        Top-K 源索引 (shape: ``(top_k, n_lat, n_lon)``)。
    topk_power_W_m2 : np.ndarray
        Top-K 功率密度 (W/m²)。
    topk_fraction : np.ndarray
        Top-K 对总功率密度的贡献占比（0~1）。
    """

    name: str
    center_freq_MHz: float
    field_strength_dbuv_per_m: np.ndarray
    power_density_W_m2: np.ndarray
    topk_indices: np.ndarray
    topk_power_W_m2: np.ndarray
    topk_fraction: np.ndarray


@dataclass
class ComputeResult:
    """Aggregated compute output for one request."""

    grid: GridDefinition
    band_results: Dict[str, BandResult] = field(default_factory=dict)
    source_ids: List[str] = field(default_factory=list)

    def write_outputs(self, output_dir: Path) -> None:
        """Persist GeoTIFF rasters and Top-3 diagnostics for each band.

        参数
        ----
        output_dir : Path
            输出目录。函数会为每个频段创建一个子目录，并写入：
            - ``*_field_strength.tif``：电场强度栅格 (dBµV/m)
            - ``*_topk.parquet``：Top-K 源贡献诊断（含功率占比）
        """
        from .io_raster import write_geotiff, write_topk_parquet

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for band_name, band in self.band_results.items():
            band_dir = output_dir / band_name
            geotiff_path = band_dir / f"{band_name}_field_strength.tif"
            topk_parquet_path = band_dir / f"{band_name}_topk.parquet"

            write_geotiff(geotiff_path, self.grid, band.field_strength_dbuv_per_m)
            write_topk_parquet(
                topk_parquet_path,
                grid=self.grid,
                band_name=band.name,
                topk_indices=band.topk_indices,
                topk_fraction=band.topk_fraction,
                topk_power_W_m2=band.topk_power_W_m2,
                source_ids=self.source_ids,
            )


class ComputeEngine:
    """Main computation orchestrator for EM 环境评估."""

    def __init__(self, config: EngineConfig = ENGINE_CONFIG) -> None:
        """Create a compute engine with optional configuration overrides."""
        self.config = config

    def compute(self, request: ComputeRequest) -> ComputeResult:
        """Run the full EM 环境估算流程并返回结果对象。

        参数
        ----
        request : ComputeRequest
            请求载荷，包含区域、网格、频段、环境参数以及辐射源。
            - 坐标单位: 度
            - 高度单位: 米
            - 距离计算: 千米
            - 频率单位: MHz
            - 功率单位: dBm (输入)、W (内部计算)

        返回
        ----
        ComputeResult
            包含每个频段的栅格化电场强度 (dBµV/m)、功率密度 (W/m²) 以及 Top-K 源诊断信息。

        说明
        ----
        该方法无状态，可安全用于后台服务的并发调用。对于服务化部署，可将引擎实例复用，
        并按需扩展缓存策略（例如对网格或传播结果缓存）。
        """
        if not request.bands:
            raise ValueError("At least one band must be provided.")

        grid = create_grid(request.region, request.grid.resolution_deg, request.grid.alt_m)
        sources = self._filter_sources(request.sources, grid, request.influence_buffer_km)

        center_freqs = bands_center_array(request.bands)
        band_results: Dict[str, BandResult] = {}
        source_ids = [src.id for src in sources]

        if not sources:
            empty_field = np.full(grid.shape, np.nan, dtype=float)
            for band, freq in zip(request.bands, center_freqs):
                band_results[band.name] = BandResult(
                    name=band.name,
                    center_freq_MHz=freq,
                    field_strength_dbuv_per_m=empty_field.copy(),
                    power_density_W_m2=empty_field.copy(),
                    topk_indices=np.full((0,) + grid.shape, -1, dtype=int),
                    topk_power_W_m2=np.full((0,) + grid.shape, np.nan, dtype=float),
                    topk_fraction=np.full((0,) + grid.shape, np.nan, dtype=float),
                )
            return ComputeResult(grid=grid, band_results=band_results, source_ids=source_ids)

        geom = self._prepare_geometry(sources, grid)

        eirp_W = eirp_dBm_to_W(np.array([src.emission.eirp_dBm for src in sources], dtype=float))

        for idx, (band, center_freq) in enumerate(zip(request.bands, center_freqs)):
            freq_array = np.full_like(geom.horizontal_km, center_freq, dtype=float)
            extra_loss_db = propagation_additional_loss_dB(
                f_MHz=freq_array,
                slant_km=geom.slant_km,
                horizontal_km=geom.horizontal_km,
                tx_alt_m=geom.tx_alt_m,
                rx_alt_m=geom.rx_alt_m,
                environment=request.environment,
            )
            # Geometric spreading represented by 4πr² term; propagation adjustment handled separately.
            gains_dBi = np.array(
                [
                    peak_gain_dBi(geom.bearing_deg[i], geom.elevation_deg[i], sources[i].antenna)
                    for i in range(len(sources))
                ],
                dtype=float,
            )
            gain_lin = 10.0 ** (gains_dBi / 10.0)

            power_density = power_density_W_m2(
                eirp_W=eirp_W,
                gain_lin=gain_lin,
                r_m=geom.slant_km * 1000.0,
                additional_loss_dB=extra_loss_db,
            )

            total_power_density, topk_indices = sum_sources_and_topk(power_density, self.config.top_k)
            topk_power = np.take_along_axis(power_density, topk_indices, axis=0)
            with np.errstate(divide="ignore", invalid="ignore"):
                fractions = np.divide(
                    topk_power,
                    total_power_density[None, ...],
                    out=np.zeros_like(topk_power),
                    where=total_power_density[None, ...] > 0.0,
                )
            field_strength = field_strength_dBuV_per_m(total_power_density)
            field_strength[~grid.mask] = np.nan
            total_power_density[~grid.mask] = np.nan

            threshold = request.metric == "E_field_dBuV_per_m" and self.config.threshold_dbuv_per_m
            if threshold:
                field_strength[field_strength < self.config.threshold_dbuv_per_m] = np.nan

            valid_mask = np.isfinite(field_strength)
            total_power_density[~valid_mask] = np.nan
            topk_indices = np.where(valid_mask[None, ...], topk_indices, -1)
            topk_power = np.where(valid_mask[None, ...], topk_power, np.nan)
            fractions = np.where(valid_mask[None, ...], fractions, np.nan)

            band_results[band.name] = BandResult(
                name=band.name,
                center_freq_MHz=center_freq,
                field_strength_dbuv_per_m=field_strength,
                power_density_W_m2=total_power_density,
                topk_indices=topk_indices,
                topk_power_W_m2=topk_power,
                topk_fraction=fractions,
            )

        return ComputeResult(grid=grid, band_results=band_results, source_ids=source_ids)

    def _filter_sources(self, sources: List[Source], grid: GridDefinition, buffer_km: float) -> List[Source]:
        """Filter sources based on a rudimentary bounding circle around the region.

        参数
        ----
        sources : list[Source]
            候选辐射源列表。
        grid : GridDefinition
            网格定义（提供区域中心与遮罩）。
        buffer_km : float
            影响半径缓冲，单位 km。

        返回
        ----
        list[Source]
            落在区域中心半径 ``extent + buffer`` 内的源。距离通过哈弗辛公式计算。
        """
        if not sources:
            return []

        mask = grid.mask
        if not mask.any():
            lat_center = float(np.mean(grid.latitudes))
            lon_center = float(np.mean(grid.longitudes))
            lat_points = grid.latitudes.ravel()
            lon_points = grid.longitudes.ravel()
        else:
            lat_center = float(np.mean(grid.latitudes[mask]))
            lon_center = float(np.mean(grid.longitudes[mask]))
            lat_points = grid.latitudes[mask]
            lon_points = grid.longitudes[mask]

        effective_radius = EARTH_RADIUS_KM * self.config.k_factor

        if lat_points.size:
            center_lat = np.full(lat_points.shape, lat_center, dtype=float)
            center_lon = np.full(lon_points.shape, lon_center, dtype=float)
            distances = haversine_km(center_lat, center_lon, lat_points, lon_points, radius_km=effective_radius)
            extent_km = float(np.max(distances))
        else:
            extent_km = 0.0

        retained: List[Source] = []
        for src in sources:
            distance_km = haversine_km(
                np.array([src.position.lat]),
                np.array([src.position.lon]),
                np.array([lat_center]),
                np.array([lon_center]),
                radius_km=effective_radius,
            )[0]
            if distance_km <= buffer_km + extent_km:
                retained.append(src)
        return retained

    def _prepare_geometry(self, sources: List[Source], grid: GridDefinition):
        """Pre-compute geometric relationships between sources and grid cells.

        返回一个 ``SimpleNamespace``，其中包含：
        - ``horizontal_km``: 水平距离 (km)
        - ``slant_km``: 斜距 (km)
        - ``bearing_deg``: 方位角 (deg)
        - ``elevation_deg``: 仰角 (deg)
        - ``tx_alt_m`` / ``rx_alt_m``: 发射/接收高度 (m)

        这些数据用于传播损耗和天线增益计算，方便在服务化环境中重复使用同一几何关系。
        """
        lat_mesh = grid.latitudes
        lon_mesh = grid.longitudes
        effective_radius = EARTH_RADIUS_KM * self.config.k_factor

        src_lat = np.array([src.position.lat for src in sources], dtype=float)[:, None, None]
        src_lon = np.array([src.position.lon for src in sources], dtype=float)[:, None, None]
        src_alt = np.array([src.position.alt_m for src in sources], dtype=float)[:, None, None]
        rx_alt = np.full(grid.shape, grid.alt_m, dtype=float)[None, ...]

        lat_targets = np.broadcast_to(lat_mesh, (len(sources),) + grid.shape)
        lon_targets = np.broadcast_to(lon_mesh, (len(sources),) + grid.shape)

        horizontal_km = haversine_km(src_lat, src_lon, lat_targets, lon_targets, radius_km=effective_radius)
        bearing_deg = forward_azimuth_deg(src_lat, src_lon, lat_targets, lon_targets)
        delta_alt_m = (rx_alt - src_alt).astype(float)
        slant_km = np.sqrt(horizontal_km**2 + (delta_alt_m / 1000.0) ** 2)
        elevation_deg = elevation_angle_deg(horizontal_km, delta_alt_m)

        return SimpleNamespace(
            horizontal_km=horizontal_km,
            bearing_deg=bearing_deg,
            slant_km=slant_km,
            elevation_deg=elevation_deg,
            tx_alt_m=src_alt,
            rx_alt_m=rx_alt,
        )
