"""FastAPI application exposing the compute engine.

REST 接口统一复用 :class:`ComputeService`，方便未来部署为独立的服务进程。
输入输出单位遵循 ``api_models`` 中的约定：经纬度为度，高度为米，电场强度为 dBµV/m。
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..api_models import ComputeRequest
from ..service import ComputeService

app = FastAPI(title="EM Environment Service", version="0.1.0")

# 允许本地前端（vite 默认5173端口）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_service = ComputeService()


class ComputeResponse(BaseModel):
    """Response payload for the `/compute` endpoint."""

    message: str = "accepted"
    bands: list[str]


class QueryRequest(BaseModel):
    """Request payload for the `/query` endpoint (units: deg / m)."""

    lat: float
    lon: float
    alt_m: float
    band: str


class QueryResponse(BaseModel):
    """Point query response.

    field_strength_dbuv_per_m : dBµV/m
    power_density_W_m2 : W/m²
    """

    band: str
    alt_m: float
    field_strength_dbuv_per_m: float
    power_density_W_m2: float
    top_contributors: list[int]


def get_service() -> ComputeService:
    """Dependency provider returning the singleton compute service."""
    return _service


@app.get("/health")
def health() -> dict[str, str]:
    """Basic health probe for liveness checks."""
    return {"status": "ok"}


@app.post("/compute", response_model=ComputeResponse)
def compute(request: ComputeRequest, service: ComputeService = Depends(get_service)) -> ComputeResponse:
    """Trigger a compute job and return available band names."""
    result = service.run_compute(request)
    bands = list(result.band_results.keys())
    return ComputeResponse(bands=bands)


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, service: ComputeService = Depends(get_service)) -> QueryResponse:
    """Query a single location for field strength and contributing sources."""
    result = service.query_point(payload.lat, payload.lon, payload.alt_m, payload.band)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not available for the given parameters.")
    return QueryResponse(
        band=result.band,
        alt_m=result.alt_m,
        field_strength_dbuv_per_m=result.field_strength_dbuv_per_m,
        power_density_W_m2=result.power_density_W_m2,
        top_contributors=result.top_contributors,
    )
