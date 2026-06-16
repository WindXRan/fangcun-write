#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书同步使用教程
"""

import os
import sys
from pathlib import Path

def show_quick_start():
    """显示快速开始"""
    print("🚀 快速开始")
    print("=" * 50)
    
    print("1. 配置飞书")
    print("   python setup_feishu.py env")
    print()
    print("2. 测试配置")
    print("   python test_feishu_sync.py")
    print()
    print("3. 同步数据")
    print("   python feishu_sync.py")
    print()
    print("4. 查看状态")
    print("   python status_feishu.py")

def show_detailed_steps():
    """显示详细步骤"""
    print("\n📋 详细步骤")
    print("=" * 50)
    
    print("第一步：创建飞书应用")
    print("1. 访问 https://open.feishu.cn/")
    print("2. 登录飞书开放平台")
    print("3. 点击'创建企业自建应用'")
    print("4. 填写应用名称和描述")
    print("5. 记录App ID和App Secret")
    print()
    
    print("第二步：配置应用权限")
    print("1. 在应用详情页面，点击'权限管理'")
    print("2. 添加以下权限：")
    print("   - sheets:spreadsheet - 读写表格")
    print("   - sheets:spreadsheet:readonly - 只读表格")
    print("3. 发布应用版本")
    print()
    
    print("第三步：创建在线表格")
    print("1. 在飞书中创建或打开一个在线表格")
    print("2. 从URL中获取表格token：")
    print("   https://xxx.feishu.cn/sheets/【表格token】")
    print("3. 获取工作表ID：")
    print("   - 在表格底部，右键点击工作表标签")
    print("   - 选择'复制工作表ID'")
    print()
    
    print("第四步：配置环境变量")
    print("运行配置脚本：")
    print("   python setup_feishu.py env")
    print()
    print("或手动创建.env文件：")
    print("   FEISHU_APP_ID=your-app-id")
    print("   FEISHU_APP_SECRET=your-app-secret")
    print("   FEISHU_SPREADSHEET_TOKEN=your-spreadsheet-token")
    print("   FEISHU_SHEET_ID=your-sheet-id")
    print()
    
    print("第五步：测试配置")
    print("运行测试脚本：")
    print("   python test_feishu_sync.py")
    print()
    print("或运行快速测试：")
    print("   python quick_test.py")
    print()
    
    print("第六步：同步数据")
    print("运行同步脚本：")
    print("   python feishu_sync.py")
    print()
    print("或使用一键脚本：")
    print("   python run.py sync-feishu")

def show_common_scenarios():
    """显示常见场景"""
    print("\n🎯 常见场景")
    print("=" * 50)
    
    print("场景1：首次配置")
    print("1. 运行配置脚本：python setup_feishu.py env")
    print("2. 编辑.env文件，填入正确的飞书配置")
    print("3. 测试配置：python test_feishu_sync.py")
    print("4. 同步数据：python feishu_sync.py")
    print()
    
    print("场景2：修改配置")
    print("1. 编辑.env文件或feishu_config.json文件")
    print("2. 测试配置：python test_feishu_sync.py")
    print("3. 同步数据：python feishu_sync.py")
    print()
    
    print("场景3：查看同步状态")
    print("1. 查看状态：python status_feishu.py")
    print("2. 查看日志：python log_feishu.py all")
    print("3. 查看统计：python stats_feishu.py all")
    print()
    
    print("场景4：排查问题")
    print("1. 诊断问题：python diagnose_feishu.py all")
    print("2. 修复问题：python fix_feishu.py all")
    print("3. 验证配置：python verify_feishu.py all")
    print()
    
    print("场景5：备份恢复")
    print("1. 备份配置：python manage_feishu.py backup")
    print("2. 恢复配置：python manage_feishu.py restore")
    print("3. 列出备份：python manage_feishu.py list")

def show_advanced_usage():
    """显示高级用法"""
    print("\n🔧 高级用法")
    print("=" * 50)
    
    print("1. 自定义同步逻辑")
    print("   - 编辑 feishu_sync.py 文件")
    print("   - 修改数据准备函数")
    print("   - 调整同步逻辑")
    print()
    
    print("2. 定时自动同步")
    print("   Windows任务计划程序：")
    print("   - 打开'任务计划程序'")
    print("   - 创建基本任务")
    print("   - 设置触发器（每天定时）")
    print("   - 设置操作（运行Python脚本）")
    print()
    print("   Linux/Mac Cron：")
    print("   - 编辑crontab：crontab -e")
    print("   - 添加定时任务：")
    print("     0 8 * * * cd /path/to/.agents/skills/story-scan && python run.py sync-feishu")
    print()
    
    print("3. 集成到其他系统")
    print("   - 导入 feishu_sync 模块")
    print("   - 调用 FeishuSync 类")
    print("   - 自定义同步逻辑")
    print()
    
    print("4. 扩展数据类型")
    print("   - 修改 load_latest_data() 函数")
    print("   - 添加新的数据文件")
    print("   - 修改数据准备函数")
    print("   - 调整同步逻辑")

def show_troubleshooting():
    """显示故障排除"""
    print("\n🔧 故障排除")
    print("=" * 50)
    
    print("问题1：导入失败")
    print("   ImportError: No module named 'requests'")
    print("   解决方案：pip install requests")
    print()
    
    print("问题2：获取token失败")
    print("   获取token失败: app access token is invalid")
    print("   解决方案：")
    print("   1. 检查App ID和App Secret是否正确")
    print("   2. 确认应用已发布版本")
    print("   3. 检查应用权限是否配置正确")
    print()
    
    print("问题3：写入表格失败")
    print("   写入表格失败: permission denied")
    print("   解决方案：")
    print("   1. 检查应用是否有表格读写权限")
    print("   2. 确认表格token和工作表ID正确")
    print("   3. 确认应用已添加到表格的协作者")
    print()
    
    print("问题4：数据格式错误")
    print("   写入表格失败: invalid value range")
    print("   解决方案：")
    print("   1. 检查数据文件是否存在")
    print("   2. 确认数据格式正确")
    print("   3. 检查表格是否有足够的列")
    print()
    
    print("问题5：网络请求超时")
    print("   解决方案：")
    print("   1. 检查网络连接")
    print("   2. 检查代理设置")
    print("   3. 增加超时时间")

def show_best_practices():
    """显示最佳实践"""
    print("\n💡 最佳实践")
    print("=" * 50)
    
    print("1. 配置管理")
    print("   - 使用环境变量或.env文件配置")
    print("   - 避免将敏感信息提交到代码仓库")
    print("   - 定期备份配置文件")
    print()
    
    print("2. 数据安全")
    print("   - 定期备份同步历史")
    print("   - 监控同步日志")
    print("   - 设置合理的同步频率")
    print()
    
    print("3. 错误处理")
    print("   - 启用详细日志记录")
    print("   - 实现重试机制")
    print("   - 监控错误日志")
    print()
    
    print("4. 性能优化")
    print("   - 合理设置同步频率")
    print("   - 只同步必要的数据")
    print("   - 清理历史数据")
    print()
    
    print("5. 团队协作")
    print("   - 共享配置文件")
    print("   - 统一同步频率")
    print("   - 定期同步数据")

def show_resources():
    """显示相关资源"""
    print("\n📚 相关资源")
    print("=" * 50)
    
    print("1. 项目文档")
    print("   - FEISHU_README.md: 详细使用指南")
    print("   - SKILL.md: 技能说明")
    print("   - README.md: 项目说明")
    print()
    
    print("2. 配置工具")
    print("   - setup_feishu.py: 配置飞书")
    print("   - config_feishu.py: 查看配置")
    print("   - config_help_feishu.py: 配置帮助")
    print()
    
    print("3. 测试工具")
    print("   - test_feishu_sync.py: 测试配置")
    print("   - test_feishu_connection.py: 测试连接")
    print("   - quick_test.py: 快速测试")
    print()
    
    print("4. 诊断工具")
    print("   - diagnose_feishu.py: 诊断问题")
    print("   - fix_feishu.py: 修复问题")
    print("   - verify_feishu.py: 验证配置")
    print()
    
    print("5. 管理工具")
    print("   - manage_feishu.py: 管理配置")
    print("   - status_feishu.py: 查看状态")
    print("   - log_feishu.py: 查看日志")
    print()
    
    print("6. 外部资源")
    print("   - 飞书开放平台: https://open.feishu.cn/")
    print("   - 飞书表格API: https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview")

def show_help():
    """显示帮助信息"""
    print("""
飞书同步使用教程

使用方法：
  python tutorial_feishu.py [选项]

选项：
  quick       显示快速开始
  detailed    显示详细步骤
  scenarios   显示常见场景
  advanced    显示高级用法
  troubleshooting 显示故障排除
  practices   显示最佳实践
  resources   显示相关资源
  all         显示所有教程
  help        显示帮助信息

示例：
  python tutorial_feishu.py quick       # 显示快速开始
  python tutorial_feishu.py detailed    # 显示详细步骤
  python tutorial_feishu.py all         # 显示所有教程
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "quick":
        show_quick_start()
    elif command == "detailed":
        show_detailed_steps()
    elif command == "scenarios":
        show_common_scenarios()
    elif command == "advanced":
        show_advanced_usage()
    elif command == "troubleshooting":
        show_troubleshooting()
    elif command == "practices":
        show_best_practices()
    elif command == "resources":
        show_resources()
    elif command == "all":
        print("📋 飞书同步完整教程")
        print("=" * 50)
        print()
        
        show_quick_start()
        show_detailed_steps()
        show_common_scenarios()
        show_advanced_usage()
        show_troubleshooting()
        show_best_practices()
        show_resources()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()