"""EM环境服务结果可视化界面

用于检查计算结果的正确性，包括：
- 电场强度分布图
- 功率密度分布图  
- Top-K贡献源分析
- 数据统计信息
- 交互式地图显示
"""

import streamlit as st
import pandas as pd
import numpy as np
import rasterio
import pyarrow.parquet as pq
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from pathlib import Path
import json
import time
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="EM环境服务结果可视化",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .info-box {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def load_geotiff_data(file_path: Path) -> Tuple[np.ndarray, Dict]:
    """加载 GeoTIFF 栅格，并返回数据与经纬度网格等元信息。

    参数
    ----
    file_path : Path
        GeoTIFF 文件路径，栅格值通常对应电场强度 (dBµV/m) 或功率密度 (W/m²)。

    返回
    ----
    tuple[np.ndarray, dict]
        - 第一个元素为栅格数据数组。
        - 第二个元素包含仿射变换、CRS、经纬度网格等，便于后续可视化。
    """
    try:
        with rasterio.open(file_path) as src:
            data = src.read(1)
            transform = src.transform
            crs = src.crs
            bounds = src.bounds
            
            # 创建坐标网格
            height, width = data.shape
            # 注意：rasterio 读取的第 0 行是影像的最上方（最大纬度）。
            # 因此这里使用 top→bottom 递减，以保证 data[i] 与 lats[i] 对齐。
            lons, lats = np.meshgrid(
                np.linspace(bounds.left, bounds.right, width),
                np.linspace(bounds.top, bounds.bottom, height)
            )
            
            return data, {
                'transform': transform,
                'crs': crs,
                'bounds': bounds,
                'lons': lons,
                'lats': lats,
                'shape': data.shape
            }
    except Exception as e:
        st.error(f"加载GeoTIFF文件失败: {e}")
        return None, {}

def load_parquet_data(file_path: Path) -> pd.DataFrame:
    """加载 Top-K 诊断的 Parquet 数据表。

    参数
    ----
    file_path : Path
        Parquet 路径。

    返回
    ----
    pandas.DataFrame
        若读取失败则返回空 DataFrame。
    """
    try:
        df = pq.read_table(file_path).to_pandas()
        return df
    except Exception as e:
        st.error(f"加载Parquet文件失败: {e}")
        return pd.DataFrame()

def load_request_config(file_path: Path) -> Dict:
    """加载用于计算的 JSON 配置，便于在可视化界面展示关键参数。

    参数
    ----
    file_path : Path
        ComputeRequest JSON 文件路径。

    返回
    ----
    dict
        原始配置字典，读取失败时返回空字典。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载配置文件失败: {e}")
        return {}

def create_heatmap(
    data: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    title: str,
    colorbar_title: str,
) -> go.Figure:
    """创建热力图，用于展示网格数据的空间分布。

    参数
    ----
    data : np.ndarray
        栅格数据，常见单位为 dBµV/m 或 W/m²。
    lons, lats : np.ndarray
        经度/纬度网格（degree）。
    title : str
        图表标题。
    colorbar_title : str
        颜色条标题（建议带单位说明）。
    """
    fig = go.Figure(data=go.Heatmap(
        z=data.astype(float),  # 确保数据类型为Python float
        x=lons[0, :].astype(float),
        y=lats[:, 0].astype(float),
        colorscale='Viridis',
        colorbar=dict(title=colorbar_title),
        hovertemplate='经度: %{x:.4f}<br>纬度: %{y:.4f}<br>值: %{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title='经度 (°)',
        yaxis_title='纬度 (°)',
        width=800,
        height=600
    )
    
    return fig

def create_statistics_plot(data: np.ndarray, title: str) -> go.Figure:
    """创建统计图表，汇总直方图、箱线图、CDF 和 Q-Q 图等指标展示。

    参数
    ----
    data : np.ndarray
        栅格数据，常见单位为 dBµV/m。
    title : str
        图表标题。

    返回
    ----
    go.Figure
        Plotly 图像对象，可直接在 Streamlit 中渲染。
    """
    # 过滤NaN值
    valid_data = data[~np.isnan(data)]
    
    if len(valid_data) == 0:
        st.warning("没有有效数据用于统计")
        return go.Figure()
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('直方图', '箱线图', '累积分布', 'Q-Q图'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # 直方图
    fig.add_trace(
        go.Histogram(x=valid_data, nbinsx=50, name='分布'),
        row=1, col=1
    )
    
    # 箱线图
    fig.add_trace(
        go.Box(y=valid_data, name='箱线图'),
        row=1, col=2
    )
    
    # 累积分布
    sorted_data = np.sort(valid_data)
    cumulative = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
    fig.add_trace(
        go.Scatter(x=sorted_data, y=cumulative, mode='lines', name='累积分布'),
        row=2, col=1
    )
    
    # Q-Q图（简化版）
    from scipy import stats
    qq_data = stats.probplot(valid_data, dist="norm")
    fig.add_trace(
        go.Scatter(x=qq_data[0][0], y=qq_data[0][1], mode='markers', name='Q-Q图'),
        row=2, col=2
    )
    
    fig.update_layout(
        title=title,
        showlegend=False,
        height=600
    )
    
    return fig

def create_beam_diagram(sources: List[Dict], region_center_lat: float, region_center_lon: float, 
                       title: str = "辐射源波束示意图") -> go.Figure:
    """绘制所有辐射源的相对位置和波束方向图。

    - 以区域中心为参考点，计算源的相对位置
    - 用箭头表示波束方向，箭头长度表示强度（EIRP）
    - 箭头宽度表示波束宽度（HPBW）
    """
    fig = go.Figure()
    if not sources:
        fig.update_layout(title=title, xaxis_title="相对经度 (km)", yaxis_title="相对纬度 (km)")
        return fig

    # 颜色循环
    palette = px.colors.qualitative.Set2 + px.colors.qualitative.Set3
    
    # 计算相对位置和波束信息
    beam_data = []
    for idx, src in enumerate(sources):
        pos = src.get("position", {})
        emission = src.get("emission", {})
        ant = src.get("antenna", {})
        pointing = ant.get("pointing", {})
        pattern = ant.get("pattern", {})
        
        # 相对位置（km）
        src_lat = float(pos.get("lat", 0.0))
        src_lon = float(pos.get("lon", 0.0))
        rel_lat_km = (src_lat - region_center_lat) * 111.0  # 近似1度=111km
        rel_lon_km = (src_lon - region_center_lon) * 111.0 * np.cos(np.radians(region_center_lat))
        
        # 波束参数
        az_deg = float(pointing.get("az_deg", 0.0))
        hpbw_deg = float(pattern.get("hpbw_deg", 20.0))
        eirp_dbm = float(emission.get("eirp_dBm", 90.0))
        
        # 归一化强度（用于箭头长度）
        intensity_norm = (eirp_dbm - 50.0) / 50.0  # 50-100dBm映射到0-1
        intensity_norm = max(0.1, min(1.0, intensity_norm))  # 限制在0.1-1.0
        
        # 箭头长度（km）
        arrow_length = intensity_norm * 20.0  # 最大20km
        
        # 箭头方向（转换为数学角度：北=0°，东=90°）
        az_math = 90.0 - az_deg  # 转换为数学坐标系
        
        beam_data.append({
            'idx': idx,
            'id': str(src.get("id", f"src_{idx+1}")),
            'rel_lat_km': rel_lat_km,
            'rel_lon_km': rel_lon_km,
            'az_deg': az_deg,
            'az_math': az_math,
            'hpbw_deg': hpbw_deg,
            'eirp_dbm': eirp_dbm,
            'arrow_length': arrow_length,
            'color': palette[idx % len(palette)]
        })
    
    # 使用扇形表示波束（位置 + 扇形，无箭头）
    for beam in beam_data:
        # 源位置点
        fig.add_trace(go.Scatter(
            x=[beam['rel_lon_km']], y=[beam['rel_lat_km']], mode='markers',
            marker=dict(size=10, color=beam['color'], line=dict(width=1, color='black')),
            name=f"{beam['id']} 位置", showlegend=False,
            hovertemplate=f"源: {beam['id']}<br>EIRP: {beam['eirp_dbm']:.1f} dBm<extra></extra>"
        ))

        # 扇形半径与角度
        radius = beam['arrow_length']  # 用先前计算的强度映射作为半径
        half = beam['hpbw_deg'] / 2.0
        angles = np.linspace(beam['az_math'] - half, beam['az_math'] + half, 40)
        sector_x = [beam['rel_lon_km']] + [beam['rel_lon_km'] + radius * np.cos(np.radians(a)) for a in angles] + [beam['rel_lon_km']]
        sector_y = [beam['rel_lat_km']] + [beam['rel_lat_km'] + radius * np.sin(np.radians(a)) for a in angles] + [beam['rel_lat_km']]

        fig.add_trace(go.Scatter(
            x=sector_x, y=sector_y, mode='lines', fill='toself',
            line=dict(width=1, color=beam['color']), fillcolor=beam['color'], opacity=0.25,
            name=f"{beam['id']} 波束扇形", showlegend=False, hoverinfo='skip'
        ))

    # 设置布局
    fig.update_layout(
        title=title,
        xaxis_title="相对经度 (km)",
        yaxis_title="相对纬度 (km)",
        showlegend=True,
        height=500,
        width=600,
        xaxis=dict(scaleanchor="y", scaleratio=1),  # 保持纵横比
        yaxis=dict(scaleanchor="x", scaleratio=1)
    )
    
    return fig

def create_interactive_map(
    data: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    sources: List[Dict],
    title: str,
    color_scheme: str = "blue_to_red",
) -> folium.Map:
    """创建交互式地图，用于结合栅格结果与辐射源信息进行空间分析。

    参数
    ----
    data : np.ndarray
        栅格数据（dBµV/m 或 W/m²）。
    lons, lats : np.ndarray
        经纬度网格（degree）。
    sources : list[dict]
        辐射源列表，字段与 ``ComputeRequest`` 中定义的结构一致。
    title : str
        地图标题。
    color_scheme : str, 默认 ``"blue_to_red"``
        色彩渐变方案，影响热力层的视觉呈现。
    """
    # 计算地图中心
    center_lat = np.mean(lats)
    center_lon = np.mean(lons)
    
    # 创建地图
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # 添加数据热力图
    from folium.plugins import HeatMap
    
    # 过滤NaN值并计算数据范围
    valid_data = data[~np.isnan(data)]
    
    if len(valid_data) > 0:
        # 计算数据统计信息
        data_min = np.min(valid_data)
        data_max = np.max(valid_data)
        data_mean = np.mean(valid_data)
        data_std = np.std(valid_data)
        
        # 使用分位数来设置更好的色彩范围，避免极值影响
        q10 = np.percentile(valid_data, 10)
        q90 = np.percentile(valid_data, 90)
        
        # 准备热力图数据，对数据进行归一化处理
        heat_data = []
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if not np.isnan(data[i, j]):
                    # 对数据进行归一化，映射到0-1范围
                    normalized_value = (data[i, j] - q10) / (q90 - q10) if q90 > q10 else 0.5
                    normalized_value = max(0, min(1, normalized_value))  # 确保在0-1范围内
                    
                    heat_data.append([
                        float(lats[i, j]), 
                        float(lons[i, j]), 
                        float(normalized_value)
                    ])
        
        if heat_data:
            # 定义不同的色彩方案
            color_schemes = {
                'blue_to_red': {
                    0.0: 'blue',      # 低值 - 蓝色
                    0.2: 'cyan',      # 较低值 - 青色
                    0.4: 'lime',      # 中等值 - 绿色
                    0.6: 'yellow',    # 较高值 - 黄色
                    0.8: 'orange',    # 高值 - 橙色
                    1.0: 'red'        # 最高值 - 红色
                },
                'green_to_red': {
                    0.0: 'darkgreen', # 低值 - 深绿色
                    0.2: 'green',     # 较低值 - 绿色
                    0.4: 'yellow',    # 中等值 - 黄色
                    0.6: 'orange',    # 较高值 - 橙色
                    0.8: 'darkred',   # 高值 - 深红色
                    1.0: 'red'        # 最高值 - 红色
                },
                'purple_to_yellow': {
                    0.0: 'purple',    # 低值 - 紫色
                    0.2: 'blue',      # 较低值 - 蓝色
                    0.4: 'cyan',      # 中等值 - 青色
                    0.6: 'lime',      # 较高值 - 绿色
                    0.8: 'yellow',    # 高值 - 黄色
                    1.0: 'white'      # 最高值 - 白色
                },
                'cool_to_warm': {
                    0.0: 'darkblue',  # 低值 - 深蓝色
                    0.2: 'blue',      # 较低值 - 蓝色
                    0.4: 'lightblue', # 中等值 - 浅蓝色
                    0.6: 'lightgreen', # 较高值 - 浅绿色
                    0.8: 'orange',    # 高值 - 橙色
                    1.0: 'red'        # 最高值 - 红色
                }
            }
            
            # 使用选择的色彩方案
            gradient_config = color_schemes.get(color_scheme, color_schemes['blue_to_red'])
            
            HeatMap(
                heat_data, 
                name='电场强度分布',
                gradient=gradient_config,
                min_opacity=0.3,
                max_zoom=18,
                radius=15,
                blur=10
            ).add_to(m)
    
    # 添加辐射源标记
    for source in sources:
        folium.Marker(
            [float(source['position']['lat']), float(source['position']['lon'])],
            popup=f"源ID: {source['id']}<br>类型: {source['type']}<br>EIRP: {source['emission']['eirp_dBm']} dBm",
            icon=folium.Icon(color='red', icon='radio')
        ).add_to(m)
    
    # 添加图例
    folium.LayerControl().add_to(m)
    
    return m

def display_data_statistics(data: np.ndarray, title: str):
    """显示数据统计信息，帮助用户快速理解数值范围与分布。

    参数
    ----
    data : np.ndarray
        栅格数据。
    title : str
        统计卡片标题，用于配合 Streamlit UI。
    """
    valid_data = data[~np.isnan(data)]
    
    if len(valid_data) == 0:
        st.warning("没有有效数据")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("最小值", f"{np.min(valid_data):.2f}")
    with col2:
        st.metric("最大值", f"{np.max(valid_data):.2f}")
    with col3:
        st.metric("平均值", f"{np.mean(valid_data):.2f}")
    with col4:
        st.metric("标准差", f"{np.std(valid_data):.2f}")
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("中位数", f"{np.median(valid_data):.2f}")
    with col6:
        st.metric("25%分位数", f"{np.percentile(valid_data, 25):.2f}")
    with col7:
        st.metric("75%分位数", f"{np.percentile(valid_data, 75):.2f}")
    with col8:
        st.metric("有效像素数", f"{len(valid_data):,}")

def main():
    """Streamlit 应用入口，提供文件选择、数据加载、热力图、统计和 Top-K 分析等功能。"""
    # 页面标题
    st.markdown('<h1 class="main-header">📡 EM环境服务结果可视化</h1>', unsafe_allow_html=True)
    
    # 初始化session state
    if 'latest_output_dir' not in st.session_state:
        st.session_state.latest_output_dir = "outputs/latest"
    
    # 侧边栏 - 文件选择
    st.sidebar.header("📁 文件选择")
    
    # 配置来源
    st.sidebar.subheader("🔧 配置来源")
    config_mode = st.sidebar.radio(
        "选择配置方式",
        options=["从文件/示例", "参数编辑器"],
        index=0,
        help="可从示例/上传JSON加载，或在编辑器中按规范逐项设置"
    )

    config_data = {}
    config_source = ""

    if config_mode == "从文件/示例":
        # JSON文件上传
        uploaded_file = st.sidebar.file_uploader(
            "上传JSON配置文件",
            type=['json'],
            help="上传计算参数配置文件"
        )

        # 示例文件选择（动态扫描 examples 目录）
        st.sidebar.subheader("📋 示例文件")
        try:
            ex_dir = Path("examples")
            dynamic_files = [p.name for p in ex_dir.glob("request_*.json")]
            dynamic_files.sort()
        except Exception:
            dynamic_files = []

        selected_example = st.sidebar.selectbox(
            "选择示例文件",
            ["自定义"] + dynamic_files,
            index=0,
            key="example_select",
            help="从 examples/ 目录自动加载，以 request_*.json 为准"
        )

        # 配置文件路径
        if uploaded_file is not None:
            config_data = json.loads(uploaded_file.read().decode('utf-8'))
            config_source = "uploaded"
        elif selected_example != "自定义":
            config_file = f"examples/{selected_example}"
            config_data = load_request_config(Path(config_file))
            config_source = "example"
            st.sidebar.success(f"已选择示例: {selected_example}")
        else:
            config_file = st.sidebar.text_input(
                "配置文件路径",
                value="examples/request_basic_free_space.json",
                help="用于获取辐射源信息的JSON配置文件"
            )
            config_data = load_request_config(Path(config_file))
            config_source = "custom"
    else:
        # 参数编辑器（依据 doc/EM_env_service_spec.md 规范）
        st.sidebar.subheader("🛠 可视化参数编辑器")

        # 默认状态
        if "editor_config" not in st.session_state:
            st.session_state.editor_config = {
                "region": {
                    "crs": "WGS84",
                    "polygon": [
                        {"lat": 34.10, "lon": 118.10},
                        {"lat": 34.10, "lon": 119.20},
                        {"lat": 33.20, "lon": 119.20},
                        {"lat": 33.20, "lon": 118.10},
                    ],
                },
                "grid": {"resolution_deg": 0.01, "alt_m": 100},
                "influence_buffer_km": 200,
                "environment": {
                    "propagation": {"model": "free_space"},
                    "atmosphere": {"gas_loss": "auto", "rain_rate_mmph": 0, "fog_lwc_gm3": 0},
                    "earth": {"k_factor": 1.3333333333},
                },
                "bands": [
                    {"name": "VHF", "f_min_MHz": 100, "f_max_MHz": 300, "ref_bw_kHz": 1000},
                    {"name": "UHF", "f_min_MHz": 300, "f_max_MHz": 1000, "ref_bw_kHz": 1000},
                    {"name": "L",   "f_min_MHz": 1000, "f_max_MHz": 2000, "ref_bw_kHz": 1000},
                    {"name": "S",   "f_min_MHz": 2000, "f_max_MHz": 4000, "ref_bw_kHz": 1000},
                ],
                "metric": "E_field_dBuV_per_m",
                "combine_sources": "power_sum",
                "temporal_agg": "peak",
                "limits": {"max_sources": 50, "max_region_km": 200},
                "sources": [],
            }

        ec = st.session_state.editor_config

        # 区域（用矩形便捷输入生成 polygon）
        with st.sidebar.expander("🌍 区域设置（矩形）", expanded=True):
            lat_min = st.number_input("纬度最小值", value=min(p["lat"] for p in ec["region"]["polygon"]))
            lat_max = st.number_input("纬度最大值", value=max(p["lat"] for p in ec["region"]["polygon"]))
            lon_min = st.number_input("经度最小值", value=min(p["lon"] for p in ec["region"]["polygon"]))
            lon_max = st.number_input("经度最大值", value=max(p["lon"] for p in ec["region"]["polygon"]))
            if lat_max <= lat_min or lon_max <= lon_min:
                st.sidebar.warning("请确保最大值大于最小值")
            polygon = [
                {"lat": float(lat_max), "lon": float(lon_min)},
                {"lat": float(lat_max), "lon": float(lon_max)},
                {"lat": float(lat_min), "lon": float(lon_max)},
                {"lat": float(lat_min), "lon": float(lon_min)},
            ]
            ec["region"]["polygon"] = polygon

        # 网格与影响半径
        with st.sidebar.expander("📐 网格与影响半径", expanded=True):
            ec["grid"]["resolution_deg"] = st.number_input("分辨率 (度)", value=float(ec["grid"]["resolution_deg"]), min_value=0.001, max_value=1.0, step=0.001, format="%.3f")
            ec["grid"]["alt_m"] = st.number_input("接收高度 (米)", value=int(ec["grid"]["alt_m"]), min_value=0, max_value=10000, step=10)
            ec["influence_buffer_km"] = st.number_input("影响半径 (km)", value=int(ec["influence_buffer_km"]), min_value=0, max_value=1000, step=10)

        # 环境参数
        with st.sidebar.expander("🌤️ 环境设置", expanded=False):
            model = st.selectbox("传播模型", ["free_space", "two_ray_flat"], index=0 if ec["environment"]["propagation"]["model"]=="free_space" else 1)
            ec["environment"]["propagation"]["model"] = model
            gas_loss_input = st.text_input("大气气体损耗(dB/km) 或 auto", value=str(ec["environment"]["atmosphere"]["gas_loss"]))
            try:
                ec["environment"]["atmosphere"]["gas_loss"] = float(gas_loss_input) if gas_loss_input.strip().lower() != "auto" else "auto"
            except ValueError:
                st.sidebar.warning("气体损耗请输入数值或 auto")
            ec["environment"]["atmosphere"]["rain_rate_mmph"] = st.number_input("雨衰雨强(mm/h)", value=float(ec["environment"]["atmosphere"]["rain_rate_mmph"]), min_value=0.0, step=1.0)
            ec["environment"]["atmosphere"]["fog_lwc_gm3"] = st.number_input("雾液态含水量(g/m³)", value=float(ec["environment"]["atmosphere"]["fog_lwc_gm3"]), min_value=0.0, step=0.1)
            st.caption("地球折射系数 k_factor 固定为 4/3 (1.3333)")

        # 频段（从规范默认集合中挑选）
        with st.sidebar.expander("📡 频段设置", expanded=False):
            default_band_defs = [
                ("VHF", 100, 300), ("UHF", 300, 1000), ("L", 1000, 2000), ("S", 2000, 4000),
                ("C", 4000, 8000), ("X", 8000, 12000), ("Ku", 12000, 18000), ("Ka", 26500, 40000),
            ]
            current_names = [b["name"] for b in ec["bands"]]
            selected = st.multiselect("选择频段", [n for n,_,_ in default_band_defs], default=current_names)
            new_bands = []
            for name, fmin, fmax in default_band_defs:
                if name in selected:
                    new_bands.append({"name": name, "f_min_MHz": fmin, "f_max_MHz": fmax, "ref_bw_kHz": 1000})
            ec["bands"] = new_bands

        # 计算与聚合
        with st.sidebar.expander("🧮 计算与聚合", expanded=False):
            ec["metric"] = st.selectbox("强度指标", ["E_field_dBuV_per_m"], index=0)
            ec["combine_sources"] = st.selectbox("源功率合并", ["power_sum"], index=0)
            ec["temporal_agg"] = st.selectbox("时间聚合", ["peak"], index=0)

        # 规模约束
        with st.sidebar.expander("📏 规模约束", expanded=False):
            ec["limits"]["max_sources"] = int(st.number_input("最大源数量", value=int(ec["limits"]["max_sources"]), min_value=1, step=1))
            ec["limits"]["max_region_km"] = int(st.number_input("最大区域尺度(km)", value=int(ec["limits"]["max_region_km"]), min_value=10, step=10))

        # 辐射源（可视化可增删表单）
        with st.sidebar.expander("📻 辐射源设置", expanded=False):
            if "editor_sources" not in st.session_state:
                st.session_state.editor_sources = ec["sources"] or []
            # 版本计数用于强制刷新控件 key，避免与旧状态冲突
            if "editor_src_revs" not in st.session_state:
                st.session_state.editor_src_revs = [0 for _ in st.session_state.editor_sources]
            # 与源数量对齐
            if len(st.session_state.editor_src_revs) != len(st.session_state.editor_sources):
                st.session_state.editor_src_revs = [0 for _ in st.session_state.editor_sources]

            def _ensure_dict(d, key, default):
                if key not in d or not isinstance(d[key], dict):
                    d[key] = default
                return d[key]

            # 区域内随机点工具
            def _point_in_poly(lat: float, lon: float, poly_points):
                inside = False
                n = len(poly_points)
                for i in range(n):
                    j = (i - 1) % n
                    yi = float(poly_points[i]["lat"]); yj = float(poly_points[j]["lat"])
                    xi = float(poly_points[i]["lon"]); xj = float(poly_points[j]["lon"])
                    intersect = ((yi > lat) != (yj > lat)) and (
                        lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
                    )
                    if intersect:
                        inside = not inside
                return inside

            def _random_point_in_polygon(poly_points):
                if not poly_points:
                    return 0.0, 0.0
                lats = [float(p["lat"]) for p in poly_points]
                lons = [float(p["lon"]) for p in poly_points]
                lat_min, lat_max = min(lats), max(lats)
                lon_min, lon_max = min(lons), max(lons)
                for _ in range(1000):
                    lat = float(np.random.uniform(lat_min, lat_max))
                    lon = float(np.random.uniform(lon_min, lon_max))
                    if _point_in_poly(lat, lon, poly_points):
                        return lat, lon
                # 兜底：返回多边形中心
                return float(np.mean(lats)), float(np.mean(lons))

            # 操作按钮
            cols = st.columns(2)
            with cols[0]:
                if st.button("➕ 新增源", key="add_src_btn"):
                    st.session_state.editor_sources.append({
                        "id": f"src_{len(st.session_state.editor_sources)+1}",
                        "type": "radar",
                        "position": {"lat": 0.0, "lon": 0.0, "alt_m": 0.0},
                        "emission": {
                            "eirp_dBm": 90.0,
                            "center_freq_MHz": 3000.0,
                            "bandwidth_MHz": 10.0,
                            "polarization": "H",
                            "duty_cycle": 1.0,
                        },
                        "antenna": {
                            "pattern": {"type": "simplified_directional", "hpbw_deg": 3.0, "vpbw_deg": 3.0, "sidelobe_template": "MIL-STD-20"},
                            "pointing": {"az_deg": 0.0, "el_deg": 0.0},
                            "scan": {"mode": "none", "rpm": 0, "sector_deg": 90},
                        },
                    })
                    st.session_state.editor_src_revs.append(0)
            with cols[1]:
                if st.button("🗑️ 清空", key="clear_src_btn"):
                    st.session_state.editor_sources = []
                    st.session_state.editor_src_revs = []

            # 列表渲染
            for idx, src in enumerate(list(st.session_state.editor_sources)):
                with st.expander(f"源 {idx+1}: {src.get('id','(未命名)')}", expanded=False):
                    rev = st.session_state.editor_src_revs[idx] if idx < len(st.session_state.editor_src_revs) else 0
                    # 基本信息
                    src["id"] = st.text_input("ID", value=str(src.get("id", "")), key=f"src_id_{idx}")
                    src["type"] = st.selectbox("类型", ["radar", "comm", "jammer", "other"], index=["radar","comm","jammer","other"].index(src.get("type", "radar")), key=f"src_type_{idx}")

                    # 位置
                    pos = _ensure_dict(src, "position", {"lat":0.0, "lon":0.0, "alt_m":0.0})
                    
                    # 检查是否需要随机化（在控件创建前，直接写入 session_state）
                    if f"randomize_src_{idx}" in st.session_state and st.session_state[f"randomize_src_{idx}"]:
                        poly = st.session_state.editor_config.get("region", {}).get("polygon", [])
                        rnd_lat, rnd_lon = _random_point_in_polygon(poly)
                        pos["lat"], pos["lon"] = float(rnd_lat), float(rnd_lon)
                        st.session_state[f"src_lat_{idx}"] = float(rnd_lat)
                        st.session_state[f"src_lon_{idx}"] = float(rnd_lon)
                        del st.session_state[f"randomize_src_{idx}"]
                    
                    c1, c2, c3 = st.columns([1,1,1])
                    with c1:
                        # 使用 rev 参与 key，强制重建控件以采用最新默认值
                        pos["lat"] = float(st.number_input("纬度", value=float(pos.get("lat", 0.0)), step=0.01, key=f"src_lat_{idx}_{rev}"))
                        pos["alt_m"] = float(st.number_input("高度(m)", value=float(pos.get("alt_m", 0.0)), step=10.0, key=f"src_alt_{idx}_{rev}"))
                    with c2:
                        pos["lon"] = float(st.number_input("经度", value=float(pos.get("lon", 0.0)), step=0.01, key=f"src_lon_{idx}_{rev}"))
                    with c3:
                        if st.button("区域内随机", key=f"src_rand_{idx}"):
                            poly = st.session_state.editor_config.get("region", {}).get("polygon", [])
                            rnd_lat, rnd_lon = _random_point_in_polygon(poly)
                            pos["lat"], pos["lon"] = float(rnd_lat), float(rnd_lon)
                            # 增加 rev 以强制控件重建
                            st.session_state.editor_src_revs[idx] = rev + 1
                            st.rerun()

                    # 发射
                    emi = _ensure_dict(src, "emission", {"eirp_dBm":90.0, "center_freq_MHz":3000.0, "bandwidth_MHz":10.0, "polarization":"H", "duty_cycle":1.0})
                    c3, c4 = st.columns(2)
                    with c3:
                        emi["eirp_dBm"] = float(st.number_input("EIRP(dBm)", value=float(emi.get("eirp_dBm", 90.0)), step=1.0, key=f"src_eirp_{idx}"))
                        emi["bandwidth_MHz"] = float(st.number_input("带宽(MHz)", value=float(emi.get("bandwidth_MHz", 10.0)), step=1.0, key=f"src_bw_{idx}"))
                        emi["duty_cycle"] = float(st.number_input("占空比", value=float(emi.get("duty_cycle", 1.0)), min_value=0.0, max_value=1.0, step=0.1, key=f"src_dc_{idx}"))
                    with c4:
                        emi["center_freq_MHz"] = float(st.number_input("中心频率(MHz)", value=float(emi.get("center_freq_MHz", 3000.0)), step=10.0, key=f"src_cf_{idx}"))
                        emi["polarization"] = st.selectbox("极化", ["H","V","RHCP","LHCP"], index=["H","V","RHCP","LHCP"].index(emi.get("polarization","H")), key=f"src_pol_{idx}")

                    # 天线
                    ant = _ensure_dict(src, "antenna", {"pattern":{}, "pointing":{}, "scan":{}})
                    pat = _ensure_dict(ant, "pattern", {"type":"simplified_directional","hpbw_deg":3.0,"vpbw_deg":3.0,"sidelobe_template":"MIL-STD-20"})
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        pat["type"] = st.selectbox("方向图类型", ["simplified_directional"], index=0, key=f"src_pat_type_{idx}")
                    with p2:
                        pat["hpbw_deg"] = float(st.number_input("HPBW_h(°)", value=float(pat.get("hpbw_deg",3.0)), step=0.5, key=f"src_hpbw_{idx}"))
                    with p3:
                        pat["vpbw_deg"] = float(st.number_input("HPBW_v(°)", value=float(pat.get("vpbw_deg",3.0)), step=0.5, key=f"src_vpbw_{idx}"))
                    pat["sidelobe_template"] = st.selectbox("副瓣模板", ["MIL-STD-20","RCS-13","Radar-Narrow-25","Comm-Omni-Back-10"], index=["MIL-STD-20","RCS-13","Radar-Narrow-25","Comm-Omni-Back-10"].index(pat.get("sidelobe_template","MIL-STD-20")), key=f"src_slt_{idx}")

                    pnt = _ensure_dict(ant, "pointing", {"az_deg":0.0,"el_deg":0.0})
                    q1, q2 = st.columns(2)
                    with q1:
                        pnt["az_deg"] = float(st.number_input("指向方位(°)", value=float(pnt.get("az_deg",0.0)), step=1.0, key=f"src_az_{idx}"))
                    with q2:
                        pnt["el_deg"] = float(st.number_input("指向仰角(°)", value=float(pnt.get("el_deg",0.0)), step=1.0, key=f"src_el_{idx}"))

                    scn = _ensure_dict(ant, "scan", {"mode":"none","rpm":0,"sector_deg":90})
                    r1, r2, r3 = st.columns(3)
                    with r1:
                        scn["mode"] = st.selectbox("扫描模式", ["none","circular","sector"], index=["none","circular","sector"].index(scn.get("mode","none")), key=f"src_scan_mode_{idx}")
                    with r2:
                        scn["rpm"] = int(st.number_input("转速(rpm)", value=int(scn.get("rpm",0)), step=1, key=f"src_scan_rpm_{idx}"))
                    with r3:
                        scn["sector_deg"] = int(st.number_input("扇区角(°)", value=int(scn.get("sector_deg",90)), step=5, key=f"src_scan_sector_{idx}"))

                    # 删除按钮
                    if st.button("删除该源", key=f"del_src_{idx}"):
                        st.session_state.editor_sources.pop(idx)
                        if idx < len(st.session_state.editor_src_revs):
                            st.session_state.editor_src_revs.pop(idx)

            # 同步回编辑器配置
            ec["sources"] = st.session_state.editor_sources

        # 构造配置
        config_data = {
            "region": ec["region"],
            "grid": ec["grid"],
            "influence_buffer_km": ec["influence_buffer_km"],
            "environment": ec["environment"],
            "bands": ec["bands"],
            "metric": ec["metric"],
            "combine_sources": ec["combine_sources"],
            "temporal_agg": ec["temporal_agg"],
            "limits": ec["limits"],
            "sources": ec["sources"],
        }
        config_source = "editor"
    
    # 计算参数配置
    st.sidebar.header("⚙️ 计算参数")
    
    if config_data:
        if config_mode == "从文件/示例":
            # 区域配置
            st.sidebar.subheader("🌍 区域设置")
            region = config_data.get('region', {})
            polygon_points = region.get('polygon', [])
            
            if polygon_points:
                st.sidebar.write(f"**区域点数**: {len(polygon_points)}")
                if st.sidebar.button("显示区域坐标"):
                    for i, point in enumerate(polygon_points):
                        st.sidebar.write(f"点{i+1}: ({point['lat']:.4f}, {point['lon']:.4f})")
            
            # 网格配置
            st.sidebar.subheader("📐 网格设置")
            grid = config_data.get('grid', {})
            resolution = st.sidebar.number_input(
                "分辨率 (度)",
                value=grid.get('resolution_deg', 0.02),
                min_value=0.001,
                max_value=1.0,
                step=0.001,
                format="%.3f",
                key="file_mode_resolution_deg",
            )
            altitude = st.sidebar.number_input(
                "接收高度 (米)",
                value=grid.get('alt_m', 50),
                min_value=0,
                max_value=10000,
                step=10,
                key="file_mode_alt_m",
            )
            
            # 环境配置
            st.sidebar.subheader("🌤️ 环境设置")
            env = config_data.get('environment', {})
            # 支持的传播模型列表
            supported_models = ["free_space", "two_ray", "two_ray_flat", "atmospheric"]
            current_model = env.get('propagation', {}).get('model', 'free_space')
            
            # 如果当前模型不在支持列表中，使用默认值
            if current_model not in supported_models:
                current_model = 'free_space'
            
            propagation_model = st.sidebar.selectbox(
                "传播模型",
                supported_models,
                index=supported_models.index(current_model),
                key="file_mode_propagation_model",
            )
            
            # 频段配置
            st.sidebar.subheader("📡 频段设置")
            bands = config_data.get('bands', [])
            if bands:
                st.sidebar.write(f"**频段数量**: {len(bands)}")
                for i, band in enumerate(bands):
                    with st.sidebar.expander(f"频段 {band.get('name', f'Band_{i}')}"):
                        st.write(f"频率范围: {band.get('f_min_MHz', 0)}-{band.get('f_max_MHz', 0)} MHz")
                        st.write(f"参考带宽: {band.get('ref_bw_kHz', 0)} kHz")
            
            # 辐射源配置
            st.sidebar.subheader("📻 辐射源设置")
            sources = config_data.get('sources', [])
            if sources:
                st.sidebar.write(f"**辐射源数量**: {len(sources)}")
                for i, source in enumerate(sources):
                    with st.sidebar.expander(f"源 {source.get('id', f'Source_{i}')}"):
                        st.write(f"类型: {source.get('type', 'Unknown')}")
                        pos = source.get('position', {})
                        st.write(f"位置: ({pos.get('lat', 0):.4f}, {pos.get('lon', 0):.4f}, {pos.get('alt_m', 0)}m)")
                        emission = source.get('emission', {})
                        st.write(f"EIRP: {emission.get('eirp_dBm', 0)} dBm")
                        st.write(f"频率: {emission.get('center_freq_MHz', 0)} MHz")
                        
                        # 新增：强度信息
                        bandwidth = emission.get('bandwidth_MHz', 0)
                        duty_cycle = emission.get('duty_cycle', 1.0)
                        st.write(f"带宽: {bandwidth} MHz")
                        st.write(f"占空比: {duty_cycle:.2f}")
                        
                        # 新增：波束方向信息
                        antenna = source.get('antenna', {})
                        pointing = antenna.get('pointing', {})
                        pattern = antenna.get('pattern', {})
                        scan = antenna.get('scan', {})
                        
                        st.write(f"**波束方向**")
                        st.write(f"方位角: {pointing.get('az_deg', 0):.1f}°")
                        st.write(f"仰角: {pointing.get('el_deg', 0):.1f}°")
                        st.write(f"水平波束宽度: {pattern.get('hpbw_deg', 0):.1f}°")
                        st.write(f"垂直波束宽度: {pattern.get('vpbw_deg', 0):.1f}°")
                        st.write(f"副瓣模板: {pattern.get('sidelobe_template', 'N/A')}")
                        
                        st.write(f"**扫描模式**")
                        scan_mode = scan.get('mode', 'none')
                        st.write(f"模式: {scan_mode}")
                        if scan_mode != 'none':
                            st.write(f"转速: {scan.get('rpm', 0)} rpm")
                            if scan_mode == 'sector':
                                st.write(f"扇区角: {scan.get('sector_deg', 0)}°")
        else:
            # 编辑器模式下仅展示摘要，避免与编辑器控件重复导致重复ID
            st.sidebar.info("当前为参数编辑器模式，以下显示只读摘要。")
            grid = config_data.get('grid', {})
            st.sidebar.write(f"分辨率(度): {grid.get('resolution_deg', 'N/A')} | 高度(m): {grid.get('alt_m', 'N/A')}")
            env = config_data.get('environment', {})
            st.sidebar.write(f"传播模型: {env.get('propagation', {}).get('model', 'free_space')}")
            bands = config_data.get('bands', [])
            st.sidebar.write(f"频段数量: {len(bands)}")
    
    # 重新计算按钮
    st.sidebar.header("🔄 重新计算")
    if st.sidebar.button("🚀 运行计算", type="primary"):
        if config_data:
            # 更新配置数据
            if config_mode == "从文件/示例":
                if 'grid' in config_data:
                    config_data['grid']['resolution_deg'] = resolution
                    config_data['grid']['alt_m'] = altitude
                if 'environment' in config_data and 'propagation' in config_data['environment']:
                    config_data['environment']['propagation']['model'] = propagation_model
            
            # 保存临时配置文件
            temp_config_path = Path("temp_config.json")
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # 运行计算
            import subprocess
            import sys
            
            output_dir = f"outputs/visualizer_{int(time.time())}"
            try:
                result = subprocess.run([
                    sys.executable, "-m", "emenv.app.cli",
                    str(temp_config_path),
                    "--output-dir", output_dir
                ], capture_output=True, text=True, check=True)
                
                # 更新session state中的输出目录
                st.session_state.latest_output_dir = output_dir
                
                st.sidebar.success(f"✅ 计算完成！输出目录: {output_dir}")
                st.sidebar.info("🔄 正在加载新结果...")
                
                # 清理临时文件
                temp_config_path.unlink()
                
                # 自动刷新页面
                st.rerun()
                
            except subprocess.CalledProcessError as e:
                st.sidebar.error(f"❌ 计算失败: {e.stderr}")
        else:
            st.sidebar.error("❌ 请先加载配置文件")
    
    # 输出目录选择
    output_dir = st.sidebar.text_input(
        "输出目录路径", 
        value=st.session_state.latest_output_dir,
        help="包含GeoTIFF和Parquet文件的目录"
    )
    
    # 更新session state
    st.session_state.latest_output_dir = output_dir
    
    output_path = Path(output_dir)
    if not output_path.exists():
        st.sidebar.error(f"目录不存在: {output_path}")
        st.stop()
    
    # 频段选择
    available_bands = []
    if output_path.exists():
        for band_dir in output_path.iterdir():
            if band_dir.is_dir():
                geotiff_file = band_dir / f"{band_dir.name}_field_strength.tif"
                if geotiff_file.exists():
                    available_bands.append(band_dir.name)
    
    if not available_bands:
        st.sidebar.error("未找到可用的频段数据")
        st.stop()
    
    selected_band = st.sidebar.selectbox("选择频段", available_bands)
    
    # 加载数据
    band_path = output_path / selected_band
    geotiff_file = band_path / f"{selected_band}_field_strength.tif"
    parquet_file = band_path / f"{selected_band}_topk.parquet"
    
    # 加载GeoTIFF数据
    field_data, geo_info = load_geotiff_data(geotiff_file)
    if field_data is None:
        st.stop()
    
    # 加载Parquet数据
    topk_data = load_parquet_data(parquet_file)
    
    # 主界面
    st.header(f"📊 {selected_band} 频段分析结果")
    
    # 显示当前数据源信息
    st.info(f"📁 当前数据源: `{output_dir}` | 📡 频段: `{selected_band}`")
    
    # 数据统计
    st.subheader("📈 数据统计")
    display_data_statistics(field_data, f"{selected_band} 频段电场强度")
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 地图可视化", "📊 统计图表", "🔍 Top-K分析", "ℹ️ 配置信息"])
    
    with tab1:
        st.subheader("🗺️ 交互式地图")
        
        # 色彩方案选择
        col1, col2 = st.columns([3, 1])
        with col1:
            color_scheme_options = {
                'blue_to_red': '蓝-青-绿-黄-橙-红 (推荐)',
                'green_to_red': '绿-黄-橙-红',
                'purple_to_yellow': '紫-蓝-青-绿-黄-白',
                'cool_to_warm': '深蓝-蓝-浅蓝-浅绿-橙-红'
            }
            selected_color_scheme = st.selectbox(
                "选择地图色彩方案",
                list(color_scheme_options.keys()),
                index=0,
                format_func=lambda x: color_scheme_options[x],
                help="选择不同的色彩渐变方案来优化地图视觉效果"
            )
        
        with col2:
            st.write("")  # 占位符，保持布局平衡
        
        # 创建地图
        sources = config_data.get('sources', [])
        interactive_map = create_interactive_map(
            field_data, 
            geo_info['lons'], 
            geo_info['lats'],
            sources,
            f"{selected_band} 频段电场强度分布",
            selected_color_scheme
        )
        
        # 显示地图
        st_folium(interactive_map, width=1000, height=600)
        
        # 热力图 + 波束示意并排展示
        st.subheader("🔥 热力图 与 📡 波束示意")
        c_left, c_right = st.columns([3, 2])
        with c_left:
            heatmap_fig = create_heatmap(
                field_data,
                geo_info['lons'],
                geo_info['lats'],
                f"{selected_band} 频段电场强度分布",
                "电场强度 (dBμV/m)"
            )
            st.plotly_chart(heatmap_fig, use_container_width=True)
        with c_right:
            sources_for_plot = config_data.get('sources', []) if isinstance(config_data, dict) else []
            # 计算区域中心
            region = config_data.get('region', {}) if isinstance(config_data, dict) else {}
            polygon = region.get('polygon', [])
            if polygon:
                center_lat = sum(p['lat'] for p in polygon) / len(polygon)
                center_lon = sum(p['lon'] for p in polygon) / len(polygon)
            else:
                center_lat, center_lon = 0.0, 0.0
            beam_fig = create_beam_diagram(sources_for_plot, center_lat, center_lon, title="📡 辐射源波束示意图")
            st.plotly_chart(beam_fig, use_container_width=True)
    
    with tab2:
        st.subheader("📊 统计图表")
        
        # 统计图表
        stats_fig = create_statistics_plot(field_data, f"{selected_band} 频段电场强度统计")
        if stats_fig.data:
            st.plotly_chart(stats_fig, use_container_width=True)
        
        # 数据分布信息
        st.subheader("📋 详细统计信息")
        
        valid_data = field_data[~np.isnan(field_data)]
        if len(valid_data) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本统计**")
                stats_dict = {
                    "数据点数": len(valid_data),
                    "最小值": f"{np.min(valid_data):.2f} dBμV/m",
                    "最大值": f"{np.max(valid_data):.2f} dBμV/m",
                    "平均值": f"{np.mean(valid_data):.2f} dBμV/m",
                    "中位数": f"{np.median(valid_data):.2f} dBμV/m",
                    "标准差": f"{np.std(valid_data):.2f} dBμV/m"
                }
                for key, value in stats_dict.items():
                    st.write(f"- {key}: {value}")
            
            with col2:
                st.write("**分位数信息**")
                percentiles = [10, 25, 50, 75, 90, 95, 99]
                for p in percentiles:
                    value = np.percentile(valid_data, p)
                    st.write(f"- {p}%分位数: {value:.2f} dBμV/m")
    
    with tab3:
        st.subheader("🔍 Top-K贡献源分析")
        
        if not topk_data.empty:
            # Top-K数据概览
            st.write(f"**数据概览**: {len(topk_data)} 条记录")
            
            # 按贡献比例排序 - 计算平均贡献比例而不是总和
            top_contributors = topk_data.groupby('source_id')['fraction'].mean().sort_values(ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**各源贡献比例**")
                for source_id, fraction in top_contributors.items():
                    if source_id:
                        st.write(f"- {source_id}: {fraction:.1%}")
            
            with col2:
                st.write("**Top-K数据表**")
                st.dataframe(topk_data.head(20))
            
            # 贡献源分布图
            if len(top_contributors) > 0:
                fig = px.bar(
                    x=top_contributors.values,
                    y=top_contributors.index,
                    orientation='h',
                    title="各源平均贡献比例",
                    labels={'x': '平均贡献比例', 'y': '源ID'}
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("未找到Top-K数据")
    
    with tab4:
        st.subheader("ℹ️ 配置信息")
        
        if config_data:
            # 基本信息
            st.write("**计算区域**")
            region = config_data.get('region', {})
            if 'polygon' in region:
                for i, point in enumerate(region['polygon']):
                    st.write(f"- 点{i+1}: ({point['lat']:.4f}, {point['lon']:.4f})")
            
            # 网格信息
            st.write("**网格设置**")
            grid = config_data.get('grid', {})
            st.write(f"- 分辨率: {grid.get('resolution_deg', 'N/A')}°")
            st.write(f"- 高度: {grid.get('alt_m', 'N/A')} m")
            
            # 环境设置
            st.write("**环境参数**")
            env = config_data.get('environment', {})
            st.write(f"- 传播模型: {env.get('propagation', {}).get('model', 'N/A')}")
            st.write(f"- 大气损耗: {env.get('atmosphere', {}).get('gas_loss', 'N/A')}")
            
            # 辐射源信息
            st.write("**辐射源信息**")
            sources = config_data.get('sources', [])
            for i, source in enumerate(sources):
                st.write(f"**源 {i+1}: {source.get('id', 'Unknown')}**")
                st.write(f"- 类型: {source.get('type', 'N/A')}")
                pos = source.get('position', {})
                st.write(f"- 位置: ({pos.get('lat', 'N/A')}, {pos.get('lon', 'N/A')}, {pos.get('alt_m', 'N/A')}m)")
                emission = source.get('emission', {})
                st.write(f"- EIRP: {emission.get('eirp_dBm', 'N/A')} dBm")
                st.write(f"- 频率: {emission.get('center_freq_MHz', 'N/A')} MHz")
                
                # 新增：强度信息
                bandwidth = emission.get('bandwidth_MHz', 'N/A')
                duty_cycle = emission.get('duty_cycle', 'N/A')
                st.write(f"- 带宽: {bandwidth} MHz")
                st.write(f"- 占空比: {duty_cycle}")
                
                # 新增：波束方向信息
                antenna = source.get('antenna', {})
                pointing = antenna.get('pointing', {})
                pattern = antenna.get('pattern', {})
                scan = antenna.get('scan', {})
                
                st.write(f"- **波束方向**:")
                st.write(f"  - 方位角: {pointing.get('az_deg', 'N/A')}°")
                st.write(f"  - 仰角: {pointing.get('el_deg', 'N/A')}°")
                st.write(f"  - 水平波束宽度: {pattern.get('hpbw_deg', 'N/A')}°")
                st.write(f"  - 垂直波束宽度: {pattern.get('vpbw_deg', 'N/A')}°")
                st.write(f"  - 副瓣模板: {pattern.get('sidelobe_template', 'N/A')}")
                
                st.write(f"- **扫描模式**:")
                scan_mode = scan.get('mode', 'N/A')
                st.write(f"  - 模式: {scan_mode}")
                if scan_mode != 'none' and scan_mode != 'N/A':
                    st.write(f"  - 转速: {scan.get('rpm', 'N/A')} rpm")
                    if scan_mode == 'sector':
                        st.write(f"  - 扇区角: {scan.get('sector_deg', 'N/A')}°")
        else:
            st.warning("未找到配置文件信息")
    
    # 页脚
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "EM环境服务结果可视化工具 | 用于检查计算正确性"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
