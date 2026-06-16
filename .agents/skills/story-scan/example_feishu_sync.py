#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步使用示例
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def example_sync():
    """示例：同步数据到飞书"""
    print("📊 飞书同步使用示例")
    print("=" * 50)
    
    # 检查环境变量
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  请先设置飞书环境变量：")
        print()
        print("Windows PowerShell:")
        print('  $env:FEISHU_APP_ID="your-app-id"')
        print('  $env:FEISHU_APP_SECRET="your-app-secret"')
        print('  $env:FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
        print('  $env:FEISHU_SHEET_ID="your-sheet-id"')
        print()
        print("Linux/Mac:")
        print('  export FEISHU_APP_ID="your-app-id"')
        print('  export FEISHU_APP_SECRET="your-app-secret"')
        print('  export FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
        print('  export FEISHU_SHEET_ID="your-sheet-id"')
        print()
        print("或在 .env 文件中配置：")
        print("  FEISHU_APP_ID=your-app-id")
        print("  FEISHU_APP_SECRET=your-app-secret")
        print("  FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token")
        print("  FEISHU_SHEET_ID=your-sheet-id")
        return False
    
    print("✅ 飞书环境变量已配置")
    print()
    print("📋 使用步骤：")
    print("1. 在飞书开放平台创建应用，获取App ID和App Secret")
    print("2. 创建一个在线表格，获取表格token和工作表ID")
    print("3. 给应用添加表格读写权限")
    print("4. 运行同步命令：")
    print("   python run.py sync-feishu")
    print()
    print("🔍 测试配置：")
    print("   python test_feishu_sync.py")
    print()
    print("📊 同步的数据包括：")
    print("  - 女频新书榜数据")
    print("  - 市场总结数据")
    print("  - 市场数据（热门题材、书名模式等）")
    
    return True

def example_custom_sync():
    """示例：自定义同步"""
    print()
    print("🔧 自定义同步示例")
    print("=" * 50)
    print()
    print("如果需要同步其他数据，可以修改 feishu_sync.py 文件：")
    print()
    print("1. 修改 prepare_rank_data() 函数，调整排行榜数据格式")
    print("2. 修改 prepare_summary_data() 函数，调整市场总结数据格式")
    print("3. 修改 prepare_market_data() 函数，调整市场数据格式")
    print("4. 修改 sync_to_feishu() 函数，调整同步逻辑")
    print()
    print("📖 飞书API文档：")
    print("  https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview")

if __name__ == "__main__":
    if example_sync():
        example_custom_sync()