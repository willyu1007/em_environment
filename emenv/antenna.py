"""Antenna gain modelling utilities.

该模块提供主瓣增益、扫描覆盖以及副瓣模板的计算函数，在服务化部署时可快速评估天线在不同方向上的
辐射能力。角度统一使用度 (degree) 表示，增益使用 dBi（相对于各向同性辐射体的增益）。
"""

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
    """Compute the mainlobe directional gain using a separable Gaussian approximation.

    参数
    ----
    delta_az_deg : np.ndarray
        方位角偏移，单位度。正负表示相对主指向的偏移方向。
    delta_el_deg : np.ndarray
        俯仰角偏移，单位度。
    hpbw_deg : float
        水平半功率角 (Half-Power Beam Width)，单位度。
    vpbw_deg : float
        垂直半功率角，单位度。
    g_peak_dBi : float, 默认 0.0
        主瓣峰值增益，单位 dBi。0 dBi 表示各向同性辐射源。

    返回
    ----
    np.ndarray
        主瓣方向上的增益（dBi）。当偏移超过半功率角时会快速衰减。

    说明
    ----
    该模型假设天线主瓣近似为高斯分布，可快速用于实时服务的方向性评估。
    """
    k = 4.0 * np.log(2.0)
    gh = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_az_deg / max(hpbw_deg, 1e-6)) ** 2
    gv = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_el_deg / max(vpbw_deg, 1e-6)) ** 2
    return np.minimum(gh, gv)


def in_scan_coverage(bearing_deg: np.ndarray, antenna: Antenna) -> np.ndarray:
    """Check whether bearings fall within the antenna scan envelope.

    参数
    ----
    bearing_deg : np.ndarray
        相对天线位置的方位角（度）。通常由目标点到天线的方位角计算。
    antenna : Antenna
        天线设置，包含扫描模式（none/circular/sector）以及扫描扇区宽度。

    返回
    ----
    np.ndarray
        布尔数组，True 表示该方向处于扫描覆盖范围内，False 表示不会照射。

    说明
    ----
    该函数在服务化场景下可用于快速过滤不需要计算的方向，减少无效的传播耗时。
    """
    mode = antenna.scan.mode
    if mode == "none":
        # 固定指向视为始终覆盖，方向性由主瓣/副瓣增益决定。
        return np.ones_like(bearing_deg, dtype=bool)
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
    """Evaluate peak gain toward each target point considering scanning behaviour.

    参数
    ----
    point_bearing_deg : np.ndarray
        目标方位角，单位度。
    point_elev_deg : np.ndarray
        目标俯仰角，单位度。
    antenna : Antenna
        天线配置（含主瓣宽度、副瓣模板、指向角度以及扫描方式）。
    g_peak_dBi : float, 默认 0.0
        主瓣峰值增益（dBi）。

    返回
    ----
    np.ndarray
        每个目标方向上的有效峰值增益（dBi）。当方向不在扫描覆盖内时，返回副瓣或默认增益。

    说明
    ----
    该函数将主瓣、高斯衰减和标准副瓣模板组合在一起，方便上层服务统一调用。
    返回值可直接转为线性增益 ``10^(dBi/10)`` 用于功率密度计算。
    """
    coverage = in_scan_coverage(point_bearing_deg, antenna)
    off_az = angular_diff_deg(point_bearing_deg, antenna.pointing_az_deg)
    off_el = point_elev_deg - antenna.pointing_el_deg
    g_mb = mainlobe_gain_dBi(off_az, off_el, antenna.pattern.hpbw_deg, antenna.pattern.vpbw_deg, g_peak_dBi)
    sidelobe_template = SL_TEMPLATES.get(antenna.pattern.sidelobe_template, SL_TEMPLATES["MIL-STD-20"])
    g_sl = sidelobe_template(np.abs(off_az))

    # 主瓣和副瓣叠加，扫描覆盖外仅保留副瓣电平。
    combined_gain = np.maximum(g_mb, g_sl)
    return np.where(coverage, combined_gain, g_sl)
