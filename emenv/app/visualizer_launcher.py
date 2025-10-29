#!/usr/bin/env python3
"""EM环境服务结果可视化启动脚本

使用方法:
    python -m emenv.app.visualizer
    或
    streamlit run emenv/app/visualizer.py
"""

import subprocess
import sys
from pathlib import Path

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = [
        'streamlit',
        'plotly',
        'folium',
        'streamlit-folium',
        'scipy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 启动EM环境服务结果可视化界面...")
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 获取脚本路径
    script_path = Path(__file__).parent / "visualizer.py"
    
    # 启动Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(script_path),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 可视化界面已关闭")

if __name__ == "__main__":
    main()
