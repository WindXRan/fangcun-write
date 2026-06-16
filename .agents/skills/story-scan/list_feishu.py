#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出飞书同步功能
"""

import os
import sys
from pathlib import Path

def list_scripts():
    """列出所有脚本"""
    print("📜 飞书同步脚本列表")
    print("=" * 50)
    
    scripts = [
        ("feishu_sync.py", "飞书同步主脚本", "同步数据到飞书在线表格"),
        ("test_feishu_sync.py", "测试飞书同步配置", "测试导入、数据加载、飞书配置"),
        ("test_feishu_connection.py", "测试飞书连接", "测试获取token、读写表格"),
        ("quick_test.py", "快速测试", "快速测试飞书同步功能"),
        ("setup_feishu.py", "配置飞书", "创建.env或JSON配置文件"),
        ("start_feishu_sync.py", "快速启动同步", "一键启动飞书同步"),
        ("status_feishu.py", "查看同步状态", "查看配置、数据、历史状态"),
        ("log_feishu.py", "查看同步日志", "查看日志、历史、错误、统计"),
        ("cleanup_feishu.py", "清理同步历史", "清理历史记录和临时文件"),
        ("example_feishu_sync.py", "使用示例", "查看使用示例和自定义方法"),
        ("help_feishu.py", "帮助信息", "查看详细帮助信息"),
        ("list_feishu.py", "功能列表", "列出所有功能和脚本"),
    ]
    
    for i, (script, name, description) in enumerate(scripts, 1):
        script_path = Path(__file__).parent / script
        exists = "✅" if script_path.exists() else "❌"
        print(f"{i:2d}. {exists} {script}")
        print(f"    名称: {name}")
        print(f"    描述: {description}")
        print()

def list_commands():
    """列出所有命令"""
    print("🚀 飞书同步命令列表")
    print("=" * 50)
    
    commands = [
        ("python run.py sync-feishu", "使用一键脚本同步数据"),
        ("python feishu_sync.py", "直接运行同步脚本"),
        ("python feishu_sync.py --test", "测试模式（只读取数据不写入）"),
        ("python setup_feishu.py env", "创建.env配置文件"),
        ("python setup_feishu.py config", "创建JSON配置文件"),
        ("python test_feishu_sync.py", "测试同步配置"),
        ("python test_feishu_connection.py", "测试飞书连接"),
        ("python quick_test.py", "快速测试"),
        ("python start_feishu_sync.py", "快速启动同步"),
        ("python status_feishu.py", "查看同步状态"),
        ("python log_feishu.py log", "查看同步日志"),
        ("python log_feishu.py history", "查看同步历史"),
        ("python log_feishu.py errors", "查看错误记录"),
        ("python log_feishu.py stats", "查看统计信息"),
        ("python cleanup_feishu.py history", "清理同步历史"),
        ("python cleanup_feishu.py temp", "清理临时文件"),
        ("python example_feishu_sync.py", "查看使用示例"),
        ("python help_feishu.py", "查看帮助信息"),
        ("python list_feishu.py", "查看功能列表"),
    ]
    
    for i, (command, description) in enumerate(commands, 1):
        print(f"{i:2d}. {command}")
        print(f"    描述: {description}")
        print()

def list_features():
    """列出所有功能"""
    print("🎯 飞书同步功能列表")
    print("=" * 50)
    
    features = [
        ("数据同步", "将story-scan采集的数据同步到飞书在线表格"),
        ("配置管理", "创建和管理飞书配置文件"),
        ("连接测试", "测试飞书连接和表格读写权限"),
        ("状态监控", "查看同步状态、配置状态、数据状态"),
        ("日志管理", "查看同步日志、历史记录、错误信息"),
        ("历史清理", "清理同步历史记录和临时文件"),
        ("快速启动", "一键启动飞书同步功能"),
        ("使用示例", "查看使用示例和自定义方法"),
        ("帮助信息", "查看详细帮助信息和故障排除"),
        ("功能列表", "列出所有功能和脚本"),
    ]
    
    for i, (feature, description) in enumerate(features, 1):
        print(f"{i:2d}. {feature}")
        print(f"    描述: {description}")
        print()

def list_data_types():
    """列出同步的数据类型"""
    print("📊 同步的数据类型")
    print("=" * 50)
    
    data_types = [
        ("排行榜数据", "A-H列", "女频新书榜、男频新书榜等"),
        ("市场总结", "J-L列", "高频题材、热度趋势"),
        ("市场数据", "N-S列", "热门题材、书名模式、标签组合等"),
    ]
    
    for i, (data_type, columns, description) in enumerate(data_types, 1):
        print(f"{i}. {data_type}")
        print(f"   列位置: {columns}")
        print(f"   描述: {description}")
        print()

def list_dependencies():
    """列出依赖"""
    print("📦 依赖列表")
    print("=" * 50)
    
    dependencies = [
        ("requests", "HTTP请求库", "必需"),
        ("python-dotenv", "环境变量管理", "可选"),
        ("json", "JSON处理", "内置"),
        ("pathlib", "路径处理", "内置"),
        ("datetime", "日期时间处理", "内置"),
    ]
    
    for i, (package, description, required) in enumerate(dependencies, 1):
        print(f"{i}. {package}")
        print(f"   描述: {description}")
        print(f"   必需: {required}")
        print()

def list_related_files():
    """列出相关文件"""
    print("📄 相关文件")
    print("=" * 50)
    
    files = [
        (".env.example", "环境变量示例文件"),
        (".env", "环境变量配置文件"),
        ("feishu_config.json", "JSON配置文件"),
        ("feishu_sync_history.json", "同步历史记录"),
        ("feishu_sync.log", "同步日志文件"),
        ("FEISHU_README.md", "详细使用指南"),
        ("SKILL.md", "技能说明"),
        ("README.md", "项目说明"),
    ]
    
    for i, (filename, description) in enumerate(files, 1):
        file_path = Path(__file__).parent / filename
        exists = "✅" if file_path.exists() else "❌"
        print(f"{i}. {exists} {filename}")
        print(f"   描述: {description}")
        print()

def show_help():
    """显示帮助信息"""
    print("""
列出飞书同步功能

使用方法：
  python list_feishu.py [选项]

选项：
  scripts     列出所有脚本
  commands    列出所有命令
  features    列出所有功能
  data        列出同步的数据类型
  deps        列出依赖
  files       列出相关文件
  all         列出所有信息
  help        显示帮助信息

示例：
  python list_feishu.py scripts   # 列出所有脚本
  python list_feishu.py commands  # 列出所有命令
  python list_feishu.py features  # 列出所有功能
  python list_feishu.py all       # 列出所有信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "scripts":
        list_scripts()
    elif command == "commands":
        list_commands()
    elif command == "features":
        list_features()
    elif command == "data":
        list_data_types()
    elif command == "deps":
        list_dependencies()
    elif command == "files":
        list_related_files()
    elif command == "all":
        print("📋 飞书同步功能完整列表")
        print("=" * 50)
        print()
        
        list_scripts()
        list_commands()
        list_features()
        list_data_types()
        list_dependencies()
        list_related_files()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()