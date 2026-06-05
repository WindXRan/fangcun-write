# -*- coding: utf-8 -*-
"""
时间统计 + 断点续传工具：记录耗时，支持中断后继续。

用法：
  # 计时
  python timer.py start <任务名> [--session <会话ID>]
  python timer.py stop <任务名> [--session <会话ID>]
  
  # 检查点（断点续传）
  python timer.py checkpoint <任务名> --status <pending|running|completed|failed> [--session <会话ID>]
  python timer.py status [--session <会话ID>]
  python timer.py pending [--session <会话ID>]
  python timer.py is-completed <任务名> [--session <会话ID>]
  
  # 报告
  python timer.py report [--session <会话ID>] [--output <输出文件>]
  python timer.py sessions

示例：
  # 计时
  python timer.py start "蒸馏-第1章" --session vplan-新书
  python timer.py stop "蒸馏-第1章" --session vplan-新书
  
  # 检查点
  python timer.py checkpoint "蒸馏-第1章" --status completed --session vplan-新书
  python timer.py pending --session vplan-新书
  python timer.py is-completed "蒸馏-第1章" --session vplan-新书
"""

import sys
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Windows 控制台编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 数据目录
DATA_DIR = Path.home() / ".story-engine" / "sessions"


def get_session_file(session_id: str) -> Path:
    """获取会话文件路径"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{session_id}.json"


def load_session(session_id: str) -> dict:
    """加载会话数据"""
    session_file = get_session_file(session_id)
    if session_file.exists():
        with open(session_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "tasks": {}
    }


def save_session(session_id: str, data: dict):
    """保存会话数据"""
    session_file = get_session_file(session_id)
    with open(session_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_duration(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def get_or_create_task(data: dict, task_name: str) -> dict:
    """获取或创建任务"""
    if task_name not in data["tasks"]:
        data["tasks"][task_name] = {
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
            "status": "pending",
            "checkpoints": []
        }
    return data["tasks"][task_name]


# ==================== 计时功能 ====================

def start_timer(task_name: str, session_id: str = "default"):
    """开始计时"""
    data = load_session(session_id)
    task = get_or_create_task(data, task_name)
    
    task["start_time"] = datetime.now().isoformat()
    task["status"] = "running"
    
    save_session(session_id, data)
    print(f"⏱️ 开始: {task_name}")


def stop_timer(task_name: str, session_id: str = "default", status: str = "completed"):
    """结束计时"""
    data = load_session(session_id)
    
    if task_name not in data["tasks"]:
        print(f"❌ 未找到任务: {task_name}")
        return
    
    task = data["tasks"][task_name]
    end_time = datetime.now()
    
    if task["start_time"]:
        start_time = datetime.fromisoformat(task["start_time"])
        duration = (end_time - start_time).total_seconds()
        task["duration_seconds"] = round(duration, 2)
    
    task["end_time"] = end_time.isoformat()
    task["status"] = status
    
    save_session(session_id, data)
    
    duration_str = format_duration(task.get("duration_seconds", 0))
    status_emoji = "✅" if status == "completed" else "❌"
    print(f"{status_emoji} 结束: {task_name} ({duration_str})")


# ==================== 检查点功能 ====================

def checkpoint(task_name: str, status: str, session_id: str = "default", message: str = ""):
    """记录检查点"""
    data = load_session(session_id)
    task = get_or_create_task(data, task_name)
    
    # 更新状态
    task["status"] = status
    
    # 记录检查点
    checkpoint_entry = {
        "time": datetime.now().isoformat(),
        "status": status,
        "message": message
    }
    if "checkpoints" not in task:
        task["checkpoints"] = []
    task["checkpoints"].append(checkpoint_entry)
    
    # 如果是 completed 或 failed，设置结束时间
    if status in ["completed", "failed"] and not task.get("end_time"):
        task["end_time"] = datetime.now().isoformat()
        if task.get("start_time"):
            start_time = datetime.fromisoformat(task["start_time"])
            duration = (datetime.now() - start_time).total_seconds()
            task["duration_seconds"] = round(duration, 2)
    
    save_session(session_id, data)
    
    status_emoji = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")
    print(f"{status_emoji} 检查点: {task_name} -> {status}")


def mark_completed(task_name: str, session_id: str = "default"):
    """标记任务完成"""
    checkpoint(task_name, "completed", session_id)


def mark_failed(task_name: str, session_id: str = "default", message: str = ""):
    """标记任务失败"""
    checkpoint(task_name, "failed", session_id, message)


def is_completed(task_name: str, session_id: str = "default") -> bool:
    """检查任务是否完成"""
    data = load_session(session_id)
    if task_name not in data["tasks"]:
        return False
    return data["tasks"][task_name].get("status") == "completed"


def get_pending_tasks(session_id: str = "default") -> list:
    """获取待完成的任务"""
    data = load_session(session_id)
    pending = []
    for task_name, task_info in data["tasks"].items():
        if task_info.get("status") in ["pending", "failed"]:
            pending.append(task_name)
    return pending


def get_completed_tasks(session_id: str = "default") -> list:
    """获取已完成的任务"""
    data = load_session(session_id)
    completed = []
    for task_name, task_info in data["tasks"].items():
        if task_info.get("status") == "completed":
            completed.append(task_name)
    return completed


# ==================== 批量任务 ====================

def batch_start(task_names: list, session_id: str = "default"):
    """批量开始任务"""
    data = load_session(session_id)
    now = datetime.now().isoformat()
    
    for task_name in task_names:
        task = get_or_create_task(data, task_name)
        if task["status"] == "pending":
            task["start_time"] = now
            task["status"] = "running"
    
    save_session(session_id, data)
    print(f"⏱️ 批量开始: {len(task_names)} 个任务")


def batch_checkpoint(task_names: list, status: str, session_id: str = "default"):
    """批量记录检查点"""
    for task_name in task_names:
        checkpoint(task_name, status, session_id)


def get_task_range(prefix: str, start: int, end: int, session_id: str = "default") -> dict:
    """获取任务范围的状态"""
    data = load_session(session_id)
    result = {}
    
    for i in range(start, end + 1):
        task_name = f"{prefix}-{i}"
        if task_name in data["tasks"]:
            result[task_name] = data["tasks"][task_name].get("status", "pending")
        else:
            result[task_name] = "pending"
    
    return result


def get_pending_in_range(prefix: str, start: int, end: int, session_id: str = "default") -> list:
    """获取范围内的待完成任务"""
    result = get_task_range(prefix, start, end, session_id)
    return [name for name, status in result.items() if status in ["pending", "failed"]]


def get_completed_in_range(prefix: str, start: int, end: int, session_id: str = "default") -> list:
    """获取范围内的已完成任务"""
    result = get_task_range(prefix, start, end, session_id)
    return [name for name, status in result.items() if status == "completed"]


# ==================== 状态显示 ====================

def show_status(session_id: str = "default"):
    """显示会话状态"""
    data = load_session(session_id)
    
    print(f"📊 会话状态: {session_id}")
    print(f"   创建时间: {data.get('created_at', 'N/A')}")
    print()
    
    if not data["tasks"]:
        print("   无任务记录")
        return
    
    # 统计
    total = len(data["tasks"])
    completed = sum(1 for t in data["tasks"].values() if t.get("status") == "completed")
    running = sum(1 for t in data["tasks"].values() if t.get("status") == "running")
    pending = sum(1 for t in data["tasks"].values() if t.get("status") == "pending")
    failed = sum(1 for t in data["tasks"].values() if t.get("status") == "failed")
    
    print(f"   总计: {total} | ✅ 完成: {completed} | 🔄 运行中: {running} | ⏳ 待处理: {pending} | ❌ 失败: {failed}")
    print()
    
    # 按状态分组显示
    status_groups = {"running": [], "pending": [], "failed": [], "completed": []}
    for task_name, task_info in data["tasks"].items():
        status = task_info.get("status", "pending")
        status_groups[status].append(task_name)
    
    if status_groups["running"]:
        print("🔄 运行中:")
        for name in status_groups["running"][:5]:
            print(f"   - {name}")
        if len(status_groups["running"]) > 5:
            print(f"   ... 共 {len(status_groups['running'])} 个")
    
    if status_groups["failed"]:
        print("❌ 失败:")
        for name in status_groups["failed"][:5]:
            print(f"   - {name}")
        if len(status_groups["failed"]) > 5:
            print(f"   ... 共 {len(status_groups['failed'])} 个")
    
    if status_groups["pending"]:
        print(f"⏳ 待处理: {len(status_groups['pending'])} 个")
    
    if status_groups["completed"]:
        print(f"✅ 已完成: {len(status_groups['completed'])} 个")


def show_pending(session_id: str = "default"):
    """显示待完成任务"""
    pending = get_pending_tasks(session_id)
    
    if not pending:
        print("✅ 没有待完成的任务")
        return
    
    print(f"⏳ 待完成任务 ({len(pending)} 个):")
    for task_name in pending:
        print(f"   - {task_name}")


# ==================== 报告 ====================

def generate_report(session_id: str = None, output_file: str = None) -> str:
    """生成统计报告"""
    if session_id:
        sessions = [session_id]
    else:
        sessions = []
        if DATA_DIR.exists():
            for f in DATA_DIR.glob("*.json"):
                sessions.append(f.stem)
    
    if not sessions:
        return "📭 没有找到任何会话"
    
    report_lines = []
    report_lines.append("# ⏱️ 时间统计报告")
    report_lines.append("")
    
    for sid in sessions:
        data = load_session(sid)
        report_lines.append(f"## 会话: {sid}")
        report_lines.append(f"- 创建时间: {data.get('created_at', 'N/A')}")
        report_lines.append("")
        
        if not data["tasks"]:
            report_lines.append("*无任务记录*")
            report_lines.append("")
            continue
        
        # 统计
        total = len(data["tasks"])
        completed = sum(1 for t in data["tasks"].values() if t.get("status") == "completed")
        total_duration = sum(t.get("duration_seconds", 0) for t in data["tasks"].values() if t.get("duration_seconds"))
        
        report_lines.append(f"### 概览")
        report_lines.append(f"- 总任务数: {total}")
        report_lines.append(f"- 已完成: {completed}")
        report_lines.append(f"- 总耗时: {format_duration(total_duration)}")
        report_lines.append("")
        
        # 任务明细
        report_lines.append("### 任务明细")
        report_lines.append("")
        report_lines.append("| 任务 | 状态 | 耗时 |")
        report_lines.append("|------|------|------|")
        
        # 按状态排序：running > failed > pending > completed
        status_order = {"running": 0, "failed": 1, "pending": 2, "completed": 3}
        sorted_tasks = sorted(data["tasks"].items(), key=lambda x: status_order.get(x[1].get("status", "pending"), 99))
        
        for task_name, task_info in sorted_tasks:
            status = task_info.get("status", "pending")
            status_emoji = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")
            duration_str = format_duration(task_info.get("duration_seconds", 0)) if task_info.get("duration_seconds") else "-"
            report_lines.append(f"| {task_name} | {status_emoji} {status} | {duration_str} |")
        
        report_lines.append("")
    
    report = "\n".join(report_lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 报告已保存: {output_file}")
    else:
        print(report)
    
    return report


def list_sessions():
    """列出所有会话"""
    if not DATA_DIR.exists():
        print("📭 没有找到任何会话")
        return
    
    sessions = list(DATA_DIR.glob("*.json"))
    if not sessions:
        print("📭 没有找到任何会话")
        return
    
    print("📋 可用会话:")
    for session_file in sorted(sessions):
        session_id = session_file.stem
        data = load_session(session_id)
        task_count = len(data.get("tasks", {}))
        completed = sum(1 for t in data.get("tasks", {}).values() if t.get("status") == "completed")
        created_at = data.get("created_at", "N/A")
        print(f"  - {session_id} ({completed}/{task_count} 完成, 创建于 {created_at})")


def cleanup_sessions(days_old: int = 30):
    """清理旧会话"""
    if not DATA_DIR.exists():
        return
    
    cutoff = datetime.now() - timedelta(days=days_old)
    removed = 0
    
    for session_file in DATA_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            created_at = datetime.fromisoformat(data.get("created_at", "2000-01-01"))
            if created_at < cutoff:
                session_file.unlink()
                removed += 1
        except:
            pass
    
    if removed:
        print(f"🧹 已清理 {removed} 个旧会话")


# ==================== 命令行入口 ====================

def parse_session_arg(args: list) -> str:
    """解析 --session 参数"""
    if '--session' in args:
        idx = args.index('--session')
        if idx + 1 < len(args):
            return args[idx + 1]
    return "default"


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    session_id = parse_session_arg(args)
    
    if command == 'start':
        if not args:
            print("用法: python timer.py start <任务名> [--session <会话ID>]")
            sys.exit(1)
        start_timer(args[0], session_id)
    
    elif command == 'stop':
        if not args:
            print("用法: python timer.py stop <任务名> [--session <会话ID>]")
            sys.exit(1)
        status = "completed"
        if '--status' in args:
            idx = args.index('--status')
            if idx + 1 < len(args):
                status = args[idx + 1]
        stop_timer(args[0], session_id, status)
    
    elif command == 'checkpoint':
        if len(args) < 2:
            print("用法: python timer.py checkpoint <任务名> --status <状态> [--session <会话ID>]")
            sys.exit(1)
        task_name = args[0]
        status = "completed"
        if '--status' in args:
            idx = args.index('--status')
            if idx + 1 < len(args):
                status = args[idx + 1]
        message = ""
        if '--message' in args:
            idx = args.index('--message')
            if idx + 1 < len(args):
                message = args[idx + 1]
        checkpoint(task_name, status, session_id, message)
    
    elif command == 'mark-completed':
        if not args:
            print("用法: python timer.py mark-completed <任务名> [--session <会话ID>]")
            sys.exit(1)
        mark_completed(args[0], session_id)
    
    elif command == 'mark-failed':
        if not args:
            print("用法: python timer.py mark-failed <任务名> [--session <会话ID>]")
            sys.exit(1)
        message = ""
        if '--message' in args:
            idx = args.index('--message')
            if idx + 1 < len(args):
                message = args[idx + 1]
        mark_failed(args[0], session_id, message)
    
    elif command == 'is-completed':
        if not args:
            print("用法: python timer.py is-completed <任务名> [--session <会话ID>]")
            sys.exit(1)
        result = is_completed(args[0], session_id)
        print("true" if result else "false")
        sys.exit(0 if result else 1)
    
    elif command == 'status':
        show_status(session_id)
    
    elif command == 'pending':
        show_pending(session_id)
    
    elif command == 'report':
        output_file = None
        if '--output' in args:
            idx = args.index('--output')
            if idx + 1 < len(args):
                output_file = args[idx + 1]
        generate_report(session_id, output_file)
    
    elif command == 'sessions':
        list_sessions()
    
    elif command == 'cleanup':
        days = 30
        if '--days' in args:
            idx = args.index('--days')
            if idx + 1 < len(args):
                days = int(args[idx + 1])
        cleanup_sessions(days)
    
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)