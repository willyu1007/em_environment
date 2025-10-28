from emenv.api_models import (
    Antenna,
    AntennaPattern,
    Band,
    ComputeRequest,
    GridSpec,
    LatLon,
    Region,
    ScanSpec,
    Source,
    SourcePosition,
    Emission,
)
from emenv.engine import ComputeEngine


def build_simple_request() -> ComputeRequest:
    region = Region(
        polygon=[
            LatLon(lat=34.0, lon=118.0),
            LatLon(lat=34.0, lon=118.2),
            LatLon(lat=33.8, lon=118.2),
            LatLon(lat=33.8, lon=118.0),
        ]
    )
    grid = GridSpec(resolution_deg=0.05, alt_m=0.0)
    band = Band(name="S", f_min_MHz=2000.0, f_max_MHz=4000.0)
    source = Source(
        id="src1",
        position=SourcePosition(lat=33.9, lon=118.1, alt_m=50.0),
        emission=Emission(
            eirp_dBm=90.0,
            center_freq_MHz=3200.0,
            bandwidth_MHz=10.0,
            polarization="H",
            duty_cycle=1.0,
        ),
        antenna=Antenna(
            pattern=AntennaPattern(hpbw_deg=3.0, vpbw_deg=3.0),
            scan=ScanSpec(mode="circular", rpm=12.0, sector_deg=360.0),
        ),
    )
    return ComputeRequest(region=region, grid=grid, bands=[band], sources=[source])


def test_engine_basic_compute():
    request = build_simple_request()
    engine = ComputeEngine()
    result = engine.compute(request)

    assert "S" in result.band_results
    band_result = result.band_results["S"]
    assert band_result.field_strength_dbuv_per_m.shape == result.grid.shape
    expected_top = min(3, len(result.source_ids))
    assert band_result.topk_indices.shape[0] == expected_top
    assert band_result.topk_power_W_m2.shape == (expected_top,) + result.grid.shape
    assert band_result.topk_fraction.shape == (expected_top,) + result.grid.shape
