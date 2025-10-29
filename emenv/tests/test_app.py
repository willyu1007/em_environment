import json
import sys

import numpy as np
from fastapi.testclient import TestClient

from emenv.app.cli import main as cli_main
from emenv.app.rest import app


def _sample_request_dict() -> dict:
    return {
        "region": {
            "crs": "WGS84",
            "polygon": [
                {"lat": 34.0, "lon": 118.0},
                {"lat": 34.0, "lon": 118.2},
                {"lat": 33.8, "lon": 118.2},
                {"lat": 33.8, "lon": 118.0},
            ],
        },
        "grid": {"resolution_deg": 0.05, "alt_m": 0.0},
        "influence_buffer_km": 200,
        "environment": {
            "propagation": {"model": "free_space"},
            "atmosphere": {"gas_loss": "auto", "rain_rate_mmph": 0, "fog_lwc_gm3": 0},
            "earth": {"k_factor": 1.3333333333},
        },
        "bands": [
            {"name": "S", "f_min_MHz": 2000.0, "f_max_MHz": 4000.0, "ref_bw_kHz": 1000},
        ],
        "metric": "E_field_dBuV_per_m",
        "combine_sources": "power_sum",
        "temporal_agg": "peak",
        "limits": {"max_sources": 50, "max_region_km": 200},
        "sources": [
            {
                "id": "src1",
                "type": "radar",
                "position": {"lat": 33.9, "lon": 118.1, "alt_m": 50.0},
                "emission": {
                    "eirp_dBm": 90.0,
                    "center_freq_MHz": 3200.0,
                    "bandwidth_MHz": 10.0,
                    "polarization": "H",
                    "duty_cycle": 1.0,
                },
                "antenna": {
                    "pattern": {
                        "type": "simplified_directional",
                        "hpbw_deg": 3.0,
                        "vpbw_deg": 3.0,
                        "sidelobe_template": "MIL-STD-20",
                    },
                    "pointing": {"az_deg": 0.0, "el_deg": 0.0},
                    "scan": {"mode": "circular", "rpm": 12.0, "sector_deg": 360.0},
                },
            }
        ],
    }


def test_cli_generates_outputs(tmp_path, monkeypatch, capsys):
    request_dict = _sample_request_dict()
    input_path = tmp_path / "request.json"
    input_path.write_text(json.dumps(request_dict), encoding="utf-8")
    output_dir = tmp_path / "outputs"

    monkeypatch.setattr(sys, "argv", ["emenv-cli", str(input_path), "--output-dir", str(output_dir)])
    cli_main()

    captured = capsys.readouterr()
    assert "Computed bands" in captured.out
    geotiff = output_dir / "S" / "S_field_strength.tif"
    parquet = output_dir / "S" / "S_topk.parquet"
    assert geotiff.exists()
    assert parquet.exists()


def test_rest_compute_and_query():
    client = TestClient(app)
    payload = _sample_request_dict()

    resp = client.post("/compute", json=payload)
    assert resp.status_code == 200
    assert resp.json()["bands"] == ["S"]

    query_payload = {"lat": 33.9, "lon": 118.1, "alt_m": 0.0, "band": "S"}
    query_resp = client.post("/query", json=query_payload)
    assert query_resp.status_code == 200
    result = query_resp.json()
    assert result["band"] == "S"
    assert result["alt_m"] == 0.0
    assert np.isfinite(result["field_strength_dbuv_per_m"])


def test_rest_query_alt_mismatch():
    client = TestClient(app)
    payload = _sample_request_dict()
    client.post("/compute", json=payload)

    query_payload = {"lat": 33.9, "lon": 118.1, "alt_m": 100.0, "band": "S"}
    query_resp = client.post("/query", json=query_payload)
    assert query_resp.status_code == 404
