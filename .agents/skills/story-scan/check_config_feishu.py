#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查飞书同步配置
"""

import os
import sys
import json
import requests
from pathlib import Path

def check_env_vars():
    """检查环境变量"""
    print("🔧 检查环境变量")
    print("=" * 50)
    
    required_vars = [
        ('FEISHU_APP_ID', '飞书应用ID'),
        ('FEISHU_APP_SECRET', '飞书应用密钥'),
        ('FEISHU_SPREADSHEET_TOKEN', '表格token'),
        ('FEISHU_SHEET_ID', '工作表ID'),
    ]
    
    all_ok = True
    results = []
    
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: 已设置")
            results.append((var, True))
        else:
            print(f"❌ {var}: 未设置")
            print(f"   描述: {description}")
            results.append((var, False))
            all_ok = False
    
    return all_ok, results

def check_env_file():
    """检查.env文件"""
    print("\n📄 检查.env文件")
    print("=" * 50)
    
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print(f"❌ .env文件不存在: {env_file}")
        return False
    
    print(f"✅ .env文件存在: {env_file}")
    
    # 检查文件内容
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    missing_vars = []
    
    for var in required_vars:
        if var not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少变量: {', '.join(missing_vars)}")
        return False
    
    print("✅ .env文件内容完整")
    return True

def check_json_config():
    """检查JSON配置文件"""
    print("\n📄 检查JSON配置文件")
    print("=" * 50)
    
    config_file = Path(__file__).parent / "feishu_config.json"
    
    if not config_file.exists():
        print(f"❌ JSON配置文件不存在: {config_file}")
        return False
    
    print(f"✅ JSON配置文件存在: {config_file}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        feishu_config = config.get('feishu', {})
        if not feishu_config:
            print("❌ 飞书配置为空")
            return False
        
        required_keys = ['app_id', 'app_secret', 'spreadsheet_token', 'sheet_id']
        missing_keys = [key for key in required_keys if key not in feishu_config]
        
        if missing_keys:
            print(f"❌ 缺少配置项: {', '.join(missing_keys)}")
            return False
        
        print("✅ JSON配置文件内容完整")
        return True
        
    except json.JSONDecodeError:
        print("❌ JSON配置文件格式错误")
        return False

def check_connection():
    """检查飞书连接"""
    print("\n🔗 检查飞书连接")
    print("=" * 50)
    
    # 获取配置
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    spreadsheet_token = os.getenv('FEISHU_SPREADSHEET_TOKEN')
    sheet_id = os.getenv('FEISHU_SHEET_ID')
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 配置不完整，无法检查连接")
        return False
    
    # 测试获取token
    print("1. 测试获取访问token...")
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"❌ 获取token失败: {result.get('msg')}")
            return False
        
        token = result.get("tenant_access_token")
        print("✅ 获取token成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 测试读取表格
    print("2. 测试读取表格...")
    try:
        url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"❌ 读取表格失败: {result.get('msg')}")
            return False
        
        print("✅ 读取表格成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    print("✅ 飞书连接检查通过")
    return True

def check_data_files():
    """检查数据文件"""
    print("\n📊 检查数据文件")
    print("=" * 50)
    
    data_dir = Path(__file__).parent / "data"
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return False
    
    print(f"✅ 数据目录存在: {data_dir}")
    
    # 检查排行榜数据
    rank_files = list(data_dir.glob("latest_*_ranks.json"))
    if rank_files:
        print(f"✅ 排行榜数据: {len(rank_files)} 个文件")
    else:
        print("❌ 排行榜数据: 无")
        return False
    
    # 检查市场总结
    summary_files = list(data_dir.glob("market_summary_*.json"))
    if summary_files:
        print(f"✅ 市场总结: {len(summary_files)} 个文件")
    else:
        print("❌ 市场总结: 无")
        return False
    
    # 检查市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if market_data_file.exists():
        print(f"✅ 市场数据: {market_data_file.name}")
    else:
        print("❌ 市场数据: 无")
        return False
    
    print("✅ 数据文件检查通过")
    return True

def check_dependencies():
    """检查依赖"""
    print("\n📦 检查依赖")
    print("=" * 50)
    
    try:
        import requests
        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests: 未安装")
        return False
    
    print("✅ 依赖检查通过")
    return True

def check_all():
    """检查所有配置"""
    print("🔍 飞书同步配置完整检查")
    print("=" * 50)
    print()
    
    checks = [
        ("环境变量", check_env_vars),
        (".env文件", check_env_file),
        ("JSON配置文件", check_json_config),
        ("飞书连接", check_connection),
        ("数据文件", check_data_files),
        ("依赖", check_dependencies),
    ]
    
    results = []
    all_passed = True
    
    for name, check_func in checks:
        try:
            if name == "环境变量":
                ok, details = check_func()
                results.append((name, ok, details))
            else:
                ok = check_func()
                results.append((name, ok, None))
            
            if not ok:
                all_passed = False
        except Exception as e:
            results.append((name, False, str(e)))
            all_passed = False
    
    # 显示检查结果
    print("\n📋 检查结果")
    print("=" * 50)
    
    for name, ok, details in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
        if isinstance(details, list):
            for var, var_ok in details:
                var_status = "✅" if var_ok else "❌"
                print(f"   {var_status} {var}")
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有检查通过！")
        print("\n下一步:")
        print("  1. 运行 'python feishu_sync.py' 同步数据")
        print("  2. 或运行 'python run.py sync-feishu' 使用一键脚本")
    else:
        print("❌ 部分检查失败")
        print("\n请解决上述问题后重试")
        print("查看帮助: python help_feishu.py")
    
    return all_passed

def show_help():
    """显示帮助信息"""
    print("""
检查飞书同步配置

使用方法：
  python check_config_feishu.py [选项]

选项：
  env         检查环境变量
  file        检查.env文件
  json        检查JSON配置文件
  connection  检查飞书连接
  data        检查数据文件
  deps        检查依赖
  all         检查所有配置
  help        显示帮助信息

示例：
  python check_config_feishu.py env         # 检查环境变量
  python check_config_feishu.py connection  # 检查飞书连接
  python check_config_feishu.py all         # 检查所有配置
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        check_env_vars()
    elif command == "file":
        check_env_file()
    elif command == "json":
        check_json_config()
    elif command == "connection":
        check_connection()
    elif command == "data":
        check_data_files()
    elif command == "deps":
        check_dependencies()
    elif command == "all":
        check_all()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()