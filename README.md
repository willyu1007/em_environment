# EM Environment Service

按照《EM_env_service_code_framework》要求搭建的电磁态势估算服务骨架，包含核心计算引擎、REST API 与 CLI。

## 结构概览
- `emenv/`：核心库
  - `api_models.py`：Pydantic 输入输出模型
  - `engine.py`：主计算引擎，完成源贡献叠加、Top‑3 统计与栅格输出调度
  - `service.py`：对外服务封装（缓存 compute 结果并提供查询及可选落盘）
  - `io_raster.py`：GeoTIFF 与 Top‑3 Parquet 写出工具
  - `app/rest.py`：FastAPI 入口
  - `app/cli.py`：命令行入口（支持 `--output-dir` 生成 GeoTIFF/Parquet）
  - 其他模块：地理、网格、天线、传播、组合等工具
- `examples/`：示例输入、运行说明与 5 组测试数据
- `doc/`：规范文档、Agent 指南与迭代记录

## 快速开始
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 运行示例计算并生成成果文件
python -m emenv.app.cli examples/request_basic_free_space.json --output-dir outputs/latest

# 启动 REST 服务
uvicorn emenv.app.rest:app --reload
```

## 示例数据
- `examples/request_basic_free_space.json`：单源自由空间基线
- `examples/request_two_ray.json`：双源两射线/大气衰减
- `examples/request_multi_band_dense.json`：多频段高空场景
- `examples/request_comm_and_jammer.json`：通信基站与干扰机
- `examples/request_wide_area.json`：大范围多源混合传播

## 测试
```bash
pip install -e .[dev]
pytest
```
