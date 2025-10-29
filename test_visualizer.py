#!/usr/bin/env python3
"""可视化工具测试脚本

用于验证可视化工具的基本功能
"""

import subprocess
import sys
from pathlib import Path
import tempfile
import json

def run_test_computation():
    """运行测试计算"""
    print("🧪 运行测试计算...")
    
    # 创建临时输出目录
    temp_dir = Path(tempfile.mkdtemp())
    output_dir = temp_dir / "test_output"
    
    try:
        # 运行CLI计算
        result = subprocess.run([
            sys.executable, "-m", "emenv.app.cli",
            "examples/request_basic_free_space.json",
            "--output-dir", str(output_dir)
        ], capture_output=True, text=True, check=True)
        
        print("✅ 测试计算完成")
        return output_dir
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试计算失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None

def check_visualization_dependencies():
    """检查可视化依赖"""
    print("🔍 检查可视化依赖...")
    
    required_packages = [
        'streamlit',
        'plotly', 
        'folium',
        'streamlit_folium',
        'scipy'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def test_file_loading():
    """测试文件加载功能"""
    print("📁 测试文件加载...")
    
    try:
        # 导入可视化模块
        from emenv.app.visualizer import load_geotiff_data, load_parquet_data, load_request_config
        
        # 测试配置文件加载
        config = load_request_config(Path("examples/request_basic_free_space.json"))
        if config:
            print("✅ 配置文件加载成功")
        else:
            print("❌ 配置文件加载失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 文件加载测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始可视化工具测试...")
    
    # 检查依赖
    if not check_visualization_dependencies():
        sys.exit(1)
    
    # 测试文件加载
    if not test_file_loading():
        sys.exit(1)
    
    # 运行测试计算
    output_dir = run_test_computation()
    if not output_dir:
        sys.exit(1)
    
    print("\n🎉 所有测试通过！")
    print(f"📁 测试输出目录: {output_dir}")
    print("\n💡 现在可以启动可视化界面:")
    print("   python -m emenv.app.visualizer_launcher")
    print(f"   然后在界面中设置输出目录为: {output_dir}")

if __name__ == "__main__":
    main()
