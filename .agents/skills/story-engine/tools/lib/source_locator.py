"""源文定位器：根据配置和章节号找到源文章节文件。"""

import os
import glob
from pathlib import Path


def find_source_file(config, ch):
    """找到源文章节文件路径。返回 Path 或 None。"""
    author = config.get('author', '')
    source_book = config.get('source_book', '')
    base_dir = config.get('base_dir', '.')

    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
        f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        f"projects/{author}/{source_book}/源文/第{ch}章*.txt",
        f"projects/{author}/{source_book}/源文/第{ch:03d}章*.txt",
    ]

    for pat in patterns:
        full_pat = os.path.join(base_dir, pat)
        files = sorted(glob.glob(full_pat))
        if files:
            return Path(files[0])

    return None


def get_source_text(config, ch):
    """获取源文章节文本。返回 str 或 None。"""
    f = find_source_file(config, ch)
    if f and f.exists():
        try:
            return f.read_text(encoding='utf-8')
        except Exception:
            return None
    return None


def get_source_dir(config):
    """获取源文章节目录。返回 str 或 None。"""
    author = config.get('author', '')
    source_book = config.get('source_book', '')
    base_dir = config.get('base_dir', '.')

    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/",
        f"projects/{author}/{source_book}/源文/",
    ]

    for pat in patterns:
        full = os.path.join(base_dir, pat)
        if os.path.isdir(full):
            return full

    return None


def get_total_chapters(config):
    """获取源文总章数。"""
    import re
    src_dir = get_source_dir(config)
    if not src_dir:
        return 0
    files = [f for f in os.listdir(src_dir) if f.endswith('.txt')]
    return len(files)
