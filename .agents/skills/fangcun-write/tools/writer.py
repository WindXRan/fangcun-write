"""
fangcun-write: 通用写章模块

流程（与原版 fangcun-novel 一致）：
1. 写章（run_one）
2. 按需修复：字数超标→trim，字数不足→expand（3轮重试）
3. 统一润色：每章必 polish（对比源文风格）
4. validate：质量检查（不通过不阻断，只警告）
"""

import os
import re
import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 依赖模块
_NOVEL_TOOLS = Path(__file__).parent.parent.parent / "fangcun-novel" / "tools"
_ANALYZE_TOOLS = Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"
for _d in [str(_NOVEL_TOOLS), str(_ANALYZE_TOOLS)]:
    if _d not in sys.path:
        sys.path.insert(0, _d)

from lib.text_metrics import count_metrics
from utils import get_source_text, count_source_chars


def _get_run_one():
    from phases.guides import run_one
    return run_one


def get_writer_dirs(config):
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    return {
        "rewrites_dir": rewrites_dir,
        "chapters_dir": rewrites_dir / "chapters",
        "guides_dir": rewrites_dir / "guides",
    }


def _get_text_chars(text):
    return len(re.sub(r'\s', '', text))


# ============================================================
# 写章主入口（与原版 phase_write 一致）
# ============================================================

def write_chapter(config, ch_num, mode="imitation", context=None, auto_fix=True, max_retries=0):
    """写单章（不含后处理，后处理由 pipeline 统一调度）。"""
    run_one = _get_run_one()
    try:
        extra = {}
        if context:
            extra["context"] = context
        return run_one(config, "write-chapter", ch_num, extra_replacements=extra if extra else None)
    except Exception as e:
        print(f"    [ERROR] ch{ch_num:03d} 写章失败: {e}")
        return None


# ============================================================
# 后处理：trim/expand/polish（独立函数，pipeline 调用）
# ============================================================

def trim_chapter(config, ch_num, mode="imitation"):
    """精简章节"""
    run_one = _get_run_one()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    chars = _get_text_chars(text)
    src_chars = count_source_chars(config, ch_num)
    target = min(src_chars, 3000) if src_chars > 0 else 2500
    target = max(target, 2000)
    to_delete = max(0, chars - target)
    try:
        result = run_one(config, "trim-chapter", ch_num, extra_replacements={
            "content": text,
            "目标字数": str(target),
            "当前字数": str(chars),
            "需删减": str(to_delete),
        })
        if result:
            result_chars = _get_text_chars(result)
            if result_chars < target * 0.75:
                print(f"    [WARN] trim 砍太多 ({result_chars}/{target})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] trim 失败: {e}")
        return None


def expand_chapter(config, ch_num, mode="imitation", target_chars=None):
    """扩写章节"""
    run_one = _get_run_one()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    chars = _get_text_chars(text)
    src_chars = count_source_chars(config, ch_num)
    target = max(src_chars, 2000) if src_chars > 0 else 2500
    try:
        result = run_one(config, "expand-chapter", ch_num, extra_replacements={
            "content": text,
        })
        if result:
            result_chars = _get_text_chars(result)
            if result_chars > 3500:
                print(f"    [WARN] expand 加太多 ({result_chars})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] expand 失败: {e}")
        return None


def polish_chapter(config, ch_num, mode="imitation"):
    """润色章节（对比源文风格）"""
    run_one = _get_run_one()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    source_text = get_source_text(config, ch_num) if mode == "imitation" else None
    chars = _get_text_chars(text)
    try:
        return run_one(config, "polish-chapter", ch_num, extra_replacements={
            "content": text,
            "source_text": source_text or "（无源文）",
            "min_chars": str(int(chars * 0.9)),
            "max_chars": str(int(chars * 1.1)),
        })
    except Exception as e:
        print(f"    [WARN] polish 失败: {e}")
        return None


def rewrite_chapter(config, ch_num, mode="imitation", reason=""):
    """重写章节"""
    run_one = _get_run_one()
    try:
        return run_one(config, "write-chapter", ch_num, retry_context=reason or "整章重写")
    except Exception as e:
        print(f"    [ERROR] rewrite 失败: {e}")
        return None
