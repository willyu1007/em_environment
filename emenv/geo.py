"""Geodesic helpers on a spherical Earth approximation.

提供大圆距离、正向方位角以及仰角计算，角度统一以度表示，距离/半径使用千米 (km)，高度差使用米 (m)。
这些函数是传播引擎和未来服务化接口中的基础几何模块。
"""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0


def haversine_km(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: np.ndarray,
    lon2: np.ndarray,
    radius_km: float = EARTH_RADIUS_KM,
) -> np.ndarray:
    """Compute great-circle distance between two points in kilometres.

    参数
    ----
    lat1, lon1, lat2, lon2 : np.ndarray
        起点与终点的纬度/经度，单位度，可为标量或数组（自动广播）。
    radius_km : float, 默认 ``EARTH_RADIUS_KM``
        球体半径 (km)。可通过 ``k_factor`` 调整有效地球半径。

    返回
    ----
    np.ndarray
        大圆距离，单位 km。
    """
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    dlat = lat2_rad - lat1_rad
    dlon = np.deg2rad(lon2 - lon1)

    sin_dlat = np.sin(dlat * 0.5)
    sin_dlon = np.sin(dlon * 0.5)
    a = sin_dlat**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * sin_dlon**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1.0 - a, 0.0)))
    return radius_km * c


def forward_azimuth_deg(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Compute forward azimuth from point 1 to point 2 in degrees.

    参数
    ----
    lat1, lon1, lat2, lon2 : np.ndarray
        起点与终点的纬度/经度（度）。

    返回
    ----
    np.ndarray
        前向方位角（0° 指向正北，顺时针增加）。
    """
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    dlon_rad = np.deg2rad(lon2 - lon1)

    y = np.sin(dlon_rad) * np.cos(lat2_rad)
    x = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon_rad)
    azimuth_rad = np.arctan2(y, x)
    return (np.rad2deg(azimuth_rad) + 360.0) % 360.0


def elevation_angle_deg(horizontal_km: np.ndarray, delta_alt_m: np.ndarray) -> np.ndarray:
    """Compute elevation angle from horizontal distance and altitude delta.

    参数
    ----
    horizontal_km : np.ndarray
        水平距离 (km)。
    delta_alt_m : np.ndarray
        高度差 (m)，接收高度减去发射高度。

    返回
    ----
    np.ndarray
        仰角，单位度。正值表示目标在水平面之上。
    """
    horizontal_m = np.maximum(horizontal_km, 1e-6) * 1000.0
    return np.rad2deg(np.arctan2(delta_alt_m, horizontal_m))
