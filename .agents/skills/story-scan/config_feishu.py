#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步配置
"""

import os
import sys
import json
from pathlib import Path

def show_env_config():
    """显示环境变量配置"""
    print("🔧 环境变量配置")
    print("=" * 50)
    
    required_vars = [
        ('FEISHU_APP_ID', '飞书应用ID'),
        ('FEISHU_APP_SECRET', '飞书应用密钥'),
        ('FEISHU_SPREADSHEET_TOKEN', '表格token'),
        ('FEISHU_SHEET_ID', '工作表ID'),
    ]
    
    all_configured = True
    
    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
            print(f"   描述: {description}")
        else:
            print(f"❌ {var}: 未设置")
            print(f"   描述: {description}")
            all_configured = False
    
    return all_configured

def show_env_file_config():
    """显示.env文件配置"""
    print("\n📄 .env文件配置")
    print("=" * 50)
    
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print(f"❌ .env文件不存在: {env_file}")
        return False
    
    print(f"✅ .env文件存在: {env_file}")
    
    # 读取文件内容
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析配置
    config = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    # 显示配置
    feishu_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    
    for var in feishu_vars:
        if var in config:
            value = config[var]
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: 未配置")
    
    return True

def show_json_config():
    """显示JSON配置文件"""
    print("\n📄 JSON配置文件")
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
        if feishu_config:
            print("✅ 飞书配置:")
            for key, value in feishu_config.items():
                if 'secret' in key.lower() or 'token' in key.lower():
                    display_value = str(value)[:4] + '****' + str(value)[-4:] if len(str(value)) > 8 else '****'
                else:
                    display_value = value
                print(f"   {key}: {display_value}")
        else:
            print("❌ 飞书配置: 未配置")
        
        sync_config = config.get('sync', {})
        if sync_config:
            print("\n✅ 同步配置:")
            for key, value in sync_config.items():
                print(f"   {key}: {value}")
        else:
            print("\n❌ 同步配置: 未配置")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ JSON配置文件格式错误")
        return False

def show_config_priority():
    """显示配置优先级"""
    print("\n📊 配置优先级")
    print("=" * 50)
    
    print("飞书同步功能按以下优先级读取配置：")
    print()
    print("1. 环境变量（最高优先级）")
    print("   - FEISHU_APP_ID")
    print("   - FEISHU_APP_SECRET")
    print("   - FEISHU_SPREADSHEET_TOKEN")
    print("   - FEISHU_SHEET_ID")
    print()
    print("2. .env文件（中等优先级）")
    print("   - 位置: .agents/skills/story-scan/.env")
    print("   - 格式: KEY=VALUE")
    print()
    print("3. JSON配置文件（最低优先级）")
    print("   - 位置: .agents/skills/story-scan/feishu_config.json")
    print("   - 格式: JSON对象")
    print()
    print("建议：使用环境变量或.env文件配置，避免将敏感信息提交到代码仓库。")

def show_config_examples():
    """显示配置示例"""
    print("\n📝 配置示例")
    print("=" * 50)
    
    print("1. 环境变量配置示例：")
    print("   Windows PowerShell:")
    print('   $env:FEISHU_APP_ID="your-app-id"')
    print('   $env:FEISHU_APP_SECRET="your-app-secret"')
    print('   $env:FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
    print('   $env:FEISHU_SHEET_ID="your-sheet-id"')
    print()
    print("   Linux/Mac:")
    print('   export FEISHU_APP_ID="your-app-id"')
    print('   export FEISHU_APP_SECRET="your-app-secret"')
    print('   export FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
    print('   export FEISHU_SHEET_ID="your-sheet-id"')
    print()
    print("2. .env文件配置示例：")
    print("   FEISHU_APP_ID=your-app-id")
    print("   FEISHU_APP_SECRET=your-app-secret")
    print("   FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token")
    print("   FEISHU_SHEET_ID=your-sheet-id")
    print()
    print("3. JSON配置文件示例：")
    print('   {')
    print('     "feishu": {')
    print('       "app_id": "your-app-id",')
    print('       "app_secret": "your-app-secret",')
    print('       "spreadsheet_token": "your-spreadsheet-token",')
    print('       "sheet_id": "your-sheet-id"')
    print('     },')
    print('     "sync": {')
    print('       "auto_sync": false,')
    print('       "sync_interval": 3600,')
    print('       "data_types": ["ranks", "summary", "market_data"]')
    print('     }')
    print('   }')

def show_help():
    """显示帮助信息"""
    print("""
查看飞书同步配置

使用方法：
  python config_feishu.py [选项]

选项：
  env       显示环境变量配置
  file      显示.env文件配置
  json      显示JSON配置文件
  priority  显示配置优先级
  examples  显示配置示例
  all       显示所有配置信息
  help      显示帮助信息

示例：
  python config_feishu.py env       # 显示环境变量配置
  python config_feishu.py file      # 显示.env文件配置
  python config_feishu.py json      # 显示JSON配置文件
  python config_feishu.py all       # 显示所有配置信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        show_env_config()
    elif command == "file":
        show_env_file_config()
    elif command == "json":
        show_json_config()
    elif command == "priority":
        show_config_priority()
    elif command == "examples":
        show_config_examples()
    elif command == "all":
        print("📋 飞书同步配置完整信息")
        print("=" * 50)
        print()
        
        show_env_config()
        show_env_file_config()
        show_json_config()
        show_config_priority()
        show_config_examples()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()