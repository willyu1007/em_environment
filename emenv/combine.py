"""Source combination utilities (辐射源功率叠加工具).

提供 EIRP 单位转换、功率密度计算以及电场强度换算函数。所有功率单位均使用瓦特 (W) 或 dBm，
距离使用米 (m)，电场强度输出 dBµV/m（相当于以 1 微伏/米为参考的对数单位）。
"""

from __future__ import annotations

import numpy as np

Z0 = 377.0  # Free-space impedance


def eirp_dBm_to_W(eirp_dBm: np.ndarray) -> np.ndarray:
    """Convert equivalent isotropically radiated power from dBm to Watts.

    参数
    ----
    eirp_dBm : np.ndarray
        EIRP，单位 dBm。dBm 的含义是以 1 mW 为参考的对数功率。

    返回
    ----
    np.ndarray
        线性功率，单位瓦特 (W)。
    """
    return 10.0 ** ((np.asarray(eirp_dBm) - 30.0) / 10.0)


def power_density_W_m2(
    eirp_W: np.ndarray,
    gain_lin: np.ndarray,
    r_m: np.ndarray,
    additional_loss_dB: np.ndarray,
) -> np.ndarray:
    """Compute power density at range with optional additional attenuation.

    参数
    ----
    eirp_W : np.ndarray
        辐射源的等效各向同性辐射功率，单位瓦特 (W)。
    gain_lin : np.ndarray
        天线增益的线性值（无量纲），通常由 ``10^(dBi/10)`` 获得。
    r_m : np.ndarray
        发射与接收点之间的斜距，单位米 (m)。
    additional_loss_dB : np.ndarray
        附加损耗，单位 dB（正值表示额外衰减）。

    返回
    ----
    np.ndarray
        功率密度，单位瓦特每平方米 (W/m²)。

    说明
    ----
    基于几何扩散（4πr²）计算自由空间功率密度，并通过附加损耗项叠加传播模型结果。
    """
    fs_term = (eirp_W[..., None, None] * gain_lin) / (4.0 * np.pi * np.maximum(r_m, 1.0) ** 2)
    return fs_term * 10.0 ** (-np.asarray(additional_loss_dB) / 10.0)


def field_strength_dBuV_per_m(power_density_W_m2: np.ndarray) -> np.ndarray:
    """Convert power density to electric field strength in dBµV/m.

    参数
    ----
    power_density_W_m2 : np.ndarray
        功率密度，单位 W/m²。

    返回
    ----
    np.ndarray
        电场强度，单位 dBµV/m。该单位表示与 1 微伏/米相比的对数比值。

    说明
    ----
    使用自由空间阻抗 ``Z0 = 377 Ω`` 计算 ``E = sqrt(Z0 * S)``，再转换为对数形式。
    """
    e_v_per_m = np.sqrt(Z0 * np.maximum(power_density_W_m2, 1e-30))
    return 20.0 * np.log10(e_v_per_m) + 120.0


def sum_sources_and_topk(power_density: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate power density contributions and extract Top-K sources.

    参数
    ----
    power_density : np.ndarray
        形状为 ``(n_sources, n_lat, n_lon)`` 的功率密度栈，单位 W/m²。
    top_k : int
        需要输出的主导辐射源数量。

    返回
    ----
    tuple[np.ndarray, np.ndarray]
        ``(total, indices)``：
        - ``total`` 为各网格点总功率密度 (W/m²)
        - ``indices`` 为 Top-K 源的索引矩阵，可用于回查源 ID

    说明
    ----
    该函数支持服务化后提供“主贡献源诊断”，便于在线接口返回影响最大的发射源。
    """
    total = np.sum(power_density, axis=0)
    if top_k <= 0:
        return total, np.empty((0,) + total.shape, dtype=int)
    top_indices = np.argsort(power_density, axis=0)[-top_k:][::-1]
    return total, top_indices
