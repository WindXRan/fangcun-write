"""缓存管理和数据加载模块。

管理模块级缓存：system prompt、skeleton map、book data、events、skeleton、adaptation。
"""

import json
from pathlib import Path

from utils import get_source_text, count_source_chars
from prompt_meta import load_system_prompt, get_system_prompt_name

# 模块级缓存：system prompt（全局共享，省 token）
_system_prompt_cache = {}


def _get_system_prompt_cached(prompt_type):
    """获取 system prompt（模块级缓存）。"""
    global _system_prompt_cache
    if prompt_type not in _system_prompt_cache:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "agent.md"
        _system_prompt_cache[prompt_type] = load_system_prompt(sp_name) or ""
    return _system_prompt_cache[prompt_type]


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
            try:
                _book_data_cache = json.loads(bd_path.read_text(encoding="utf-8"))
            except Exception:
                _book_data_cache = {}
            return _book_data_cache
    _book_data_cache = {}
    return _book_data_cache


# 模块级缓存：events.json 映射后版本
_events_mapped_cache = None


def _load_events_mapped(config):
    """加载 events.json 并替换为新名（模块级缓存）。"""
    global _events_mapped_cache
    if _events_mapped_cache is not None:
        return _events_mapped_cache

    from file_io import load_events
    from guides_name import _build_name_map
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
    from guides_name import _build_name_map
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
    from guides_name import _build_name_map
    adaptation = load_adaptation(config)
    name_map = _build_name_map(config)

    if not name_map or not adaptation:
        _adaptation_mapped_cache = adaptation
        return adaptation

    for old, new in name_map.items():
        adaptation = adaptation.replace(old, new)

    _adaptation_mapped_cache = adaptation
    return adaptation
