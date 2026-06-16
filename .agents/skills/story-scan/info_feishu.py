#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步信息
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def show_system_info():
    """显示系统信息"""
    print("💻 系统信息")
    print("=" * 50)
    
    print(f"操作系统: {sys.platform}")
    print(f"Python版本: {sys.version}")
    print(f"当前目录: {os.getcwd()}")
    print(f"脚本目录: {Path(__file__).parent}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def show_config_info():
    """显示配置信息"""
    print("\n🔧 配置信息")
    print("=" * 50)
    
    # 环境变量
    print("环境变量:")
    env_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_SPREADSHEET_TOKEN', 'FEISHU_SHEET_ID']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'SECRET' in var or 'TOKEN' in var:
                display_value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: 未设置")
    
    # .env文件
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"\n📄 .env文件: {env_file}")
        print(f"  大小: {env_file.stat().st_size} 字节")
        print(f"  修改时间: {datetime.fromtimestamp(env_file.stat().st_mtime)}")
    else:
        print(f"\n📄 .env文件: 不存在")
    
    # JSON配置文件
    config_file = Path(__file__).parent / "feishu_config.json"
    if config_file.exists():
        print(f"\n📄 JSON配置文件: {config_file}")
        print(f"  大小: {config_file.stat().st_size} 字节")
        print(f"  修改时间: {datetime.fromtimestamp(config_file.stat().st_mtime)}")
    else:
        print(f"\n📄 JSON配置文件: 不存在")

def show_data_info():
    """显示数据信息"""
    print("\n📊 数据信息")
    print("=" * 50)
    
    data_dir = Path(__file__).parent / "data"
    if data_dir.exists():
        print(f"数据目录: {data_dir}")
        
        # 排行榜数据
        rank_files = list(data_dir.glob("latest_*_ranks.json"))
        if rank_files:
            print(f"\n排行榜数据: {len(rank_files)} 个文件")
            for file in rank_files:
                print(f"  - {file.name}")
                print(f"    大小: {file.stat().st_size} 字节")
                print(f"    修改时间: {datetime.fromtimestamp(file.stat().st_mtime)}")
        else:
            print("\n排行榜数据: 无")
        
        # 市场总结
        summary_files = list(data_dir.glob("market_summary_*.json"))
        if summary_files:
            print(f"\n市场总结: {len(summary_files)} 个文件")
            for file in summary_files:
                print(f"  - {file.name}")
                print(f"    大小: {file.stat().st_size} 字节")
                print(f"    修改时间: {datetime.fromtimestamp(file.stat().st_mtime)}")
        else:
            print("\n市场总结: 无")
        
        # 市场数据
        market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
        if market_data_file.exists():
            print(f"\n市场数据: {market_data_file.name}")
            print(f"  大小: {market_data_file.stat().st_size} 字节")
            print(f"  修改时间: {datetime.fromtimestamp(market_data_file.stat().st_mtime)}")
        else:
            print("\n市场数据: 无")
    else:
        print(f"数据目录: 不存在")

def show_history_info():
    """显示历史信息"""
    print("\n📜 历史信息")
    print("=" * 50)
    
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    if history_file.exists():
        print(f"历史文件: {history_file}")
        print(f"  大小: {history_file.stat().st_size} 字节")
        print(f"  修改时间: {datetime.fromtimestamp(history_file.stat().st_mtime)}")
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if history:
                print(f"  记录数: {len(history)} 条")
                
                # 最近记录
                last_record = history[-1]
                print(f"\n最近记录:")
                print(f"  时间: {last_record.get('timestamp', '未知')}")
                print(f"  状态: {last_record.get('status', '未知')}")
                print(f"  消息: {last_record.get('message', '未知')}")
                
                # 统计
                success_count = len([r for r in history if r.get('status') == 'success'])
                error_count = len([r for r in history if r.get('status') == 'error'])
                print(f"\n统计:")
                print(f"  总记录: {len(history)}")
                print(f"  成功: {success_count}")
                print(f"  失败: {error_count}")
                
        except json.JSONDecodeError:
            print("  ❌ 历史文件格式错误")
    else:
        print("历史文件: 不存在")

def show_script_info():
    """显示脚本信息"""
    print("\n📜 脚本信息")
    print("=" * 50)
    
    scripts = [
        ("feishu_sync.py", "飞书同步主脚本"),
        ("test_feishu_sync.py", "测试飞书同步配置"),
        ("test_feishu_connection.py", "测试飞书连接"),
        ("quick_test.py", "快速测试"),
        ("setup_feishu.py", "配置飞书"),
        ("start_feishu_sync.py", "快速启动同步"),
        ("status_feishu.py", "查看同步状态"),
        ("log_feishu.py", "查看同步日志"),
        ("cleanup_feishu.py", "清理同步历史"),
        ("example_feishu_sync.py", "使用示例"),
        ("help_feishu.py", "帮助信息"),
        ("list_feishu.py", "功能列表"),
        ("config_feishu.py", "查看配置"),
        ("error_feishu.py", "查看错误"),
        ("stats_feishu.py", "查看统计"),
        ("validate_feishu.py", "验证配置"),
        ("info_feishu.py", "查看信息"),
    ]
    
    for script, description in scripts:
        script_path = Path(__file__).parent / script
        if script_path.exists():
            print(f"✅ {script}")
            print(f"   描述: {description}")
            print(f"   大小: {script_path.stat().st_size} 字节")
            print(f"   修改时间: {datetime.fromtimestamp(script_path.stat().st_mtime)}")
        else:
            print(f"❌ {script}")
            print(f"   描述: {description}")
            print(f"   状态: 不存在")

def show_documentation_info():
    """显示文档信息"""
    print("\n📖 文档信息")
    print("=" * 50)
    
    docs = [
        ("FEISHU_README.md", "详细使用指南"),
        ("SKILL.md", "技能说明"),
        ("README.md", "项目说明"),
        (".env.example", "环境变量示例"),
    ]
    
    for doc, description in docs:
        doc_path = Path(__file__).parent / doc
        if doc_path.exists():
            print(f"✅ {doc}")
            print(f"   描述: {description}")
            print(f"   大小: {doc_path.stat().st_size} 字节")
            print(f"   修改时间: {datetime.fromtimestamp(doc_path.stat().st_mtime)}")
        else:
            print(f"❌ {doc}")
            print(f"   描述: {description}")
            print(f"   状态: 不存在")

def show_help():
    """显示帮助信息"""
    print("""
查看飞书同步信息

使用方法：
  python info_feishu.py [选项]

选项：
  system      显示系统信息
  config      显示配置信息
  data        显示数据信息
  history     显示历史信息
  scripts     显示脚本信息
  docs        显示文档信息
  all         显示所有信息
  help        显示帮助信息

示例：
  python info_feishu.py system   # 显示系统信息
  python info_feishu.py config   # 显示配置信息
  python info_feishu.py all      # 显示所有信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "system":
        show_system_info()
    elif command == "config":
        show_config_info()
    elif command == "data":
        show_data_info()
    elif command == "history":
        show_history_info()
    elif command == "scripts":
        show_script_info()
    elif command == "docs":
        show_documentation_info()
    elif command == "all":
        print("📋 飞书同步完整信息")
        print("=" * 50)
        print()
        
        show_system_info()
        show_config_info()
        show_data_info()
        show_history_info()
        show_script_info()
        show_documentation_info()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()