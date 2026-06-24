"""世界观和概念模块。

管理世界观文本、世界观约束、风格类型等。
"""

import re
from pathlib import Path

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


# 模块级缓存：blacklist 文本
_blacklist_cache = None


def _get_blacklist_text(config, chapter_num=None):
    """获取黑名单文本（模块级缓存）。只加载本章相关的黑名单项。"""
    global _blacklist_cache
    if _blacklist_cache is not None:
        return _blacklist_cache

    base_dir = Path(config.get("base_dir", "."))
    rewrites_dir = base_dir / config.get("rewrites_dir", "")
    source_dir = rewrites_dir.parent
    
    # 尝试从 _cache/styles/blacklist.md 加载
    blacklist_path = source_dir / "_cache" / "styles" / "blacklist.md"
    if blacklist_path.exists():
        content = blacklist_path.read_text(encoding="utf-8")[:1000]  # 限制长度
        _blacklist_cache = content
    else:
        _blacklist_cache = "（黑名单文件不存在）"
    return _blacklist_cache
