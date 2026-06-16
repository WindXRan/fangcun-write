#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速配置飞书同步功能
"""

import os
import sys
import json
from pathlib import Path

def create_env_file():
    """创建.env文件"""
    env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        print(f"⚠️  .env文件已存在: {env_file}")
        overwrite = input("是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("跳过创建.env文件")
            return False
    
    print("\n📝 请输入飞书配置信息：")
    print("（如果还没有，请先在飞书开放平台创建应用）")
    print()
    
    app_id = input("App ID: ").strip()
    app_secret = input("App Secret: ").strip()
    spreadsheet_token = input("表格token: ").strip()
    sheet_id = input("工作表ID: ").strip()
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 所有字段都是必填的")
        return False
    
    # 写入.env文件
    env_content = f"""# 飞书配置
FEISHU_APP_ID={app_id}
FEISHU_APP_SECRET={app_secret}
FEISHU_SPREADSHEET_TOKEN={spreadsheet_token}
FEISHU_SHEET_ID={sheet_id}
"""
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"\n✅ .env文件已创建: {env_file}")
    return True

def create_config_file():
    """创建配置文件"""
    config_file = Path(__file__).parent / "feishu_config.json"
    
    if config_file.exists():
        print(f"⚠️  配置文件已存在: {config_file}")
        overwrite = input("是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("跳过创建配置文件")
            return False
    
    print("\n📝 请输入飞书配置信息：")
    print("（如果还没有，请先在飞书开放平台创建应用）")
    print()
    
    app_id = input("App ID: ").strip()
    app_secret = input("App Secret: ").strip()
    spreadsheet_token = input("表格token: ").strip()
    sheet_id = input("工作表ID: ").strip()
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 所有字段都是必填的")
        return False
    
    # 创建配置
    config = {
        "feishu": {
            "app_id": app_id,
            "app_secret": app_secret,
            "spreadsheet_token": spreadsheet_token,
            "sheet_id": sheet_id
        },
        "sync": {
            "auto_sync": False,
            "sync_interval": 3600,
            "data_types": ["ranks", "summary", "market_data"]
        }
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 配置文件已创建: {config_file}")
    return True

def show_help():
    """显示帮助信息"""
    print("""
飞书同步配置工具

使用方法：
  python setup_feishu.py [选项]

选项：
  env       创建.env环境变量文件
  config    创建JSON配置文件
  help      显示帮助信息

示例：
  python setup_feishu.py env      # 创建.env文件
  python setup_feishu.py config   # 创建JSON配置文件
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "env":
        create_env_file()
    elif command == "config":
        create_config_file()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()