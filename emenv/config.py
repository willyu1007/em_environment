"""Centralized configuration defaults for the EM environment estimation engine.

配置项用于控制网格分辨率、影响半径、阈值等参数，便于在服务化后通过注入或环境变量进行覆盖。
所有长度使用米（m）或千米（km），角度使用度，电场强度以 dBµV/m 表示。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:
    """Default numerical configuration for the compute engine.

    Attributes
    ----------
    grid_resolution_deg : float
        默认网格分辨率，单位度。0.01° 约等于 1.1 km 的地面间距。
    influence_buffer_km : float
        在区域边界外额外保留的影响范围（km），用于筛选可能影响结果的辐射源。
    threshold_dbuv_per_m : float
        结果阈值，单位 dBµV/m（相当于以 1 微伏/米为参考的对数值）。小于该值的点可设为无效。
    top_k : int
        输出 Top-K 辐射源，便于定位主要贡献者。
    k_factor : float
        等效地球曲率系数（无量纲）。4/3 模型是常用的折射近似。
    """

    grid_resolution_deg: float = 0.01
    influence_buffer_km: float = 200.0
    threshold_dbuv_per_m: float = 40.0
    top_k: int = 3
    k_factor: float = 4.0 / 3.0


@dataclass(frozen=True)
class AtmosphereDefaults:
    """Default atmospheric attenuation parameters.

    Attributes
    ----------
    gas_loss_mode : str
        大气气体衰减模式（``"auto"`` 表示自适应）。若设置为数字字符串，则直接视为 dB/km。
    rain_rate_mmph : float
        降雨率，单位为毫米/小时 (mm/h)。
    fog_lwc_gm3 : float
        雾的液态含水量，单位克/立方米 (g/m³)。
    """

    gas_loss_mode: float = 0.004  # dB/km baseline气体衰减（翻倍）
    rain_rate_mmph: float = 0.0
    fog_lwc_gm3: float = 0.0


ENGINE_CONFIG = EngineConfig()
ATMOSPHERE_DEFAULTS = AtmosphereDefaults()
