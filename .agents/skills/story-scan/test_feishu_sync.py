#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步测试脚本
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_import():
    """测试导入"""
    try:
        from feishu_sync import FeishuSync, load_latest_data
        print("✅ 导入成功")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_data_loading():
    """测试数据加载"""
    try:
        from feishu_sync import load_latest_data
        data_dir = Path(__file__).parent / "data"
        data = load_latest_data(data_dir)
        print(f"✅ 数据加载成功，找到 {len(data)} 个数据文件")
        for key in data.keys():
            print(f"  - {key}")
        return True
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return False

def test_feishu_config():
    """测试飞书配置"""
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  缺少飞书环境变量: {', '.join(missing_vars)}")
        print("请设置以下环境变量:")
        for var in required_vars:
            print(f"  export {var}='your-value'")
        return False
    else:
        print("✅ 飞书配置完整")
        return True

def main():
    """主测试函数"""
    print("🧪 飞书同步测试")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_import),
        ("数据加载测试", test_data_loading),
        ("飞书配置测试", test_feishu_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}:")
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！可以运行飞书同步")
        print("\n下一步:")
        print("1. 设置飞书环境变量")
        print("2. 运行: python feishu_sync.py")
    else:
        print("⚠️  部分测试失败，请检查配置")

if __name__ == "__main__":
    main()