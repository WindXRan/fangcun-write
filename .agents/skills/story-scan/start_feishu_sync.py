#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动飞书同步功能
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """主函数"""
    print("🚀 快速启动飞书同步功能")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 9):
        print("❌ 需要Python 3.9+")
        return False
    
    # 检查依赖
    print("\n📦 检查依赖...")
    try:
        import requests
        print("  ✅ requests")
    except ImportError:
        print("  ❌ requests (未安装)")
        print("  运行: pip install requests")
        return False
    
    # 检查飞书配置
    print("\n🔧 检查飞书配置...")
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"  ⚠️  缺少环境变量: {', '.join(missing_vars)}")
        print()
        print("请设置环境变量：")
        print()
        print("Windows PowerShell:")
        print('  $env:FEISHU_APP_ID="your-app-id"')
        print('  $env:FEISHU_APP_SECRET="your-app-secret"')
        print('  $env:FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
        print('  $env:FEISHU_SHEET_ID="your-sheet-id"')
        print()
        print("或创建 .env 文件")
        return False
    
    print("  ✅ 飞书配置完整")
    
    # 运行测试
    print("\n🧪 运行测试...")
    test_script = Path(__file__).parent / "test_feishu_sync.py"
    if test_script.exists():
        result = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)
        if result.returncode != 0:
            print("  ❌ 测试失败")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return False
        print("  ✅ 测试通过")
    
    # 运行同步
    print("\n📊 开始同步...")
    sync_script = Path(__file__).parent / "feishu_sync.py"
    if sync_script.exists():
        result = subprocess.run([sys.executable, str(sync_script)], capture_output=False)
        if result.returncode != 0:
            print("  ❌ 同步失败")
            return False
        print("  ✅ 同步完成")
    
    print("\n" + "=" * 50)
    print("🎉 飞书同步完成！")
    print("\n下一步:")
    print("  1. 打开飞书表格查看数据")
    print("  2. 设置定时任务自动同步")
    print("  3. 查看 FEISHU_README.md 了解更多用法")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 启动失败，请检查配置")
        sys.exit(1)