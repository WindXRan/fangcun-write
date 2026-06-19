"""
story-engine 文件 I/O 层 — 统一管理所有文件读写。

路径规则：
  源书级（_cache/）: events, skeleton, adaptation, styles, chapters, header, toc
  项目级（rewrites/）: settings, guides, chapters, concept, state
"""

import json
import re
from pathlib import Path


# ─── 路径解析 ──────────────────────────────────────────────────────────────

def get_cache_dir(config) -> Path:
    """获取源书 _cache/ 目录。"""
    base_dir = config.get("base_dir", ".")
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    return Path(base_dir) / "projects" / author / source_book / "_cache"


def get_chapters_dir(config) -> Path:
    """获取源文章节目录。"""
    cache = get_cache_dir(config)
    chapters = cache / "chapters"
    if chapters.exists():
        return chapters
    # 兼容 source_dir 配置
    if config.get("source_chapter_dir"):
        sd = Path(config["source_chapter_dir"])
        if sd.exists():
            return sd
    return chapters


def get_rewrites_dir(config) -> Path:
    """获取仿写输出目录。"""
    return Path(config.get("rewrites_dir", ""))


def get_guides_dir(config) -> Path:
    """获取 guides 目录。"""
    return get_rewrites_dir(config) / "guides"


def get_chapters_output_dir(config) -> Path:
    """获取仿写章节目录。"""
    return get_rewrites_dir(config) / "chapters"


def get_styles_dir(config) -> Path:
    """获取文笔指纹目录（源书级）。"""
    return get_cache_dir(config) / "styles"


# ─── 源文读取 ──────────────────────────────────────────────────────────────

def get_source_text(config, ch_num: int) -> str:
    """读取源文单章全文。"""
    chapters_dir = get_chapters_dir(config)
    for f in sorted(chapters_dir.glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m and int(m.group(1)) == ch_num:
            return f.read_text(encoding="utf-8")
    return ""


def get_source_chapters(config) -> list[tuple[int, Path]]:
    """获取源文章节列表 [(章号, 路径), ...]。"""
    chapters_dir = get_chapters_dir(config)
    chapters = []
    for f in sorted(chapters_dir.glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m:
            chapters.append((int(m.group(1)), f))
    return chapters


def get_total_chapters(config) -> int:
    """获取源文总章数。"""
    chapters = get_source_chapters(config)
    return len(chapters) if chapters else 0


# ─── 共享产物读写（_cache/ 级）────────────────────────────────────────────

def load_events(config) -> list[dict]:
    """读取事件表。"""
    f = get_cache_dir(config) / "events.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def save_events(config, events: list[dict]):
    """保存事件表。"""
    f = get_cache_dir(config) / "events.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def get_events_text(config, chapter_ids=None) -> str:
    """读取事件表，返回格式化文本。"""
    events = load_events(config)
    if chapter_ids:
        events = [e for e in events if e.get("id") in chapter_ids]
    valid = [e for e in events if e.get("event")]
    if not valid:
        return "事件表不存在或为空"
    return "\n".join(
        f"第{e.get('chapter_index', e.get('id', '?'))}章，标题:{e.get('chapter', '?')}，事件:{e.get('event', '?')}"
        for e in valid
    )


def load_skeleton(config) -> str:
    """读取故事骨架。"""
    f = get_cache_dir(config) / "story_skeleton.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_skeleton(config, content: str):
    """保存故事骨架。"""
    f = get_cache_dir(config) / "story_skeleton.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_adaptation(config) -> str:
    """读取改编策略。"""
    f = get_cache_dir(config) / "adaptation_strategy.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_adaptation(config, content: str):
    """保存改编策略。"""
    f = get_cache_dir(config) / "adaptation_strategy.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_style_text(config, ch_num: int) -> str:
    """加载文笔指纹（算法锚点 + LLM 分析）。"""
    styles_dir = get_styles_dir(config)
    parts = []
    f = styles_dir / f"style_{ch_num:03d}.md"
    if f.exists():
        parts.append(f.read_text(encoding="utf-8"))
    f_llm = styles_dir / f"style_{ch_num:03d}_llm.md"
    if f_llm.exists():
        parts.append(f_llm.read_text(encoding="utf-8"))
    return "\n\n".join(parts) if parts else ""


def get_chapter_event(config, ch_num: int) -> str:
    """提取指定章节的事件摘要。"""
    events = load_events(config)
    for e in events:
        if e.get("id") == ch_num or e.get("chapter_index") == ch_num:
            if e.get("event"):
                return f"第{ch_num}章：{e['event']}"
    return ""


# ─── 项目产物读写（rewrites/ 级）──────────────────────────────────────────

def load_concept(config) -> str:
    """读取 concept.md。"""
    f = get_rewrites_dir(config) / "concept.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_concept(config, content: str):
    """保存 concept.md。"""
    f = get_rewrites_dir(config) / "concept.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_source_analysis(config) -> str:
    """读取 source_analysis.md。"""
    f = get_rewrites_dir(config) / "source_analysis.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_source_analysis(config, content: str):
    """保存 source_analysis.md。"""
    f = get_rewrites_dir(config) / "source_analysis.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_settings(config, filename: str) -> str:
    """读取 settings/ 下的文件。"""
    f = get_rewrites_dir(config) / "settings" / filename
    if f.exists():
        return f.read_text(encoding="utf-8")
    # 兼容旧结构
    f2 = get_rewrites_dir(config) / filename
    return f2.read_text(encoding="utf-8") if f2.exists() else ""


def save_settings(config, filename: str, content: str):
    """保存 settings/ 下的文件。"""
    f = get_rewrites_dir(config) / "settings" / filename
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_characters(config) -> str:
    """读取 characters.md。"""
    return load_settings(config, "characters.md")


def load_plot(config) -> str:
    """读取 plot.md。"""
    return load_settings(config, "plot.md")


def load_world(config) -> str:
    """读取 world.md。"""
    return load_settings(config, "world.md")


def load_plot_guide(config, ch_num: int) -> str:
    """读取 plot_guide。"""
    f = get_guides_dir(config) / f"plot_{ch_num}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_plot_guide(config, ch_num: int, content: str):
    """保存 plot_guide。"""
    f = get_guides_dir(config) / f"plot_{ch_num}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_style_guide(config, ch_num: int) -> str:
    """读取 style_guide。"""
    f = get_guides_dir(config) / f"style_{ch_num}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_style_guide(config, ch_num: int, content: str):
    """保存 style_guide。"""
    f = get_guides_dir(config) / f"style_{ch_num}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def load_chapter(config, ch_num: int) -> str:
    """读取仿写章节。"""
    f = get_chapters_output_dir(config) / f"ch_{ch_num:03d}.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_chapter(config, ch_num: int, content: str):
    """保存仿写章节。"""
    f = get_chapters_output_dir(config) / f"ch_{ch_num:03d}.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def get_written_chapters(config) -> list[int]:
    """获取已写章节列表。"""
    chapters_dir = get_chapters_output_dir(config)
    if not chapters_dir.exists():
        return []
    result = []
    for f in sorted(chapters_dir.glob("ch_*.txt")):
        m = re.search(r"ch_(\d+)\.txt", f.name)
        if m:
            result.append(int(m.group(1)))
    return result


# ─── 片段提取（供 prompt 注入用）───────────────────────────────────────────

def get_skeleton_context(config, ch_num: int) -> str:
    """从骨架中提取与指定章节相关的片段。"""
    skeleton = load_skeleton(config)
    if not skeleton:
        return ""

    lines = skeleton.split("\n")
    result = []

    # 找本章所属幕
    for i, line in enumerate(lines):
        if "第" in line and "幕" in line and "→" in line:
            m = re.search(r"第(\d+)-(\d+)章", line)
            if m:
                start_ch, end_ch = int(m.group(1)), int(m.group(2))
                if start_ch <= ch_num <= end_ch:
                    result.append(f"【所属幕】{line.strip()}")
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if lines[j].startswith("**功能") or lines[j].startswith("**核心问题") or lines[j].startswith("**幕末转折"):
                            result.append(lines[j].strip())
                        if lines[j].startswith("### 第") or lines[j].startswith("## "):
                            break
                    break

    # 找分集信息
    for line in lines:
        if re.match(rf"\|\s*{ch_num}\s*\|", line):
            result.append(f"【分集总览】{line.strip()}")
            break

    return "\n".join(result) if result else ""


def get_adaptation_principles(config) -> str:
    """从改编策略中提取核心原则。"""
    adaptation = load_adaptation(config)
    if not adaptation:
        return ""

    lines = adaptation.split("\n")
    result = []
    in_principles = False

    for line in lines:
        if "核心改编原则" in line or "改编原则" in line:
            in_principles = True
            continue
        if in_principles:
            if line.startswith("## ") or line.startswith("### "):
                break
            if line.strip():
                result.append(line.strip())
            if len(result) >= 15:
                break

    return "\n".join(result) if result else ""


# ─── 状态管理（兼容现有 StateManager）─────────────────────────────────────

def get_state_path(config) -> Path:
    """获取 state.json 路径。"""
    return get_rewrites_dir(config) / "state.json"
