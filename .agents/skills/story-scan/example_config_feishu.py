#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步配置示例
"""

import os
import sys
import json
from pathlib import Path

def show_env_example():
    """显示环境变量示例"""
    print("📋 环境变量示例")
    print("=" * 50)
    
    print("Windows PowerShell:")
    print('  $env:FEISHU_APP_ID="cli_xxxxxxxxxx"')
    print('  $env:FEISHU_APP_SECRET="xxxxxxxxxx"')
    print('  $env:FEISHU_SPREADSHEET_TOKEN="shtcnxxxxxxxxxx"')
    print('  $env:FEISHU_SHEET_ID="xxxxxxxxxx"')
    print()
    print("Windows CMD:")
    print('  set FEISHU_APP_ID=cli_xxxxxxxxxx')
    print('  set FEISHU_APP_SECRET=xxxxxxxxxx')
    print('  set FEISHU_SPREADSHEET_TOKEN=shtcnxxxxxxxxxx')
    print('  set FEISHU_SHEET_ID=xxxxxxxxxx')
    print()
    print("Linux/Mac:")
    print('  export FEISHU_APP_ID="cli_xxxxxxxxxx"')
    print('  export FEISHU_APP_SECRET="xxxxxxxxxx"')
    print('  export FEISHU_SPREADSHEET_TOKEN="shtcnxxxxxxxxxx"')
    print('  export FEISHU_SHEET_ID="xxxxxxxxxx"')

def show_env_file_example():
    """显示.env文件示例"""
    print("\n📄 .env文件示例")
    print("=" * 50)
    
    print("# 飞书配置示例")
    print("FEISHU_APP_ID=cli_xxxxxxxxxx")
    print("FEISHU_APP_SECRET=xxxxxxxxxx")
    print("FEISHU_SPREADSHEET_TOKEN=shtcnxxxxxxxxxx")
    print("FEISHU_SHEET_ID=xxxxxxxxxx")
    print()
    print("# 其他配置")
    print("API_BASE_URL=https://api.deepseek.com")
    print("API_KEY=your-api-key")
    print("API_MODEL=deepseek-chat")

def show_json_config_example():
    """显示JSON配置文件示例"""
    print("\n📄 JSON配置文件示例")
    print("=" * 50)
    
    config = {
        "feishu": {
            "app_id": "cli_xxxxxxxxxx",
            "app_secret": "xxxxxxxxxx",
            "spreadsheet_token": "shtcnxxxxxxxxxx",
            "sheet_id": "xxxxxxxxxx"
        },
        "sync": {
            "auto_sync": False,
            "sync_interval": 3600,
            "data_types": ["ranks", "summary", "market_data"]
        }
    }
    
    print(json.dumps(config, indent=2, ensure_ascii=False))

def show_config_file_example():
    """显示配置文件示例"""
    print("\n📄 配置文件示例")
    print("=" * 50)
    
    print("1. .env文件")
    print("   位置: .agents/skills/story-scan/.env")
    print("   格式: KEY=VALUE")
    print()
    print("2. JSON配置文件")
    print("   位置: .agents/skills/story-scan/feishu_config.json")
    print("   格式: JSON对象")
    print()
    print("3. 环境变量")
    print("   设置方式: 操作系统环境变量")
    print("   优先级: 最高")

def show_config_values():
    """显示配置值示例"""
    print("\n📊 配置值示例")
    print("=" * 50)
    
    print("1. App ID")
    print("   格式: cli_xxxxxxxxxx")
    print("   示例: cli_a1b2c3d4e5f6")
    print("   说明: 飞书应用ID，在应用详情页面获取")
    print()
    
    print("2. App Secret")
    print("   格式: 字母数字组合")
    print("   示例: abcdefghijklmnopqrstuvwxyz")
    print("   说明: 飞书应用密钥，在应用详情页面获取")
    print()
    
    print("3. Spreadsheet Token")
    print("   格式: shtcnxxxxxxxxxx")
    print("   示例: shtcnabcdefghij")
    print("   说明: 表格token，从表格URL中获取")
    print()
    
    print("4. Sheet ID")
    print("   格式: 字母数字组合")
    print("   示例: abcdefghij")
    print("   说明: 工作表ID，在表格底部右键获取")

def show_config_creation():
    """显示配置创建示例"""
    print("\n🔧 配置创建示例")
    print("=" * 50)
    
    print("1. 创建.env文件")
    print("   python setup_feishu.py env")
    print()
    print("2. 创建JSON配置文件")
    print("   python setup_feishu.py config")
    print()
    print("3. 手动创建配置文件")
    print("   创建 .agents/skills/story-scan/.env 文件")
    print("   创建 .agents/skills/story-scan/feishu_config.json 文件")

def show_config_validation_example():
    """显示配置验证示例"""
    print("\n🔍 配置验证示例")
    print("=" * 50)
    
    print("1. 测试配置")
    print("   python test_feishu_sync.py")
    print()
    print("2. 测试连接")
    print("   python test_feishu_connection.py")
    print()
    print("3. 快速测试")
    print("   python quick_test.py")
    print()
    print("4. 验证配置")
    print("   python verify_feishu.py all")
    print()
    print("5. 诊断问题")
    print("   python diagnose_feishu.py all")

def show_config_usage_example():
    """显示配置使用示例"""
    print("\n🚀 配置使用示例")
    print("=" * 50)
    
    print("1. 同步数据")
    print("   python feishu_sync.py")
    print()
    print("2. 使用一键脚本")
    print("   python run.py sync-feishu")
    print()
    print("3. 查看状态")
    print("   python status_feishu.py")
    print()
    print("4. 查看日志")
    print("   python log_feishu.py all")
    print()
    print("5. 查看统计")
    print("   python stats_feishu.py all")

def show_config_management_example():
    """显示配置管理示例"""
    print("\n🛠️  配置管理示例")
    print("=" * 50)
    
    print("1. 备份配置")
    print("   python manage_feishu.py backup")
    print()
    print("2. 恢复配置")
    print("   python manage_feishu.py restore")
    print()
    print("3. 列出备份")
    print("   python manage_feishu.py list")
    print()
    print("4. 导出配置")
    print("   python manage_feishu.py export")
    print()
    print("5. 导入配置")
    print("   python manage_feishu.py import")
    print()
    print("6. 重置配置")
    print("   python manage_feishu.py reset")

def show_config_troubleshooting_example():
    """显示配置故障排除示例"""
    print("\n🔧 配置故障排除示例")
    print("=" * 50)
    
    print("1. 诊断问题")
    print("   python diagnose_feishu.py all")
    print()
    print("2. 修复问题")
    print("   python fix_feishu.py all")
    print()
    print("3. 验证配置")
    print("   python verify_feishu.py all")
    print()
    print("4. 查看帮助")
    print("   python config_help_feishu.py all")
    print()
    print("5. 查看教程")
    print("   python tutorial_feishu.py all")

def show_help():
    """显示帮助信息"""
    print("""
飞书同步配置示例

使用方法：
  python example_config_feishu.py [选项]

选项：
  env         显示环境变量示例
  file        显示.env文件示例
  json        显示JSON配置文件示例
  config      显示配置文件示例
  values      显示配置值示例
  creation    显示配置创建示例
  validation  显示配置验证示例
  usage       显示配置使用示例
  management  显示配置管理示例
  troubleshooting 显示配置故障排除示例
  all         显示所有示例
  help        显示帮助信息

示例：
  python example_config_feishu.py env     # 显示环境变量示例
  python example_config_feishu.py json    # 显示JSON配置文件示例
  python example_config_feishu.py all     # 显示所有示例
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        show_env_example()
    elif command == "file":
        show_env_file_example()
    elif command == "json":
        show_json_config_example()
    elif command == "config":
        show_config_file_example()
    elif command == "values":
        show_config_values()
    elif command == "creation":
        show_config_creation()
    elif command == "validation":
        show_config_validation_example()
    elif command == "usage":
        show_config_usage_example()
    elif command == "management":
        show_config_management_example()
    elif command == "troubleshooting":
        show_config_troubleshooting_example()
    elif command == "all":
        print("📋 飞书同步配置完整示例")
        print("=" * 50)
        print()
        
        show_env_example()
        show_env_file_example()
        show_json_config_example()
        show_config_file_example()
        show_config_values()
        show_config_creation()
        show_config_validation_example()
        show_config_usage_example()
        show_config_management_example()
        show_config_troubleshooting_example()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()