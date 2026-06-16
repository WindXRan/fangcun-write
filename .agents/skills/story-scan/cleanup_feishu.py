#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理飞书同步历史记录
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def cleanup_history():
    """清理同步历史"""
    print("🧹 清理飞书同步历史记录")
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
        
        print(f"📊 当前同步记录: {len(history)} 条")
        
        # 显示最近10条
        print("\n📜 最近10条记录:")
        recent = history[-10:]
        for i, record in enumerate(recent, 1):
            timestamp = record.get('timestamp', '未知')
            status = record.get('status', '未知')
            message = record.get('message', '')
            print(f"  {i}. {timestamp}: {status} {message}")
        
        # 询问是否清理
        print("\n⚠️  警告：清理操作不可恢复！")
        choice = input("请选择操作:\n  1. 清理所有记录\n  2. 清理30天前的记录\n  3. 取消\n请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            # 清理所有记录
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            print("✅ 已清理所有同步记录")
            
        elif choice == '2':
            # 清理30天前的记录
            thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            new_history = []
            
            for record in history:
                timestamp_str = record.get('timestamp', '')
                if timestamp_str:
                    try:
                        # 尝试解析时间戳
                        if 'T' in timestamp_str:
                            record_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
                        else:
                            record_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp()
                        
                        if record_time >= thirty_days_ago:
                            new_history.append(record)
                    except ValueError:
                        # 无法解析时间戳，保留记录
                        new_history.append(record)
                else:
                    # 没有时间戳，保留记录
                    new_history.append(record)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(new_history, f, indent=2, ensure_ascii=False)
            
            cleaned_count = len(history) - len(new_history)
            print(f"✅ 已清理 {cleaned_count} 条30天前的记录")
            print(f"📊 剩余记录: {len(new_history)} 条")
            
        elif choice == '3':
            print("❌ 取消清理操作")
            return False
        else:
            print("❌ 无效选项")
            return False
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False

def cleanup_temp_files():
    """清理临时文件"""
    print("\n🧹 清理临时文件")
    print("=" * 50)
    
    temp_files = [
        Path(__file__).parent / "feishu_sync.log",
        Path(__file__).parent / "feishu_sync_debug.log",
        Path(__file__).parent / "feishu_sync_error.log",
    ]
    
    cleaned_count = 0
    for temp_file in temp_files:
        if temp_file.exists():
            try:
                temp_file.unlink()
                print(f"  ✅ 已删除: {temp_file.name}")
                cleaned_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {temp_file.name} - {e}")
        else:
            print(f"  ⚠️  文件不存在: {temp_file.name}")
    
    if cleaned_count > 0:
        print(f"\n✅ 已清理 {cleaned_count} 个临时文件")
    else:
        print("\n⚠️  没有需要清理的临时文件")
    
    return True

def show_help():
    """显示帮助信息"""
    print("""
清理飞书同步历史记录

使用方法：
  python cleanup_feishu.py [选项]

选项：
  history   清理同步历史记录
  temp      清理临时文件
  all       清理所有（历史记录+临时文件）
  help      显示帮助信息

示例：
  python cleanup_feishu.py history   # 清理同步历史
  python cleanup_feishu.py temp      # 清理临时文件
  python cleanup_feishu.py all       # 清理所有
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "history":
        cleanup_history()
    elif command == "temp":
        cleanup_temp_files()
    elif command == "all":
        cleanup_history()
        cleanup_temp_files()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()