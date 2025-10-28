"""Application-facing service layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from .api_models import ComputeRequest
from .engine import ComputeEngine, ComputeResult


@dataclass
class QueryResult:
    band: str
    field_strength_dbuv_per_m: float
    power_density_W_m2: float
    top_contributors: list[int]


class ComputeService:
    """Facade aggregating engine runs and point queries."""

    def __init__(self, engine: Optional[ComputeEngine] = None) -> None:
        self.engine = engine or ComputeEngine()
        self._last_result: Optional[ComputeResult] = None

    def run_compute(self, request: ComputeRequest, output_dir: Optional[Path] = None) -> ComputeResult:
        """Execute the compute pipeline and cache the result."""
        result = self.engine.compute(request)
        self._last_result = result
        if output_dir is not None:
            result.write_outputs(Path(output_dir))
        return result

    def query_point(self, lat: float, lon: float, band_name: str) -> Optional[QueryResult]:
        """Return nearest-neighbour values for a given point and band."""
        if self._last_result is None:
            return None

        band_result = self._last_result.band_results.get(band_name)
        if band_result is None:
            return None

        grid = self._last_result.grid
        lat_grid = grid.latitudes
        lon_grid = grid.longitudes

        lat_idx = int(np.abs(lat_grid[:, 0] - lat).argmin())
        lon_idx = int(np.abs(lon_grid[0, :] - lon).argmin())

        if not grid.mask[lat_idx, lon_idx]:
            return None

        field_val = float(band_result.field_strength_dbuv_per_m[lat_idx, lon_idx])
        power_val = float(band_result.power_density_W_m2[lat_idx, lon_idx])
        top_idx = [int(i) for i in band_result.topk_indices[:, lat_idx, lon_idx]]

        return QueryResult(
            band=band_name,
            field_strength_dbuv_per_m=field_val,
            power_density_W_m2=power_val,
            top_contributors=top_idx,
        )
