"""Source combination utilities."""

from __future__ import annotations

import numpy as np

Z0 = 377.0  # Free-space impedance


def eirp_dBm_to_W(eirp_dBm: np.ndarray) -> np.ndarray:
    """Convert EIRP from dBm to Watts."""
    return 10.0 ** ((np.asarray(eirp_dBm) - 30.0) / 10.0)


def power_density_W_m2(eirp_W: np.ndarray, gain_lin: np.ndarray, r_m: np.ndarray, additional_loss_dB: np.ndarray) -> np.ndarray:
    """Compute power density at range with optional additional attenuation."""
    fs_term = (eirp_W[..., None, None] * gain_lin) / (4.0 * np.pi * np.maximum(r_m, 1.0) ** 2)
    return fs_term * 10.0 ** (-np.asarray(additional_loss_dB) / 10.0)


def field_strength_dBuV_per_m(power_density_W_m2: np.ndarray) -> np.ndarray:
    """Convert power density to electric field strength."""
    e_v_per_m = np.sqrt(Z0 * np.maximum(power_density_W_m2, 1e-30))
    return 20.0 * np.log10(e_v_per_m) + 120.0


def sum_sources_and_topk(power_density: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    """Sum power densities and return indices of the top-k contributing sources."""
    total = np.sum(power_density, axis=0)
    if top_k <= 0:
        return total, np.empty((0,) + total.shape, dtype=int)
    top_indices = np.argsort(power_density, axis=0)[-top_k:][::-1]
    return total, top_indices
