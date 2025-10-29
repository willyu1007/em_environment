# EM环境服务结果可视化工具

## 简介

这是一个基于Streamlit的Web可视化界面，用于检查EM环境服务计算结果的正确性。该工具可以：

- 📊 显示电场强度分布图
- 🗺️ 提供交互式地图可视化
- 📈 展示详细的统计图表
- 🔍 分析Top-K贡献源
- ℹ️ 显示配置信息

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法1: 使用启动脚本（推荐）

```bash
python -m emenv.app.visualizer_launcher
```

### 方法2: 直接启动Streamlit

```bash
streamlit run emenv/app/visualizer.py
```

### 方法3: 使用Python模块

```bash
python -m emenv.app.visualizer
```

## 界面说明

### 侧边栏配置

- **输出目录路径**: 指定包含GeoTIFF和Parquet文件的目录
- **选择频段**: 选择要分析的频段
- **配置文件路径**: 指定用于获取辐射源信息的JSON配置文件

### 主要功能

#### 1. 数据统计
- 显示电场强度的基本统计信息
- 包括最小值、最大值、平均值、标准差等

#### 2. 地图可视化
- **交互式地图**: 使用Folium显示地理分布
- **热力图**: 使用Plotly显示电场强度分布
- 支持缩放、平移等交互操作

#### 3. 统计图表
- **直方图**: 显示数据分布
- **箱线图**: 显示数据统计特征
- **累积分布**: 显示累积概率分布
- **Q-Q图**: 检查数据正态性

#### 4. Top-K分析
- 显示各辐射源的贡献比例
- 提供详细的Top-K数据表
- 可视化各源的总贡献比例

#### 5. 配置信息
- 显示计算区域信息
- 显示网格设置
- 显示环境参数
- 显示辐射源详细信息

## 示例工作流程

1. **运行计算**:
   ```bash
   python -m emenv.app.cli examples/request_basic_free_space.json --output-dir outputs/demo
   ```

2. **启动可视化**:
   ```bash
   python -m emenv.app.visualizer_launcher
   ```

3. **配置参数**:
   - 输出目录: `outputs/demo`
   - 选择频段: `S`
   - 配置文件: `examples/request_basic_free_space.json`

4. **查看结果**:
   - 检查数据统计是否合理
   - 查看地图分布是否符合预期
   - 分析Top-K贡献源
   - 验证配置参数

## 故障排除

### 常见问题

1. **依赖包缺失**
   ```bash
   pip install streamlit plotly folium streamlit-folium scipy pandas
   ```

2. **端口被占用**
   - 默认端口8501被占用时，Streamlit会自动选择其他端口
   - 可以在命令行中指定端口: `streamlit run emenv/app/visualizer.py --server.port 8502`

3. **文件路径错误**
   - 确保输出目录存在且包含正确的文件
   - 检查GeoTIFF和Parquet文件是否完整

4. **内存不足**
   - 对于大型数据集，可能需要增加系统内存
   - 可以考虑降低网格分辨率

### 性能优化

- 使用SSD存储提高文件读取速度
- 关闭不必要的浏览器标签页
- 对于大型数据集，可以先进行数据采样

## 技术特性

- **响应式设计**: 支持不同屏幕尺寸
- **交互式图表**: 支持缩放、悬停等操作
- **实时更新**: 修改参数后自动刷新
- **多格式支持**: 支持GeoTIFF和Parquet文件格式
- **中文界面**: 完全中文化的用户界面

## 扩展功能

可以根据需要添加以下功能：
- 多频段对比分析
- 时间序列分析
- 数据导出功能
- 自定义颜色映射
- 更多统计指标

---

如有问题或建议，请联系EM环境服务开发团队。
