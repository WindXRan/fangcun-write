#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步日志
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def show_log_file(log_file: Path, lines: int = 50):
    """显示日志文件"""
    if not log_file.exists():
        print(f"⚠️  日志文件不存在: {log_file}")
        return False
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.readlines()
        
        if not content:
            print(f"⚠️  日志文件为空: {log_file}")
            return True
        
        # 显示最后N行
        recent_lines = content[-lines:]
        print(f"📜 日志文件: {log_file.name} (最后{len(recent_lines)}行)")
        print("-" * 50)
        
        for line in recent_lines:
            print(line.rstrip())
        
        print("-" * 50)
        print(f"📊 总行数: {len(content)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 读取日志文件失败: {e}")
        return False

def show_history():
    """显示同步历史"""
    print("📜 飞书同步历史")
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
        
        print(f"📊 同步记录: {len(history)} 条")
        print()
        
        # 显示所有记录
        for i, record in enumerate(history, 1):
            timestamp = record.get('timestamp', '未知')
            status = record.get('status', '未知')
            message = record.get('message', '')
            data_count = record.get('data_count', 0)
            
            # 状态图标
            if status == 'success':
                status_icon = '✅'
            elif status == 'error':
                status_icon = '❌'
            elif status == 'warning':
                status_icon = '⚠️'
            else:
                status_icon = 'ℹ️'
            
            print(f"{i}. {timestamp}")
            print(f"   {status_icon} {status}: {message}")
            if data_count > 0:
                print(f"   📊 数据量: {data_count} 条")
            print()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_recent_errors():
    """显示最近的错误"""
    print("❌ 最近的错误")
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
        
        # 显示最近10条错误
        recent_errors = error_records[-10:]
        for i, record in enumerate(recent_errors, 1):
            timestamp = record.get('timestamp', '未知')
            message = record.get('message', '')
            error_type = record.get('error_type', '未知')
            
            print(f"{i}. {timestamp}")
            print(f"   错误类型: {error_type}")
            print(f"   错误信息: {message}")
            print()
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_success_stats():
    """显示成功统计"""
    print("📊 成功统计")
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
        
        # 统计信息
        total_count = len(history)
        success_count = len([r for r in history if r.get('status') == 'success'])
        error_count = len([r for r in history if r.get('status') == 'error'])
        warning_count = len([r for r in history if r.get('status') == 'warning'])
        
        # 成功率
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        print(f"📊 总记录数: {total_count}")
        print(f"✅ 成功次数: {success_count}")
        print(f"❌ 失败次数: {error_count}")
        print(f"⚠️  警告次数: {warning_count}")
        print(f"📈 成功率: {success_rate:.1f}%")
        
        # 最近同步时间
        if history:
            last_record = history[-1]
            last_time = last_record.get('timestamp', '未知')
            last_status = last_record.get('status', '未知')
            print(f"\n🕒 最后同步: {last_time}")
            print(f"   状态: {last_status}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_help():
    """显示帮助信息"""
    print("""
查看飞书同步日志

使用方法：
  python log_feishu.py [选项]

选项：
  log       显示同步日志文件
  history   显示同步历史记录
  errors    显示最近的错误
  stats     显示成功统计
  all       显示所有信息
  help      显示帮助信息

示例：
  python log_feishu.py log       # 显示日志文件
  python log_feishu.py history   # 显示同步历史
  python log_feishu.py errors    # 显示错误记录
  python log_feishu.py stats     # 显示统计信息
  python log_feishu.py all       # 显示所有信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "log":
        log_file = Path(__file__).parent / "feishu_sync.log"
        show_log_file(log_file)
    elif command == "history":
        show_history()
    elif command == "errors":
        show_recent_errors()
    elif command == "stats":
        show_success_stats()
    elif command == "all":
        print("📊 飞书同步完整信息")
        print("=" * 50)
        print()
        
        # 显示日志
        log_file = Path(__file__).parent / "feishu_sync.log"
        show_log_file(log_file, 20)
        print()
        
        # 显示历史
        show_history()
        print()
        
        # 显示错误
        show_recent_errors()
        print()
        
        # 显示统计
        show_success_stats()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()