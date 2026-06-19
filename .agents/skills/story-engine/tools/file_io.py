"""
story-engine 项目级 I/O — rewrites/ 目录下的文件读写。

源书级 I/O（events/skeleton/adaptation/styles）在 source-engine/tools/file_io.py。
"""

import re
from pathlib import Path

# 从 source-engine 导入源书级 I/O（延迟导入，避免循环依赖）
_source_engine_tools = str(Path(__file__).parent.parent.parent / "source-engine" / "tools")


def _ensure_source_engine():
    """确保 source-engine 在 sys.path 中。"""
    import sys
    if _source_engine_tools not in sys.path:
        sys.path.insert(0, _source_engine_tools)


# ─── 路径解析 ──────────────────────────────────────────────────────────────

def get_rewrites_dir(config) -> Path:
    """获取仿写输出目录。"""
    return Path(config.get("rewrites_dir", ""))


def get_guides_dir(config) -> Path:
    """获取 guides 目录。"""
    return get_rewrites_dir(config) / "guides"


def get_chapters_output_dir(config) -> Path:
    """获取仿写章节目录。"""
    return get_rewrites_dir(config) / "chapters"


# ─── 源书级 I/O（代理到 source-engine）────────────────────────────────────

def get_cache_dir(config):
    _ensure_source_engine()
    from file_io import get_cache_dir as _get
    return _get(config)


def get_source_text(config, ch_num: int) -> str:
    _ensure_source_engine()
    from file_io import get_source_text as _get
    return _get(config, ch_num)


def get_source_chapters(config):
    _ensure_source_engine()
    from file_io import get_source_chapters as _get
    return _get(config)


def get_total_chapters(config) -> int:
    _ensure_source_engine()
    from file_io import get_total_chapters as _get
    return _get(config)


def load_events(config):
    _ensure_source_engine()
    from file_io import load_events as _get
    return _get(config)


def save_events(config, events):
    _ensure_source_engine()
    from file_io import save_events as _get
    return _get(config, events)


def get_events_text(config, chapter_ids=None) -> str:
    _ensure_source_engine()
    from file_io import get_events_text as _get
    return _get(config, chapter_ids)


def get_chapter_event(config, ch_num: int) -> str:
    _ensure_source_engine()
    from file_io import get_chapter_event as _get
    return _get(config, ch_num)


def load_skeleton(config) -> str:
    _ensure_source_engine()
    from file_io import load_skeleton as _get
    return _get(config)


def save_skeleton(config, content: str):
    _ensure_source_engine()
    from file_io import save_skeleton as _get
    return _get(config, content)


def get_skeleton_context(config, ch_num: int) -> str:
    """从骨架中提取与指定章节相关的片段（过滤短剧术语，适配小说仿写）。"""
    skeleton = load_skeleton(config)
    if not skeleton:
        return ""

    lines = skeleton.split("\n")
    result = []

    # 短剧专用关键词（过滤掉）
    DRAMA_KEYWORDS = ["付费", "卡点", "投流", "素材", "ROI", "单集公式", "集末钩子", "股价级"]

    def is_drama_line(line):
        return any(kw in line for kw in DRAMA_KEYWORDS)

    # 1. 找本章所属幕
    for i, line in enumerate(lines):
        if "第" in line and "幕" in line and "→" in line:
            m = re.search(r"第(\d+)-(\d+)章", line)
            if m:
                start_ch, end_ch = int(m.group(1)), int(m.group(2))
                if start_ch <= ch_num <= end_ch:
                    if not is_drama_line(line):
                        result.append(f"【所属幕】{line.strip()}")
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if lines[j].startswith("**功能") or lines[j].startswith("**核心问题") or lines[j].startswith("**幕末转折"):
                            if not is_drama_line(lines[j]):
                                result.append(lines[j].strip())
                        if lines[j].startswith("### 第") or lines[j].startswith("## "):
                            break
                    break

    # 2. 找分集信息
    for line in lines:
        if re.match(rf"\|\s*{ch_num}\s*\|", line):
            if not is_drama_line(line):
                result.append(f"【分集信息】{line.strip()}")
            break

    # 3. 提取人物小传（如果本章涉及关键角色）
    in_chars = False
    char_lines = []
    for line in lines:
        if "人物小传" in line:
            in_chars = True
            continue
        if in_chars:
            if line.startswith("### ") or line.startswith("## "):
                break
            char_lines.append(line)
    if char_lines:
        # 只取前 500 字（主角+反一号）
        result.append("【核心角色】\n" + "\n".join(char_lines)[:500])

    return "\n".join(result) if result else ""


def load_adaptation(config) -> str:
    _ensure_source_engine()
    from file_io import load_adaptation as _get
    return _get(config)


def save_adaptation(config, content: str):
    _ensure_source_engine()
    from file_io import save_adaptation as _get
    return _get(config, content)


def get_adaptation_principles(config) -> str:
    """从改编策略中提取核心原则（过滤短剧术语，适配小说仿写）。"""
    adaptation = load_adaptation(config)
    if not adaptation:
        return ""

    lines = adaptation.split("\n")
    result = []
    in_principles = False

    # 短剧专用关键词（整行跳过）
    DRAMA_KEYWORDS = ["付费", "卡点", "投流", "素材", "ROI", "单集公式", "集末钩子", "股价级", "竖屏", "横屏", "AI短剧", "AI 形态"]

    for line in lines:
        if "核心改编原则" in line or "改编原则" in line:
            in_principles = True
            continue
        if in_principles:
            if line.startswith("## ") or line.startswith("### "):
                break
            if line.strip():
                # 跳过包含短剧关键词的行
                if any(kw in line for kw in DRAMA_KEYWORDS):
                    continue
                result.append(line.strip())
            if len(result) >= 15:
                break

    return "\n".join(result) if result else ""


def load_style_text(config, ch_num: int) -> str:
    _ensure_source_engine()
    from file_io import load_style_text as _get
    return _get(config, ch_num)


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


def load_plot(config) -> str:
    return load_settings(config, "plot.md")


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
