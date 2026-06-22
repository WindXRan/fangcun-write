"""Phase 2: plot-guide 生成"""

import os
import re
import json
import time
from pathlib import Path

import _path_setup  # noqa: F401
from utils import (
    get_total_chapters, count_source_chars, batch_run, debug_dump_prompt,
    get_source_text
)
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from prompt_loader import load_prompt


# 骨架映射缓存
_skeleton_map_cache = None


def _load_skeleton_map(config):
    """加载 skeleton_map.json（模块级缓存）。"""
    global _skeleton_map_cache
    if _skeleton_map_cache is not None:
        return _skeleton_map_cache
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    map_path = rewrites_dir / "skeleton_map.json"
    if map_path.exists():
        _skeleton_map_cache = json.loads(map_path.read_text(encoding="utf-8"))
    else:
        _skeleton_map_cache = {}
    return _skeleton_map_cache


def _get_source_text_for_chapter(config, ch):
    """获取源文文本。如果有 skeleton_map，按映射加载多个源文章节。"""
    skel_map = _load_skeleton_map(config)
    chapters = skel_map.get("chapters", [])
    if not chapters:
        # 没有骨架映射，按传统 1:1 加载
        return get_source_text(config, ch)

    # 找到新章节 ch 对应的源文章节
    for entry in chapters:
        if entry.get("ch") == ch:
            source_chs = entry.get("source", [])
            action = entry.get("action", "keep")
            if action == "new" or not source_chs:
                return None  # 全新章节，没有源文参考
            # 合并多个源文章节的文本
            parts = []
            for src_ch in source_chs:
                text = get_source_text(config, src_ch)
                if text:
                    parts.append(f"--- 源文第{src_ch}章 ---\n{text}")
            return "\n\n".join(parts) if parts else None
    return None


def _get_source_chars_for_chapter(config, ch):
    """获取源文字数。如果有 skeleton_map，按映射计算。"""
    skel_map = _load_skeleton_map(config)
    chapters = skel_map.get("chapters", [])
    if not chapters:
        return count_source_chars(config, ch)

    for entry in chapters:
        if entry.get("ch") == ch:
            source_chs = entry.get("source", [])
            action = entry.get("action", "keep")
            if action == "new" or not source_chs:
                return 2000  # 全新章节用默认字数
            total = 0
            for src_ch in source_chs:
                total += count_source_chars(config, src_ch)
            return total
    return count_source_chars(config, ch)

# 模块级缓存：book_data.json 每章都读，缓存一次
_book_data_cache = None


def _get_book_data(rewrites_dir):
    """读取 book_data.json（模块级缓存）。"""
    global _book_data_cache
    if _book_data_cache is not None:
        return _book_data_cache
    if rewrites_dir:
        bd_path = Path(rewrites_dir) / "book_data.json"
        if bd_path.exists():
            import json
            try:
                _book_data_cache = json.loads(bd_path.read_text(encoding="utf-8"))
            except Exception:
                _book_data_cache = {}
            return _book_data_cache
    _book_data_cache = {}
    return _book_data_cache


# 模块级缓存：角色名映射
_name_map_cache = None


def _build_name_map(config):
    """从 characters.md 构建源文名→新名映射（模块级缓存）。LLM 生成，不做脚本兜底。"""
    global _name_map_cache
    if _name_map_cache is not None:
        return _name_map_cache

    _name_map_cache = {}
    base_dir = Path(config.get("base_dir", "."))
    rewrites_dir = base_dir / config.get("rewrites_dir", "")

    chars_files = []
    chars_path1 = rewrites_dir / "settings" / "characters.md"
    chars_path2 = rewrites_dir / "characters.md"
    if chars_path1.exists():
        chars_files.append(chars_path1)
    if chars_path2.exists():
        chars_files.append(chars_path2)

    if not chars_files:
        return _name_map_cache

    for chars_path in chars_files:
        chars_text = chars_path.read_text(encoding="utf-8")

        # 格式1: 【新名】（源文对应：源文名）
        for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
            new_name = m.group(1).strip()
            old_names_raw = m.group(2).strip()
            old_names = re.split(r'[/、]', old_names_raw)
            for old_name in old_names:
                old_name = old_name.strip()
                if old_name and old_name != new_name and old_name not in _name_map_cache:
                    _name_map_cache[old_name] = new_name

        # 格式2: ## 【角色位】新名（原料名）
        for m in re.finditer(r'##\s*【[^】]+】(.+?)（原(.+?)）', chars_text):
            new_name = m.group(1).strip()
            old_name = m.group(2).strip()
            if old_name and new_name and old_name != new_name and old_name not in _name_map_cache:
                _name_map_cache[old_name] = new_name

        # 格式3: 表格行
        for line in chars_text.split('\n'):
            line = line.strip()
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) < 2:
                continue
            old_name = cells[0]
            new_name = cells[1]
            if old_name in ('源文名', '----', '---', '===') or new_name in ('新名', '----', '---', '==='):
                continue
            if '-' in old_name or '-' in new_name:
                continue
            if old_name and new_name and old_name != new_name and old_name not in _name_map_cache:
                _name_map_cache[old_name] = new_name

    return _name_map_cache


# 模块级缓存：events.json 映射后版本
_events_mapped_cache = None


def _load_events_mapped(config):
    """加载 events.json 并替换为新名（模块级缓存）。"""
    global _events_mapped_cache
    if _events_mapped_cache is not None:
        return _events_mapped_cache

    from file_io import load_events
    events = load_events(config)
    name_map = _build_name_map(config)

    if not name_map:
        _events_mapped_cache = events
        return events

    mapped = []
    for e in events:
        e_copy = dict(e)
        event_text = e_copy.get("event", "")
        for old, new in name_map.items():
            event_text = event_text.replace(old, new)
        e_copy["event"] = event_text
        mapped.append(e_copy)

    _events_mapped_cache = mapped
    return mapped


# 模块级缓存：story_skeleton.md 映射后版本
_skeleton_mapped_cache = None


def _load_skeleton_mapped(config):
    """加载 story_skeleton.md 并替换为新名（模块级缓存）。"""
    global _skeleton_mapped_cache
    if _skeleton_mapped_cache is not None:
        return _skeleton_mapped_cache

    from file_io import load_skeleton
    skeleton = load_skeleton(config)
    name_map = _build_name_map(config)

    if not name_map or not skeleton:
        _skeleton_mapped_cache = skeleton
        return skeleton

    for old, new in name_map.items():
        skeleton = skeleton.replace(old, new)

    _skeleton_mapped_cache = skeleton
    return skeleton


# 模块级缓存：adaptation_strategy.md 映射后版本
_adaptation_mapped_cache = None


def _load_adaptation_mapped(config):
    """加载 adaptation_strategy.md 并替换为新名（模块级缓存）。"""
    global _adaptation_mapped_cache
    if _adaptation_mapped_cache is not None:
        return _adaptation_mapped_cache

    from file_io import load_adaptation
    adaptation = load_adaptation(config)
    name_map = _build_name_map(config)

    if not name_map or not adaptation:
        _adaptation_mapped_cache = adaptation
        return adaptation

    for old, new in name_map.items():
        adaptation = adaptation.replace(old, new)

    _adaptation_mapped_cache = adaptation
    return adaptation


# 模块级缓存：源文风格指纹 {ch: fingerprint_dict}
_style_fingerprint_cache = {}


def _get_style_fingerprint(config, ch):
    """获取源文风格指纹（模块级缓存）。"""
    if ch in _style_fingerprint_cache:
        return _style_fingerprint_cache[ch]

    src_text = get_source_text(config, ch)
    if not src_text:
        return None

    from lib.text_metrics import count_style_fingerprint
    fp = count_style_fingerprint(src_text)
    _style_fingerprint_cache[ch] = fp
    return fp


# 模块级缓存：文笔指纹文本（映射后） {ch: style_text}
_style_text_cache = {}


def _get_style_text_mapped(config, ch):
    """获取文笔指纹文本，替换源文名字，保留风格信息。"""
    if ch in _style_text_cache:
        return _style_text_cache[ch]

    from file_io import load_style_text
    style_text = load_style_text(config, ch)
    if not style_text:
        _style_text_cache[ch] = None
        return None

    # 替换源文角色名（包括昵称）
    name_map = _build_name_map(config)
    if name_map:
        # 添加昵称映射
        extended_map = dict(name_map)
        # 从 characters.md 提取昵称映射
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for line in chars_text.split('\n'):
                if '→' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        old_nick = parts[0]
                        new_nick = parts[1]
                        if old_nick and new_nick and old_nick != new_nick:
                            extended_map[old_nick] = new_nick
        
        # 替换所有名字
        for old_name, new_name in extended_map.items():
            style_text = style_text.replace(old_name, new_name)

    # 保留<style_deep>部分，去掉例句行
    filtered_lines = []
    in_style_deep = False
    for line in style_text.split("\n"):
        # 跟踪<style_deep>部分
        if '<style_deep>' in line:
            in_style_deep = True
        if '</style_deep>' in line:
            in_style_deep = False
            filtered_lines.append(line)
            continue
        
        # 在<style_deep>内，保留所有内容（包括例子）
        if in_style_deep:
            filtered_lines.append(line)
            continue
        
        # 在<style_deep>外，去掉例句行
        if re.match(r'^\s*(例句|例|示例)[：:]', line.strip()):
            continue
        filtered_lines.append(line)
    
    style_text = "\n".join(filtered_lines)

    _style_text_cache[ch] = style_text
    return style_text


# 模块级缓存：世界观文本
_world_cache = None


def _get_world_text(config):
    """获取世界观文本（模块级缓存）。"""
    global _world_cache
    if _world_cache is not None:
        return _world_cache

    world_path = Path(config["rewrites_dir"]) / "world.md"
    if world_path.exists():
        _world_cache = world_path.read_text(encoding="utf-8")[:2000]
    else:
        _world_cache = "（世界观文件不存在，请参考源文设定）"
    return _world_cache


# 模块级缓存：世界观约束
_world_constraint_cache = None


def _get_world_constraint(config):
    """从 concept.md 提取世界观约束（时间线/年龄/地点）。"""
    global _world_constraint_cache
    if _world_constraint_cache is not None:
        return _world_constraint_cache

    concept_path = Path(config.get("rewrites_dir", "")) / "concept.md"
    if not concept_path.exists():
        _world_constraint_cache = "（concept.md 不存在）"
        return _world_constraint_cache

    concept = concept_path.read_text(encoding="utf-8")

    # 提取定位、故事核、卖点等关键信息作为约束
    parts = []
    for section in ["定位", "故事核", "卖点", "策略"]:
        m = re.search(rf'(?:##?\s*\d*\.?\s*{section}.*?\n)(.*?)(?=\n##|\Z)', concept, re.DOTALL)
        if m:
            text = m.group(1).strip()[:200]
            if text:
                parts.append(f"- {section}：{text}")

    # 提取角色年龄/身份信息
    chars_path = Path(config["rewrites_dir"]) / "characters.md"
    if not chars_path.exists():
        chars_path = Path(config["rewrites_dir"]) / "settings" / "characters.md"
    if chars_path.exists():
        chars_text = chars_path.read_text(encoding="utf-8")
        # 动态提取所有角色名（从 characters.md 解析）
        char_names = [m.group(1).strip() for m in re.finditer(r'【(.+?)】[（(]源文对应', chars_text)]
        for name in char_names[:5]:  # 最多取5个主角
            m = re.search(rf'【{re.escape(name)}】.*?(?:功能位|身份)[：:]\s*(.+)', chars_text)
            if m:
                parts.append(f"- {name}身份：{m.group(1).strip()[:50]}")

    _world_constraint_cache = "\n".join(parts) if parts else "（未提取到世界观约束）"
    return _world_constraint_cache


# 模块级缓存：全量角色名映射表文本
_name_map_text_cache = None


def _build_name_map_text(config):
    """从 characters.md 构建角色名映射表文本。格式：源文名→新名"""
    global _name_map_text_cache
    if _name_map_text_cache is not None:
        return _name_map_text_cache

    chars_path = Path(config["rewrites_dir"]) / "characters.md"
    if not chars_path.exists():
        _name_map_text_cache = ""
        return ""

    chars_text = chars_path.read_text(encoding="utf-8")
    items = []
    seen = set()

    # 格式1: 表格行 | 源文名 | 新名 | ... |
    for line in chars_text.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) < 2:
            continue
        old_name = cells[0]
        new_name = cells[1]
        if old_name in ('源文名', '----', '---', '===') or new_name in ('新名', '----', '---', '==='):
            continue
        if '-' in old_name or '-' in new_name:
            continue
        if old_name and new_name and old_name != new_name and old_name not in seen:
            items.append(f"{old_name}→{new_name}")
            seen.add(old_name)

    # 格式2: 【新名】（源文对应：源文名）
    for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
        new_name = m.group(1).strip()
        old_name = m.group(2).strip()
        if new_name != old_name and old_name not in seen:
            items.append(f"{old_name}→{new_name}")
            seen.add(old_name)

    _name_map_text_cache = "、".join(items) if items else ""
    return _name_map_text_cache


# 模块级缓存：风格类型文本
_genre_cache = None


def _get_genre_text(config):
    """获取风格类型文本（模块级缓存）。"""
    global _genre_cache
    if _genre_cache is not None:
        return _genre_cache

    concept_path = Path(config.get("rewrites_dir", "")) / "concept.md"
    if concept_path.exists():
        concept_text = concept_path.read_text(encoding="utf-8")
        # 匹配 "## 风格类型" 或 "## 2. 风格类型" 等格式
        genre_match = re.search(r'##\s*\d*\.?\s*风格类型.*?\n(.*?)(?=\n##|\Z)', concept_text, re.DOTALL)
        if genre_match:
            _genre_cache = genre_match.group(1).strip()
        else:
            # 尝试匹配 "定位" 行
            pos_match = re.search(r'定位[：:]\s*(.+)', concept_text)
            if pos_match:
                _genre_cache = f"题材类型：{pos_match.group(1).strip()}"
            else:
                _genre_cache = "（风格类型未提取，请参考源文基调）"
    else:
        _genre_cache = "（concept.md 不存在）"
    return _genre_cache


def _extract_gender_info(chars_text):
    """从 characters.md 提取角色性别信息。返回格式："{角色名}（{性别}）、..."。"""
    genders = []
    for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
        name = m.group(1).strip()
        start = m.end()
        next_section = chars_text[start:start+500]
        gender = "未知"
        if re.search(r'女主|女性|女孩|姑娘|小姐|姐姐|妹妹|女儿|她\b', next_section):
            gender = "女"
        elif re.search(r'男主|男性|男孩|小子|先生|哥哥|弟弟|儿子|他\b', next_section):
            gender = "男"
        if gender != "未知":
            genders.append(f"{name}（{gender}）")
    return "、".join(genders) if genders else ""


def _build_name_list(chars_text):
    """从 characters.md 构建完整角色名列表。格式：苏念（女，源文：李观澜）、凌霄（男，源文：江流）..."""
    items = []
    for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
        new_name = m.group(1).strip()
        old_name = m.group(2).strip()
        start = m.end()
        section = chars_text[start:start+300]
        gender = ""
        if re.search(r'女性|女孩|女儿|她\b|女主|小姐|姐姐|妹妹', section):
            gender = "女"
        elif re.search(r'男性|男孩|儿子|他\b|男主|先生|哥哥|弟弟', section):
            gender = "男"
        if new_name == old_name:
            entry = new_name
        elif gender:
            entry = f"{new_name}（{gender}，源文：{old_name}）"
        else:
            entry = f"{new_name}（源文：{old_name}）"
        items.append(entry)
    return "、".join(items) if items else ""


def _extract_info_release(config, chapter_num):
    """从 events.json 提取本章功能描述，支持骨架映射。"""
    from file_io import load_events
    
    events = load_events(config)
    if not events:
        return f"（第{chapter_num}章事件未找到）"
    
    # 检查骨架映射
    skel_map = _load_skeleton_map(config)
    source_chs = []
    action = "keep"
    for entry in skel_map.get("chapters", []):
        if entry.get("ch") == chapter_num:
            source_chs = entry.get("source", [])
            action = entry.get("action", "keep")
            break
    
    if action == "new" or not source_chs:
        # 全新章节，返回骨架映射中的 function 描述
        for entry in skel_map.get("chapters", []):
            if entry.get("ch") == chapter_num:
                func = entry.get("function", "")
                title = entry.get("title", "")
                conflict = entry.get("conflict_desc", "")
                page_turn = entry.get("page_turn", "")
                page_turn_desc = entry.get("page_turn_desc", "")
                lines = [f"## 本章任务", f"- 章名：{title}", f"- 功能：{func}", f"- 类型：全新设计（源文无对应）"]
                if conflict:
                    lines.append(f"- 冲突：{conflict}")
                if page_turn:
                    lines.append(f"- 翻页理由：{page_turn}（{page_turn_desc}）")
                return "\n".join(lines)
        return f"（第{chapter_num}章：全新设计）"
    
    # 收集所有源文章节的事件
    all_events = []
    for src_ch in source_chs:
        for e in events:
            if e.get("chapter_index") == src_ch or e.get("id") == src_ch:
                all_events.append(e)
    
    if not all_events:
        return f"（第{chapter_num}章事件未找到）"
    
    # 合并事件描述
    info_lines = []
    for entry in skel_map.get("chapters", []):
        if entry.get("ch") == chapter_num:
            info_lines.append(f"## 本章任务")
            info_lines.append(f"- 章名：{entry.get('title', '')}")
            info_lines.append(f"- 功能：{entry.get('function', '')}")
            if len(source_chs) > 1:
                info_lines.append(f"- 源文对应：第{', '.join(str(c) for c in source_chs)}章（已合并）")
            conflict = entry.get("conflict_desc", "")
            page_turn = entry.get("page_turn", "")
            page_turn_desc = entry.get("page_turn_desc", "")
            if conflict:
                info_lines.append(f"- 冲突：{conflict}")
            if page_turn:
                info_lines.append(f"- 翻页理由：{page_turn}（{page_turn_desc}）")
            break
    
    for e in all_events:
        event_text = e.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 4:
            characters = parts[2].strip() if len(parts) > 2 else ""
            function = parts[4].strip() if len(parts) > 4 else ""
            if characters:
                info_lines.append(f"- 出场角色：{characters}")
            if function:
                info_lines.append(f"- 源文功能：{function}")
    
    return "\n".join(info_lines) if info_lines else f"（第{chapter_num}章事件未找到）"


def _get_chapter_characters(config, ch_num):
    """从 events.json 提取本章出场角色，映射为新名。"""
    # 使用缓存的映射版本
    events = _load_events_mapped(config)

    # 找本章事件（已经是新名）
    chars = set()
    for e in events:
        if e.get("id") == ch_num or e.get("chapter_index") == ch_num:
            event_text = e.get("event", "")
            # 事件格式：| 第X章 标题 | 角色1、角色2 | 事件 | ...
            parts = event_text.split("|")
            if len(parts) >= 3:
                raw_chars = parts[2].strip()
                for c in re.split(r"[、，,]", raw_chars):
                    c = c.strip()
                    if c:
                        chars.add(c)
            break

    if not chars:
        # fallback: 返回全部角色
        chars_path = Path(config["rewrites_dir"]) / "settings" / "characters.md"
        if not chars_path.exists():
            chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            return _build_name_list(chars_path.read_text(encoding="utf-8"))
        return ""

    return "、".join(sorted(chars))




def _load_character_cards(config, ch_num):
    """加载本章出场角色的卡内容（从 characters/ 目录读取独立文件）。"""
    # 使用缓存的映射版本
    events = _load_events_mapped(config)

    # 构建角色最早出场章节映射
    char_first_ch = {}
    for e in events:
        ch = e.get("id") or e.get("chapter_index")
        event_text = e.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 3:
            for c in re.split(r"[、，,]", parts[2].strip()):
                c = c.strip()
                if c:
                    if c not in char_first_ch:
                        char_first_ch[c] = ch

    # 从 events.json 提取本章出场角色
    chars = set()
    for e in events:
        if e.get("id") == ch_num or e.get("chapter_index") == ch_num:
            event_text = e.get("event", "")
            parts = event_text.split("|")
            if len(parts) >= 3:
                for c in re.split(r"[、，,]", parts[2].strip()):
                    c = c.strip()
                    if c:
                        chars.add(c)
            break

    if not chars:
        return "（无角色信息）"

    # 读取角色卡文件
    base_dir = Path(config.get("base_dir", "."))
    rewrites_dir = base_dir / config.get("rewrites_dir", "")
    cards_dir = rewrites_dir / "characters"
    cards = []
    
    # 添加出场角色列表（含最早出场章节）
    char_list = []
    for name in sorted(chars):
        first_ch = char_first_ch.get(name, "?")
        char_list.append(f"- {name}（第{first_ch}章首次出场）")
    
    cards.append(f"## 本章出场角色（第{ch_num}章）\n" + "\n".join(char_list))
    cards.append("")
    
    for name in sorted(chars):
        card_path = cards_dir / f"{name}.md"
        if card_path.exists():
            cards.append(card_path.read_text(encoding="utf-8"))
        else:
            # fallback: 从 characters.md 中提取该角色
            chars_path = rewrites_dir / "settings" / "characters.md"
            if not chars_path.exists():
                chars_path = rewrites_dir / "characters.md"
            if chars_path.exists():
                chars_text = chars_path.read_text(encoding="utf-8")
                # 匹配格式1: 【角色名】
                m = re.search(rf'【{re.escape(name)}】[\s\S]*?(?=【[^】]|$)', chars_text)
                if m:
                    cards.append(m.group(0).strip())
                else:
                    # 匹配格式2: ### 【角色位】name（...）— 角色位不是名字
                    m = re.search(rf'###\s*【[^】]+】{re.escape(name)}[（(][\s\S]*?(?=###|$)', chars_text)
                    if m:
                        cards.append(m.group(0).strip())
                    else:
                        # 匹配格式3: 角色名出现在表格行中，提取该行+后续角色卡
                        m = re.search(rf'【[^】]*{re.escape(name)}[^】]*】[\s\S]*?(?=###\s*【|$)', chars_text)
                        if m:
                            cards.append(m.group(0).strip())

    return "\n\n".join(cards) if cards else "（无角色信息）"


def _extract_highlights(src_text, max_chars=300):
    """从源文提取情绪密度最高的段落作为参考。"""
    if not src_text:
        return ""
    
    # 按段落分割
    paragraphs = [p.strip() for p in src_text.split('\n') if p.strip() and len(p.strip()) > 20]
    if not paragraphs:
        return ""
    
    # 情绪关键词权重
    emotion_words = {
        '哭': 3, '泪': 3, '怕': 2, '紧': 2, '慌': 2, '急': 2, '抖': 2,
        '死': 3, '命': 2, '血': 3, '痛': 2, '苦': 2, '惨': 2,
        '笑': 1, '喜': 1, '乐': 1, '甜': 1, '暖': 1,
        '怒': 2, '恨': 2, '骂': 2, '打': 2, '摔': 2,
        '空': 2, '饿': 2, '冷': 2, '黑': 1, '暗': 1,
    }
    
    # 计算每段的情绪分数
    scored = []
    for p in paragraphs:
        score = sum(emotion_words.get(w, 0) for w in p if w in emotion_words)
        # 对话加分（有引号）
        if '"' in p or '"' in p or '「' in p:
            score += 2
        # 短句加分（节奏感）
        short_sents = len([s for s in p.split('。') if 0 < len(s) < 20])
        score += short_sents
        scored.append((score, p))
    
    # 按分数排序，取前几段
    scored.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    total = 0
    for score, p in scored:
        if total + len(p) > max_chars:
            break
        result.append(p)
        total += len(p)
    
    return '\n\n'.join(result[:3])  # 最多3段


# ============================================================
# 续写模式支持
# ============================================================

def _is_continue_mode(config):
    """判断是否是续写模式。"""
    return config.get("mode") == "continue"


def _get_continue_plan_event(config, ch_num):
    """从续写方案（plan.md）中提取本章事件。
    
    续写方案格式：
    | 卷/段 | 章节范围 | 核心事件 | 情绪基调 | 爽点 |
    |-------|----------|----------|----------|------|
    | 第一卷 | 1-50章 | {核心事件} | {延续原作基调} | {爽点} |
    
    或者：
    **关键事件：**
    1. 第1-10章：{事件}
    2. 第11-20章：{事件}
    """
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    
    # 尝试读取续写方案
    plan_files = [
        rewrites_dir / "续写方案.md",
        rewrites_dir / "plan.md",
    ]
    
    # 也检查plans目录
    plans_dir = rewrites_dir.parent / "续写引擎" / "plans"
    if plans_dir.exists():
        for f in plans_dir.glob("plan_*.md"):
            plan_files.append(f)
    
    plan_text = None
    for pf in plan_files:
        if pf.exists():
            plan_text = pf.read_text(encoding="utf-8")
            break
    
    if not plan_text:
        return None
    
    # 提取情节线表格中的事件
    # 格式：| 第一卷 | 1-50章 | {核心事件} | ...
    import re
    for line in plan_text.split('\n'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) < 3:
            continue
        
        # 解析章节范围
        range_cell = cells[1]  # 如 "1-50章"
        range_match = re.search(r'(\d+)[-~](\d+)', range_cell)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start <= ch_num <= end:
                return cells[2]  # 核心事件
    
    # 提取关键事件
    # 格式：1. 第1-10章：{事件}
    for line in plan_text.split('\n'):
        match = re.match(r'\d+\.\s*第(\d+)[-~](\d+)章[：:]\s*(.+)', line.strip())
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start <= ch_num <= end:
                return match.group(3).strip()
    
    return None


def _get_continue_style(config, ch_num):
    """续写模式的风格参考：从原作前3章提取详细写法指令。"""
    from pathlib import Path
    import re
    
    # 直接读取源文
    base_dir = Path(config.get("base_dir", "."))
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    src_dir = base_dir / "projects" / author / source_book / "_cache" / "chapters"
    
    if not src_dir.exists():
        return None
    
    # 使用原作前3章作为风格参考
    style_parts = []
    write_instructions = []
    
    for i in range(1, 4):
        src_file = src_dir / f"第{i}章.txt"
        if not src_file.exists():
            src_file = src_dir / f"第{i:03d}章.txt"
        if not src_file.exists():
            continue
            
        src_text = src_file.read_text(encoding="utf-8")
        if not src_text:
            continue
        
        # 统计句长
        sentences = re.split(r'[。！？]', src_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sent_len = sum(len(s) for s in sentences) // len(sentences)
            style_parts.append(f"第{i}章风格：句长{avg_sent_len}字")
        
        # 统计对话占比
        dialogue_lines = [line for line in src_text.split('\n') if '"' in line or '"' in line]
        if dialogue_lines:
            dialogue_chars = sum(len(line) for line in dialogue_lines)
            total_chars = len(src_text.replace('\n', '').replace(' ', ''))
            dialogue_ratio = dialogue_chars / total_chars if total_chars > 0 else 0
            write_instructions.append(f"第{i}章对话特点：{len(dialogue_lines)}句对话，占比{dialogue_ratio:.0%}")
        
        # 统计段落结构
        paragraphs = [p.strip() for p in src_text.split('\n') if p.strip() and len(p.strip()) > 20]
        if paragraphs:
            avg_para_len = sum(len(p) for p in paragraphs) // len(paragraphs)
            write_instructions.append(f"第{i}章段落：平均{avg_para_len}字/段")
    
    if style_parts or write_instructions:
        result = "续写风格参考（原作前3章）：\n"
        if style_parts:
            result += "\n".join(style_parts) + "\n"
        if write_instructions:
            result += "\n写法指令：\n" + "\n".join(write_instructions[:6])
        return result
    return None


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def phase_guides(config, start, end, workers=5, state_mgr=None):
    """生成 plot_guide（含文笔指纹提取 + 全书风格聚合）。"""
    from lib.api_client import get_api_url
    
    guides_dir = f"{config['rewrites_dir']}/guides"

    if state_mgr:
        state_mgr.phase_start("guides")

    # 先提取文笔指纹（如果还没有提取）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: 文笔指纹 + plot_guide (ch{start}-{end}, {workers}w)")
    print("=" * 50)
    
    _extract_style_fingerprints(config, start, end, workers)

    # plot-guide（JSON 输出 + 模板合并）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: plot_guide (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    ok, fail = batch_run(config, "plot-guide", start, end, workers, guides_dir,
                         "plot_{ch}.md", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one_with_template)

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")

    # 验证 Guide 质量
    if ok:
        print(f"\n{'=' * 50}")
        print(f"Guide 质量验证")
        print("=" * 50)
        _validate_guides(config, ok)

    if state_mgr:
        if fail:
            state_mgr.phase_failed("guides", error=f"{len(fail)} fail")
        else:
            state_mgr.phase_done("guides")


def _validate_guides(config, ok_guides):
    """验证 Guide 质量。"""
    issues = []
    for ch, path in ok_guides.items():
        try:
            content = Path(path).read_text(encoding="utf-8")
            
            # 检查是否有占位符
            placeholders = re.findall(r'\{[a-zA-Z\u4e00-\u9fa5]+\}', content)
            if placeholders:
                issues.append(f"ch{ch}: 有占位符 {set(placeholders)}")
            
            # 检查是否有角色名占位符
            if '【女主】' in content or '【男主】' in content:
                issues.append(f"ch{ch}: 角色名还是占位符")
            
            # 检查节拍表是否有内容
            if '| # |' in content and content.count('|') < 20:
                issues.append(f"ch{ch}: 节拍表可能不完整")
            
            # 检查是否有"待确认"
            if '待确认' in content:
                issues.append(f"ch{ch}: 有待确认内容")
            
            # 新增：检查情绪功能是否具体
            if '情绪功能' in content:
                # 提取情绪功能部分
                ef_match = re.search(r'情绪功能[：:]\s*(.+?)(?=\n|$)', content)
                if ef_match:
                    ef_text = ef_match.group(1).strip()
                    # 检查是否过于笼统
                    generic_phrases = ['推进剧情', '发展关系', '制造冲突', '推进故事']
                    if any(phrase in ef_text for phrase in generic_phrases) and len(ef_text) < 20:
                        issues.append(f"ch{ch}: 情绪功能过于笼统: '{ef_text[:30]}...'")
            
            # 新增：检查核心冲突是否有梯度
            if '核心冲突' in content:
                conflict_match = re.search(r'核心冲突[：:]\s*(.+?)(?=\n##|\n\n|$)', content, re.DOTALL)
                if conflict_match:
                    conflict_text = conflict_match.group(1).strip()
                    # 检查是否提到升级/梯度
                    if '升级' not in conflict_text and '梯度' not in conflict_text and '递进' not in conflict_text:
                        if len(conflict_text) > 10:  # 只有当冲突描述足够长时才警告
                            issues.append(f"ch{ch}: 核心冲突可能缺少升级梯度")
            
            # 新增：检查写法技巧是否可执行
            if '写法技巧' in content:
                tech_match = re.search(r'写法技巧[：:]\s*(.+?)(?=\n##|\n\n|$)', content, re.DOTALL)
                if tech_match:
                    tech_text = tech_match.group(1).strip()
                    # 检查是否有具体技巧
                    if len(tech_text) < 20:
                        issues.append(f"ch{ch}: 写法技巧可能不够具体")
            
            # 新增：检查源文高光是否被引用
            if '源文高光' in content and '{源文高光}' in content:
                issues.append(f"ch{ch}: 源文高光占位符未被替换")
                
        except Exception as e:
            issues.append(f"ch{ch}: 读取失败 {e}")
    
    if issues:
        print(f"  [WARN] {len(issues)} 个问题:")
        for issue in issues[:10]:  # 最多显示10个
            print(f"    - {issue}")
    else:
        print(f"  [OK] 全部通过")


def _extract_style_fingerprints(config, start, end, workers):
    """提取源文文笔指纹（算法锚点 + LLM分析）。"""
    from phases.style_extract import phase_style_extract
    phase_style_extract(config, start, end, workers)


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, 
            system_prompt=None, extra_replacements=None, retry_context=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。
    
    Args:
        retry_context: 重试时附带的修正提示（如"代词密度偏离源文"），注入 system_prompt
    """
    from lib.api_client import call_llm, get_api_url

    prompts_dir = config.get("prompts_dir", str(Path(__file__).parent.parent.parent / "prompts"))
    base_dir = config.get("base_dir", os.getcwd())

    n = str(chapter_num) if chapter_num else "1"
    n_plus1 = str(chapter_num + 1) if chapter_num else "2"
    total_ch = get_total_chapters(config)
    replacements = {
        "新书名": Path(config.get("rewrites_dir", "")).name,
        "N": n,
        "N_plus1": n_plus1,
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
    }

    # 需要源文字数时，脚本计算
    if prompt_type in ("plot-guide", "write-chapter") and chapter_num:
        src_chars = _get_source_chars_for_chapter(config, chapter_num)
        target_chars = src_chars if src_chars > 0 else 1500
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
        # 源文句长（从文笔指纹提取，供仿写对标）
        if "源文句长" not in replacements:
            src_text = _get_source_text_for_chapter(config, chapter_num)
            if src_text:
                from lib.text_metrics import count_metrics
                src_metrics = count_metrics(src_text)
                replacements["源文句长"] = str(int(src_metrics.get("avg_sent_len", 25)))
            else:
                replacements["源文句长"] = "25"
    
    # trim/expand 目标字数硬编码 2000-3000
    if prompt_type in ("trim-chapter", "expand-chapter") and chapter_num:
        replacements.setdefault("目标字数", "2500")
        replacements.setdefault("目标字数_min", "2000")
        replacements.setdefault("目标字数_max", "3000")
    
    # plot-guide 注入信息释放清单（不传源文全文，防止换皮）
    if prompt_type == "plot-guide" and chapter_num:
        # 从 events.json 提取本章事件信息
        info_release = _extract_info_release(config, chapter_num)
        replacements["event"] = info_release
        
        # 源文高光（保留，用于风格参考）
        source_text = _get_source_text_for_chapter(config, chapter_num)
        if source_text:
            highlights = _extract_highlights(source_text, max_chars=500)
            replacements["highlights"] = highlights or ""
        else:
            replacements["highlights"] = ""
        
        # 注入源文结构缓存（per-chapter）
        if "structure" not in replacements:
            from phases.style_extract import load_chapter_structure
            ch_struct = load_chapter_structure(config, chapter_num)
            replacements["structure"] = ch_struct or "（结构未提取）"
        # 注入本章出场角色卡内容
        if "characters" not in replacements and chapter_num:
            replacements["characters"] = _load_character_cards(config, chapter_num)
        # 注入世界观
        if "world" not in replacements:
            replacements["world"] = _get_world_text(config)
        # 注入世界观约束（统一时间线/年龄/地点）
        if "world_constraint" not in replacements:
            replacements["world_constraint"] = _get_world_constraint(config)

    # 写章时注入本章出场角色的卡内容
    if prompt_type == "write-chapter" and chapter_num:
        if "characters" not in replacements:
            replacements["characters"] = _load_character_cards(config, chapter_num)
        if "world" not in replacements:
            replacements["world"] = _get_world_text(config)
        if "style" not in replacements:
            style_text = _get_style_text_mapped(config, chapter_num)
            replacements["style"] = style_text or "（风格未提取）"
        # 注入 name_map
        if "name_map" not in replacements:
            replacements["name_map"] = _build_name_map_text(config)

    # 注入源书级产物（从 _cache/ 读取，使用缓存的映射版本）
    if chapter_num:
        from file_io import get_chapter_event, get_skeleton_context, get_adaptation_principles

        # 判断是否是续写模式
        is_continue = _is_continue_mode(config)
        
        if is_continue:
            # 续写模式：从plan.md提取事件
            ch_event = _get_continue_plan_event(config, chapter_num)
            if ch_event:
                ch_event = f"第{chapter_num}章：{ch_event}"
            else:
                ch_event = "（续写方案中未找到本章事件）"
            
            # 续写模式：从concept.md提取骨架和改编原则
            concept_path = Path(config.get("rewrites_dir", "")) / "concept.md"
            if concept_path.exists():
                concept_text = concept_path.read_text(encoding="utf-8")
                # 提取全局结构
                skel_match = re.search(r'<structure>(.*?)</structure>', concept_text, re.DOTALL)
                if skel_match:
                    skel_ctx = skel_match.group(1).strip()[:1000]
                else:
                    skel_ctx = "（续写模式：请参考concept.md中的剧情结构）"
                # 提取改写原则
                adapt_match = re.search(r'<principles>(.*?)</principles>', concept_text, re.DOTALL)
                if adapt_match:
                    adapt_pr = adapt_match.group(1).strip()[:1000]
                else:
                    adapt_pr = "（续写模式：延续原作核心要素）"
            else:
                skel_ctx = "（续写模式：请参考续写方案中的情节线）"
                adapt_pr = "（续写模式：延续原作核心要素）"
        else:
            # 仿写模式：从源文events.json提取
            events_mapped = _load_events_mapped(config)
            
            ch_event = "（事件未提取）"
            for e in events_mapped:
                if e.get("id") == chapter_num or e.get("chapter_index") == chapter_num:
                    if e.get("event"):
                        ch_event = f"第{chapter_num}章：{e['event']}"
                    break
            
            # 使用缓存的骨架和改编策略
            skeleton_mapped = _load_skeleton_mapped(config)
            adaptation_mapped = _load_adaptation_mapped(config)
            
            skel_ctx = get_skeleton_context(config, chapter_num) or "（骨架未生成）"
            adapt_pr = get_adaptation_principles(config) or "（改编策略未生成）"

            # 对骨架和改编策略的上下文也做替换
            name_map = _build_name_map(config)
            if name_map:
                for old_name, new_name in name_map.items():
                    skel_ctx = skel_ctx.replace(old_name, new_name)
                    adapt_pr = adapt_pr.replace(old_name, new_name)

        replacements.setdefault("event", ch_event)
        replacements.setdefault("structure", skel_ctx)
        replacements.setdefault("principles", adapt_pr)

    # 注入角色行为卡片（写章时需要）
    if prompt_type == "write-chapter" and "角色行为卡片" not in replacements:
        char_card = _load_char_card(config)
        replacements["角色行为卡片"] = char_card

    # 合并额外替换变量
    if extra_replacements:
        replacements.update(extra_replacements)

    # 优先从 tasks/ 目录加载 task prompt，fallback 到 prompts/
    task_path = Path(__file__).parent.parent / "tasks" / f"{prompt_type}.md"
    if task_path.exists():
        prompt_path = str(task_path)
    else:
        prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    # 新架构：task prompt 不含 {变量}，用 XML 标签拼接 context
    if prompt_type == "write-chapter" and chapter_num:
        ctx_parts = []
        if replacements.get("style"):
            ctx_parts.append(f"<style>\n{replacements['style']}\n</style>")
        if replacements.get("characters"):
            ctx_parts.append(f"<characters>\n{replacements['characters']}\n</characters>")
        if replacements.get("name_map"):
            ctx_parts.append(f"<name_map>\n{replacements['name_map']}\n</name_map>")
        if replacements.get("structure"):
            ctx_parts.append(f"<structure>\n{replacements['structure']}\n</structure>")
        if replacements.get("principles"):
            ctx_parts.append(f"<principles>\n{replacements['principles']}\n</principles>")
        ctx_parts.append(f"<word_count>目标字数：{replacements.get('目标字数', '?')}字（{replacements.get('目标字数_min', '?')}~{replacements.get('目标字数_max', '?')}）</word_count>")
        if ctx_parts:
            user_prompt = user_prompt + "\n\n" + "\n\n".join(ctx_parts)

    elif prompt_type == "plot-guide" and chapter_num:
        ctx_parts = []
        if replacements.get("event"):
            ctx_parts.append(f"<event>\n{replacements['event']}\n</event>")
        if replacements.get("characters"):
            ctx_parts.append(f"<characters>\n{replacements['characters']}\n</characters>")
        if replacements.get("highlights"):
            ctx_parts.append(f"<highlights>\n{replacements['highlights']}\n</highlights>")
        if replacements.get("structure"):
            ctx_parts.append(f"<blacklist>\n{replacements['structure']}\n</blacklist>")
        if replacements.get("world"):
            ctx_parts.append(f"<world>\n{replacements['world']}\n</world>")
        if ctx_parts:
            user_prompt = user_prompt + "\n\n" + "\n\n".join(ctx_parts)

    if not system_prompt:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-generic.md"
        system_prompt = load_system_prompt(sp_name) or ""

    # XML 标签注入（fangcun-drama 同款，write-chapter 用 markdown+△ 格式不注入）
    xml_tags = {
        "plot-guide": "<plotGuide>章纲内容</plotGuide>",
        "style-guide": "<styleGuide>风格指南内容</styleGuide>",
    }
    if prompt_type in xml_tags:
        system_prompt += f"\n\n你必须使用如下XML格式输出全部内容：\n{xml_tags[prompt_type]}"

    # 重试修正提示：注入 system_prompt 前端
    if retry_context:
        system_prompt = f"【修正提示】上一次写这章存在以下问题：{retry_context}。这次务必修正。\n\n{system_prompt}"

    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)

    # 不限制 max_tokens
    max_tokens = None

    # === 保存 prompt 到 _debug/（每次调用都保存，不占token） ===
    if chapter_num:
        debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc)

    # prompts_only: 只输出 prompt，不调 API
    if config.get("prompts_only"):
        return f"<!-- PROMPTS_ONLY: {prompt_type} ch{chapter_num} — prompt 已保存至 _debug/ -->"

    label = f"ch{chapter_num or '?'} {prompt_type}"

    t_req = time.time()
    try:
        result = call_llm(config, prompt_type, user_prompt, system_prompt, ch=chapter_num, max_tokens=max_tokens)
        elapsed = time.time() - t_req
        print(f"  [OK] {label} ({elapsed:.0f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f"  [FAIL] {label} ({elapsed:.0f}s): {e}")
        raise


def process_plot_guide_output(config, chapter_num, ai_output):
    """处理 plot-guide 的输出，填充剩余模板变量。
    
    AI 已在 prompt 中直接输出完整 markdown（模板内嵌），
    这里只做 {N}、{女主名} 等变量的补替换。
    """
    from pathlib import Path
    from prompt_loader import make_book_data_replacements

    result = ai_output

    src_chars = count_source_chars(config, chapter_num)
    replacements = {
        "N": str(chapter_num),
        "N03d": f"{chapter_num:03d}",
        "源文字数": str(src_chars),
        "目标字数": str(src_chars),
        "目标字数_min": str(int(src_chars * 0.9)),
        "目标字数_max": str(int(src_chars * 1.1)),
        "作者名": config.get("author", ""),
        "新书名": Path(config.get("rewrites_dir", "")).name,
        "源书名": config.get("source_book", ""),
    }
    book_data = _get_book_data(config.get("rewrites_dir", ""))
    if book_data:
        bd_replacements = make_book_data_replacements(book_data)
        replacements.update(bd_replacements)
    else:
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for role, key in [("男主", "男主名"), ("女主", "女主名")]:
                m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                if m and key not in replacements:
                    replacements[key] = m.group(1)

    result = safe_format(result, replacements)

    return result


def _strip_source_text(plot_guide_text):
    """从 plot_guide 中去掉源文全文部分，防止 write-chapter 照抄。
    
    源文全文通常在"排除项"之后，以大段正文形式出现。
    只保留节拍映射、分析结果、排除项等结构化内容。
    """
    # 方式1：去掉"排除项"之后的所有内容（源文全文通常在最后）
    markers = ["## 排除项", "## 地点约束"]
    cut_pos = len(plot_guide_text)
    for marker in markers:
        pos = plot_guide_text.find(marker)
        if pos != -1:
            # 找到标记后，保留标记本身，去掉后面的大段文字
            end_of_line = plot_guide_text.find("\n", pos + len(marker))
            if end_of_line != -1:
                # 检查标记后是否有大量文字（源文全文）
                after = plot_guide_text[end_of_line:]
                if len(after) > 500:  # 超过500字认为是源文全文
                    cut_pos = min(cut_pos, end_of_line)

    if cut_pos < len(plot_guide_text):
        return plot_guide_text[:cut_pos].rstrip()

    # 方式2：如果上面没找到，检查是否有"源文全文"标记
    # 只在明确标记后截断，不截断长文本
    source_markers = ["## 源文全文", "## Source Text", "---\n\n第"]
    for marker in source_markers:
        pos = plot_guide_text.find(marker)
        if pos != -1:
            return plot_guide_text[:pos].rstrip()

    return plot_guide_text


def run_one_with_template(config, prompt_type, chapter_num=None, **kwargs):
    """包装 run_one，自动处理模板合并和 XML 提取。"""
    result = run_one(config, prompt_type, chapter_num, **kwargs)

    # prompts_only 跳过处理
    if config.get("prompts_only"):
        return result

    # XML 标签提取（fangcun-drama 同款）
    xml_tag_map = {
        "plot-guide": "plotGuide",
        "write-chapter": "chapter",
        "style-guide": "styleGuide",
    }
    if prompt_type in xml_tag_map:
        tag = xml_tag_map[prompt_type]
        m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", result)
        if m:
            result = m.group(1).strip()
        else:
            m_open = re.search(rf"<{tag}[^>]*>", result)
            if m_open:
                result = result[m_open.end():].strip()

    # plot-guide 模板合并
    if prompt_type == "plot-guide":
        result = process_plot_guide_output(config, chapter_num, result)
        # 去掉源文全文（防止 write-chapter 照抄）
        result = _strip_source_text(result)
        # 替换源文角色名（LLM 产出中可能残留源文角色名）
        name_map = _build_name_map(config)
        if name_map:
            for old_name, new_name in sorted(name_map.items(), key=lambda x: -len(x[0])):
                result = result.replace(old_name, new_name)

    return result





def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    from utils import get_source_text
    from lib.text_metrics import count_metrics
    text = get_source_text(config, ch)
    if text:
        return count_metrics(text)
    return None


def _load_char_card(config):
    """从 characters.md 读取角色行为卡片（主角+配角），注入写章 prompt。"""
    rewrites_dir = Path(config["rewrites_dir"])
    # 优先 settings/ 目录，fallback 到 rewrites_dir 根目录
    chars_path = rewrites_dir / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = rewrites_dir / "characters.md"
    if not chars_path.exists():
        return "（角色设定文件不存在）"
    text = chars_path.read_text(encoding="utf-8")
    
    # 按角色分块：找到所有 ## 开头的角色名行
    import re
    blocks = re.split(r'^(## .+)$', text, flags=re.MULTILINE)
    
    sections = []
    for i, block in enumerate(blocks):
        if block.startswith("## "):
            role_name = block.strip().lstrip("#").strip()
            # 获取该角色的完整内容（直到下一个 ## 或文件结尾）
            content = ""
            for j in range(i+1, min(i+10, len(blocks))):
                if blocks[j].startswith("## "):
                    break
                content += blocks[j]
            
            # 提取行为模式字段
            card_lines = []
            for keyword in ["应激模式", "决策方式", "情感表达", "致命弱点", "核心动机", "能力边界"]:
                idx = content.find(keyword)
                if idx >= 0:
                    line = content[idx:idx+200].strip().split("\n")[0]
                    card_lines.append(line)
            
            if card_lines:
                sections.append(f"【{role_name}】\n" + "\n".join(card_lines))
    
    return "\n\n".join(sections[:12]) if sections else "（角色设定中无行为卡片）"

