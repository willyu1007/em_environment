"""Sampling grid construction utilities for the EM environment engine.

该模块负责根据用户选定的多边形区域生成经纬度采样网格，并提供掩膜矩阵指示哪些网格点位于区域内部。
网格分辨率以角度（degree）表示，高度以米（m）表示，这些约定与后续传播计算和服务接口保持一致，
便于未来将算法部署为在线服务时直接复用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np

from .api_models import Region


@dataclass(frozen=True)
class GridDefinition:
    """Structured representation of the sampling grid.

    Attributes
    ----------
    latitudes : np.ndarray
        二维纬度网格，单位为度 (degree)。矩阵形状为 ``(n_lat, n_lon)``。
    longitudes : np.ndarray
        二维经度网格，单位为度。与 ``latitudes`` 同形状。
    mask : np.ndarray
        布尔矩阵，True 表示网格点位于目标多边形内；False 表示在区域外。用于屏蔽无效单元。
    resolution_deg : float
        网格角分辨率，单位为度。该值同时适用于经度和纬度方向。
    alt_m : float
        观测高度，单位为米 (m)。在服务化时可与不同高度切片结合形成多层结果。
    """

    latitudes: np.ndarray
    longitudes: np.ndarray
    mask: np.ndarray
    resolution_deg: float
    alt_m: float

    @property
    def shape(self) -> Tuple[int, int]:
        """Return the grid dimensions as ``(n_lat, n_lon)``."""
        return self.latitudes.shape


def _polygon_arrays(polygon: Iterable) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize polygon vertices into separate latitude/longitude arrays.

    参数
    ----
    polygon :
        由支持 ``.lat``/``.lon`` 属性或 ``{"lat": ..., "lon": ...}`` 键的对象组成的可迭代对象。

    返回
    ----
    tuple[np.ndarray, np.ndarray]
        ``(latitudes, longitudes)``，均为 float64 数组，单位为度。按照输入顺序排列。
    """
    lats = np.array([p.lat if hasattr(p, "lat") else p["lat"] for p in polygon], dtype=float)
    lons = np.array([p.lon if hasattr(p, "lon") else p["lon"] for p in polygon], dtype=float)
    return lats, lons


def _point_in_polygon(
    lats: np.ndarray,
    lons: np.ndarray,
    poly_lats: np.ndarray,
    poly_lons: np.ndarray,
) -> np.ndarray:
    """Vectorized ray-casting test for whether grid points fall inside a polygon.

    参数
    ----
    lats, lons : np.ndarray
        需要测试的点集合，通常为网格网点，单位为度。
    poly_lats, poly_lons : np.ndarray
        多边形顶点的纬度与经度，单位为度。

    返回
    ----
    np.ndarray
        布尔矩阵，True 表示点位于多边形内部或边界上。
    """
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
    """Construct mesh grids and inside-mask for a region.

    参数
    ----
    region : Region
        区域定义，必须为 WGS84 坐标系。``region.polygon`` 里的点以度为单位。
    resolution_deg : float
        网格分辨率（度）。数值越小，采样精度越高，但栅格数量也会增加。

    返回
    ----
    tuple[np.ndarray, np.ndarray, np.ndarray]
        - ``lat_mesh`` : 2D 纬度网格 (degree)。
        - ``lon_mesh`` : 2D 经度网格 (degree)。
        - ``mask`` : 布尔网格，标识区域内的采样点。

    说明
    ----
    网格在纬度和经度方向使用相同的角度步长。对于未来服务化部署，可直接将该函数输出作为
    栅格化计算的输入，并通过缓存或网格模板减少重复计算。
    """
    poly_lats, poly_lons = _polygon_arrays(region.polygon)
    min_lat, max_lat = poly_lats.min(), poly_lats.max()
    min_lon, max_lon = poly_lons.min(), poly_lons.max()

    lat_values = np.arange(min_lat, max_lat + resolution_deg, resolution_deg)
    lon_values = np.arange(min_lon, max_lon + resolution_deg, resolution_deg)
    lon_mesh, lat_mesh = np.meshgrid(lon_values, lat_values)

    mask = _point_in_polygon(lat_mesh, lon_mesh, poly_lats, poly_lons)
    return lat_mesh, lon_mesh, mask


def create_grid(region: Region, resolution_deg: float, alt_m: float) -> GridDefinition:
    """Factory helper that wraps ``build_grid`` into a :class:`GridDefinition`.

    参数
    ----
    region : Region
        目标区域，坐标单位为度。
    resolution_deg : float
        网格角分辨率（degree）。
    alt_m : float
        观测高度，单位为米。通常对应接收机/监测天线的高度。

    返回
    ----
    GridDefinition
        完整的网格定义，可在引擎以及REST服务中复用。
    """
    lat_mesh, lon_mesh, mask = build_grid(region, resolution_deg)
    return GridDefinition(
        latitudes=lat_mesh,
        longitudes=lon_mesh,
        mask=mask,
        resolution_deg=resolution_deg,
        alt_m=alt_m,
    )
