"""Pydantic models describing the compute API.

所有坐标均采用 WGS84（纬度/经度单位为度），高度以米表示，频率以 MHz 表示，功率以 dBm 或线性瓦特
表示。该约定便于 REST/CLI 调用统一，并为后续服务化部署提供清晰的数据契约。
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator


class LatLon(BaseModel):
    """Geographic coordinate pair in WGS84 (单位: 度)."""

    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class Region(BaseModel):
    """Polygonal region of interest.

    Attributes
    ----------
    crs : Literal["WGS84"]
        坐标参考系，固定为 WGS84。
    polygon : list[LatLon]
        区域顶点序列，按顺时针或逆时针给出，至少包含 3 个点。
    """

    crs: Literal["WGS84"] = "WGS84"
    polygon: List[LatLon]

    @validator("polygon")
    def validate_polygon(cls, value: List[LatLon]) -> List[LatLon]:
        if len(value) < 3:
            raise ValueError("polygon must contain at least 3 vertices")

        area = 0.0
        for idx, current in enumerate(value):
            nxt = value[(idx + 1) % len(value)]
            area += current.lon * nxt.lat - nxt.lon * current.lat

        if area > 0.0:
            value = list(reversed(value))
        return value


class GridSpec(BaseModel):
    """Sampling grid specification.

    Attributes
    ----------
    resolution_deg : float
        网格角分辨率（度）。值越小网格越密。
    alt_m : float
        网格高度，单位米。
    """

    resolution_deg: float = Field(0.01, gt=0)
    alt_m: float


class Atmosphere(BaseModel):
    """Atmospheric conditions used in attenuation models.

    Attributes
    ----------
    gas_loss : float | Literal["auto"]
        气体衰减（dB/km），或 ``"auto"`` 表示使用经验模型。
    rain_rate_mmph : float
        降雨率，单位毫米/小时 (mm/h)。
    fog_lwc_gm3 : float
        雾液态含水量，单位克/立方米 (g/m³)。
    """

    gas_loss: float | Literal["auto"] = "auto"
    rain_rate_mmph: float = Field(0.0, ge=0.0)
    fog_lwc_gm3: float = Field(0.0, ge=0.0)


class Propagation(BaseModel):
    """Propagation model selector."""

    model: Literal["free_space", "two_ray_flat"] = "free_space"


class Earth(BaseModel):
    """Earth model parameters (用于折射近似)."""

    k_factor: float = Field(4.0 / 3.0, gt=0.0)


class Environment(BaseModel):
    """Combined environment configuration for propagation calculations."""

    propagation: Propagation = Propagation()
    atmosphere: Atmosphere = Atmosphere()
    earth: Earth = Earth()


class AntennaPattern(BaseModel):
    """Simplified antenna pattern description.

    Attributes
    ----------
    hpbw_deg, vpbw_deg : float
        水平/垂直半功率角 (degree)。
    sidelobe_template : str
        预设副瓣模板名称，决定扫描外方向的默认增益。
    """

    type: Literal["simplified_directional"] = "simplified_directional"
    hpbw_deg: float = Field(..., gt=0)
    vpbw_deg: float = Field(..., gt=0)
    sidelobe_template: Literal["MIL-STD-20", "RCS-13", "Radar-Narrow-25", "Comm-Omni-Back-10"] = "MIL-STD-20"


class ScanSpec(BaseModel):
    """Antenna scanning behaviour.

    Attributes
    ----------
    mode : str
        扫描模式：``none``（固定）、``circular``（全向旋转）、``sector``（扇区往返）。
    rpm : float
        转速（每分钟转数）。用于未来的时间分辨支持。
    sector_deg : float
        扇区宽度，单位度。
    """

    mode: Literal["none", "circular", "sector"] = "none"
    rpm: float = Field(0.0, ge=0.0)
    sector_deg: float = Field(0.0, ge=0.0, le=360.0)


class Antenna(BaseModel):
    """Complete antenna configuration including pointing and scanning."""

    pattern: AntennaPattern
    pointing_az_deg: float = 0.0
    pointing_el_deg: float = 0.0
    scan: ScanSpec = ScanSpec()

    @root_validator(pre=True)
    def extract_pointing(cls, values: dict) -> dict:
        pointing = values.pop("pointing", None)
        if pointing:
            values.setdefault("pointing_az_deg", pointing.get("az_deg", 0.0))
            values.setdefault("pointing_el_deg", pointing.get("el_deg", 0.0))
        return values


class Emission(BaseModel):
    """Emission characteristics of a source.

    Attributes
    ----------
    eirp_dBm : float
        等效各向同性辐射功率，单位 dBm（相对于 1 mW 的对数尺度）。
    center_freq_MHz : float
        中心频率，单位 MHz。
    bandwidth_MHz : float
        带宽，单位 MHz。
    polarization : str
        极化方式：水平(H)、垂直(V)、右旋圆极化(RHCP)、左旋圆极化(LHCP)。
    duty_cycle : float
        占空比，范围 0～1。表示平均开机时间占比，在峰值评估中常取 1。
    """

    eirp_dBm: float
    center_freq_MHz: float = Field(..., gt=0)
    bandwidth_MHz: float = Field(..., gt=0)
    polarization: Literal["H", "V", "RHCP", "LHCP"]
    duty_cycle: float = Field(1.0, ge=0.0, le=1.0)


class SourcePosition(BaseModel):
    """Geodetic position of a source (lat/lon in degrees, altitude in metres)."""

    lat: float
    lon: float
    alt_m: float


class Source(BaseModel):
    """Complete source definition used by the compute engine and service interfaces."""

    id: str
    type: Literal["radar", "comm", "jammer", "other"] = "other"
    position: SourcePosition
    emission: Emission
    antenna: Antenna


class Band(BaseModel):
    """Frequency band definition (单位: MHz / kHz)."""

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
    """Compute workload constraints to guard server resources."""

    max_sources: int = Field(50, gt=0)
    max_region_km: float = Field(1000.0, gt=0)
    max_grid_points: int = Field(200000, gt=0)

    @validator("max_region_km")
    def validate_max_region_km(cls, value: float) -> float:
        if value > 1000.0:
            raise ValueError("max_region_km cannot exceed 1000 km")
        return value

    @validator("max_grid_points")
    def validate_max_grid_points(cls, value: int) -> int:
        if value > 200000:
            raise ValueError("max_grid_points cannot exceed 200000")
        return value


class ComputeRequest(BaseModel):
    """Top-level request payload accepted by CLI/REST 服务.

    字段涵盖区域、网格、环境、频段、源列表等信息，所有单位与文档保持一致（度、米、km、MHz、dBm）。
    """

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
