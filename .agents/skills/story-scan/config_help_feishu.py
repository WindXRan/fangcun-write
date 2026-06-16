#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步配置帮助
"""

import os
import sys
from pathlib import Path

def show_basic_config():
    """显示基本配置"""
    print("📋 基本配置")
    print("=" * 50)
    
    print("飞书同步需要以下配置：")
    print()
    print("1. 飞书应用配置")
    print("   - App ID: 飞书应用ID")
    print("   - App Secret: 飞书应用密钥")
    print()
    print("2. 表格配置")
    print("   - Spreadsheet Token: 表格token")
    print("   - Sheet ID: 工作表ID")
    print()
    print("3. 配置方式")
    print("   - 环境变量（推荐）")
    print("   - .env文件")
    print("   - JSON配置文件")

def show_env_config():
    """显示环境变量配置"""
    print("\n🔧 环境变量配置")
    print("=" * 50)
    
    print("Windows PowerShell:")
    print('  $env:FEISHU_APP_ID="your-app-id"')
    print('  $env:FEISHU_APP_SECRET="your-app-secret"')
    print('  $env:FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
    print('  $env:FEISHU_SHEET_ID="your-sheet-id"')
    print()
    print("Windows CMD:")
    print('  set FEISHU_APP_ID=your-app-id')
    print('  set FEISHU_APP_SECRET=your-app-secret')
    print('  set FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token')
    print('  set FEISHU_SHEET_ID=your-sheet-id')
    print()
    print("Linux/Mac:")
    print('  export FEISHU_APP_ID="your-app-id"')
    print('  export FEISHU_APP_SECRET="your-app-secret"')
    print('  export FEISHU_SPREADSHEET_TOKEN="your-spreadsheet-token"')
    print('  export FEISHU_SHEET_ID="your-sheet-id"')

def show_env_file_config():
    """显示.env文件配置"""
    print("\n📄 .env文件配置")
    print("=" * 50)
    
    print("创建 .env 文件，内容如下：")
    print()
    print("# 飞书配置")
    print("FEISHU_APP_ID=your-app-id")
    print("FEISHU_APP_SECRET=your-app-secret")
    print("FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token")
    print("FEISHU_SHEET_ID=your-sheet-id")
    print()
    print("文件位置：.agents/skills/story-scan/.env")

def show_json_config():
    """显示JSON配置文件"""
    print("\n📄 JSON配置文件")
    print("=" * 50)
    
    print("创建 feishu_config.json 文件，内容如下：")
    print()
    print("{")
    print('  "feishu": {')
    print('    "app_id": "your-app-id",')
    print('    "app_secret": "your-app-secret",')
    print('    "spreadsheet_token": "your-spreadsheet-token",')
    print('    "sheet_id": "your-sheet-id"')
    print('  },')
    print('  "sync": {')
    print('    "auto_sync": false,')
    print('    "sync_interval": 3600,')
    print('    "data_types": ["ranks", "summary", "market_data"]')
    print('  }')
    print("}")
    print()
    print("文件位置：.agents/skills/story-scan/feishu_config.json")

def show_feishu_app_config():
    """显示飞书应用配置"""
    print("\n🔧 飞书应用配置")
    print("=" * 50)
    
    print("1. 创建飞书应用")
    print("   - 访问 https://open.feishu.cn/")
    print("   - 登录飞书开放平台")
    print("   - 点击'创建企业自建应用'")
    print("   - 填写应用名称和描述")
    print()
    print("2. 获取App ID和App Secret")
    print("   - 在应用详情页面")
    print("   - 找到'凭证与基础信息'")
    print("   - 记录App ID和App Secret")
    print()
    print("3. 配置应用权限")
    print("   - 点击'权限管理'")
    print("   - 添加以下权限：")
    print("     - sheets:spreadsheet - 读写表格")
    print("     - sheets:spreadsheet:readonly - 只读表格")
    print("   - 发布应用版本")

def show_spreadsheet_config():
    """显示表格配置"""
    print("\n📊 表格配置")
    print("=" * 50)
    
    print("1. 创建在线表格")
    print("   - 在飞书中创建或打开一个在线表格")
    print("   - 记录表格的token和工作表ID")
    print()
    print("2. 获取表格token")
    print("   - 从URL中获取表格token：")
    print("   - https://xxx.feishu.cn/sheets/【表格token】")
    print()
    print("3. 获取工作表ID")
    print("   - 在表格底部，右键点击工作表标签")
    print("   - 选择'复制工作表ID'")
    print()
    print("4. 添加应用到表格协作者")
    print("   - 在表格右上角点击'分享'")
    print("   - 添加飞书应用为协作者")
    print("   - 给予读写权限")

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

def show_config_validation():
    """显示配置验证"""
    print("\n🔍 配置验证")
    print("=" * 50)
    
    print("配置完成后，可以运行以下命令验证配置：")
    print()
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

def show_config_tools():
    """显示配置工具"""
    print("\n🛠️  配置工具")
    print("=" * 50)
    
    print("1. 配置飞书")
    print("   python setup_feishu.py env      # 创建.env文件")
    print("   python setup_feishu.py config   # 创建JSON配置文件")
    print()
    print("2. 查看配置")
    print("   python config_feishu.py all     # 查看所有配置信息")
    print()
    print("3. 验证配置")
    print("   python verify_feishu.py all     # 验证所有配置")
    print()
    print("4. 诊断问题")
    print("   python diagnose_feishu.py all   # 诊断所有问题")
    print()
    print("5. 修复问题")
    print("   python fix_feishu.py all        # 修复所有问题")
    print()
    print("6. 管理配置")
    print("   python manage_feishu.py backup  # 备份配置")
    print("   python manage_feishu.py restore # 恢复配置")

def show_troubleshooting():
    """显示故障排除"""
    print("\n🔧 故障排除")
    print("=" * 50)
    
    print("1. 获取token失败")
    print("   - 检查App ID和App Secret是否正确")
    print("   - 确认飞书应用已创建")
    print("   - 确认应用已发布版本")
    print()
    print("2. 读取表格失败")
    print("   - 检查表格token和工作表ID是否正确")
    print("   - 确认应用有表格读取权限")
    print()
    print("3. 写入表格失败")
    print("   - 检查应用是否有表格写入权限")
    print("   - 确认表格未被锁定")
    print()
    print("4. 数据加载失败")
    print("   - 检查数据文件是否存在")
    print("   - 运行数据采集脚本")
    print()
    print("5. 网络请求超时")
    print("   - 检查网络连接")
    print("   - 检查代理设置")

def show_help():
    """显示帮助信息"""
    print("""
飞书同步配置帮助

使用方法：
  python config_help_feishu.py [选项]

选项：
  basic       显示基本配置
  env         显示环境变量配置
  file        显示.env文件配置
  json        显示JSON配置文件
  app         显示飞书应用配置
  spreadsheet 显示表格配置
  priority    显示配置优先级
  validation  显示配置验证
  tools       显示配置工具
  troubleshooting 显示故障排除
  all         显示所有帮助信息
  help        显示帮助信息

示例：
  python config_help_feishu.py basic       # 显示基本配置
  python config_help_feishu.py env         # 显示环境变量配置
  python config_help_feishu.py all         # 显示所有帮助信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "basic":
        show_basic_config()
    elif command == "env":
        show_env_config()
    elif command == "file":
        show_env_file_config()
    elif command == "json":
        show_json_config()
    elif command == "app":
        show_feishu_app_config()
    elif command == "spreadsheet":
        show_spreadsheet_config()
    elif command == "priority":
        show_config_priority()
    elif command == "validation":
        show_config_validation()
    elif command == "tools":
        show_config_tools()
    elif command == "troubleshooting":
        show_troubleshooting()
    elif command == "all":
        print("📋 飞书同步配置完整帮助")
        print("=" * 50)
        print()
        
        show_basic_config()
        show_env_config()
        show_env_file_config()
        show_json_config()
        show_feishu_app_config()
        show_spreadsheet_config()
        show_config_priority()
        show_config_validation()
        show_config_tools()
        show_troubleshooting()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()