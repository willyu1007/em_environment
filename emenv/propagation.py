"""Propagation loss models."""

from __future__ import annotations

import numpy as np

from .api_models import Environment


def fspl_dB(f_MHz: np.ndarray, r_km: np.ndarray) -> np.ndarray:
    """Free-space path loss (Friis) in dB."""
    return 32.45 + 20.0 * np.log10(np.maximum(f_MHz, 1e-6)) + 20.0 * np.log10(np.maximum(r_km, 1e-6))


def two_ray_flat_loss_dB(
    f_MHz: np.ndarray,
    horizontal_km: np.ndarray,
    tx_alt_m: np.ndarray,
    rx_alt_m: np.ndarray,
) -> np.ndarray:
    """Two-ray ground reflection loss approximation with phase interference."""
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
    """Crude approximation of atmospheric, rain, and fog attenuation."""
    freq_GHz = np.maximum(f_MHz, 1e-6) / 1000.0
    gas_base = 0.001 if gas_loss_mode == "auto" else float(gas_loss_mode)
    gas_loss = gas_base * (1.0 + 0.1 * freq_GHz**1.2)
    rain_loss = 0.0001 * rain_rate_mmph * freq_GHz**0.8
    fog_loss = 0.0002 * fog_lwc_gm3 * freq_GHz**2
    return gas_loss + rain_loss + fog_loss


def total_extra_loss_dB(f_MHz: np.ndarray, r_km: np.ndarray, environment: Environment) -> np.ndarray:
    """Total additional attenuation accumulated along the path."""
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
    """Loss relative to ideal FSPL plus additional atmospheric attenuation."""
    base_adjustment = np.zeros_like(f_MHz, dtype=float)

    if environment.propagation.model == "two_ray_flat":
        two_ray_loss = two_ray_flat_loss_dB(f_MHz, horizontal_km, tx_alt_m, rx_alt_m)
        fspl_loss = fspl_dB(f_MHz, slant_km)
        base_adjustment = two_ray_loss - fspl_loss

    extra = total_extra_loss_dB(f_MHz, slant_km, environment)
    return base_adjustment + extra
