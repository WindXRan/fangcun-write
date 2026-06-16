#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断飞书同步问题
"""

import os
import sys
import json
import requests
from pathlib import Path

def diagnose_env_vars():
    """诊断环境变量"""
    print("🔧 诊断环境变量")
    print("=" * 50)
    
    required_vars = [
        ('FEISHU_APP_ID', '飞书应用ID'),
        ('FEISHU_APP_SECRET', '飞书应用密钥'),
        ('FEISHU_SPREADSHEET_TOKEN', '表格token'),
        ('FEISHU_SHEET_ID', '工作表ID'),
    ]
    
    issues = []
    
    for var, description in required_vars:
        value = os.getenv(var)
        if not value:
            issues.append(f"❌ {var}: 未设置")
            issues.append(f"   描述: {description}")
            issues.append(f"   解决方案: 设置环境变量 {var}")
        else:
            # 检查格式
            if var == 'FEISHU_APP_ID' and not value.isalnum():
                issues.append(f"⚠️  {var}: 格式可能不正确")
                issues.append(f"   当前值: {value[:4]}****{value[-4:] if len(value) > 8 else '****'}")
                issues.append(f"   期望格式: 字母数字组合")
            elif var == 'FEISHU_APP_SECRET' and len(value) < 10:
                issues.append(f"⚠️  {var}: 长度可能不足")
                issues.append(f"   当前长度: {len(value)}")
                issues.append(f"   期望长度: 至少10个字符")
            elif var == 'FEISHU_SPREADSHEET_TOKEN' and not value.isalnum():
                issues.append(f"⚠️  {var}: 格式可能不正确")
                issues.append(f"   当前值: {value[:4]}****{value[-4:] if len(value) > 8 else '****'}")
                issues.append(f"   期望格式: 字母数字组合")
            elif var == 'FEISHU_SHEET_ID' and not value.isalnum():
                issues.append(f"⚠️  {var}: 格式可能不正确")
                issues.append(f"   当前值: {value[:4]}****{value[-4:] if len(value) > 8 else '****'}")
                issues.append(f"   期望格式: 字母数字组合")
            else:
                print(f"✅ {var}: 验证通过")
    
    if issues:
        print("\n发现的问题:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n✅ 环境变量诊断通过")
        return True

def diagnose_env_file():
    """诊断.env文件"""
    print("\n📄 诊断.env文件")
    print("=" * 50)
    
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print("❌ .env文件不存在")
        print("   解决方案: 创建.env文件")
        print("   运行: python setup_feishu.py env")
        return False
    
    print(f"✅ .env文件存在: {env_file}")
    
    # 检查文件权限
    if not os.access(env_file, os.R_OK):
        print("❌ .env文件不可读")
        print("   解决方案: 检查文件权限")
        return False
    
    print("✅ .env文件可读")
    
    # 检查文件内容
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
        missing_vars = []
        
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ 缺少变量: {', '.join(missing_vars)}")
            print("   解决方案: 在.env文件中添加缺少的变量")
            return False
        
        print("✅ .env文件内容完整")
        return True
        
    except Exception as e:
        print(f"❌ 读取.env文件失败: {e}")
        print("   解决方案: 检查文件编码和权限")
        return False

def diagnose_json_config():
    """诊断JSON配置文件"""
    print("\n📄 诊断JSON配置文件")
    print("=" * 50)
    
    config_file = Path(__file__).parent / "feishu_config.json"
    
    if not config_file.exists():
        print("❌ JSON配置文件不存在")
        print("   解决方案: 创建JSON配置文件")
        print("   运行: python setup_feishu.py config")
        return False
    
    print(f"✅ JSON配置文件存在: {config_file}")
    
    # 检查文件权限
    if not os.access(config_file, os.R_OK):
        print("❌ JSON配置文件不可读")
        print("   解决方案: 检查文件权限")
        return False
    
    print("✅ JSON配置文件可读")
    
    # 检查文件内容
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        feishu_config = config.get('feishu', {})
        if not feishu_config:
            print("❌ 飞书配置为空")
            print("   解决方案: 在JSON配置文件中添加飞书配置")
            return False
        
        required_keys = ['app_id', 'app_secret', 'spreadsheet_token', 'sheet_id']
        missing_keys = [key for key in required_keys if key not in feishu_config]
        
        if missing_keys:
            print(f"❌ 缺少配置项: {', '.join(missing_keys)}")
            print("   解决方案: 在JSON配置文件中添加缺少的配置项")
            return False
        
        print("✅ JSON配置文件内容完整")
        return True
        
    except json.JSONDecodeError:
        print("❌ JSON配置文件格式错误")
        print("   解决方案: 检查JSON格式是否正确")
        return False
    except Exception as e:
        print(f"❌ 读取JSON配置文件失败: {e}")
        print("   解决方案: 检查文件编码和权限")
        return False

def diagnose_connection():
    """诊断飞书连接"""
    print("\n🔗 诊断飞书连接")
    print("=" * 50)
    
    # 获取配置
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    spreadsheet_token = os.getenv('FEISHU_SPREADSHEET_TOKEN')
    sheet_id = os.getenv('FEISHU_SHEET_ID')
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 配置不完整，无法诊断连接")
        print("   解决方案: 先完善配置")
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
            print("   解决方案: 检查网络连接")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            error_msg = result.get('msg', '未知错误')
            print(f"❌ 获取token失败: {error_msg}")
            
            # 提供具体的解决方案
            if "app id" in error_msg.lower():
                print("   解决方案: 检查App ID是否正确")
            elif "app secret" in error_msg.lower():
                print("   解决方案: 检查App Secret是否正确")
            elif "app" in error_msg.lower() and "not found" in error_msg.lower():
                print("   解决方案: 确认飞书应用已创建")
            else:
                print("   解决方案: 检查飞书应用配置")
            
            return False
        
        token = result.get("tenant_access_token")
        print("✅ 获取token成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        print("   解决方案: 检查网络连接，或增加超时时间")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        print("   解决方案: 检查网络连接和代理设置")
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
            print("   解决方案: 检查网络连接")
            return False
        
        result = response.json()
        
        if result.get("code") != 0:
            error_msg = result.get('msg', '未知错误')
            print(f"❌ 读取表格失败: {error_msg}")
            
            # 提供具体的解决方案
            if "permission" in error_msg.lower():
                print("   解决方案: 检查应用是否有表格读取权限")
            elif "token" in error_msg.lower():
                print("   解决方案: 检查表格token是否正确")
            elif "sheet" in error_msg.lower():
                print("   解决方案: 检查工作表ID是否正确")
            else:
                print("   解决方案: 检查表格配置和权限")
            
            return False
        
        print("✅ 读取表格成功")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        print("   解决方案: 检查网络连接，或增加超时时间")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        print("   解决方案: 检查网络连接和代理设置")
        return False
    
    print("✅ 飞书连接诊断通过")
    return True

def diagnose_data_files():
    """诊断数据文件"""
    print("\n📊 诊断数据文件")
    print("=" * 50)
    
    data_dir = Path(__file__).parent / "data"
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        print("   解决方案: 运行数据采集脚本")
        print("   运行: python run.py scrape")
        return False
    
    print(f"✅ 数据目录存在: {data_dir}")
    
    # 检查排行榜数据
    rank_files = list(data_dir.glob("latest_*_ranks.json"))
    if rank_files:
        print(f"✅ 排行榜数据: {len(rank_files)} 个文件")
    else:
        print("❌ 排行榜数据: 无")
        print("   解决方案: 运行数据采集脚本")
        print("   运行: python run.py scrape")
        return False
    
    # 检查市场总结
    summary_files = list(data_dir.glob("market_summary_*.json"))
    if summary_files:
        print(f"✅ 市场总结: {len(summary_files)} 个文件")
    else:
        print("❌ 市场总结: 无")
        print("   解决方案: 运行数据构建脚本")
        print("   运行: python run.py build")
        return False
    
    # 检查市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if market_data_file.exists():
        print(f"✅ 市场数据: {market_data_file.name}")
    else:
        print("❌ 市场数据: 无")
        print("   解决方案: 运行市场数据同步脚本")
        print("   运行: python sync_market_data.py")
        return False
    
    print("✅ 数据文件诊断通过")
    return True

def diagnose_dependencies():
    """诊断依赖"""
    print("\n📦 诊断依赖")
    print("=" * 50)
    
    try:
        import requests
        print(f"✅ requests: {requests.__version__}")
    except ImportError:
        print("❌ requests: 未安装")
        print("   解决方案: 安装requests库")
        print("   运行: pip install requests")
        return False
    
    try:
        import json
        print("✅ json: 内置模块")
    except ImportError:
        print("❌ json: 内置模块异常")
        print("   解决方案: 检查Python安装")
        return False
    
    print("✅ 依赖诊断通过")
    return True

def diagnose_all():
    """诊断所有问题"""
    print("🔍 飞书同步问题完整诊断")
    print("=" * 50)
    print()
    
    diagnoses = [
        ("环境变量", diagnose_env_vars),
        (".env文件", diagnose_env_file),
        ("JSON配置文件", diagnose_json_config),
        ("飞书连接", diagnose_connection),
        ("数据文件", diagnose_data_files),
        ("依赖", diagnose_dependencies),
    ]
    
    results = []
    all_passed = True
    
    for name, diagnose_func in diagnoses:
        try:
            ok = diagnose_func()
            results.append((name, ok))
            if not ok:
                all_passed = False
        except Exception as e:
            results.append((name, False))
            all_passed = False
    
    # 显示诊断结果
    print("\n📋 诊断结果")
    print("=" * 50)
    
    for name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    # 总结
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有诊断通过！")
        print("\n下一步:")
        print("  1. 运行 'python feishu_sync.py' 同步数据")
        print("  2. 或运行 'python run.py sync-feishu' 使用一键脚本")
    else:
        print("❌ 发现问题，请根据上述提示解决")
        print("\n查看帮助: python help_feishu.py")
    
    return all_passed

def show_help():
    """显示帮助信息"""
    print("""
诊断飞书同步问题

使用方法：
  python diagnose_feishu.py [选项]

选项：
  env         诊断环境变量
  file        诊断.env文件
  json        诊断JSON配置文件
  connection  诊断飞书连接
  data        诊断数据文件
  deps        诊断依赖
  all         诊断所有问题
  help        显示帮助信息

示例：
  python diagnose_feishu.py env         # 诊断环境变量
  python diagnose_feishu.py connection  # 诊断飞书连接
  python diagnose_feishu.py all         # 诊断所有问题
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        diagnose_env_vars()
    elif command == "file":
        diagnose_env_file()
    elif command == "json":
        diagnose_json_config()
    elif command == "connection":
        diagnose_connection()
    elif command == "data":
        diagnose_data_files()
    elif command == "deps":
        diagnose_dependencies()
    elif command == "all":
        diagnose_all()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()