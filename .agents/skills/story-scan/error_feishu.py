#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步错误
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def show_error_history():
    """显示错误历史"""
    print("❌ 错误历史记录")
    print("=" * 50)
    
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    
    if not history_file.exists():
        print("⚠️  同步历史文件不存在")
        return True
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        if not history:
            print("⚠️  同步历史为空")
            return True
        
        # 筛选错误记录
        error_records = [r for r in history if r.get('status') == 'error']
        
        if not error_records:
            print("✅ 没有错误记录")
            return True
        
        print(f"📊 错误记录: {len(error_records)} 条")
        print()
        
        # 显示所有错误记录
        for i, record in enumerate(error_records, 1):
            timestamp = record.get('timestamp', '未知')
            message = record.get('message', '')
            error_type = record.get('error_type', '未知')
            data_count = record.get('data_count', 0)
            
            print(f"{i}. {timestamp}")
            print(f"   错误类型: {error_type}")
            print(f"   错误信息: {message}")
            if data_count > 0:
                print(f"   数据量: {data_count} 条")
            print()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_error_types():
    """显示错误类型"""
    print("📊 错误类型统计")
    print("=" * 50)
    
    history_file = Path(__file__).parent / "feishu_sync_history.json"
    
    if not history_file.exists():
        print("⚠️  同步历史文件不存在")
        return True
    
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        if not history:
            print("⚠️  同步历史为空")
            return True
        
        # 筛选错误记录
        error_records = [r for r in history if r.get('status') == 'error']
        
        if not error_records:
            print("✅ 没有错误记录")
            return True
        
        # 统计错误类型
        error_types = {}
        for record in error_records:
            error_type = record.get('error_type', '未知')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        print(f"📊 错误类型: {len(error_types)} 种")
        print()
        
        # 按数量排序
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        
        for i, (error_type, count) in enumerate(sorted_errors, 1):
            print(f"{i}. {error_type}")
            print(f"   次数: {count}")
            print(f"   占比: {count/len(error_records)*100:.1f}%")
            print()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_error_solutions():
    """显示错误解决方案"""
    print("🔧 常见错误解决方案")
    print("=" * 50)
    
    solutions = [
        {
            "error": "获取token失败",
            "solution": "检查App ID和App Secret是否正确",
            "details": [
                "1. 确认飞书应用已创建",
                "2. 确认App ID和App Secret正确",
                "3. 确认应用已发布版本",
                "4. 检查网络连接"
            ]
        },
        {
            "error": "读取表格失败",
            "solution": "检查表格token和工作表ID是否正确",
            "details": [
                "1. 确认表格已创建",
                "2. 确认表格token正确",
                "3. 确认工作表ID正确",
                "4. 确认应用有表格读取权限"
            ]
        },
        {
            "error": "写入表格失败",
            "solution": "检查应用权限和表格配置",
            "details": [
                "1. 确认应用有表格写入权限",
                "2. 确认表格未被锁定",
                "3. 确认工作表有足够空间",
                "4. 检查数据格式是否正确"
            ]
        },
        {
            "error": "数据加载失败",
            "solution": "检查数据文件是否存在",
            "details": [
                "1. 确认数据目录存在",
                "2. 确认数据文件存在",
                "3. 确认数据文件格式正确",
                "4. 运行数据采集脚本"
            ]
        },
        {
            "error": "网络请求超时",
            "solution": "检查网络连接和代理设置",
            "details": [
                "1. 检查网络连接",
                "2. 检查代理设置",
                "3. 增加超时时间",
                "4. 尝试使用VPN"
            ]
        }
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"{i}. {solution['error']}")
        print(f"   解决方案: {solution['solution']}")
        print("   详细步骤:")
        for detail in solution['details']:
            print(f"     {detail}")
        print()

def show_error_logs():
    """显示错误日志"""
    print("📜 错误日志")
    print("=" * 50)
    
    log_files = [
        Path(__file__).parent / "feishu_sync.log",
        Path(__file__).parent / "feishu_sync_error.log",
        Path(__file__).parent / "feishu_sync_debug.log",
    ]
    
    for log_file in log_files:
        if log_file.exists():
            print(f"📄 {log_file.name}:")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.readlines()
                
                if content:
                    # 显示最后20行
                    recent_lines = content[-20:]
                    for line in recent_lines:
                        print(f"  {line.rstrip()}")
                else:
                    print("  ⚠️  日志文件为空")
            except Exception as e:
                print(f"  ❌ 读取日志文件失败: {e}")
            print()
        else:
            print(f"⚠️  日志文件不存在: {log_file.name}")
            print()

def show_error_prevention():
    """显示错误预防措施"""
    print("🛡️  错误预防措施")
    print("=" * 50)
    
    prevention_measures = [
        {
            "category": "配置检查",
            "measures": [
                "定期检查飞书应用状态",
                "确认表格token和工作表ID有效",
                "检查应用权限是否过期",
                "备份配置文件"
            ]
        },
        {
            "category": "数据验证",
            "measures": [
                "同步前检查数据文件完整性",
                "验证数据格式是否正确",
                "检查数据量是否合理",
                "备份重要数据"
            ]
        },
        {
            "category": "网络监控",
            "measures": [
                "监控网络连接状态",
                "设置合理的超时时间",
                "实现重试机制",
                "记录网络请求日志"
            ]
        },
        {
            "category": "日志记录",
            "measures": [
                "启用详细日志记录",
                "定期清理日志文件",
                "监控错误日志",
                "设置日志轮转"
            ]
        }
    ]
    
    for i, category in enumerate(prevention_measures, 1):
        print(f"{i}. {category['category']}")
        for measure in category['measures']:
            print(f"   - {measure}")
        print()

def show_help():
    """显示帮助信息"""
    print("""
查看飞书同步错误

使用方法：
  python error_feishu.py [选项]

选项：
  history     显示错误历史记录
  types       显示错误类型统计
  solutions   显示错误解决方案
  logs        显示错误日志
  prevention  显示错误预防措施
  all         显示所有错误信息
  help        显示帮助信息

示例：
  python error_feishu.py history     # 显示错误历史
  python error_feishu.py types       # 显示错误类型
  python error_feishu.py solutions   # 显示解决方案
  python error_feishu.py all         # 显示所有错误信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "history":
        show_error_history()
    elif command == "types":
        show_error_types()
    elif command == "solutions":
        show_error_solutions()
    elif command == "logs":
        show_error_logs()
    elif command == "prevention":
        show_error_prevention()
    elif command == "all":
        print("📋 飞书同步错误完整信息")
        print("=" * 50)
        print()
        
        show_error_history()
        show_error_types()
        show_error_solutions()
        show_error_logs()
        show_error_prevention()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()