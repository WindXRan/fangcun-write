#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试飞书同步功能
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def quick_test():
    """快速测试"""
    print("🚀 快速测试飞书同步功能")
    print("=" * 50)
    
    # 1. 测试导入
    print("\n1. 测试导入...")
    try:
        from feishu_sync import FeishuSync, load_latest_data
        print("   ✅ 导入成功")
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
        print("   请确保已安装依赖: pip install requests")
        return False
    
    # 2. 测试数据加载
    print("\n2. 测试数据加载...")
    try:
        data_dir = Path(__file__).parent / "data"
        data = load_latest_data(data_dir)
        print(f"   ✅ 数据加载成功，找到 {len(data)} 个数据文件")
    except Exception as e:
        print(f"   ❌ 数据加载失败: {e}")
        return False
    
    # 3. 测试飞书配置
    print("\n3. 测试飞书配置...")
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"   ⚠️  缺少环境变量: {', '.join(missing_vars)}")
        print("   请设置环境变量后重试")
        return False
    else:
        print("   ✅ 飞书配置完整")
    
    # 4. 测试飞书连接
    print("\n4. 测试飞书连接...")
    try:
        feishu = FeishuSync()
        token = feishu.get_tenant_access_token()
        print(f"   ✅ 获取token成功")
    except Exception as e:
        print(f"   ❌ 飞书连接失败: {e}")
        print("   请检查飞书配置是否正确")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有测试通过！")
    print("\n下一步:")
    print("  运行完整同步: python feishu_sync.py")
    print("  或使用一键脚本: python run.py sync-feishu")
    
    return True

if __name__ == "__main__":
    quick_test()