# 电磁环境态势估算服务 —— 输入字段与使用说明（v1）

> 目标：在不考虑遮蔽/绕射的前提下，估算战场兴趣区域（200×200 km 量级）的电磁态势。精度取务实方案，重点体现主要辐射源（雷达/通信/压制）对区域内不同频段的场强影响。

## 总体约定
- 坐标系：WGS-84，经纬度（度）。
- 高度：**AMSL**（海拔，米）。仅支持**单一高度切片**一次计算。
- 默认分辨率：`grid.resolution_deg = 0.01`。
- 影响半径：`influence_buffer_km = 200`（用于包含区外源的贡献）。
- 频段参考带宽：**1 MHz**（`ref_bw_kHz = 1000`）。
- 强度指标：**E_field_dBuV_per_m**（在 `ref_bw_kHz` 上折算）。
- 传播模型：默认 `free_space`；可选 `two_ray_flat`（平坦地面两射线）。
- 折射系数：`k_factor = 4/3`（固定，不对外暴露）。
- 天线扫描聚合：**peak**（扫描主瓣扫过网格点时的瞬时峰值）。
- 源功率合并：`power_sum`（线性功率相加）。
- 不考虑遮蔽：不加载地形/建筑，不做 LOS/绕射判定。

---

## 输入字段
### 1) 区域与采样
```jsonc
{
  "region": {
    "crs": "WGS84",
    "polygon": [ { "lat": 0, "lon": 0 }, ... ] // 顺时针，禁止 holes
  },
  "grid": {
    "resolution_deg": 0.01,  // 默认
    "alt_m": 0               // 单一高度切片，AMSL，必填
  },
  "influence_buffer_km": 200 // 默认
}
```

### 2) 环境参数（仅衰减）
```jsonc
"environment": {
  "propagation": { "model": "free_space" },   // 可选 "two_ray_flat"
  "atmosphere": {
    "gas_loss": "auto",       // 按频率近似。可为数值(dB/km)覆盖
    "rain_rate_mmph": 0,      // 雨衰（近似）；默认0
    "fog_lwc_gm3": 0          // 雾衰（近似）；默认0
  },
  "earth": { "k_factor": 1.3333333333 }       // 固定4/3
}
```
> `two_ray_flat` 假设无限平坦地面，仅在开启时引入地面反射项。

### 3) 信号源（数组）
每个源：
```jsonc
{
  "id": "string",
  "type": "radar|comm|jammer|other",
  "position": { "lat": 0.0, "lon": 0.0, "alt_m": 0.0 }, // AMSL
  "emission": {
    "eirp_dBm": 95,                // 推荐直接给 EIRP
    "center_freq_MHz": 3200,
    "bandwidth_MHz": 10,
    "polarization": "H|V|RHCP|LHCP",
    "duty_cycle": 1.0              // 信息保留；peak 输出不做平均
  },
  "antenna": {
    "pattern": {
      "type": "simplified_directional",
      "hpbw_deg": 3.0,
      "vpbw_deg": 3.0,
      "sidelobe_template": "MIL-STD-20" // 见下表
    },
    "pointing": { "az_deg": 0.0, "el_deg": 0.0 },
    "scan": { "mode": "none|circular|sector", "rpm": 12, "sector_deg": 90 }
  }
}
```

### 4) 频段与指标
默认频段（可增删）：`VHF / UHF / L / S / C / X / Ku / Ka`，统一 `ref_bw_kHz = 1000`。
```jsonc
"bands": [
  { "name": "VHF", "f_min_MHz": 100, "f_max_MHz": 300,  "ref_bw_kHz": 1000 },
  { "name": "UHF", "f_min_MHz": 300, "f_max_MHz": 1000, "ref_bw_kHz": 1000 },
  { "name": "L",   "f_min_MHz": 1000,"f_max_MHz": 2000, "ref_bw_kHz": 1000 },
  { "name": "S",   "f_min_MHz": 2000,"f_max_MHz": 4000, "ref_bw_kHz": 1000 },
  { "name": "C",   "f_min_MHz": 4000,"f_max_MHz": 8000, "ref_bw_kHz": 1000 },
  { "name": "X",   "f_min_MHz": 8000,"f_max_MHz": 12000,"ref_bw_kHz": 1000 },
  { "name": "Ku",  "f_min_MHz": 12000,"f_max_MHz": 18000,"ref_bw_kHz": 1000 },
  { "name": "Ka",  "f_min_MHz": 26500,"f_max_MHz": 40000,"ref_bw_kHz": 1000 }
]
```
强度指标：`"metric": "E_field_dBuV_per_m"`。

### 5) 计算与聚合选项
```jsonc
"combine_sources": "power_sum",    // 线性功率相加
"temporal_agg": "peak"             // 扫描取峰值
```
规模约束（建议上限）：
```jsonc
"limits": { "max_sources": 50, "max_region_km": 200 }
```

### 6) 输出（占位，后续细化）
- **查询接口**：`query(lat, lon, alt_m, band)` → 返回场强及（可选）按源分解。
- **栅格产品**：按 `grid.resolution_deg × bands × 单高度切片` 输出（建议 GeoTIFF/NetCDF + 分块 Parquet）。

---

## 内置 sidelobe 模板
| 名称 | 特性（主瓣外包络，近似） | 适用场景 |
|---|---|---|
| `MIL-STD-20` *(默认)* | 主瓣外统一 −20 dB 地板 | 通用、快速估算 |
| `RCS-13` | 第一副瓣约 −13 dB，远副瓣不高于 −20 dB | 经典雷达近似 |
| `Radar-Narrow-25` | 第一副瓣 −20 dB，远副瓣 −25 dB | 窄波束雷达 |
| `Comm-Omni-Back-10` | 类全向，背瓣约 −10 dB | 通信/干扰器简化 |

> 模板以 HPBW 高斯主瓣近似为基础，仅约束主瓣外包络。需要更精细时，再支持 CSV 极化图导入。

---

## 示例（最小可运行）
```jsonc
{
  "region": {
    "crs": "WGS84",
    "polygon": [
      { "lat": 34.10, "lon": 118.10 },
      { "lat": 34.10, "lon": 119.20 },
      { "lat": 33.20, "lon": 119.20 },
      { "lat": 33.20, "lon": 118.10 }
    ]
  },
  "grid": { "resolution_deg": 0.01, "alt_m": 100 },
  "influence_buffer_km": 200,
  "environment": {
    "propagation": { "model": "free_space" },
    "atmosphere": { "gas_loss": "auto", "rain_rate_mmph": 0, "fog_lwc_gm3": 0 },
    "earth": { "k_factor": 1.3333333333 }
  },
  "bands": [
    { "name": "S", "f_min_MHz": 2000, "f_max_MHz": 4000, "ref_bw_kHz": 1000 },
    { "name": "X", "f_min_MHz": 8000, "f_max_MHz": 12000, "ref_bw_kHz": 1000 }
  ],
  "metric": "E_field_dBuV_per_m",
  "combine_sources": "power_sum",
  "temporal_agg": "peak",
  "limits": { "max_sources": 50, "max_region_km": 200 },
  "sources": [
    {
      "id": "radar_01",
      "type": "radar",
      "position": { "lat": 33.80, "lon": 118.60, "alt_m": 20 },
      "emission": { "eirp_dBm": 95, "center_freq_MHz": 3200, "bandwidth_MHz": 10, "polarization": "H", "duty_cycle": 0.1 },
      "antenna": {
        "pattern": { "type": "simplified_directional", "hpbw_deg": 3.0, "vpbw_deg": 3.0, "sidelobe_template": "MIL-STD-20" },
        "pointing": { "az_deg": 45, "el_deg": 0 },
        "scan": { "mode": "circular", "rpm": 12, "sector_deg": 360 }
      }
    }
  ]
}
```

## 输入校验要点（建议）
- `grid.alt_m` 为单值（米，AMSL）。
- `polygon` 顶点数 ≥ 3，顺时针；不允许自交。区域不宜超过约 200×200 km。
- 每个源必须提供 `position`、`emission.center_freq_MHz`、`emission.eirp_dBm`（或可推导等效 EIRP）、`antenna.pattern`。
- `bands` 中 `f_min_MHz < f_max_MHz`，`ref_bw_kHz > 0`，且统一默认 1000。
- `temporal_agg` 仅支持 `peak`（本版）。

—— 完 ——
