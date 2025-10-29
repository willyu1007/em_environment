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
- `examples/`：示例输入、运行说明与多组测试数据
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
- `examples/request_mega_urban.json`：24 源城市密集网络（VHF–C）
- `examples/request_highland_complex.json`：高原复杂地形 22 源（UHF–Ku，两射线）
- `examples/request_maritime_network.json`：海上编队 25 源（HF–X，多类型混合）

> 提示：REST `/query` 接口需提供 `alt_m` 参数（与预计算高度一致），否则将返回 404。

## 测试
```bash
pip install -e .[dev]
pytest
```

## 详细使用指南

完整的程序运行和算法调用指南请参考：[程序运行和算法调用指南](doc/program_usage_guide.md)

该指南包含：
- 环境安装和配置
- 命令行接口详细使用说明
- REST API调用方法
- 算法调用细节和参数说明
- 输入输出格式详解
- 实际使用示例
- 故障排除和性能优化建议

## 结果可视化工具

为了方便检查计算结果的正确性，项目提供了基于Web的可视化界面：

### 启动可视化界面
```bash
# 方法1: 使用启动脚本（推荐）
python -m emenv.app.visualizer_launcher

# 方法2: 直接启动
streamlit run emenv/app/visualizer.py
```

### 可视化功能
- 📊 **数据统计**: 显示电场强度的基本统计信息
- 🗺️ **交互式地图**: 使用Folium显示地理分布和热力图
- 📈 **统计图表**: 直方图、箱线图、累积分布、Q-Q图
- 🔍 **Top-K分析**: 各辐射源贡献比例分析
- ℹ️ **配置信息**: 显示计算参数和辐射源信息

详细的可视化工具使用说明请参考：[可视化工具指南](doc/visualization_guide.md)
