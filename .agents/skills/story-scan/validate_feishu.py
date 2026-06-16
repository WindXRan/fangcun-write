#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证飞书同步配置
"""

import os
import sys
import json
import requests
from pathlib import Path

def validate_env_vars():
    """验证环境变量"""
    print("🔧 验证环境变量")
    print("=" * 50)
    
    required_vars = [
        ('FEISHU_APP_ID', '飞书应用ID', r'^[a-zA-Z0-9]+$'),
        ('FEISHU_APP_SECRET', '飞书应用密钥', r'^[a-zA-Z0-9]+$'),
        ('FEISHU_SPREADSHEET_TOKEN', '表格token', r'^[a-zA-Z0-9]+$'),
        ('FEISHU_SHEET_ID', '工作表ID', r'^[a-zA-Z0-9]+$'),
    ]
    
    all_valid = True
    results = []
    
    for var, description, pattern in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ {var}: 未设置")
            print(f"   描述: {description}")
            results.append((var, False, "未设置"))
            all_valid = False
        elif not re.match(pattern, value):
            print(f"❌ {var}: 格式不正确")
            print(f"   描述: {description}")
            print(f"   期望格式: {pattern}")
            results.append((var, False, "格式不正确"))
            all_valid = False
        else:
            print(f"✅ {var}: 验证通过")
            results.append((var, True, "验证通过"))
    
    return all_valid, results

def validate_env_file():
    """验证.env文件"""
    print("\n📄 验证.env文件")
    print("=" * 50)
    
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print(f"❌ .env文件不存在: {env_file}")
        return False, "文件不存在"
    
    print(f"✅ .env文件存在: {env_file}")
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必需的变量
        required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
        missing_vars = []
        
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少变量: {', '.join(missing_vars)}")
            return False, f"缺少变量: {', '.join(missing_vars)}"
        
        print("✅ .env文件验证通过")
        return True, "验证通过"
        
    except Exception as e:
        print(f"❌ 读取.env文件失败: {e}")
        return False, f"读取失败: {e}"

def validate_json_config():
    """验证JSON配置文件"""
    print("\n📄 验证JSON配置文件")
    print("=" * 50)
    
    config_file = Path(__file__).parent / "feishu_config.json"
    
    if not config_file.exists():
        print(f"❌ JSON配置文件不存在: {config_file}")
        return False, "文件不存在"
    
    print(f"✅ JSON配置文件存在: {config_file}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查飞书配置
        feishu_config = config.get('feishu', {})
        if not feishu_config:
            print("❌ 飞书配置为空")
            return False, "飞书配置为空"
        
        required_keys = ['app_id', 'app_secret', 'spreadsheet_token', 'sheet_id']
        missing_keys = [key for key in required_keys if key not in feishu_config]
        
        if missing_keys:
            print(f"❌ 缺少配置项: {', '.join(missing_keys)}")
            return False, f"缺少配置项: {', '.join(missing_keys)}"
        
        print("✅ JSON配置文件验证通过")
        return True, "验证通过"
        
    except json.JSONDecodeError:
        print("❌ JSON配置文件格式错误")
        return False, "格式错误"
    except Exception as e:
        print(f"❌ 读取JSON配置文件失败: {e}")
        return False, f"读取失败: {e}"

def validate_connection():
    """验证飞书连接"""
    print("\n🔗 验证飞书连接")
    print("=" * 50)
    
    # 获取配置
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    spreadsheet_token = os.getenv('FEISHU_SPREADSHEET_TOKEN')
    sheet_id = os.getenv('FEISHU_SHEET_ID')
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 配置不完整，无法验证连接")
        return False, "配置不完整"
    
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
            return False, f"HTTP请求失败: {response.status_code}"
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"❌ 获取token失败: {result.get('msg')}")
            return False, f"获取token失败: {result.get('msg')}"
        
        token = result.get("tenant_access_token")
        print("✅ 获取token成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False, "请求超时"
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False, f"请求失败: {e}"
    
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
            return False, f"HTTP请求失败: {response.status_code}"
        
        result = response.json()
        
        if result.get("code") != 0:
            print(f"❌ 读取表格失败: {result.get('msg')}")
            return False, f"读取表格失败: {result.get('msg')}"
        
        print("✅ 读取表格成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False, "请求超时"
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return False, f"请求失败: {e}"
    
    print("✅ 飞书连接验证通过")
    return True, "验证通过"

def validate_data_files():
    """验证数据文件"""
    print("\n📊 验证数据文件")
    print("=" * 50)
    
    data_dir = Path(__file__).parent / "data"
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return False, "数据目录不存在"
    
    print(f"✅ 数据目录存在: {data_dir}")
    
    # 检查排行榜数据
    rank_files = list(data_dir.glob("latest_*_ranks.json"))
    if rank_files:
        print(f"✅ 排行榜数据: {len(rank_files)} 个文件")
    else:
        print("❌ 排行榜数据: 无")
        return False, "排行榜数据不存在"
    
    # 检查市场总结
    summary_files = list(data_dir.glob("market_summary_*.json"))
    if summary_files:
        print(f"✅ 市场总结: {len(summary_files)} 个文件")
    else:
        print("❌ 市场总结: 无")
        return False, "市场总结不存在"
    
    # 检查市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if market_data_file.exists():
        print(f"✅ 市场数据: {market_data_file.name}")
    else:
        print("❌ 市场数据: 无")
        return False, "市场数据不存在"
    
    print("✅ 数据文件验证通过")
    return True, "验证通过"

def validate_dependencies():
    """验证依赖"""
    print("\n📦 验证依赖")
    print("=" * 50)
    
    try:
        import requests
        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests: 未安装")
        return False, "requests未安装"
    
    try:
        import json
        print("✅ json: 内置模块")
    except ImportError:
        print("❌ json: 内置模块异常")
        return False, "json模块异常"
    
    print("✅ 依赖验证通过")
    return True, "验证通过"

def validate_all():
    """验证所有配置"""
    print("🔍 飞书同步配置完整验证")
    print("=" * 50)
    print()
    
    validations = [
        ("环境变量", validate_env_vars),
        (".env文件", validate_env_file),
        ("JSON配置文件", validate_json_config),
        ("飞书连接", validate_connection),
        ("数据文件", validate_data_files),
        ("依赖", validate_dependencies),
    ]
    
    results = []
    all_passed = True
    
    for name, validation_func in validations:
        try:
            if name == "环境变量":
                valid, details = validation_func()
                results.append((name, valid, details))
            else:
                valid, message = validation_func()
                results.append((name, valid, message))
            
            if not valid:
                all_passed = False
        except Exception as e:
            results.append((name, False, f"验证异常: {e}"))
            all_passed = False
    
    # 显示验证结果
    print("\n📋 验证结果")
    print("=" * 50)
    
    for name, valid, details in results:
        status = "✅" if valid else "❌"
        print(f"{status} {name}")
        if isinstance(details, list):
            for var, var_valid, message in details:
                var_status = "✅" if var_valid else "❌"
                print(f"   {var_status} {var}: {message}")
        else:
            print(f"   {details}")
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有验证通过！")
        print("\n下一步:")
        print("  1. 运行 'python feishu_sync.py' 同步数据")
        print("  2. 或运行 'python run.py sync-feishu' 使用一键脚本")
    else:
        print("❌ 部分验证失败")
        print("\n请解决上述问题后重试")
        print("查看帮助: python help_feishu.py")
    
    return all_passed

def show_help():
    """显示帮助信息"""
    print("""
验证飞书同步配置

使用方法：
  python validate_feishu.py [选项]

选项：
  env         验证环境变量
  file        验证.env文件
  json        验证JSON配置文件
  connection  验证飞书连接
  data        验证数据文件
  deps        验证依赖
  all         验证所有配置
  help        显示帮助信息

示例：
  python validate_feishu.py env         # 验证环境变量
  python validate_feishu.py connection  # 验证飞书连接
  python validate_feishu.py all         # 验证所有配置
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        validate_env_vars()
    elif command == "file":
        validate_env_file()
    elif command == "json":
        validate_json_config()
    elif command == "connection":
        validate_connection()
    elif command == "data":
        validate_data_files()
    elif command == "deps":
        validate_dependencies()
    elif command == "all":
        validate_all()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()