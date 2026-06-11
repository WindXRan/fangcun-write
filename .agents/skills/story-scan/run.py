#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄指数一键运行脚本
用法：python run.py [命令]
命令：
  scrape    - 运行爬虫采集数据
  build     - 构建分析数据
  serve     - 启动本地看板
  all       - 完整流程（爬虫+构建+启动）
  status    - 查看数据状态
  help      - 显示帮助信息
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Windows 控制台默认 GBK 编码，无法输出 emoji，强制使用 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 项目根目录
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

def run_cmd(cmd, cwd=None, timeout=None):
    """运行命令并输出结果"""
    print(f"\n{'='*60}")
    print(f"🚀 执行: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd or ROOT_DIR,
            timeout=timeout,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏰ 命令超时（{timeout}秒）")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def check_dependencies(required_packages=None):
    """检查依赖是否安装"""
    if required_packages is None:
        required_packages = ['playwright', 'pandas', 'openpyxl']
    
    print("\n📦 检查依赖...")
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖: {', '.join(missing_packages)}")
        print("运行: pip install -r requirements.txt")
        return False
    
    # 检查 Playwright 浏览器
    if 'playwright' in required_packages:
        print("\n🌐 检查 Playwright 浏览器...")
        playwright_cache = Path.home() / "AppData" / "Local" / "ms-playwright"
        if playwright_cache.exists():
            print("  ✅ Playwright 浏览器已安装")
        else:
            print("  ❌ Playwright 浏览器未安装")
            print("运行: playwright install chromium")
            return False
    
    return True

def show_status():
    """显示数据状态"""
    print("\n📊 数据状态:")
    print('='*60)
    
    # 检查原始数据
    print("\n📁 原始数据:")
    for prefix in ['male_new', 'male_read', 'female_new', 'female_read']:
        files = list(DATA_DIR.glob(f"fanqie_{prefix}_ranks_*.json"))
        if files:
            latest = max(files, key=lambda f: f.stem)
            date = latest.stem.split('_')[-1]
            size = latest.stat().st_size / 1024
            print(f"  ✅ {prefix}: {date} ({size:.1f} KB)")
        else:
            print(f"  ❌ {prefix}: 无数据")
    
    # 检查分析数据
    print("\n📈 分析数据:")
    for prefix in ['male_new', 'male_read', 'female_new', 'female_read']:
        latest_file = DATA_DIR / f"latest_{prefix}_ranks.json"
        if latest_file.exists():
            print(f"  ✅ {prefix}: 已生成")
        else:
            print(f"  ❌ {prefix}: 未生成")
    
    # 检查市场总结
    print("\n📰 市场总结:")
    for prefix in ['male_new', 'male_read', 'female_new', 'female_read']:
        summary_file = DATA_DIR / f"market_summary_{prefix}.json"
        if summary_file.exists():
            print(f"  ✅ {prefix}: 已生成")
        else:
            print(f"  ❌ {prefix}: 未生成")
    
    # 检查作者分析
    print("\n✍️  作者分析:")
    author_dir = DATA_DIR / "author"
    if author_dir.exists():
        files = list(author_dir.glob("*.json"))
        print(f"  📊 共 {len(files)} 个分析文件")
    else:
        print("  ❌ 未生成")

def scrape():
    """运行爬虫"""
    print("\n🕷️  开始数据采集...")
    return run_cmd("python scrape_fanqie_ranks.py", timeout=1200)

def build():
    """构建分析数据"""
    print("\n🔧 开始构建分析数据...")
    return run_cmd("python scripts/build_latest.py", timeout=300)

def serve():
    """启动本地服务 - 跳转到 story-web"""
    print("\n🌐 启动书库服务（含排行榜）...")
    print("访问地址:")
    print("  - 书库首页: http://localhost:5000/")
    print("  - 番茄排行榜: http://localhost:5000/ranks/")
    print("  - 趋势风向: http://localhost:5000/ranks/trend.html")
    print("  - 创作灵感: http://localhost:5000/ranks/author.html")
    print("\n按 Ctrl+C 停止服务")
    
    # 启动 story-web
    web_dir = ROOT_DIR.parent.parent / "skills" / "story-web"
    return run_cmd("python app.py", cwd=str(web_dir))

def show_help():
    """显示帮助信息"""
    print(__doc__)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    # 切换到项目目录
    os.chdir(ROOT_DIR)
    
    if command == "scrape":
        if check_dependencies(['playwright', 'pandas', 'openpyxl']):
            scrape()
    
    elif command == "build":
        build()
    
    elif command == "serve":
        serve()
    
    elif command == "all":
        if check_dependencies(['playwright', 'pandas', 'openpyxl']):
            if scrape():
                build()
                serve()
    
    elif command == "status":
        show_status()
    
    elif command == "help":
        show_help()
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()