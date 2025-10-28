import numpy as np

from emenv.antenna import peak_gain_dBi
from emenv.api_models import Antenna, AntennaPattern, ScanSpec


def test_peak_gain_circular_scan_returns_peak():
    antenna = Antenna(
        pattern=AntennaPattern(hpbw_deg=3.0, vpbw_deg=3.0),
        pointing_az_deg=0.0,
        pointing_el_deg=0.0,
        scan=ScanSpec(mode="circular", rpm=12.0, sector_deg=360.0),
    )
    bearing = np.array([[10.0]])
    elev = np.array([[0.0]])
    gain = peak_gain_dBi(bearing, elev, antenna)
    assert np.allclose(gain, 0.0)


def test_peak_gain_sector_off_axis_uses_sidelobe():
    antenna = Antenna(
        pattern=AntennaPattern(hpbw_deg=3.0, vpbw_deg=3.0),
        pointing_az_deg=0.0,
        pointing_el_deg=0.0,
        scan=ScanSpec(mode="sector", rpm=12.0, sector_deg=60.0),
    )
    bearing = np.array([[100.0]])
    elev = np.array([[0.0]])
    gain = peak_gain_dBi(bearing, elev, antenna)
    assert np.all(gain <= 0.0)
