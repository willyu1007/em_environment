"""Grid construction utilities for the EM environment engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np

from .api_models import Region


@dataclass(frozen=True)
class GridDefinition:
    """Structured representation of the sampling grid."""

    latitudes: np.ndarray  # 2D mesh
    longitudes: np.ndarray  # 2D mesh
    mask: np.ndarray  # boolean mask for polygon interior
    resolution_deg: float
    alt_m: float

    @property
    def shape(self) -> Tuple[int, int]:
        return self.latitudes.shape


def _polygon_arrays(polygon: Iterable) -> Tuple[np.ndarray, np.ndarray]:
    lats = np.array([p.lat if hasattr(p, "lat") else p["lat"] for p in polygon], dtype=float)
    lons = np.array([p.lon if hasattr(p, "lon") else p["lon"] for p in polygon], dtype=float)
    return lats, lons


def _point_in_polygon(lats: np.ndarray, lons: np.ndarray, poly_lats: np.ndarray, poly_lons: np.ndarray) -> np.ndarray:
    """Vectorized ray casting point-in-polygon test."""
    inside = np.zeros_like(lats, dtype=bool)
    x = lons
    y = lats
    xverts = poly_lons
    yverts = poly_lats
    n = len(poly_lats)
    j = n - 1
    for i in range(n):
        yi = yverts[i]
        yj = yverts[j]
        xi = xverts[i]
        xj = xverts[j]
        intersect = ((yi > y) != (yj > y)) & (
            x < (xj - xi) * (y - yi) / np.maximum(yj - yi, 1e-12) + xi
        )
        inside ^= intersect
        j = i
    return inside


def build_grid(region: Region, resolution_deg: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construct latitude/longitude meshgrids and polygon mask."""
    poly_lats, poly_lons = _polygon_arrays(region.polygon)
    min_lat, max_lat = poly_lats.min(), poly_lats.max()
    min_lon, max_lon = poly_lons.min(), poly_lons.max()

    lat_values = np.arange(min_lat, max_lat + resolution_deg, resolution_deg)
    lon_values = np.arange(min_lon, max_lon + resolution_deg, resolution_deg)
    lon_mesh, lat_mesh = np.meshgrid(lon_values, lat_values)

    mask = _point_in_polygon(lat_mesh, lon_mesh, poly_lats, poly_lons)
    return lat_mesh, lon_mesh, mask


def create_grid(region: Region, resolution_deg: float, alt_m: float) -> GridDefinition:
    """Factory to build a grid definition."""
    lat_mesh, lon_mesh, mask = build_grid(region, resolution_deg)
    return GridDefinition(
        latitudes=lat_mesh,
        longitudes=lon_mesh,
        mask=mask,
        resolution_deg=resolution_deg,
        alt_m=alt_m,
    )
