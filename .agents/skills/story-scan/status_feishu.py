#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步状态
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def check_env_config():
    """检查环境变量配置"""
    print("🔧 环境变量配置:")
    
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    all_configured = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: 未设置")
            all_configured = False
    
    return all_configured

def check_env_file():
    """检查.env文件"""
    print("\n📄 .env文件:")
    
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"  ✅ 文件存在: {env_file}")
        
        # 读取文件内容
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有飞书配置
        feishu_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
        for var in feishu_vars:
            if var in content:
                print(f"    ✅ {var}: 已配置")
            else:
                print(f"    ⚠️  {var}: 未配置")
        
        return True
    else:
        print(f"  ❌ 文件不存在: {env_file}")
        return False

def check_config_file():
    """检查配置文件"""
    print("\n📄 配置文件:")
    
    config_file = Path(__file__).parent / "feishu_config.json"
    if config_file.exists():
        print(f"  ✅ 文件存在: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            feishu_config = config.get('feishu', {})
            if feishu_config:
                print(f"    ✅ 飞书配置: 已配置")
                for key, value in feishu_config.items():
                    if 'secret' in key.lower() or 'token' in key.lower():
                        display_value = str(value)[:4] + '****' + str(value)[-4:] if len(str(value)) > 8 else '****'
                    else:
                        display_value = value
                    print(f"      {key}: {display_value}")
            else:
                print(f"    ❌ 飞书配置: 未配置")
            
            return True
        except json.JSONDecodeError:
            print(f"    ❌ 配置文件格式错误")
            return False
    else:
        print(f"  ❌ 文件不存在: {config_file}")
        return False

def check_data_files():
    """检查数据文件"""
    print("\n📊 数据文件:")
    
    data_dir = Path(__file__).parent / "data"
    if not data_dir.exists():
        print(f"  ❌ 数据目录不存在: {data_dir}")
        return False
    
    print(f"  ✅ 数据目录: {data_dir}")
    
    # 检查排行榜数据
    rank_files = list(data_dir.glob("latest_*_ranks.json"))
    if rank_files:
        print(f"  ✅ 排行榜数据: {len(rank_files)} 个文件")
        for file in rank_files:
            print(f"    - {file.name}")
    else:
        print(f"  ❌ 排行榜数据: 无")
    
    # 检查市场总结
    summary_files = list(data_dir.glob("market_summary_*.json"))
    if summary_files:
        print(f"  ✅ 市场总结: {len(summary_files)} 个文件")
        for file in summary_files:
            print(f"    - {file.name}")
    else:
        print(f"  ❌ 市场总结: 无")
    
    # 检查市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if market_data_file.exists():
        print(f"  ✅ 市场数据: {market_data_file.name}")
    else:
        print(f"  ❌ 市场数据: 无")
    
    return True

def check_dependencies():
    """检查依赖"""
    print("\n📦 依赖检查:")
    
    try:
        import requests
        print(f"  ✅ requests: {requests.__version__}")
    except ImportError:
        print(f"  ❌ requests: 未安装")
        return False
    
    return True

def show_sync_history():
    """显示同步历史"""
    print("\n📜 同步历史:")
    
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if history:
                print(f"  ✅ 同步记录: {len(history)} 条")
                # 显示最近5条
                recent = history[-5:]
                for record in recent:
                    timestamp = record.get('timestamp', '未知')
                    status = record.get('status', '未知')
                    message = record.get('message', '')
                    print(f"    - {timestamp}: {status} {message}")
            else:
                print(f"  ⚠️  同步记录: 无")
        except json.JSONDecodeError:
            print(f"  ❌ 同步历史文件格式错误")
    else:
        print(f"  ⚠️  同步历史文件不存在")

def show_recommendations():
    """显示建议"""
    print("\n💡 建议:")
    
    # 检查是否已配置
    env_configured = check_env_config()
    env_file_exists = check_env_file()
    config_file_exists = check_config_file()
    
    if not env_configured and not env_file_exists and not config_file_exists:
        print("  1. 运行 'python setup_feishu.py env' 创建.env文件")
        print("  2. 或运行 'python setup_feishu.py config' 创建JSON配置文件")
        print("  3. 确保飞书应用有表格读写权限")
    elif env_configured:
        print("  1. 运行 'python quick_test.py' 测试配置")
        print("  2. 运行 'python feishu_sync.py' 同步数据")
        print("  3. 查看 FEISHU_README.md 了解更多用法")
    else:
        print("  1. 检查配置文件中的飞书信息是否正确")
        print("  2. 确保飞书应用有表格读写权限")
        print("  3. 运行 'python quick_test.py' 测试配置")

def main():
    """主函数"""
    print("📊 飞书同步状态检查")
    print("=" * 50)
    
    # 检查各项配置
    env_configured = check_env_config()
    env_file_exists = check_env_file()
    config_file_exists = check_config_file()
    data_exists = check_data_files()
    deps_ok = check_dependencies()
    
    # 显示同步历史
    show_sync_history()
    
    # 显示建议
    show_recommendations()
    
    # 总结
    print("\n" + "=" * 50)
    print("📋 状态总结:")
    
    if env_configured or env_file_exists or config_file_exists:
        print("  ✅ 飞书配置: 已配置")
    else:
        print("  ❌ 飞书配置: 未配置")
    
    if data_exists:
        print("  ✅ 数据文件: 存在")
    else:
        print("  ❌ 数据文件: 不存在")
    
    if deps_ok:
        print("  ✅ 依赖: 已安装")
    else:
        print("  ❌ 依赖: 未安装")
    
    print("\n🚀 下一步:")
    if env_configured and data_exists and deps_ok:
        print("  1. 运行 'python quick_test.py' 测试配置")
        print("  2. 运行 'python feishu_sync.py' 同步数据")
    else:
        print("  1. 解决上述问题")
        print("  2. 运行 'python setup_feishu.py' 配置飞书")
        print("  3. 查看 FEISHU_README.md 了解详细步骤")

if __name__ == "__main__":
    main()