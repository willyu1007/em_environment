"""FastAPI application exposing the compute engine."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from ..api_models import ComputeRequest
from ..service import ComputeService

app = FastAPI(title="EM Environment Service", version="0.1.0")
_service = ComputeService()


class ComputeResponse(BaseModel):
    message: str = "accepted"
    bands: list[str]


class QueryRequest(BaseModel):
    lat: float
    lon: float
    band: str


class QueryResponse(BaseModel):
    band: str
    field_strength_dbuv_per_m: float
    power_density_W_m2: float
    top_contributors: list[int]


def get_service() -> ComputeService:
    return _service


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/compute", response_model=ComputeResponse)
def compute(request: ComputeRequest, service: ComputeService = Depends(get_service)) -> ComputeResponse:
    result = service.run_compute(request)
    bands = list(result.band_results.keys())
    return ComputeResponse(bands=bands)


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, service: ComputeService = Depends(get_service)) -> QueryResponse:
    result = service.query_point(payload.lat, payload.lon, payload.band)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not available for the given parameters.")
    return QueryResponse(
        band=result.band,
        field_strength_dbuv_per_m=result.field_strength_dbuv_per_m,
        power_density_W_m2=result.power_density_W_m2,
        top_contributors=result.top_contributors,
    )
