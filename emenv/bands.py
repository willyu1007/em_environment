"""Band utilities (频段工具函数).

服务化接口常使用频段上下限（MHz）定义通道，本模块提供中心频率计算等辅助函数。
"""

from __future__ import annotations

import numpy as np

from .api_models import Band


def band_center_freq_MHz(band: Band) -> float:
    """Compute the center frequency for a band entry (单位: MHz).

    参数
    ----
    band : Band
        频段定义，包含 ``f_min_MHz`` 与 ``f_max_MHz``。

    返回
    ----
    float
        频段中心频率 (MHz)，即 ``(f_min + f_max) / 2``。
    """
    return 0.5 * (band.f_min_MHz + band.f_max_MHz)


def bands_center_array(bands: list[Band]) -> np.ndarray:
    """Return an array of centre frequencies for provided bands.

    参数
    ----
    bands : list[Band]
        频段列表。

    返回
    ----
    np.ndarray
        以 float 形式表示的中心频率数组 (MHz)。
    """
    return np.array([band_center_freq_MHz(b) for b in bands], dtype=float)
