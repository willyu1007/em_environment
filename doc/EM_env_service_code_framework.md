# 电磁态势估算服务 —— 云顶代码框架文档（v1）
> 面向代码生成模型（如 OpenAI Codex、GPT-4/5 代码助手）直接产出代码骨架与关键实现。  
> 语言建议：**Python 3.10+**（数值计算与服务端实现成熟、生态丰富）。

---

## 0. 关键设定（已拍板）
- 单高度切片（AMSL，单位 m）。
- 网格分辨率：默认 **0.01°**。
- 传播：默认 **Free Space**；可选 **Two-Ray Flat**（开关，默认关闭）。
- 大气/雨雾：近似附加损耗（可关，默认开，参数见前置规范）。
- 有效地球半径：**k = 4/3**（固定）。
- 天线：HPBW 高斯主瓣 + **副瓣模板**（4 种，默认 `MIL-STD-20`）。
- 扫描时间聚合：**peak**（主瓣扫过那一刻的峰值）。
- 频段：VHF/UHF/L/S/C/X/Ku/Ka，统一参考带宽 **1 MHz**；**Ka 段不做 3 点采样**。
- 叠加：功率密度域求和（power_sum）。
- 阈值裁剪：**40 dBμV/m** 以下可裁剪为 no-data（可配置）。
- Top-k 贡献：**k=3 固定**（用于诊断输出）。
- 规模：最大源数 50；区域尺寸约 200×200 km；输出不考虑遮蔽/绕射。

---

## 1. 代码工程结构（建议）
```text
emenv/
  ├─ emenv/                          # 核心库
  │   ├─ __init__.py
  │   ├─ config.py                   # 配置模型与默认值
  │   ├─ geo.py                      # 地理/测地工具（球面距离、方位）
  │   ├─ grid.py                     # 网格生成、瓦片切分、索引
  │   ├─ antenna.py                  # 天线增益模型、模板、扫描峰值逻辑
  │   ├─ propagation.py              # FSPL、Two-Ray-Flat、大气/雨雾损耗
  │   ├─ combine.py                  # 源贡献叠加、Top-k 统计
  │   ├─ bands.py                    # 频段/参考带宽处理
  │   ├─ engine.py                   # 主计算引擎（分块、向量化、缓存）
  │   ├─ io_raster.py                # GeoTIFF/NetCDF 写出（可选 Parquet）
  │   ├─ api_models.py               # Pydantic I/O 数据模型（REST/CLI 共用）
  │   ├─ service.py                  # 查询接口：经纬度→值，按源分解
  │   └─ utils.py                    # 单位换算、数值稳定、LUT 缓存
  │
  ├─ app/
  │   ├─ __init__.py
  │   ├─ rest.py                     # FastAPI：/compute, /query, /health
  │   └─ cli.py                      # 命令行：离线批处理/生成瓦片
  │
  ├─ tests/                          # 单元/集成测试
  │   ├─ test_geo.py
  │   ├─ test_antenna.py
  │   ├─ test_propagation.py
  │   ├─ test_engine.py
  │   └─ data/fixtures.json
  │
  ├─ examples/
  │   ├─ input_spec.json             # 示例输入（可直接运行）
  │   └─ run_local.md                # 本地运行指南
  │
  ├─ pyproject.toml                  # 依赖（pydantic, numpy, numba, rasterio, xarray, fastapi, uvicorn）
  └─ README.md
```

---

## 2. 关键依赖（建议）
- **numpy**（向量化）、**numba**（可选 JIT 加速）、**pydantic**（数据模型）、**fastapi/uvicorn**（REST）。
- **rasterio**（GeoTIFF）、**xarray/netCDF4**（NetCDF）、**pyproj** 或自写测地计算（本框架内置球面测地）。
- 可选：**h3**（空间索引，若不引入，使用自写 R 树或简单球面窗口筛选）。

---

## 3. 数据模型（Pydantic 摘要）
```python
# emenv/api_models.py
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class LatLon(BaseModel):
    lat: float
    lon: float

class Region(BaseModel):
    crs: Literal["WGS84"] = "WGS84"
    polygon: List[LatLon]  # 顺时针，>=3

class GridSpec(BaseModel):
    resolution_deg: float = 0.01
    alt_m: float  # 单高度切片（AMSL）

class Atmosphere(BaseModel):
    gas_loss: float | Literal["auto"] = "auto"
    rain_rate_mmph: float = 0.0
    fog_lwc_gm3: float = 0.0

class Propagation(BaseModel):
    model: Literal["free_space", "two_ray_flat"] = "free_space"

class Earth(BaseModel):
    k_factor: float = 4/3  # 固定

class Environment(BaseModel):
    propagation: Propagation = Propagation()
    atmosphere: Atmosphere = Atmosphere()
    earth: Earth = Earth()

class AntennaPattern(BaseModel):
    type: Literal["simplified_directional"] = "simplified_directional"
    hpbw_deg: float
    vpbw_deg: float
    sidelobe_template: Literal["MIL-STD-20", "RCS-13", "Radar-Narrow-25", "Comm-Omni-Back-10"] = "MIL-STD-20"

class ScanSpec(BaseModel):
    mode: Literal["none", "circular", "sector"] = "none"
    rpm: float = 0.0
    sector_deg: float = 0.0  # circular时=360

class Antenna(BaseModel):
    pattern: AntennaPattern
    pointing_az_deg: float = 0.0
    pointing_el_deg: float = 0.0
    scan: ScanSpec = ScanSpec()

class Emission(BaseModel):
    eirp_dBm: float
    center_freq_MHz: float
    bandwidth_MHz: float
    polarization: Literal["H", "V", "RHCP", "LHCP"] = "H"
    duty_cycle: float = 1.0  # peak聚合下不启用平均

class Source(BaseModel):
    id: str
    type: Literal["radar", "comm", "jammer", "other"] = "radar"
    position: LatLon
    alt_m: float
    emission: Emission
    antenna: Antenna

class Band(BaseModel):
    name: str
    f_min_MHz: float
    f_max_MHz: float
    ref_bw_kHz: float = 1000.0

class Limits(BaseModel):
    max_sources: int = 50
    max_region_km: float = 200.0

class ComputeRequest(BaseModel):
    region: Region
    grid: GridSpec
    influence_buffer_km: float = 200.0
    environment: Environment = Environment()
    bands: List[Band]
    metric: Literal["E_field_dBuV_per_m"] = "E_field_dBuV_per_m"
    combine_sources: Literal["power_sum"] = "power_sum"
    temporal_agg: Literal["peak"] = "peak"
    limits: Limits = Limits()
    sources: List[Source]
    threshold_dbuv_per_m: float = 40.0  # 阈值裁剪
    topk_contrib: int = 3               # 固定3，可在校验中强制为3

class QueryRequest(BaseModel):
    lat: float
    lon: float
    alt_m: float
    band: str
```
> 说明：`Source.position` 为经纬度，`alt_m` 单独字段（AMSL）。

---

## 4. 算法实现要点（伪代码级）

### 4.1 球面测地（geo.py）
```python
def haversine_km(lat1, lon1, lat2, lon2) -> float: ...
def fwd_azimuth_deg(lat1, lon1, lat2, lon2) -> float: ...
# k=4/3 在 two-ray 几何/仰角估算时使用
```

### 4.2 天线增益（antenna.py）
**副瓣模板（dBi 地板/包络）**
```python
SL_TEMPLATES = {
  "MIL-STD-20": lambda off_axis_deg: -20.0,
  "RCS-13":     lambda off_axis_deg: -13.0 if off_axis_deg < 10 else -20.0,
  "Radar-Narrow-25": lambda off_axis_deg: -20.0 if off_axis_deg < 10 else -25.0,
  "Comm-Omni-Back-10": lambda off_axis_deg: -10.0
}
```

**主瓣高斯近似**（分轴，取较小值）：
```python
def mainlobe_gain_dBi(delta_az_deg, delta_el_deg, hpbw_deg, vpbw_deg, g_peak_dBi=0.0):
    k = 4.0 * np.log(2.0)
    gh = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_az_deg / hpbw_deg)**2
    gv = g_peak_dBi - 10.0 * np.log10(np.e) * k * (delta_el_deg / vpbw_deg)**2
    return min(gh, gv)
```

**扫描峰值逻辑（peak）**：
```python
def peak_gain_dBi(point_bearing_deg, point_elev_deg, antenna: Antenna):
    if in_scan_coverage(point_bearing_deg, antenna.scan):
        return 0.0  # 近似主瓣峰值
    off_az = angular_diff_deg(point_bearing_deg, antenna.pointing_az_deg)
    off_el = point_elev_deg - antenna.pointing_el_deg
    g_mb = mainlobe_gain_dBi(off_az, off_el, antenna.pattern.hpbw_deg, antenna.pattern.vpbw_deg, 0.0)
    g_sl = SL_TEMPLATES[antenna.pattern.sidelobe_template](abs(off_az))
    return max(g_mb, g_sl)
```

### 4.3 传播（propagation.py）
```python
def fspl_dB(f_MHz, r_km):
    return 32.45 + 20*np.log10(f_MHz) + 20*np.log10(np.maximum(r_km, 1e-6))
# two_ray_flat: 直射+反射，近场下限 r_min=10*lambda，相位平滑；H/V 反射系数近似
```

### 4.4 大气/雨雾（附加损耗 dB）
```python
def atmos_loss_dB_per_km(f_MHz, rain_rate_mmph, fog_lwc_gm3, gas="auto") -> float: ...
def total_extra_loss_dB(f_MHz, r_km, env): return atmos_loss_dB_per_km(...) * r_km
```

### 4.5 EIRP→电场 & 叠加（combine.py）
```python
Z0 = 377.0
def eirp_dBm_to_W(eirp_dBm): return 10**((eirp_dBm-30)/10)
def power_density_W_m2(eirp_W, gain_lin, r_m, extra_loss_dB):
    return (eirp_W * gain_lin) / (4*np.pi*r_m**2) * 10**(-extra_loss_dB/10)
def field_strength_dBuV_per_m(S_W_m2):
    E_V_m = np.sqrt(Z0 * S_W_m2); return 20*np.log10(np.maximum(E_V_m, 1e-15)) + 120.0
def sum_sources_and_topk(S_list):
    S_tot = np.sum(S_list, axis=0); idx = np.argsort(S_list, axis=0)[-3:][::-1]; return S_tot, idx
```

---

## 5. 主计算引擎（engine.py）伪代码
```python
def compute_tiles(req: ComputeRequest):
    # 1) 预处理
    tiles = build_tiles(req.region, req.grid.resolution_deg)
    srcs = filter_sources_by_buffer(req.sources, req.region, req.influence_buffer_km)
    bands = center_freqs(req.bands)  # 取中心频率

    # 2) 遍历瓦片
    for tile in tiles:
        latlon = tile.latlon_mesh()  # (H,W,2)
        geom = geom_from_sources(srcs, latlon, req.grid.alt_m, k_factor=4/3)  # r_km, bearing, elev

        for band in bands:
            f = band.center_MHz
            gains_dBi = antenna_peak_or_offaxis(srcs, geom.bearing_deg, geom.elev_deg)  # (Nsrc,H,W)
            fspl = fspl_dB(f, geom.r_km)                                               # (Nsrc,H,W)
            extra = total_extra_loss_dB(f, geom.r_km, req.environment)

            eirp_W = eirp_vector(srcs)[:,None,None]
            S = power_density_W_m2(eirp_W, 10**(gains_dBi/10), geom.r_km*1000, fspl+extra)

            S_tot, topk_idx = sum_sources_and_topk(S)
            E = field_strength_dBuV_per_m(S_tot)
            E[E < req.threshold_dbuv_per_m] = float("nan")

            write_raster(tile, band.name, E, meta=req)
            write_topk(tile, band.name, topk_idx, S, srcs)
```

---

## 6. REST 与 CLI（app/）
见骨架：`/compute`（提交计算）与 `/query`（返回值与 top-3）。CLI 支持批处理与本地测试。

---

## 7. 输出与索引
- 栅格：GeoTIFF，`nodata=NaN`，值 `E_field_dBμV/m`；每 band/瓦片一文件。
- 索引：`index.json` 记录瓦片范围、band、参数哈希、源清单快照。
- Top-3：`.jsonl` 或 `.parquet`，按像素记录 top-3 源 id 与贡献占比。

---

## 8. 测试与验收
- 覆盖 geo/antenna/propagation/engine 关键路径；
- 小区域与手算基准比对；
- Two-Ray 可先跳过，留后续任务。

---

## 9. 代码生成模型注意
- 严格按文件名与函数名创建模块；
- 先实现 FSPL 流程，Two-Ray 留 TODO；
- 必须包含阈值裁剪（40 dBμV/m）与 **Top-3 固定**；
- 使用 NumPy 向量化与分块写出，避免一次性占满内存。

—— 完 ——
