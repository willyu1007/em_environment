"""Geodesic helpers on a spherical Earth approximation."""

from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Compute great-circle distance between two points in kilometers."""
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    dlat = lat2_rad - lat1_rad
    dlon = np.deg2rad(lon2 - lon1)

    sin_dlat = np.sin(dlat * 0.5)
    sin_dlon = np.sin(dlon * 0.5)
    a = sin_dlat**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * sin_dlon**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1.0 - a, 0.0)))
    return EARTH_RADIUS_KM * c


def forward_azimuth_deg(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Compute forward azimuth from point 1 to point 2 in degrees."""
    lat1_rad = np.deg2rad(lat1)
    lat2_rad = np.deg2rad(lat2)
    dlon_rad = np.deg2rad(lon2 - lon1)

    y = np.sin(dlon_rad) * np.cos(lat2_rad)
    x = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon_rad)
    azimuth_rad = np.arctan2(y, x)
    return (np.rad2deg(azimuth_rad) + 360.0) % 360.0


def elevation_angle_deg(horizontal_km: np.ndarray, delta_alt_m: np.ndarray) -> np.ndarray:
    """Compute elevation angle from horizontal distance and altitude delta."""
    horizontal_m = np.maximum(horizontal_km, 1e-6) * 1000.0
    return np.rad2deg(np.arctan2(delta_alt_m, horizontal_m))
