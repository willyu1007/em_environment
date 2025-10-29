# Agent 接入说明

## 目标
为后续代码生成或智能体协作提供快速上手入口，聚焦电磁态势估算服务的结构、数据约束与落盘能力。

## 关键模块
- `emenv.api_models`：规范输入/输出的 Pydantic 模型，支持规范中的 `antenna.pointing.{az_deg, el_deg}` 结构，并校验多边形、频段与源参数。
- `emenv.engine.ComputeEngine`：实现单高度切片、传播损耗（FSPL/Two-Ray）、Top‑3 贡献及阈值裁剪，并在阈值以下清空 Top‑3 统计。
- `emenv.service.ComputeService`：封装计算流程，支持缓存结果、点查询以及可选的磁盘写出。
- `emenv.io_raster`：GeoTIFF 栅格和 Top‑3 Parquet 导出工具。
- `emenv.app.rest` / `emenv.app.cli`：REST 与 CLI 入口；CLI 支持 `--output-dir` 直接产出成果文件。

## 计算流程摘要
1. `grid.create_grid` 根据区域多边形生成经纬度网格与掩码。
2. `engine.ComputeEngine` 按照频段中心频率迭代：
   - `geo` 模块计算源至网格的距离、方位与仰角；
   - `antenna.peak_gain_dBi` 处理扫描/副瓣模板获得定向增益；
   - `propagation.propagation_additional_loss_dB` 叠加两射线/大气附加损耗；
   - `combine` 模块完成功率密度合成、Top‑3 排序与场强换算；
   - 低于 40 dBμV/m 的像元被置为 `NaN`。
3. 通过 `ComputeResult` 返回栅格、Top‑3 贡献、源 ID 列表，并可调用 `write_outputs(Path)` 写入 GeoTIFF/Parquet。
4. `ComputeService.query_point` 复用缓存结果完成最近邻查询（需传入与计算一致的 `alt_m`）。

## 扩展与协作建议
- 若需更精细的反射模型，可在 `propagation.two_ray_flat_loss_dB` 中加入极化相关反射系数或地面介电常数。
- 扩大区域/源规模时，考虑在 `engine` 中引入分块或并行策略，并在 `io_raster` 中增加流式写出。
- 需要外部系统接入时，可在 `service` 增加结果索引（如 JSON manifest）或引入数据库落盘。

## 注意事项
- 折射系数固定 k = 4/3，外部配置不暴露；若需调整需同步配置与文档。
- Top‑3 数量、阈值裁剪写死在 `config.EngineConfig` 中，可通过配置对象覆盖。
- 输入 polygon 必须顺时针且≥3 个顶点；单次计算仍仅支持单高度切片（AMSL）。
- REST `/query` 请求必须提供 `alt_m`，且需与计算高度一致。
- GeoTIFF 输出使用 EPSG:4326，网格默认按纬度倒序写出；Top‑3 Parquet 仅保留阈值以上像元的有效源索引与贡献份额。
