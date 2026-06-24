"""
源书级 I/O — 共享产物读写（events / skeleton / adaptation / styles / 源文）。

两套引擎共用，路径基于 _cache/。
"""

import json
import re
from pathlib import Path


# ─── 路径解析 ──────────────────────────────────────────────────────────────

def get_cache_dir(config) -> Path:
    """从 config 推断 _cache/ 路径。"""
    base_dir = config.get("base_dir", ".")
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    return Path(base_dir) / "projects" / author / source_book / "_cache"


def get_cache_dir_from_path(source_dir: str) -> Path:
    """从源文章节目录推断 _cache/ 路径。"""
    p = Path(source_dir)
    if p.name == "chapters" and p.parent.name == "_cache":
        return p.parent
    return p / "_cache"


# ─── 源文读取 ──────────────────────────────────────────────────────────────

def _resolve_chapters_dir(config) -> Path | None:
    """解析源文章节目录。优先拆文库，回退 _cache。"""
    # 1. 拆文库章节/
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        d = Path(analyze_dir) / "章节"
        if d.exists() and list(d.glob("第*章*")):
            return d
    # 2. 拆文库原文/（需切分）
    if analyze_dir:
        d = Path(analyze_dir) / "原文"
        if d.exists() and list(d.glob("*")):
            return d
    # 3. _cache/chapters/
    cache = get_cache_dir(config)
    d = cache / "chapters"
    if d.exists():
        return d
    # 4. 配置路径
    for key in ("source_chapter_dir", "source_dir"):
        if config.get(key):
            d = Path(config[key])
            if d.exists():
                return d
    return None


def get_source_text(config, ch_num: int) -> str:
    """读取源文单章全文。"""
    d = _resolve_chapters_dir(config)
    if not d:
        return ""
    # 查找：第N章*.txt 或 第N章*.md
    for f in sorted(d.glob("第*章*")):
        m = re.search(r"(\d+)", f.name)
        if m and int(m.group(1)) == ch_num:
            return f.read_text(encoding="utf-8")
    return ""


def get_source_chapters(config) -> list[tuple[int, Path]]:
    """获取源文章节列表 [(章号, 路径), ...]。"""
    d = _resolve_chapters_dir(config)
    if not d:
        return []
    chapters = []
    for f in sorted(d.glob("第*章*")):
        m = re.search(r"(\d+)", f.name)
        if m:
            chapters.append((int(m.group(1)), f))
    chapters.sort(key=lambda x: x[0])
    return chapters


def get_total_chapters(config) -> int:
    """获取源文总章数。"""
    return len(get_source_chapters(config))


# ─── 事件表 ────────────────────────────────────────────────────────────────

def load_events(config) -> list[dict]:
    """读取事件表。优先拆文库/events.json，回退 _cache/events.json。"""
    # 1. 优先拆文库
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        f = Path(analyze_dir) / "events.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    # 2. 回退 _cache
    f = get_cache_dir(config) / "events.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def _resolve_write_dir(config) -> Path:
    """解析写入目录：优先拆文库，回退 _cache。"""
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        d = Path(analyze_dir)
        d.mkdir(parents=True, exist_ok=True)
        return d
    return get_cache_dir(config)


def save_events(config, events: list[dict]):
    """保存事件表。"""
    f = _resolve_write_dir(config) / "events.json"
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


def get_chapter_event(config, ch_num: int) -> str:
    """提取指定章节的事件摘要（单行）。"""
    events = load_events(config)
    for e in events:
        if e.get("id") == ch_num or e.get("chapter_index") == ch_num:
            if e.get("event"):
                return f"第{ch_num}章：{e['event']}"
    return ""


# ─── 故事骨架 ──────────────────────────────────────────────────────────────

def load_skeleton(config) -> str:
    """读取故事骨架。优先拆文库，回退 _cache。"""
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        f = Path(analyze_dir) / "story_skeleton.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
    f = get_cache_dir(config) / "story_skeleton.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_skeleton(config, content: str):
    """保存故事骨架。"""
    f = _resolve_write_dir(config) / "story_skeleton.md"
    f.write_text(content, encoding="utf-8")


def get_skeleton_context(config, ch_num: int) -> str:
    """从骨架中提取与指定章节相关的片段（所属幕 + 分集信息）。"""
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

    # 找分集信息（模式A：逐集展开）
    for i, line in enumerate(lines):
        if re.search(rf"集\s*{ch_num}\s*[：:]", line) or re.search(rf"### 集{ch_num}", line):
            result.append("【分集信息】")
            for j in range(i, min(i + 10, len(lines))):
                if lines[j].strip():
                    result.append(lines[j].strip())
                if j > i and (lines[j].startswith("### 集") or lines[j].startswith("## ")):
                    break
            break

    # 找分集总览表中的行（模式B）
    for line in lines:
        if re.match(rf"\|\s*{ch_num}\s*\|", line):
            result.append(f"【分集总览】{line.strip()}")
            break

    return "\n".join(result) if result else ""


# ─── 改编策略 ──────────────────────────────────────────────────────────────

def load_adaptation(config) -> str:
    """读取改编策略。优先拆文库，回退 _cache。"""
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        f = Path(analyze_dir) / "adaptation_strategy.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
    f = get_cache_dir(config) / "adaptation_strategy.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def save_adaptation(config, content: str):
    """保存改编策略。"""
    f = _resolve_write_dir(config) / "adaptation_strategy.md"
    f = get_cache_dir(config) / "adaptation_strategy.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def get_adaptation_principles(config) -> str:
    """从改编策略中提取核心原则（前 5 条）。"""
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


# ─── 文笔指纹 ──────────────────────────────────────────────────────────────

def load_style_text(config, ch_num: int) -> str:
    """加载文笔指纹（算法锚点 + LLM 分析）。"""
    styles_dir = get_cache_dir(config) / "styles"
    parts = []
    f = styles_dir / f"style_{ch_num:03d}.md"
    if f.exists():
        parts.append(f.read_text(encoding="utf-8"))
    f_llm = styles_dir / f"style_{ch_num:03d}_llm.md"
    if f_llm.exists():
        parts.append(f_llm.read_text(encoding="utf-8"))
    return "\n\n".join(parts) if parts else ""
