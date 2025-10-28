import numpy as np

from emenv.geo import elevation_angle_deg, forward_azimuth_deg, haversine_km


def test_haversine_zero_distance():
    lat = np.array([[30.0]])
    lon = np.array([[120.0]])
    distance = haversine_km(lat, lon, lat, lon)
    assert np.allclose(distance, 0.0)


def test_forward_azimuth_equator():
    az = forward_azimuth_deg(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([90.0]))
    assert np.allclose(az, 90.0)


def test_elevation_angle():
    horizontal = np.array([10.0])  # km
    delta_alt = np.array([1000.0])  # m
    elev = elevation_angle_deg(horizontal, delta_alt)
    assert 0.0 < elev[0] < 10.0
