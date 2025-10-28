"""Pydantic models describing the compute API."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


class LatLon(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class Region(BaseModel):
    crs: Literal["WGS84"] = "WGS84"
    polygon: List[LatLon]

    @validator("polygon")
    def validate_polygon(cls, value: List[LatLon]) -> List[LatLon]:
        if len(value) < 3:
            raise ValueError("polygon must contain at least 3 vertices")
        return value


class GridSpec(BaseModel):
    resolution_deg: float = Field(0.01, gt=0)
    alt_m: float


class Atmosphere(BaseModel):
    gas_loss: float | Literal["auto"] = "auto"
    rain_rate_mmph: float = Field(0.0, ge=0.0)
    fog_lwc_gm3: float = Field(0.0, ge=0.0)


class Propagation(BaseModel):
    model: Literal["free_space", "two_ray_flat"] = "free_space"


class Earth(BaseModel):
    k_factor: float = Field(4.0 / 3.0, gt=0.0)


class Environment(BaseModel):
    propagation: Propagation = Propagation()
    atmosphere: Atmosphere = Atmosphere()
    earth: Earth = Earth()


class AntennaPattern(BaseModel):
    type: Literal["simplified_directional"] = "simplified_directional"
    hpbw_deg: float = Field(..., gt=0)
    vpbw_deg: float = Field(..., gt=0)
    sidelobe_template: Literal["MIL-STD-20", "RCS-13", "Radar-Narrow-25", "Comm-Omni-Back-10"] = "MIL-STD-20"


class ScanSpec(BaseModel):
    mode: Literal["none", "circular", "sector"] = "none"
    rpm: float = Field(0.0, ge=0.0)
    sector_deg: float = Field(0.0, ge=0.0, le=360.0)


class Antenna(BaseModel):
    pattern: AntennaPattern
    pointing_az_deg: float = 0.0
    pointing_el_deg: float = 0.0
    scan: ScanSpec = ScanSpec()


class Emission(BaseModel):
    eirp_dBm: float
    center_freq_MHz: float = Field(..., gt=0)
    bandwidth_MHz: float = Field(..., gt=0)
    polarization: Literal["H", "V", "RHCP", "LHCP"]
    duty_cycle: float = Field(1.0, ge=0.0, le=1.0)


class SourcePosition(BaseModel):
    lat: float
    lon: float
    alt_m: float


class Source(BaseModel):
    id: str
    type: Literal["radar", "comm", "jammer", "other"] = "other"
    position: SourcePosition
    emission: Emission
    antenna: Antenna


class Band(BaseModel):
    name: str
    f_min_MHz: float = Field(..., gt=0)
    f_max_MHz: float = Field(..., gt=0)
    ref_bw_kHz: float = Field(1000.0, gt=0)

    @validator("f_max_MHz")
    def validate_band_limits(cls, v: float, values: dict) -> float:
        f_min = values.get("f_min_MHz")
        if f_min is not None and v <= f_min:
            raise ValueError("f_max_MHz must be greater than f_min_MHz")
        return v


class Limits(BaseModel):
    max_sources: int = Field(50, gt=0)
    max_region_km: float = Field(200.0, gt=0)


class ComputeRequest(BaseModel):
    region: Region
    grid: GridSpec
    influence_buffer_km: float = Field(200.0, ge=0.0)
    environment: Environment = Environment()
    bands: List[Band] = Field(default_factory=list)
    metric: Literal["E_field_dBuV_per_m"] = "E_field_dBuV_per_m"
    combine_sources: Literal["power_sum"] = "power_sum"
    temporal_agg: Literal["peak"] = "peak"
    limits: Limits = Limits()
    sources: List[Source] = Field(default_factory=list)

    @validator("sources")
    def check_source_count(cls, sources: List[Source], values: dict) -> List[Source]:
        limits: Limits = values.get("limits", Limits())
        if len(sources) > limits.max_sources:
            raise ValueError("number of sources exceeds configured limits")
        return sources
