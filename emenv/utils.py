"""Utility helpers for numerical and angular operations.

包含角度/弧度转换、分贝与线性值互转等通用函数，贯穿整个传播计算流程。
"""

from __future__ import annotations

import math
from typing import Iterable, Tuple

import numpy as np


def deg2rad(degrees: np.ndarray | float) -> np.ndarray | float:
    """Convert degrees to radians (deg → rad)."""
    return np.deg2rad(degrees)


def rad2deg(radians: np.ndarray | float) -> np.ndarray | float:
    """Convert radians to degrees (rad → deg)."""
    return np.rad2deg(radians)


def angular_diff_deg(angle1: np.ndarray | float, angle2: np.ndarray | float) -> np.ndarray | float:
    """Shortest signed angular difference in degrees.

    返回值范围为 ``[-180°, 180°)``，便于比较方位角差异。
    """
    diff = (np.asarray(angle1) - np.asarray(angle2) + 180.0) % 360.0 - 180.0
    return diff


def db_to_linear(db_value: np.ndarray | float) -> np.ndarray | float:
    """Convert a value in decibels to linear scale."""
    return 10.0 ** (np.asarray(db_value) / 10.0)


def linear_to_db(linear_value: np.ndarray | float, floor: float = 1e-15) -> np.ndarray | float:
    """Convert a linear power value to dB with an optional numerical floor."""
    clipped = np.maximum(np.asarray(linear_value), floor)
    return 10.0 * np.log10(clipped)


def pairwise(iterable: Iterable) -> Iterable[Tuple]:
    """Yield consecutive pairs from an iterable.

    示例
    ----
    ``pairwise([1, 2, 3])`` 依次产生 ``(1, 2)``, ``(2, 3)``。
    """
    it = iter(iterable)
    prev = next(it, None)
    for current in it:
        yield prev, current
        prev = current
