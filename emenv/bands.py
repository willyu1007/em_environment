"""Band utilities."""

from __future__ import annotations

import numpy as np

from .api_models import Band


def band_center_freq_MHz(band: Band) -> float:
    """Compute the center frequency for a band entry."""
    return 0.5 * (band.f_min_MHz + band.f_max_MHz)


def bands_center_array(bands: list[Band]) -> np.ndarray:
    """Return an array of center frequencies for provided bands."""
    return np.array([band_center_freq_MHz(b) for b in bands], dtype=float)
