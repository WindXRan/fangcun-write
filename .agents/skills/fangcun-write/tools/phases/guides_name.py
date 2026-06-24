"""名称映射和角色解析模块。

从 characters.md 构建角色名映射、提取性别信息、构建角色名列表。
"""

import re
from pathlib import Path

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

        # 格式0: XML格式 <item old="源文名" new="新名" />
        for m in re.finditer(r'<item\s+old="([^"]+)"\s+new="([^"]+)"', chars_text):
            old_name = m.group(1).strip()
            new_name = m.group(2).strip()
            if old_name and new_name and old_name != new_name and old_name not in _name_map_cache:
                _name_map_cache[old_name] = new_name

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

    # 格式0: XML格式 <item old="源文名" new="新名" />
    for m in re.finditer(r'<item\s+old="([^"]+)"\s+new="([^"]+)"', chars_text):
        old_name = m.group(1).strip()
        new_name = m.group(2).strip()
        if old_name and new_name and old_name != new_name and old_name not in seen:
            items.append(f"{old_name}→{new_name}")
            seen.add(old_name)

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


def _extract_gender_info(chars_text):
    """从 characters.md 提取角色性别信息。返回格式："{角色名}（{性别}）、..."。"""
    genders = []
    
    # XML格式: <character name="新名" source="源文名"><role>...</role></character>
    for m in re.finditer(r'<character\s+name="([^"]+)"[^>]*>.*?</character>', chars_text, re.DOTALL):
        name = m.group(1).strip()
        body = m.group(0)
        gender = "未知"
        if re.search(r'女主|女性|女孩|姑娘|小姐|姐姐|妹妹|女儿', body):
            gender = "女"
        elif re.search(r'男主|男性|男孩|小子|先生|哥哥|弟弟|儿子', body):
            gender = "男"
        if gender != "未知":
            genders.append(f"{name}（{gender}）")
    
    # 旧格式: 【新名】（源文对应：源文名）
    if not genders:
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
    
    # XML格式: <character name="新名" source="源文名"><role>...</role></character>
    for m in re.finditer(r'<character\s+name="([^"]+)"\s+source="([^"]*)"[^>]*>.*?</character>', chars_text, re.DOTALL):
        new_name = m.group(1).strip()
        old_name = m.group(2).strip()
        body = m.group(0)
        gender = ""
        if re.search(r'女性|女孩|女儿|女主|小姐|姐姐|妹妹', body):
            gender = "女"
        elif re.search(r'男性|男孩|儿子|男主|先生|哥哥|弟弟', body):
            gender = "男"
        if new_name == old_name:
            entry = new_name
        elif gender:
            entry = f"{new_name}（{gender}，源文：{old_name}）"
        else:
            entry = f"{new_name}（源文：{old_name}）"
        items.append(entry)
    
    # 旧格式: 【新名】（源文对应：源文名）
    if not items:
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


def _get_chapter_characters(config, ch_num):
    """从 events.json 提取本章出场角色，映射为新名。"""
    from guides_cache import _load_events_mapped

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
    """加载本章出场角色的卡内容（直接读取，不做处理）。"""
    from guides_cache import _load_events_mapped

    # 使用缓存的映射版本
    events = _load_events_mapped(config)

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
    chars_path = rewrites_dir / "characters.md"
    
    if not chars_path.exists():
        return "（角色卡文件不存在）"
    
    chars_text = chars_path.read_text(encoding="utf-8")
    cards = []
    
    for name in sorted(chars):
        # 匹配新XML格式: <character name="角色名">...</character>
        m = re.search(rf'<character\s+name="{re.escape(name)}"[^>]*>[\s\S]*?</character>', chars_text)
        if m:
            cards.append(m.group(0))
        else:
            # 匹配旧XML格式: <角色名>...</角色名>
            m = re.search(rf'<{re.escape(name)}>([\s\S]*?)</{re.escape(name)}>', chars_text)
            if m:
                cards.append(f"<{name}>{m.group(1)}</{name}>")
            else:
                # fallback: 匹配旧格式 【角色名】（源文对应：XXX）
                m = re.search(rf'【{re.escape(name)}】[（(]源文对应[：:](.+?)[）)][\s\S]*?(?=【|$)', chars_text)
                if m:
                    cards.append(m.group(0).strip())
    
    return "\n\n".join(cards) if cards else "（无角色信息）"


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
