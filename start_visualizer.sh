#!/bin/bash
# EM环境服务结果可视化工具 - Linux/macOS快速启动脚本

echo "🚀 启动EM环境服务结果可视化界面..."
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    echo "请先安装Python 3.10或更高版本"
    exit 1
fi

# 检查虚拟环境
if [ -f ".venv/bin/activate" ]; then
    echo "📦 激活虚拟环境..."
    source .venv/bin/activate
else
    echo "⚠️  未找到虚拟环境，使用系统Python"
fi

# 检查依赖
echo "🔍 检查依赖包..."
python3 -c "import streamlit, plotly, folium" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少必要的依赖包"
    echo "请运行: pip install -r requirements.txt"
    exit 1
fi

# 启动可视化界面
echo "🌐 启动Web界面..."
echo "浏览器将自动打开 http://localhost:8501"
echo "按 Ctrl+C 停止服务"
echo

python3 -m emenv.app.visualizer_launcher
