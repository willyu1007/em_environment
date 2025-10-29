"""Application-facing service layer.

提供对计算引擎的高层封装，支持：
1. 执行一次完整的栅格化计算（可选写入 GeoTIFF/Parquet）
2. 在已有结果上执行点查询，便于 REST 服务即时响应

该层保持无状态，便于将结果缓存到内存中，为后续服务化部署打基础。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from .api_models import ComputeRequest
from .engine import ComputeEngine, ComputeResult


@dataclass
class QueryResult:
    """Point query result for a single frequency band.

    Attributes
    ----------
    band : str
        频段名称。
    alt_m : float
        结果对应的高度 (m)。
    field_strength_dbuv_per_m : float
        电场强度 (dBµV/m)。
    power_density_W_m2 : float
        功率密度 (W/m²)。
    top_contributors : list[int]
        Top-K 源的索引，便于回查源 ID。
    """

    band: str
    alt_m: float
    field_strength_dbuv_per_m: float
    power_density_W_m2: float
    top_contributors: list[int]


class ComputeService:
    """Facade aggregating engine runs and point queries."""

    def __init__(self, engine: Optional[ComputeEngine] = None) -> None:
        """Initialise the service with a compute engine (可注入以便测试或扩展缓存)."""
        self.engine = engine or ComputeEngine()
        self._last_result: Optional[ComputeResult] = None

    def run_compute(self, request: ComputeRequest, output_dir: Optional[Path] = None) -> ComputeResult:
        """Execute the compute pipeline and cache the result.

        参数
        ----
        request : ComputeRequest
            计算请求。
        output_dir : Path, 可选
            若提供，将结果写入 GeoTIFF 与 Parquet。

        返回
        ----
        ComputeResult
            计算结果对象，可用于后续查询或写盘。
        """
        result = self.engine.compute(request)
        self._last_result = result
        if output_dir is not None:
            result.write_outputs(Path(output_dir))
        return result

    def query_point(self, lat: float, lon: float, alt_m: float, band_name: str) -> Optional[QueryResult]:
        """Return nearest-neighbour values for a given point and band.

        参数
        ----
        lat, lon : float
            查询位置的纬度/经度（度）。
        alt_m : float
            查询高度（米），需与计算网格高度一致。
        band_name : str
            目标频段。

        返回
        ----
        QueryResult | None
            成功时返回点值与 Top-K 索引；若尚未运行计算、频段不存在或点在掩膜外，则返回 None。

        说明
        ----
        当前实现采用最近邻查找，未来可引入插值或 KD-Tree 加速，以满足实时服务需求。
        """
        if self._last_result is None:
            return None

        band_result = self._last_result.band_results.get(band_name)
        if band_result is None:
            return None

        grid = self._last_result.grid
        if abs(alt_m - grid.alt_m) > 1e-3:
            return None
        lat_grid = grid.latitudes
        lon_grid = grid.longitudes

        lat_idx = int(np.abs(lat_grid[:, 0] - lat).argmin())
        lon_idx = int(np.abs(lon_grid[0, :] - lon).argmin())

        if not grid.mask[lat_idx, lon_idx]:
            return None

        field_val = float(band_result.field_strength_dbuv_per_m[lat_idx, lon_idx])
        power_val = float(band_result.power_density_W_m2[lat_idx, lon_idx])
        top_idx_raw = band_result.topk_indices[:, lat_idx, lon_idx]
        top_idx = [int(i) for i in top_idx_raw if i >= 0]

        return QueryResult(
            band=band_name,
            alt_m=grid.alt_m,
            field_strength_dbuv_per_m=field_val,
            power_density_W_m2=power_val,
            top_contributors=top_idx,
        )
