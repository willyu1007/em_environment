"""Antenna gain modelling utilities."""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from .api_models import Antenna
from .utils import angular_diff_deg

SL_TEMPLATES: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "MIL-STD-20": lambda off_axis_deg: np.full_like(off_axis_deg, -20.0, dtype=float),
    "RCS-13": lambda off_axis_deg: np.where(np.abs(off_axis_deg) < 10.0, -13.0, -20.0),
    "Radar-Narrow-25": lambda off_axis_deg: np.where(np.abs(off_axis_deg) < 10.0, -20.0, -25.0),
    "Comm-Omni-Back-10": lambda off_axis_deg: np.full_like(off_axis_deg, -10.0, dtype=float),
}


def mainlobe_gain_dBi(
    delta_az_deg: np.ndarray,
    delta_el_deg: np.ndarray,
    hpbw_deg: float,
    vpbw_deg: float,
    g_peak_dBi: float = 0.0,
) -> np.ndarray:
    """Compute the mainlobe gain using a separable Gaussian approximation."""
    k = 4.0 * np.log(2.0)
    gh = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_az_deg / max(hpbw_deg, 1e-6)) ** 2
    gv = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_el_deg / max(vpbw_deg, 1e-6)) ** 2
    return np.minimum(gh, gv)


def in_scan_coverage(bearing_deg: np.ndarray, antenna: Antenna) -> np.ndarray:
    """Check whether a bearing falls within the antenna scan envelope."""
    mode = antenna.scan.mode
    if mode == "none":
        return np.zeros_like(bearing_deg, dtype=bool)
    if mode == "circular":
        return np.ones_like(bearing_deg, dtype=bool)
    if mode == "sector":
        half_sector = max(antenna.scan.sector_deg * 0.5, 0.0)
        delta = np.abs(angular_diff_deg(bearing_deg, antenna.pointing_az_deg))
        return delta <= half_sector
    return np.zeros_like(bearing_deg, dtype=bool)


def peak_gain_dBi(
    point_bearing_deg: np.ndarray,
    point_elev_deg: np.ndarray,
    antenna: Antenna,
    g_peak_dBi: float = 0.0,
) -> np.ndarray:
    """Evaluate peak gain toward the point considering scanning behaviour."""
    coverage = in_scan_coverage(point_bearing_deg, antenna)
    off_az = angular_diff_deg(point_bearing_deg, antenna.pointing_az_deg)
    off_el = point_elev_deg - antenna.pointing_el_deg
    g_mb = mainlobe_gain_dBi(off_az, off_el, antenna.pattern.hpbw_deg, antenna.pattern.vpbw_deg, g_peak_dBi)
    sidelobe_template = SL_TEMPLATES.get(antenna.pattern.sidelobe_template, SL_TEMPLATES["MIL-STD-20"])
    g_sl = sidelobe_template(np.abs(off_az))
    gain = np.maximum(g_mb, g_sl)
    return np.where(coverage, g_peak_dBi, gain)
