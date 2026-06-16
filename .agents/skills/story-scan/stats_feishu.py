#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看飞书同步统计
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

def show_sync_stats():
    """显示同步统计"""
    print("📊 同步统计")
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
        
        # 基本统计
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
        
        # 时间统计
        if history:
            # 最近同步时间
            last_record = history[-1]
            last_time = last_record.get('timestamp', '未知')
            last_status = last_record.get('status', '未知')
            print(f"\n🕒 最后同步: {last_time}")
            print(f"   状态: {last_status}")
            
            # 第一次同步时间
            first_record = history[0]
            first_time = first_record.get('timestamp', '未知')
            print(f"🕒 首次同步: {first_time}")
            
            # 同步频率
            try:
                if 'T' in last_time:
                    last_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                else:
                    last_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
                
                if 'T' in first_time:
                    first_dt = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                else:
                    first_dt = datetime.strptime(first_time, '%Y-%m-%d %H:%M:%S')
                
                days_diff = (last_dt - first_dt).days
                if days_diff > 0:
                    sync_frequency = total_count / days_diff
                    print(f"📅 同步天数: {days_diff} 天")
                    print(f"📊 平均频率: {sync_frequency:.1f} 次/天")
            except ValueError:
                pass
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_data_stats():
    """显示数据统计"""
    print("\n📊 数据统计")
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
        
        # 数据量统计
        total_data_count = sum(r.get('data_count', 0) for r in history)
        success_data_count = sum(r.get('data_count', 0) for r in history if r.get('status') == 'success')
        
        print(f"📊 总数据量: {total_data_count} 条")
        print(f"✅ 成功同步: {success_data_count} 条")
        
        # 平均数据量
        if history:
            avg_data_count = total_data_count / len(history)
            print(f"📊 平均数据量: {avg_data_count:.1f} 条/次")
        
        # 最大数据量
        if history:
            max_data_record = max(history, key=lambda r: r.get('data_count', 0))
            max_data_count = max_data_record.get('data_count', 0)
            max_data_time = max_data_record.get('timestamp', '未知')
            print(f"📊 最大数据量: {max_data_count} 条")
            print(f"   时间: {max_data_time}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_time_stats():
    """显示时间统计"""
    print("\n⏰ 时间统计")
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
        
        # 按日期统计
        daily_stats = {}
        for record in history:
            timestamp = record.get('timestamp', '')
            if timestamp:
                try:
                    if 'T' in timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    
                    date_str = dt.strftime('%Y-%m-%d')
                    if date_str not in daily_stats:
                        daily_stats[date_str] = {'total': 0, 'success': 0, 'error': 0}
                    
                    daily_stats[date_str]['total'] += 1
                    if record.get('status') == 'success':
                        daily_stats[date_str]['success'] += 1
                    elif record.get('status') == 'error':
                        daily_stats[date_str]['error'] += 1
                except ValueError:
                    pass
        
        if daily_stats:
            print(f"📅 同步天数: {len(daily_stats)} 天")
            print()
            
            # 显示最近7天的统计
            sorted_dates = sorted(daily_stats.keys(), reverse=True)
            recent_dates = sorted_dates[:7]
            
            print("📅 最近7天统计:")
            for date in recent_dates:
                stats = daily_stats[date]
                print(f"  {date}:")
                print(f"    总次数: {stats['total']}")
                print(f"    成功: {stats['success']}")
                print(f"    失败: {stats['error']}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_error_stats():
    """显示错误统计"""
    print("\n❌ 错误统计")
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
        
        # 错误类型统计
        error_types = {}
        for record in error_records:
            error_type = record.get('error_type', '未知')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        print("\n📊 错误类型统计:")
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        
        for i, (error_type, count) in enumerate(sorted_errors, 1):
            percentage = count / len(error_records) * 100
            print(f"  {i}. {error_type}")
            print(f"     次数: {count}")
            print(f"     占比: {percentage:.1f}%")
        
        # 最近错误
        print("\n🕒 最近5条错误:")
        recent_errors = error_records[-5:]
        for i, record in enumerate(recent_errors, 1):
            timestamp = record.get('timestamp', '未知')
            message = record.get('message', '')
            print(f"  {i}. {timestamp}")
            print(f"     {message}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ 同步历史文件格式错误")
        return False
    except Exception as e:
        print(f"❌ 读取同步历史失败: {e}")
        return False

def show_performance_stats():
    """显示性能统计"""
    print("\n⚡ 性能统计")
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
        
        # 计算性能指标
        total_records = len(history)
        success_records = [r for r in history if r.get('status') == 'success']
        error_records = [r for r in history if r.get('status') == 'error']
        
        # 成功率
        success_rate = len(success_records) / total_records * 100 if total_records > 0 else 0
        
        # 平均数据量
        total_data = sum(r.get('data_count', 0) for r in history)
        avg_data = total_data / total_records if total_records > 0 else 0
        
        # 错误率
        error_rate = len(error_records) / total_records * 100 if total_records > 0 else 0
        
        print(f"📊 总记录数: {total_records}")
        print(f"📈 成功率: {success_rate:.1f}%")
        print(f"📉 错误率: {error_rate:.1f}%")
        print(f"📊 平均数据量: {avg_data:.1f} 条/次")
        print(f"📊 总数据量: {total_data} 条")
        
        # 性能评级
        if success_rate >= 95:
            performance_grade = "A (优秀)"
        elif success_rate >= 80:
            performance_grade = "B (良好)"
        elif success_rate >= 60:
            performance_grade = "C (一般)"
        else:
            performance_grade = "D (需要改进)"
        
        print(f"\n🏆 性能评级: {performance_grade}")
        
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
查看飞书同步统计

使用方法：
  python stats_feishu.py [选项]

选项：
  sync        显示同步统计
  data        显示数据统计
  time        显示时间统计
  errors      显示错误统计
  performance 显示性能统计
  all         显示所有统计信息
  help        显示帮助信息

示例：
  python stats_feishu.py sync        # 显示同步统计
  python stats_feishu.py data        # 显示数据统计
  python stats_feishu.py errors      # 显示错误统计
  python stats_feishu.py all         # 显示所有统计信息
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "sync":
        show_sync_stats()
    elif command == "data":
        show_data_stats()
    elif command == "time":
        show_time_stats()
    elif command == "errors":
        show_error_stats()
    elif command == "performance":
        show_performance_stats()
    elif command == "all":
        print("📋 飞书同步统计完整信息")
        print("=" * 50)
        print()
        
        show_sync_stats()
        show_data_stats()
        show_time_stats()
        show_error_stats()
        show_performance_stats()
    elif command == "help":
        show_help()
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()