"""
fangcun-novel 项目级 I/O — rewrites/ 目录下的文件读写。

源书级 I/O（events/skeleton/adaptation/styles）从 fangcun-analyze 导入。
fangcun-analyze/tools 在 pipeline.py 启动时加入 sys.path。
"""

import re
import sys
from pathlib import Path

# ─── 源书级 I/O（从 fangcun-analyze 导入）────────────────────────────────────

from source_io import (
    get_cache_dir,
    get_source_text,
    get_source_chapters,
    get_total_chapters,
    load_events,
    save_events,
    get_events_text,
    get_chapter_event,
    load_skeleton,
    save_skeleton,
    get_skeleton_context,
    load_adaptation,
    save_adaptation,
    get_adaptation_principles,
    load_style_text,
)


# ─── 路径解析 ──────────────────────────────────────────────────────────────

def get_rewrites_dir(config) -> Path:
    return Path(config.get("rewrites_dir", ""))


def get_guides_dir(config) -> Path:
    return get_rewrites_dir(config) / "guides"


def get_chapters_output_dir(config) -> Path:
    return get_rewrites_dir(config) / "chapters"


# ─── 项目级 I/O（本地实现）─────────────────────────────────────────────────

def load_concept(config) -> str:
    f = get_rewrites_dir(config) / "concept.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_concept(config, content: str):
    f = get_rewrites_dir(config) / "concept.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_source_analysis(config) -> str:
    f = get_rewrites_dir(config) / "source_analysis.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_source_analysis(config, content: str):
    f = get_rewrites_dir(config) / "source_analysis.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_settings(config, filename: str) -> str:
    f = get_rewrites_dir(config) / "settings" / filename
    if f.exists():
        return f.read_text(encoding="utf-8")
    f2 = get_rewrites_dir(config) / filename
    return f2.read_text(encoding="utf-8") if f2.exists() else ""


def save_settings(config, filename: str, content: str):
    f = get_rewrites_dir(config) / "settings" / filename
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_characters(config) -> str:
    return load_settings(config, "characters.md")


def load_world(config) -> str:
    return load_settings(config, "world.md")


def load_plot_guide(config, ch_num: int) -> str:
    f = get_guides_dir(config) / f"plot_{ch_num}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_plot_guide(config, ch_num: int, content: str):
    f = get_guides_dir(config) / f"plot_{ch_num}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_style_guide(config, ch_num: int) -> str:
    f = get_guides_dir(config) / f"style_{ch_num}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_style_guide(config, ch_num: int, content: str):
    f = get_guides_dir(config) / f"style_{ch_num}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_chapter(config, ch_num: int) -> str:
    f = get_chapters_output_dir(config) / f"ch_{ch_num:03d}.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_chapter(config, ch_num: int, content: str):
    f = get_chapters_output_dir(config) / f"ch_{ch_num:03d}.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def get_written_chapters(config) -> list[int]:
    chapters_dir = get_chapters_output_dir(config)
    if not chapters_dir.exists():
        return []
    result = []
    for f in sorted(chapters_dir.glob("ch_*.txt")):
        m = re.search(r"ch_(\d+)\.txt", f.name)
        if m:
            result.append(int(m.group(1)))
    return result


def get_state_path(config) -> Path:
    return get_rewrites_dir(config) / "state.json"
