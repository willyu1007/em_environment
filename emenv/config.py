"""Configuration constants for the EM environment estimation engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:
    """Default numerical configuration."""

    grid_resolution_deg: float = 0.01
    influence_buffer_km: float = 200.0
    threshold_dbuv_per_m: float = 40.0
    top_k: int = 3
    k_factor: float = 4.0 / 3.0


@dataclass(frozen=True)
class AtmosphereDefaults:
    """Default atmospheric attenuation parameters."""

    gas_loss_mode: str = "auto"
    rain_rate_mmph: float = 0.0
    fog_lwc_gm3: float = 0.0


ENGINE_CONFIG = EngineConfig()
ATMOSPHERE_DEFAULTS = AtmosphereDefaults()
