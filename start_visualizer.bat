@echo off
REM EM环境服务结果可视化工具 - Windows快速启动脚本

echo 🚀 启动EM环境服务结果可视化界面...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo 请先安装Python 3.10或更高版本
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo 📦 激活虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  未找到虚拟环境，使用系统Python
)

REM 检查依赖
echo 🔍 检查依赖包...
python -c "import streamlit, plotly, folium" >nul 2>&1
if errorlevel 1 (
    echo ❌ 缺少必要的依赖包
    echo 请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

REM 启动可视化界面
echo 🌐 启动Web界面...
echo 浏览器将自动打开 http://localhost:8501
echo 按 Ctrl+C 停止服务
echo.

python -m emenv.app.visualizer_launcher

pause
