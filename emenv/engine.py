"""Numerical compute engine for EM environment estimation."""

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
from .geo import elevation_angle_deg, forward_azimuth_deg, haversine_km
from .grid import GridDefinition, create_grid
from .propagation import propagation_additional_loss_dB


@dataclass
class BandResult:
    """Result container for a single band."""

    name: str
    center_freq_MHz: float
    field_strength_dbuv_per_m: np.ndarray
    power_density_W_m2: np.ndarray
    topk_indices: np.ndarray
    topk_power_W_m2: np.ndarray
    topk_fraction: np.ndarray


@dataclass
class ComputeResult:
    """Aggregated compute output."""

    grid: GridDefinition
    band_results: Dict[str, BandResult] = field(default_factory=dict)
    source_ids: List[str] = field(default_factory=list)

    def write_outputs(self, output_dir: Path) -> None:
        """Persist GeoTIFF rasters and Top-3 diagnostics for each band."""
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
    """Main computation orchestrator."""

    def __init__(self, config: EngineConfig = ENGINE_CONFIG) -> None:
        self.config = config

    def compute(self, request: ComputeRequest) -> ComputeResult:
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
            masked_indices = np.where(grid.mask[None, ...], topk_indices, -1)
            masked_power = np.where(grid.mask[None, ...], topk_power, np.nan)
            masked_fraction = np.where(grid.mask[None, ...], fractions, np.nan)

            threshold = request.metric == "E_field_dBuV_per_m" and self.config.threshold_dbuv_per_m
            if threshold:
                field_strength[field_strength < self.config.threshold_dbuv_per_m] = np.nan

            band_results[band.name] = BandResult(
                name=band.name,
                center_freq_MHz=center_freq,
                field_strength_dbuv_per_m=field_strength,
                power_density_W_m2=total_power_density,
                topk_indices=masked_indices,
                topk_power_W_m2=masked_power,
                topk_fraction=masked_fraction,
            )

        return ComputeResult(grid=grid, band_results=band_results, source_ids=source_ids)

    def _filter_sources(self, sources: List[Source], grid: GridDefinition, buffer_km: float) -> List[Source]:
        """Filter sources based on a rudimentary bounding circle around the region."""
        if not sources:
            return []

        mask = grid.mask
        if not mask.any():
            lat_center = float(np.mean(grid.latitudes))
            lon_center = float(np.mean(grid.longitudes))
        else:
            lat_center = float(np.mean(grid.latitudes[mask]))
            lon_center = float(np.mean(grid.longitudes[mask]))

        retained: List[Source] = []
        for src in sources:
            distance_km = haversine_km(
                np.array([src.position.lat]),
                np.array([src.position.lon]),
                np.array([lat_center]),
                np.array([lon_center]),
            )[0]
            if distance_km <= buffer_km + 1.5 * max(grid.shape):
                retained.append(src)
        return retained

    def _prepare_geometry(self, sources: List[Source], grid: GridDefinition):
        lat_mesh = grid.latitudes
        lon_mesh = grid.longitudes

        src_lat = np.array([src.position.lat for src in sources], dtype=float)[:, None, None]
        src_lon = np.array([src.position.lon for src in sources], dtype=float)[:, None, None]
        src_alt = np.array([src.position.alt_m for src in sources], dtype=float)[:, None, None]
        rx_alt = np.full(grid.shape, grid.alt_m, dtype=float)[None, ...]

        lat_targets = np.broadcast_to(lat_mesh, (len(sources),) + grid.shape)
        lon_targets = np.broadcast_to(lon_mesh, (len(sources),) + grid.shape)

        horizontal_km = haversine_km(src_lat, src_lon, lat_targets, lon_targets)
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
