"""Propagation loss models (传播损耗模型).

实现自由空间路径损耗、双程平地反射近似与大气/天气附加衰减，频率统一使用 MHz，距离使用 km，
高度使用米，使其与 API 服务的输入输出保持一致。
"""

from __future__ import annotations

import numpy as np

from .api_models import Environment


def fspl_dB(f_MHz: np.ndarray, r_km: np.ndarray) -> np.ndarray:
    """Free-space path loss (Friis) in dB.

    参数
    ----
    f_MHz : np.ndarray
        信号载频，单位 MHz。
    r_km : np.ndarray
        传播路径的斜距，单位 km。

    返回
    ----
    np.ndarray
        自由空间路径损耗，单位 dB。数值越大表示信号衰减越多。
    """
    return 32.45 + 20.0 * np.log10(np.maximum(f_MHz, 1e-6)) + 20.0 * np.log10(np.maximum(r_km, 1e-6))


def two_ray_flat_loss_dB(
    f_MHz: np.ndarray,
    horizontal_km: np.ndarray,
    tx_alt_m: np.ndarray,
    rx_alt_m: np.ndarray,
) -> np.ndarray:
    """Two-ray ground reflection loss approximation with phase interference.

    参数
    ----
    f_MHz : np.ndarray
        载频，单位 MHz。
    horizontal_km : np.ndarray
        发射与接收之间的水平距离 (km)。
    tx_alt_m : np.ndarray
        发射高度 (m)。
    rx_alt_m : np.ndarray
        接收高度 (m)。

    返回
    ----
    np.ndarray
        考虑平地反射造成干涉的路径损耗 (dB)。

    说明
    ----
    采用理想导电地面假设（反射系数 -1），适合快速估算平坦地形下的干涉效应。
    为避免近场不稳定，当水平距离小于 10 个波长时会退回到 FSPL 结果。
    """
    c_m_per_s = 299_792_458.0
    wavelength_m = c_m_per_s / (np.maximum(f_MHz, 1e-6) * 1e6)

    horizontal_m = np.maximum(horizontal_km, 1e-6) * 1000.0
    ht = np.maximum(tx_alt_m, 1.0)
    hr = np.maximum(rx_alt_m, 1.0)

    direct_distance_m = np.sqrt(horizontal_m**2 + (ht - hr) ** 2)
    reflected_distance_m = np.sqrt(horizontal_m**2 + (ht + hr) ** 2)
    direct_distance_km = direct_distance_m / 1000.0

    propagation_phase = 2.0 * np.pi * (reflected_distance_m - direct_distance_m) / np.maximum(wavelength_m, 1e-9)

    # Perfectly conducting flat earth approximation: reflection coefficient -1 for horizontal pol.
    reflection_coeff = -1.0

    interference_mag = np.abs(1.0 + reflection_coeff * np.exp(-1j * propagation_phase))
    interference_mag = np.maximum(interference_mag, 1e-6)

    base_fspl = fspl_dB(f_MHz, direct_distance_km)
    interference_loss = -20.0 * np.log10(interference_mag)

    # Near-field safeguard: fall back to FSPL under 10 wavelengths horizontal separation.
    near_field = horizontal_m < 10.0 * wavelength_m
    total_loss = base_fspl + interference_loss
    return np.where(near_field, base_fspl, total_loss)


def atmospheric_loss_dB_per_km(
    f_MHz: np.ndarray,
    rain_rate_mmph: float,
    fog_lwc_gm3: float,
    gas_loss_mode: str = "auto",
) -> np.ndarray:
    """Approximate gaseous, rain, and fog attenuation per kilometre.

    参数
    ----
    f_MHz : np.ndarray
        载频 (MHz)。
    rain_rate_mmph : float
        降雨率 (毫米/小时)。
    fog_lwc_gm3 : float
        雾液态含水量 (克/立方米)。
    gas_loss_mode : str, 默认 ``"auto"``
        气体衰减模式。``"auto"`` 使用经验模型；传入数字字符串则视为固定 dB/km。

    返回
    ----
    np.ndarray
        每公里的附加衰减 (dB/km)。
    """
    freq_GHz = np.maximum(f_MHz, 1e-6) / 1000.0
    gas_base = 0.004 if gas_loss_mode == "auto" else max(0.001, float(gas_loss_mode))
    gas_loss = gas_base * (1.0 + 0.1 * freq_GHz**1.2)
    rain_loss = 0.0001 * rain_rate_mmph * freq_GHz**0.8
    fog_loss = 0.0002 * fog_lwc_gm3 * freq_GHz**2
    return gas_loss + rain_loss + fog_loss


def total_extra_loss_dB(f_MHz: np.ndarray, r_km: np.ndarray, environment: Environment) -> np.ndarray:
    """Total additional attenuation accumulated along the path.

    参数
    ----
    f_MHz : np.ndarray
        载频 (MHz)。
    r_km : np.ndarray
        路径长度 (km)。
    environment : Environment
        环境配置，决定雨雾参数及气体损耗模式。

    返回
    ----
    np.ndarray
        对整条路径的额外损耗量 (dB)。
    """
    per_km = atmospheric_loss_dB_per_km(
        f_MHz=f_MHz,
        rain_rate_mmph=environment.atmosphere.rain_rate_mmph,
        fog_lwc_gm3=environment.atmosphere.fog_lwc_gm3,
        gas_loss_mode=environment.atmosphere.gas_loss,
    )
    return per_km * np.maximum(r_km, 0.0)


def propagation_additional_loss_dB(
    f_MHz: np.ndarray,
    slant_km: np.ndarray,
    horizontal_km: np.ndarray,
    tx_alt_m: np.ndarray,
    rx_alt_m: np.ndarray,
    environment: Environment,
) -> np.ndarray:
    """Loss relative to ideal FSPL plus additional atmospheric attenuation.

    参数
    ----
    f_MHz : np.ndarray
        载频 (MHz)。
    slant_km : np.ndarray
        空间斜距 (km)。
    horizontal_km : np.ndarray
        地面平距 (km)。
    tx_alt_m : np.ndarray
        发射高度 (m)。
    rx_alt_m : np.ndarray
        接收高度 (m)。
    environment : Environment
        环境配置，决定传播模型（free_space/two_ray_flat）以及大气参数。

    返回
    ----
    np.ndarray
        相对于纯 FSPL 的附加损耗 (dB)，可直接与主功率计算叠加。

    说明
    ----
    该函数将几何附加损耗（例如双程干涉）与大气损耗合并，便于在服务层统一调用。
    """
    base_adjustment = np.zeros_like(f_MHz, dtype=float)

    if environment.propagation.model == "two_ray_flat":
        two_ray_loss = two_ray_flat_loss_dB(f_MHz, horizontal_km, tx_alt_m, rx_alt_m)
        fspl_loss = fspl_dB(f_MHz, slant_km)
        base_adjustment = two_ray_loss - fspl_loss

    extra = total_extra_loss_dB(f_MHz, slant_km, environment)
    return base_adjustment + extra
