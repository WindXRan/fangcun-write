#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试飞书连接
"""

import os
import sys
import requests
from pathlib import Path

def test_connection():
    """测试飞书连接"""
    print("🔗 测试飞书连接")
    print("=" * 50)
    
    # 检查环境变量
    print("\n1. 检查环境变量...")
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"   ❌ 缺少环境变量: {', '.join(missing_vars)}")
        return False
    
    print("   ✅ 环境变量配置完整")
    
    # 测试获取token
    print("\n2. 测试获取访问token...")
    try:
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ HTTP请求失败: {response.status_code}")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"   ❌ 获取token失败: {result.get('msg')}")
            return False
        
        token = result.get("tenant_access_token")
        print(f"   ✅ 获取token成功")
        
    except requests.exceptions.Timeout:
        print("   ❌ 请求超时，请检查网络连接")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return False
    
    # 测试读取表格
    print("\n3. 测试读取表格...")
    try:
        spreadsheet_token = os.getenv('FEISHU_SPREADSHEET_TOKEN')
        sheet_id = os.getenv('FEISHU_SHEET_ID')
        
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ HTTP请求失败: {response.status_code}")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"   ❌ 读取表格失败: {result.get('msg')}")
            return False
        
        print("   ✅ 读取表格成功")
        
    except requests.exceptions.Timeout:
        print("   ❌ 请求超时，请检查网络连接")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return False
    
    # 测试写入表格
    print("\n4. 测试写入表格...")
    try:
        # 写入测试数据
        test_data = [["测试数据", "连接测试"]]
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "valueRange": {
                "range": f"{sheet_id}!A1:B1",
                "values": test_data
            }
        }
        
        response = requests.put(url, headers=headers, json=data, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ HTTP请求失败: {response.status_code}")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"   ❌ 写入表格失败: {result.get('msg')}")
            return False
        
        print("   ✅ 写入表格成功")
        
    except requests.exceptions.Timeout:
        print("   ❌ 请求超时，请检查网络连接")
        return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 飞书连接测试成功！")
    print("\n下一步:")
    print("  1. 运行 'python feishu_sync.py' 同步数据")
    print("  2. 或运行 'python run.py sync-feishu' 使用一键脚本")
    
    return True

def show_help():
    """显示帮助信息"""
    print("""
测试飞书连接

使用方法：
  python test_feishu_connection.py

功能：
  1. 检查环境变量配置
  2. 测试获取访问token
  3. 测试读取表格
  4. 测试写入表格

示例：
  python test_feishu_connection.py
""")

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        return
    
    success = test_connection()
    
    if not success:
        print("\n❌ 连接测试失败")
        print("\n故障排除:")
        print("  1. 检查飞书环境变量是否正确设置")
        print("  2. 确认飞书应用有表格读写权限")
        print("  3. 检查表格token和工作表ID是否正确")
        print("  4. 查看 FEISHU_README.md 了解详细配置步骤")
        sys.exit(1)

if __name__ == "__main__":
    main()