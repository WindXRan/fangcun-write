#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步帮助信息
"""

import sys

def show_main_help():
    """显示主帮助信息"""
    print("""
飞书同步功能帮助

🎯 功能简介
  将story-scan采集的数据自动同步到飞书在线表格，方便团队协作和数据分析。

📦 包含的脚本
  feishu_sync.py           - 飞书同步主脚本
  test_feishu_sync.py      - 测试飞书同步配置
  test_feishu_connection.py - 测试飞书连接
  quick_test.py            - 快速测试
  setup_feishu.py          - 配置飞书
  start_feishu_sync.py     - 快速启动同步
  status_feishu.py         - 查看同步状态
  log_feishu.py            - 查看同步日志
  cleanup_feishu.py        - 清理同步历史
  example_feishu_sync.py   - 使用示例

🚀 快速开始
  1. 配置飞书：
     python setup_feishu.py env

  2. 测试配置：
     python test_feishu_sync.py

  3. 同步数据：
     python feishu_sync.py
     或
     python run.py sync-feishu

📋 详细命令
  help      - 显示此帮助信息
  setup     - 配置飞书
  test      - 测试配置
  sync      - 同步数据
  status    - 查看状态
  log       - 查看日志
  cleanup   - 清理历史
  example   - 查看示例
  all       - 显示所有帮助

📖 文档
  FEISHU_README.md         - 详细使用指南
  SKILL.md                 - 技能说明
  README.md                - 项目说明

🔗 相关链接
  飞书开放平台: https://open.feishu.cn/
  飞书表格API: https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview
""")

def show_setup_help():
    """显示配置帮助"""
    print("""
配置飞书帮助

🎯 功能
  快速配置飞书同步功能

🚀 使用方法
  python setup_feishu.py [选项]

📋 选项
  env       创建.env环境变量文件
  config    创建JSON配置文件
  help      显示帮助信息

📝 配置步骤
  1. 在飞书开放平台创建应用
  2. 获取App ID和App Secret
  3. 创建在线表格，获取表格token和工作表ID
  4. 给应用添加表格读写权限
  5. 运行配置脚本

💡 示例
  python setup_feishu.py env      # 创建.env文件
  python setup_feishu.py config   # 创建JSON配置文件
""")

def show_test_help():
    """显示测试帮助"""
    print("""
测试配置帮助

🎯 功能
  测试飞书同步配置是否正确

🚀 使用方法
  python test_feishu_sync.py
  python test_feishu_connection.py
  python quick_test.py

📋 测试内容
  1. 检查环境变量配置
  2. 测试数据加载
  3. 测试飞书连接
  4. 测试表格读写

💡 示例
  python test_feishu_sync.py      # 测试同步配置
  python test_feishu_connection.py # 测试飞书连接
  python quick_test.py            # 快速测试
""")

def show_sync_help():
    """显示同步帮助"""
    print("""
同步数据帮助

🎯 功能
  将数据同步到飞书在线表格

🚀 使用方法
  python feishu_sync.py [选项]
  python run.py sync-feishu

📋 选项
  --data-dir   指定数据目录
  --test       测试模式（只读取数据不写入）

📊 同步的数据
  1. 排行榜数据（A-H列）
  2. 市场总结（J-L列）
  3. 市场数据（N-S列）

💡 示例
  python feishu_sync.py                    # 同步数据
  python feishu_sync.py --test             # 测试模式
  python feishu_sync.py --data-dir ./data  # 指定数据目录
  python run.py sync-feishu                # 使用一键脚本
""")

def show_status_help():
    """显示状态帮助"""
    print("""
查看状态帮助

🎯 功能
  查看飞书同步的状态和配置

🚀 使用方法
  python status_feishu.py

📋 显示的信息
  1. 环境变量配置
  2. 配置文件状态
  3. 数据文件状态
  4. 依赖安装状态
  5. 同步历史记录
  6. 建议和下一步

💡 示例
  python status_feishu.py
""")

def show_log_help():
    """显示日志帮助"""
    print("""
查看日志帮助

🎯 功能
  查看飞书同步的日志和历史记录

🚀 使用方法
  python log_feishu.py [选项]

📋 选项
  log       显示同步日志文件
  history   显示同步历史记录
  errors    显示最近的错误
  stats     显示成功统计
  all       显示所有信息
  help      显示帮助信息

💡 示例
  python log_feishu.py log       # 显示日志文件
  python log_feishu.py history   # 显示同步历史
  python log_feishu.py errors    # 显示错误记录
  python log_feishu.py stats     # 显示统计信息
  python log_feishu.py all       # 显示所有信息
""")

def show_cleanup_help():
    """显示清理帮助"""
    print("""
清理历史帮助

🎯 功能
  清理飞书同步的历史记录和临时文件

🚀 使用方法
  python cleanup_feishu.py [选项]

📋 选项
  history   清理同步历史记录
  temp      清理临时文件
  all       清理所有（历史记录+临时文件）
  help      显示帮助信息

⚠️  警告
  清理操作不可恢复，请谨慎使用！

💡 示例
  python cleanup_feishu.py history   # 清理同步历史
  python cleanup_feishu.py temp      # 清理临时文件
  python cleanup_feishu.py all       # 清理所有
""")

def show_example_help():
    """显示示例帮助"""
    print("""
使用示例帮助

🎯 功能
  查看飞书同步的使用示例

🚀 使用方法
  python example_feishu_sync.py

📋 示例内容
  1. 基本使用示例
  2. 自定义同步示例
  3. 环境变量配置示例
  4. 故障排除示例

💡 示例
  python example_feishu_sync.py
""")

def show_all_help():
    """显示所有帮助"""
    print("""
飞书同步功能完整帮助

🎯 功能简介
  将story-scan采集的数据自动同步到飞书在线表格，方便团队协作和数据分析。

📦 包含的脚本
  feishu_sync.py           - 飞书同步主脚本
  test_feishu_sync.py      - 测试飞书同步配置
  test_feishu_connection.py - 测试飞书连接
  quick_test.py            - 快速测试
  setup_feishu.py          - 配置飞书
  start_feishu_sync.py     - 快速启动同步
  status_feishu.py         - 查看同步状态
  log_feishu.py            - 查看同步日志
  cleanup_feishu.py        - 清理同步历史
  example_feishu_sync.py   - 使用示例

🚀 快速开始
  1. 配置飞书：
     python setup_feishu.py env

  2. 测试配置：
     python test_feishu_sync.py

  3. 同步数据：
     python feishu_sync.py
     或
     python run.py sync-feishu

📋 详细命令
  help      - 显示此帮助信息
  setup     - 配置飞书
  test      - 测试配置
  sync      - 同步数据
  status    - 查看状态
  log       - 查看日志
  cleanup   - 清理历史
  example   - 查看示例
  all       - 显示所有帮助

📖 文档
  FEISHU_README.md         - 详细使用指南
  SKILL.md                 - 技能说明
  README.md                - 项目说明

🔗 相关链接
  飞书开放平台: https://open.feishu.cn/
  飞书表格API: https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview

📊 同步的数据
  1. 排行榜数据（A-H列）
  2. 市场总结（J-L列）
  3. 市场数据（N-S列）

🔧 故障排除
  1. 检查飞书环境变量是否正确设置
  2. 确认飞书应用有表格读写权限
  3. 检查表格token和工作表ID是否正确
  4. 查看飞书开放平台的应用日志
  5. 查看 FEISHU_README.md 了解详细步骤
""")

def show_help(command: str = None):
    """显示帮助信息"""
    if command is None or command == "help":
        show_main_help()
    elif command == "setup":
        show_setup_help()
    elif command == "test":
        show_test_help()
    elif command == "sync":
        show_sync_help()
    elif command == "status":
        show_status_help()
    elif command == "log":
        show_log_help()
    elif command == "cleanup":
        show_cleanup_help()
    elif command == "example":
        show_example_help()
    elif command == "all":
        show_all_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_main_help()

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_main_help()
        return
    
    command = sys.argv[1].lower()
    show_help(command)

if __name__ == "__main__":
    main()