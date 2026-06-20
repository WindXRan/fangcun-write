"""
文件 I/O 工具层 — 共享产物在 _cache/（源书级），剧本在 output_dir（项目级）。

路径规则：
  events.json / story_skeleton.md / adaptation_strategy.md → _cache/
  scripts/ep_NNN.txt / state.json / reviews/ → output_dir
"""

import json
import re
from pathlib import Path


def _resolve_cache_dir(output_dir: str) -> Path:
    """从 output_dir 推断 _cache/ 路径。
    
    output_dir 通常是 projects/{作者}/{源书名}/{项目名}/
    _cache 通常在 projects/{作者}/{源书名}/_cache/
    """
    p = Path(output_dir)
    # 如果 output_dir 本身包含 _cache，直接用
    if "_cache" in p.parts:
        return p
    # 否则往上找 _cache（output_dir 的父目录下）
    parent = p.parent
    cache = parent / "_cache"
    if cache.exists():
        return cache
    # 兜底：就在 output_dir 下找
    return p


def get_events(output_dir: str, chapter_ids: list[int] = None) -> str:
    """读取事件表，返回格式化文本。"""
    cache_dir = _resolve_cache_dir(output_dir)
    events_file = cache_dir / "events.json"
    if not events_file.exists():
        return "事件表不存在，请先执行事件提取（--phase event）"

    events = json.loads(events_file.read_text(encoding="utf-8"))
    if chapter_ids:
        events = [e for e in events if e.get("id") in chapter_ids]
    if not events:
        return "无匹配事件"

    lines = []
    for e in events:
        lines.append(f"第{e.get('chapter_index', e.get('id', '?'))}章，标题:{e.get('chapter', '?')}，事件:{e.get('event', '?')}")
    return "\n".join(lines)


def get_events_json(output_dir: str) -> list[dict]:
    """读取事件表原始 JSON。"""
    cache_dir = _resolve_cache_dir(output_dir)
    events_file = cache_dir / "events.json"
    if not events_file.exists():
        return []
    return json.loads(events_file.read_text(encoding="utf-8"))


def save_events(output_dir: str, events: list[dict]):
    """保存事件表到 _cache/。"""
    cache_dir = _resolve_cache_dir(output_dir)
    events_file = cache_dir / "events.json"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def get_skeleton(output_dir: str) -> str:
    """读取故事骨架。"""
    cache_dir = _resolve_cache_dir(output_dir)
    f = cache_dir / "story_skeleton.md"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def save_skeleton(output_dir: str, content: str):
    """保存故事骨架到 _cache/。"""
    cache_dir = _resolve_cache_dir(output_dir)
    f = cache_dir / "story_skeleton.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def get_adaptation(output_dir: str) -> str:
    """读取改编策略。"""
    cache_dir = _resolve_cache_dir(output_dir)
    f = cache_dir / "adaptation_strategy.md"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def save_adaptation(output_dir: str, content: str):
    """保存改编策略到 _cache/。"""
    cache_dir = _resolve_cache_dir(output_dir)
    f = cache_dir / "adaptation_strategy.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def get_novel_text(source_dir: str, chapter_index: int) -> str:
    """读取小说章节原文。"""
    source = Path(source_dir)
    for f in sorted(source.glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m and int(m.group(1)) == chapter_index:
            return f.read_text(encoding="utf-8")
    return ""


def get_novel_chapters(source_dir: str) -> list[tuple[int, Path]]:
    """获取所有章节文件列表。"""
    chapters = []
    for f in sorted(Path(source_dir).glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m:
            chapters.append((int(m.group(1)), f))
    return chapters


def get_script_content(output_dir: str, episode_ids: list[int] = None) -> str:
    """读取已有剧本文本（从 output_dir/scripts/）。"""
    scripts_dir = Path(output_dir) / "scripts"
    if not scripts_dir.exists():
        return ""
    if episode_ids is None:
        files = sorted(scripts_dir.glob("ep_*.txt"))
        if not files:
            return ""
        return files[-1].read_text(encoding="utf-8")
    parts = []
    for ep_id in episode_ids:
        f = scripts_dir / f"ep_{ep_id:03d}.txt"
        if f.exists():
            parts.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def save_script(output_dir: str, episode_num: int, content: str):
    """保存单集剧本到 output_dir/scripts/。"""
    scripts_dir = Path(output_dir) / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    f = scripts_dir / f"ep_{episode_num:03d}.txt"
    f.write_text(content, encoding="utf-8")


def get_all_scripts(output_dir: str) -> list[dict]:
    """获取所有剧本列表。"""
    scripts_dir = Path(output_dir) / "scripts"
    if not scripts_dir.exists():
        return []
    result = []
    for f in sorted(scripts_dir.glob("ep_*.txt")):
        m = re.search(r"ep_(\d+)\.txt", f.name)
        if m:
            result.append({
                "id": int(m.group(1)),
                "name": f.stem,
                "content": f.read_text(encoding="utf-8"),
            })
    return result


# ─── XML 解析 ──────────────────────────────────────────────────────────────

def extract_xml_tag(text: str, tag: str) -> str:
    """从 LLM 输出中提取 XML 标签内容。"""
    pattern = rf"<{tag}[^>]*>([\s\S]*?)</{tag}>"
    m = re.search(pattern, text)
    if m:
        return m.group(1).strip()
    pattern_open = rf"<{tag}[^>]*>"
    m_open = re.search(pattern_open, text)
    if m_open:
        return text[m_open.end():].strip()
    return text.strip()


def extract_script_items(text: str) -> list[dict]:
    """从 LLM 输出中提取所有 <scriptItem> 标签。"""
    items = []
    pattern = r'<scriptItem\s+name="([^"]*)"[^>]*>([\s\S]*?)</scriptItem>'
    for m in re.finditer(pattern, text):
        items.append({"name": m.group(1).strip(), "content": m.group(2).strip()})
    if not items:
        pattern_open = r'<scriptItem\s+name="([^"]*)"[^>]*>'
        m_open = re.search(pattern_open, text)
        if m_open:
            name = m_open.group(1).strip()
            content = text[m_open.end():].strip()
            content = re.sub(r"\s*</scriptItem>\s*$", "", content)
            items.append({"name": name, "content": content})
    return items


# ─── 骨架片段提取 ──────────────────────────────────────────────────────────

def extract_episode_from_skeleton(skeleton_text: str, ep_num: int) -> str:
    """从骨架中提取指定集的信息。"""
    lines = skeleton_text.split("\n")
    result_sections = []

    story_core = _extract_section(lines, "故事核", "隐线")
    if story_core:
        result_sections.append("### 故事核\n" + story_core)

    hidden_line = _extract_section(lines, "隐线", "人物小传")
    if hidden_line:
        result_sections.append("### 隐线\n" + hidden_line)

    char_section = _extract_section(lines, "人物小传", "三幕结构")
    if char_section:
        result_sections.append("### 人物小传\n" + char_section[:800])

    ep_info = _extract_episode_info(lines, ep_num)
    if ep_info:
        result_sections.append(f"### 第{ep_num}集分集信息\n" + ep_info)

    act_info = _extract_act_for_episode(lines, ep_num)
    if act_info:
        result_sections.append("### 所属幕\n" + act_info)

    return "\n\n".join(result_sections) if result_sections else skeleton_text[:2000]


def _extract_section(lines, start_marker, end_marker):
    result = []
    capturing = False
    for line in lines:
        if start_marker in line and (line.startswith("#") or line.startswith("**")):
            capturing = True
            continue
        if capturing and (end_marker in line and (line.startswith("#") or line.startswith("**"))):
            break
        if capturing:
            result.append(line)
    return "\n".join(result).strip()


def _extract_episode_info(lines, ep_num):
    result = []
    for line in lines:
        if re.match(rf"\|\s*{ep_num}\s*\|", line):
            result.append(line)
            break
    in_detail = False
    for line in lines:
        if re.search(rf"集{ep_num}[（(]|集{ep_num}[:：]|集{ep_num}\s", line) and "详情" in line:
            in_detail = True
            continue
        if in_detail:
            if line.startswith("### 集") or line.startswith("#### "):
                break
            result.append(line)
    return "\n".join(result).strip()


def _extract_act_for_episode(lines, ep_num):
    for line in lines:
        if "第" in line and "幕" in line and "→" in line:
            m = re.search(r"集(\d+)-(\d+)", line)
            if m:
                start_ep, end_ep = int(m.group(1)), int(m.group(2))
                if start_ep <= ep_num <= end_ep:
                    act_lines = [line]
                    idx = lines.index(line) + 1
                    while idx < len(lines):
                        if "第" in lines[idx] and "幕" in lines[idx] and "→" in lines[idx]:
                            break
                        if lines[idx].startswith("### "):
                            break
                        act_lines.append(lines[idx])
                        idx += 1
                    return "\n".join(act_lines).strip()
    return ""


# ─── 输出校验 ──────────────────────────────────────────────────────────────

def validate_script(content: str, target_words: int = 300) -> list[str]:
    """校验剧本输出质量。"""
    issues = []
    delta_count = content.count("△")
    if delta_count == 0:
        issues.append("严重：缺少△场景描述标记")
    elif delta_count < 3:
        issues.append(f"警告：△场景描述偏少（仅{delta_count}处）")

    word_count = len(content)
    if word_count > target_words * 1.5:
        issues.append(f"严重：超字数 {word_count}字（目标{target_words}字）")
    elif word_count < target_words * 0.5:
        issues.append(f"警告：字数偏少 {word_count}字（目标{target_words}字）")

    if "<scriptItem" not in content:
        issues.append("警告：缺少<scriptItem>开标签")
    if "</scriptItem>" not in content:
        issues.append("警告：缺少</scriptItem>闭合标签")

    scene_headers = re.findall(r"\d+-\d+\s+.+[日夜]/[内外]", content)
    if not scene_headers:
        issues.append("警告：未找到标准场景标题")

    return issues


def validate_event(event_text: str) -> list[str]:
    """校验事件提取结果。"""
    issues = []
    if not event_text or not event_text.strip():
        issues.append("严重：事件为空")
        return issues
    if event_text.startswith("[提取失败"):
        issues.append(f"严重：{event_text}")
        return issues
    if "|" not in event_text:
        issues.append("警告：事件格式异常")
    if len(event_text) < 20:
        issues.append(f"警告：事件描述过短（{len(event_text)}字）")
    return issues
