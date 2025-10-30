# EM 可视化（Vue3 独立版）

本目录提供一个与现有后端/Streamlit 解耦的前端，可在浏览器本地预览 GeoTIFF 栅格与 Parquet Top‑K 诊断。

## 功能
- 加载并渲染电场强度 GeoTIFF（WGS‑84）
- 解析 Parquet（Top‑K），展示 Top‑1 标注示例
- 颜色渐变可调，OSM 底图

## 运行
1. 安装 Node.js 18+
2. 目录内执行：
```bash
npm install
npm run dev
```
3. 打开输出的本地地址（默认 http://localhost:5173）

## 使用
- 在“地图”页选择 `*_field_strength.tif` 与 `*_topk.parquet` 文件（可从 `outputs/*/` 复制）
- 地图自动渲染栅格热力；加载 Parquet 后绘制 Top‑1 圈点并显示 `source_id`

## 技术栈
- Vue 3 + Vite + TypeScript
- Leaflet + georaster + georaster-layer-for-leaflet + geotiff
- parquet-wasm（浏览器解码 Parquet）

## 与现有工程的关系
- 该前端完全放置于 `web-visualizer/`，不修改/依赖现有 Python 代码，可独立运行

---
如需接入 REST 接口（替代文件选择），可后续新增环境变量与代理配置。

