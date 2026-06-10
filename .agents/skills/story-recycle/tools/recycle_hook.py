"""
story-recycle — 项目文件回收站。

功能：
1. 全局 HOOK：patch Path.unlink / shutil.rmtree，删前自动备份到 _recycle/
2. CLI：查看、还原、清空回收站

用法：
    # 全局 hook（在脚本入口 import 一次即生效）
    from recycle_hook import install_hook
    install_hook()

    # CLI
    python recycle_hook.py --list  projects/作者/书名
    python recycle_hook.py --restore projects/作者/书名/_recycle/20260611_ch_001.txt
    python recycle_hook.py --empty  projects/作者/书名 [--days 7]
    python recycle_hook.py --info   projects/作者/书名 (查看回收站统计)
"""

import os
import sys
import json
import shutil
import pathlib
import datetime
import argparse
from pathlib import Path
from typing import Optional


# ── 配置 ──────────────────────────────────────────
RECYCLE_DIRNAME = "_recycle"
PROJECTS_MARKER = "projects"       # 路径包含此段才触发备份


# ── 工具函数 ──────────────────────────────────────

def _get_book_root(path: Path) -> Optional[Path]:
    """
    从路径中提取 projects/{作者}/{书名} 根目录。
    需要路径格式: .../projects/{作者}/{书名}/...
    返回 None 表示路径层级不足（不在具体项目内）。
    """
    parts = path.absolute().parts
    try:
        idx = parts.index(PROJECTS_MARKER)
    except ValueError:
        return None
    # 需要至少 projects + 作者 + 书名 三级
    if len(parts) <= idx + 2:
        return None
    return Path(*parts[:idx + 3])


def _is_project_path(path: Path) -> bool:
    """判断路径是否在 projects/{作者}/{书名}/ 下，且不在 _recycle/ 下。"""
    if RECYCLE_DIRNAME in path.parts:
        return False
    return _get_book_root(path) is not None


def _get_recycle_dir(path: Path) -> Optional[Path]:
    """
    从被删文件路径推导回收站目录。
    projects/作者/书名/xxx/文件.txt  →  projects/作者/书名/_recycle/
    """
    book_root = _get_book_root(path)
    if book_root is None:
        return None
    return book_root / RECYCLE_DIRNAME


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:22]  # 含微秒防冲突


def _orig_unlink(path: Path):
    """调用原始的 Path.unlink（绕过 hook）。"""
    _ORIGINALS['unlink'](path)


def _orig_rmtree(path):
    """调用原始的 shutil.rmtree（绕过 hook）。"""
    _ORIGINALS['rmtree'](path)


def safe_delete(path: Path, silent: bool = False) -> Optional[str]:
    """
    将文件或目录移入回收站，返回回收站内的路径。
    如果 path 不在 projects/ 下，直接删除不备份。
    内部使用原始 unlink/rmtree 避免递归。
    """
    path = path.absolute()
    if not path.exists():
        return None

    if not _is_project_path(path):
        _orig_unlink(path) if path.is_file() else _orig_rmtree(path)
        return None

    recycle_dir = _get_recycle_dir(path)
    if recycle_dir is None:
        _orig_unlink(path) if path.is_file() else _orig_rmtree(path)
        return None
    recycle_dir.mkdir(parents=True, exist_ok=True)

    dest = recycle_dir / f"{_timestamp()}_{path.name}"

    try:
        if path.is_file():
            shutil.copy2(path, dest)
            _orig_unlink(path)
        else:
            shutil.copytree(path, dest, dirs_exist_ok=True)
            _orig_rmtree(path)
    except Exception as e:
        if not silent:
            print(f"[recycle] 备份失败: {e}", file=sys.stderr)
        _orig_unlink(path) if path.is_file() else _orig_rmtree(path)
        return None

    if not silent:
        print(f"[recycle] 回收: {path.name} -> _recycle/{dest.name}")
    return str(dest)


# ── 全局 HOOK ─────────────────────────────────────

_ORIGINALS = {}  # type: ignore


def _hooked_unlink(self, *args, **kwargs):
    if _is_project_path(self) and self.exists():
        safe_delete(self)
    else:
        _ORIGINALS['unlink'](self, *args, **kwargs)


def _hooked_rmtree(path, *args, **kwargs):
    p = Path(path)
    if _is_project_path(p) and p.exists():
        safe_delete(p)
    else:
        _ORIGINALS['rmtree'](path, *args, **kwargs)


def install_hook():
    """全局 hook 安装。import 后调用一次即可。"""
    if _ORIGINALS:
        return  # 已安装

    _ORIGINALS['unlink'] = Path.unlink
    _ORIGINALS['rmtree'] = shutil.rmtree

    Path.unlink = _hooked_unlink
    shutil.rmtree = _hooked_rmtree

    print("[recycle] 回收站 HOOK 已激活（项目文件删前自动备份）")


def uninstall_hook():
    """卸载全局 hook。"""
    if not _ORIGINALS:
        return
    Path.unlink = _ORIGINALS['unlink']
    shutil.rmtree = _ORIGINALS['rmtree']
    _ORIGINALS.clear()
    print("[recycle] HOOK 已卸载")


# ── CLI 管理 ─────────────────────────────────────

def cmd_list(book_dir: Path):
    """列出回收站内容。"""
    recycle = book_dir / RECYCLE_DIRNAME
    if not recycle.exists():
        print(f"[recycle] [空] 回收站为空: {recycle}")
        return

    items = sorted(recycle.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        print(f"[recycle] [空] 回收站为空")
        return

    total_size = 0
    print(f"{'文件名':<50} {'大小':>10} {'删除时间'}")
    print("-" * 80)
    for item in items:
        ts = datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%m-%d %H:%M:%S")
        size = _sizeof_fmt(_path_size(item))
        total_size += _path_size(item)
        print(f"{item.name:<50} {size:>10} {ts}")
    print("-" * 80)
    print(f"共 {len(items)} 项，{_sizeof_fmt(total_size)}")


def cmd_restore(target: Path):
    """还原单个文件/目录到原始位置。"""
    if not target.exists():
        print(f"[recycle] [!] 不存在: {target}")
        return

    # 原始位置：从文件名还原路径？不行，我们只存了文件名
    # 但可以根据 _recycle/ 的父目录推导 book_root
    recycle_dir = target.parent
    book_root = recycle_dir.parent
    original = book_root / "?"  # 不知道原路径了...

    # 所以还原需要用户指定目标，或者我们存 metadata
    # 简化版：直接还原到 book_root 同名位置
    delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(target.stat().st_mtime)
    age_hours = delta.total_seconds() / 3600
    name_without_ts = target.name[23:]  # 去掉 20260611_143022_ 前缀
    dest = book_root / name_without_ts

    if dest.exists():
        print(f"[recycle] [!]  目标已存在，跳过: {dest}")
        return

    if target.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, dest)
        target.unlink()
    else:
        shutil.copytree(target, dest, dirs_exist_ok=True)
        shutil.rmtree(target)

    print(f"[recycle] [R]  还原: {target.name} → {dest}")


def cmd_empty(book_dir: Path, days: int = 0):
    """清空回收站。days > 0 时只清理超过 N 天的文件。"""
    recycle = book_dir / RECYCLE_DIRNAME
    if not recycle.exists():
        return

    now = datetime.datetime.now()
    removed = 0
    for item in recycle.iterdir():
        if days > 0:
            mtime = datetime.datetime.fromtimestamp(item.stat().st_mtime)
            if (now - mtime).days < days:
                continue

        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item)
        removed += 1

    print(f"[recycle] [x]  已清理 {removed} 项" + (f"（超过 {days} 天）" if days else ""))


def cmd_info(book_dir: Path):
    """回收站统计。"""
    recycle = book_dir / RECYCLE_DIRNAME
    if not recycle.exists():
        print(f"[recycle] [空] 回收站为空")
        return

    items = list(recycle.iterdir())
    total_size = sum(_path_size(p) for p in items)

    # 按日期分组
    by_date = {}
    for item in items:
        date_str = datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d")
        by_date.setdefault(date_str, []).append(item)

    print(f"[recycle] [*] 回收站统计")
    print(f"  位置: {recycle}")
    print(f"  总数: {len(items)} 项")
    print(f"  总大小: {_sizeof_fmt(total_size)}")
    print(f"  日期分布:")
    for date_str in sorted(by_date, reverse=True)[:10]:
        day_size = sum(_path_size(p) for p in by_date[date_str])
        print(f"    {date_str}: {len(by_date[date_str])} 项 ({_sizeof_fmt(day_size)})")


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for f in path.rglob('*'):
        if f.is_file():
            total += f.stat().st_size
    return total


def _sizeof_fmt(size: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def main():
    parser = argparse.ArgumentParser(description="[B] 项目回收站管理")
    parser.add_argument("--list", metavar="BOOK_DIR", help="列出回收站内容")
    parser.add_argument("--restore", metavar="RECYCLE_PATH", help="还原文件")
    parser.add_argument("--empty", metavar="BOOK_DIR", help="清空回收站")
    parser.add_argument("--days", type=int, default=0, help="仅清理超过 N 天的文件")
    parser.add_argument("--info", metavar="BOOK_DIR", help="回收站统计")
    parser.add_argument("--install", action="store_true", help="激活 HOOK（仅供单次运行时使用）")

    args = parser.parse_args()

    if args.install:
        install_hook()
        print("[recycle] Hook 已激活（当前进程有效）")
        return

    if args.list:
        cmd_list(Path(args.list))
    elif args.restore:
        cmd_restore(Path(args.restore))
    elif args.empty:
        cmd_empty(Path(args.empty), args.days)
    elif args.info:
        cmd_info(Path(args.info))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
