"""
开书完成后，从 settings/*.md 提取结构化设定数据，输出 book_data.json。

用法：
  python extract_book_data.py --rewrites-dir <路径>
  python extract_book_data.py --config <config.json>

输出：rewrites_dir/book_data.json
"""

import re
import json
import argparse
from pathlib import Path
from datetime import datetime


def read_file(path):
    """安全读取文件，不存在返回空字符串。"""
    p = Path(path)
    return p.read_text(encoding='utf-8') if p.exists() else ''


def extract_section(text, heading_pattern):
    """从 markdown 中提取指定标题下的内容。
    heading_pattern: 匹配标题的正则（如 '## 角色设定'）
    返回匹配后的内容（到下一个同级标题为止）。
    """
    pattern = rf'({heading_pattern})\s*\n(.*?)(?=\n##|\n# |\Z)'
    m = re.search(pattern, text, re.DOTALL)
    return m.group(2).strip() if m else ''


def parse_book_info(text):
    """解析 settings/book_info.md → book_info 对象。
    
    产出 packages[] = [{title, blurb, cover_prompt, cover_image}, ...]，
    每个 package 是一套完整上架配置（番茄要求书名+简介+封面组套）。
    """
    data = {
        "name": "",
        "author": "",
        "source_book": "",
        "genre": "",
        "tags": [],
        "packages": [],
    }

    name_match = re.search(r'^#\s+(.+)', text)
    if name_match:
        data["name"] = name_match.group(1).strip()

    kv_pattern = re.compile(r'[-*]\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)')
    for m in kv_pattern.finditer(text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if '作者' in key:
            data["author"] = val
        elif '源书' in key or '源文' in key:
            data["source_book"] = val
        elif '题材' in key or '类型' in key:
            data["genre"] = val
        elif '标签' in key:
            data["tags"] = [t.strip() for t in val.replace('、', ',').split(',') if t.strip()]

    # 简介：### 版本X 下面的内容
    blurb_sections = re.findall(r'###\s*(版本\S*)\s*\n(.*?)(?=\n###|\n##|\Z)', text, re.DOTALL)
    blurbs = []
    for label, content in blurb_sections:
        blurbs.append(content.strip())

    # 书名候选：列表项
    titles = re.findall(r'^\s*[-*]\s*《(.+?)》', text, re.MULTILINE)

    # 按位置配组：第N个书名 ↔ 第N个简介
    # 番茄要求书名和简介是一套，所以按序配对
    count = max(len(titles), len(blurbs))
    for i in range(count):
        pkg = {
            "title": titles[i] if i < len(titles) else "",
            "blurb": blurbs[i] if i < len(blurbs) else "",
            "cover_prompt": "",
            "cover_image": None,
        }
        # 只保留非空 package
        if pkg["title"] or pkg["blurb"]:
            data["packages"].append(pkg)

    # fallback: 如果书名和简介都为空但书名候选存在
    if not data["packages"] and titles:
        for t in titles:
            data["packages"].append({
                "title": t, "blurb": "", "cover_prompt": "", "cover_image": None
            })

    return data


TAG_NORMALIZE = {
    "男主角": "男主", "女主角": "女主", "男二号": "男二", "女二号": "女二",
    "男配": "男配", "女配": "女配", "反派": "反派",
}


def parse_characters(text):
    """解析 settings/characters.md → characters 数组。
    
    支持三种格式：
      A: `### 郝仁 (男主)`  —— 名字在前，tag括号内（markdown标题）
      B: `## 男主：郝仁`   —— tag在前，冒号分隔
      C: `宋云(女主)`       —— 名字在前，tag括号内（纯文本，无markdown标题）
    """
    characters = []
    TAG_KEYWORDS = r'女[主二配]|男[主二配]|反派|[^\n]{0,4}(?:父亲|母亲|爷爷|奶奶|祖父|祖母|外公|外婆|闺蜜|好友|助理|管家|继母|继父|弟弟|妹妹|哥哥|姐姐)'
    
    # 格式 A: ### 郝仁 (男主) —— 名字在前，(tag) 在括号内
    pattern_a = re.compile(
        r'^#{2,4}\s+([\u4e00-\u9fa5]{2,8})[^\n]*?[(（]\s*(' + TAG_KEYWORDS + r')[^\n)]*?[)）]\s*\n(.*?)(?=\n^#{2,4}\s+|\Z)',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern_a.finditer(text):
        name, role_tag, body = m.group(1), m.group(2), m.group(3)
        _add_character(characters, role_tag.strip(), name.strip(), body)

    # 格式 B: ## 男主：郝仁 —— tag在前，冒号分隔
    pattern_b = re.compile(
        r'^#{2,4}\s+(' + TAG_KEYWORDS + r')[^\n]*?[：:]\s*([\u4e00-\u9fa5]{2,8})(?:[^\n]*?)\s*\n(.*?)(?=\n^#{2,4}\s+|\Z)',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern_b.finditer(text):
        role_tag, name, body = m.group(1), m.group(2), m.group(3)
        # 格式A已处理则不重复
        if not any(c["name"] == name.strip() for c in characters):
            _add_character(characters, role_tag.strip(), name.strip(), body)

    # 格式 C: 宋云(女主) —— 名字在前，(tag) 在括号内，纯文本无markdown标题
    pattern_c = re.compile(
        r'^([\u4e00-\u9fa5]{2,8})[^\n]*?[(（]\s*(' + TAG_KEYWORDS + r')[^\n)]*?[)）]\s*\n(.*?)(?=\n^[\u4e00-\u9fa5]{2,4}[^\n]*?[(（]|\Z)',
        re.MULTILINE | re.DOTALL
    )
    for m in pattern_c.finditer(text):
        name, role_tag, body = m.group(1), m.group(2), m.group(3)
        if not any(c["name"] == name.strip() for c in characters):
            _add_character(characters, role_tag.strip(), name.strip(), body)

    # 解析表格格式的配角
    _parse_side_characters(text, characters)

    return characters


def _add_character(characters, role_tag, name, body):
    """内部：解析角色body并添加到列表。"""
    if name.startswith('|') or name.startswith('-'):
        return
    tag_short = TAG_NORMALIZE.get(role_tag, role_tag)
    char = {
        "tag": role_tag,
        "tag_short": tag_short,
        "name": name,
        "aliases": [],
        "age": "",
        "identity": "",
        "personality": "",
        "arc": "",
        "weaknesses": [],
        "archetype": "",
        "first_appearance": 1,
        "frequency": ""
    }
    kv = re.compile(r'[-*]\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)')
    for m in kv.finditer(body):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if '身份' in key:
            char["identity"] = val
        elif '年龄' in key or '岁' in key:
            char["age"] = val
        elif '性格' in key or '核心' in key or '人设' in key:
            char["personality"] = val
        elif '弧线' in key or '成长' in key:
            char["arc"] = val
        elif '弱点' in key or '软肋' in key or '在乎' in key:
            char["weaknesses"] = [w.strip() for w in val.replace('、', ',').split(',') if w.strip()]
        elif '原型' in key or '模式' in key or '类型' in key:
            char["archetype"] = val
        elif '出场' in key or '首次' in key:
            nums = re.findall(r'\d+', val)
            if nums:
                char["first_appearance"] = int(nums[0])
    arc_match = re.search(r'弧线[：:](.*?)(?=\n[-*]|\Z)', body, re.DOTALL)
    if arc_match:
        char["arc"] = arc_match.group(1).strip()
    characters.append(char)


def _parse_side_characters(text, characters):
    """解析 ## 重要配角 下面的表格。"""
    side_char_section = re.search(r'##\s*重要配角\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if side_char_section:
        table_text = side_char_section.group(1)
        # 解析表格行（跳过表头和分隔行）
        for line in table_text.split('\n'):
            line = line.strip()
            if not line.startswith('|') or '---' in line or '角色' in line:
                continue
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if len(cells) >= 3:
                name_cell = cells[0]
                age_cell = cells[1]
                relation_cell = cells[2]
                personality_cell = cells[3] if len(cells) > 3 else ""
                
                # 提取名字：优先取括号内的名字，否则取第一个中文词
                name_match = re.search(r'[（(]([\u4e00-\u9fa5]{2,8})[）)]', name_cell)
                if name_match:
                    name = name_match.group(1)
                else:
                    name_match = re.match(r'([\u4e00-\u9fa5]{2,8})', name_cell)
                    if name_match:
                        name = name_match.group(1)
                    else:
                        name = name_cell
                
                # 根据关系确定 tag
                tag = relation_cell if relation_cell else name_cell
                char = {
                    "tag": tag,
                    "tag_short": TAG_NORMALIZE.get(tag, tag),
                    "name": name,
                    "aliases": [],
                    "age": age_cell,
                    "identity": relation_cell,
                    "personality": personality_cell,
                    "arc": "",
                    "weaknesses": [],
                    "archetype": "",
                    "first_appearance": 1,
                    "frequency": ""
                }
                characters.append(char)

    return characters


def parse_plot(text):
    """解析 settings/plot.md → plot 对象。"""
    data = {
        "main_arc": "",
        "conflict_escalation": "",
        "emotion_cores": {
            "source": {"fear": "", "essence": ""},
            "new": {"fear": "", "essence": ""}
        },
        "numerical": {
            "timeline": "",
            "countdown": None
        },
        "suspense": []
    }

    # 主线弧线：## 标题下方的内容（直到下一个 ##）
    heading_sections = re.findall(r'##\s+(.+?)\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    for heading, body in heading_sections:
        h = heading.strip()
        if '主线' in h or '弧线' in h:
            data["main_arc"] = body.strip()
        elif '时间' in h or '数值' in h:
            tl = re.search(r'(?:时间线|时间)[：:]\s*(.*?)(?:\n)', body)
            if tl:
                data["numerical"]["timeline"] = tl.group(1).strip()
        elif '悬念' in h:
            suspense_rows = re.findall(r'\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|', body)
            for sid, desc, rec in suspense_rows:
                rec_num = re.findall(r'\d+', rec)
                data["suspense"].append({
                    "id": int(sid),
                    "description": desc.strip(),
                    "recovery_chapter": int(rec_num[0]) if rec_num else None
                })

    # fallback: 单行弧线格式
    if not data["main_arc"]:
        main_match = re.search(r'(?:主线|弧线)[：:]\s*(.*?)(?:\n|$)', text)
        if main_match:
            data["main_arc"] = main_match.group(1).strip()

    # 情感内核：### 源文 / ### 新书
    emotion_sections = re.findall(r'###\s*(源文|新书)\s*\n(.*?)(?=\n###|\n##|\Z)', text, re.DOTALL)
    for label, body in emotion_sections:
        key = "source" if label == "源文" else "new"
        ess = re.search(r'\*{0,2}(?:精髓|本质|内核)\*{0,2}\s*[：:]\s*(.*?)(?:\n)', body)
        if ess:
            data["emotion_cores"][key]["essence"] = ess.group(1).strip()
        fear = re.search(r'\*{0,2}(?:恐惧|害怕)\*{0,2}\s*[：:]\s*(.*?)(?:\n)', body)
        if fear:
            data["emotion_cores"][key]["fear"] = fear.group(1).strip()

    # 时间线（非 heading 格式，兼容 **时间线**）
    if not data["numerical"]["timeline"]:
        tl_match = re.search(r'\*{0,2}时间线\*{0,2}\s*[：:]\s*(.*?)(?:\n)', text)
        if tl_match:
            data["numerical"]["timeline"] = tl_match.group(1).strip()

    return data


def parse_conflicts(text):
    """从 plot.md 提取冲突信息。"""
    data = {
        "source": {"types": [], "description": ""},
        "new": {"types": [], "description": ""},
        "peel_points": []
    }

    # 冲突类型（在 ### 源文冲突 / ### 新书冲突 内）
    sections = re.findall(r'###\s*(.+?)[冲]{0,1}[突]{0,1}\s*\n(.*?)(?=\n###|\n##|\Z)', text, re.DOTALL)
    for heading, body in sections:
        h = heading.strip()
        types = []
        for match in re.finditer(r'(?:冲突类型|类型)[：:]\s*(.+)', body):
            types.extend(t.strip() for t in match.group(1).replace('、', ',').split(',') if t.strip())
        if '源文' in h:
            data["source"]["types"] = types
            data["source"]["description"] = body.strip()[:200]
        elif '新书' in h:
            data["new"]["types"] = types
            data["new"]["description"] = body.strip()[:200]

    # 换皮点：从 ### 换皮* 章节或列表项
    for sec_heading, sec_body in re.findall(r'###\s*(.+?)\s*\n(.*?)(?=\n###|\n##|\Z)', text, re.DOTALL):
        # 冲突类型
        if any(kw in sec_heading for kw in ['冲突', '矛盾']):
            types = []
            for m in re.finditer(r'[-*]\s*\*{0,2}(?:冲突类型|类型)\*{0,2}\s*[：:]\s*(.+)', sec_body):
                types.extend(t.strip() for t in m.group(1).replace('、', ',').split(',') if t.strip())
            if '源文' in sec_heading or '原有' in sec_heading:
                data["source"]["types"] = types
            elif '新书' in sec_heading or '仿写' in sec_heading:
                data["new"]["types"] = types
        # 换皮点
        elif any(kw in sec_heading for kw in ['换皮', '映射', '对照', 'peel']):
            for line in sec_body.split('\n'):
                line = line.strip().lstrip('-* ')
                if line and ('→' in line or '→' in line):
                    data["peel_points"].append(line)

    return data


def parse_world(text):
    """解析 settings/world.md → world 对象。"""
    data = {
        "era": "",
        "category": "",
        "settings": {},
        "places": []
    }

    kv_pattern = re.compile(r'[-*]\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)')
    for m in kv_pattern.finditer(text):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if '时代' in key or '朝代' in key:
            data["era"] = val
        elif '分类' in key or '类型' in key:
            data["category"] = val
        else:
            data["settings"][key] = val

    # 地点列表
    place_lines = re.findall(r'[-*]\s*(?:[^:：\n]{1,20}$)', text, re.MULTILINE)
    for line in place_lines:
        line = line.strip().lstrip('-* ')
        if line and len(line) < 30 and '：' not in line and ':' not in line:
            data["places"].append(line)

    return data


def parse_source_analysis(text):
    """解析 settings/source_analysis.md → 对象。"""
    data = {
        "success_factors": [],
        "pleasure_formula": "",
        "archetype": "",
        "rhythm": ""
    }

    # 按 ## 标题分割
    heading_sections = re.findall(r'##\s+(.+?)\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    for heading, body in heading_sections:
        h = heading.strip()
        if '爽点' in h or '公式' in h:
            data["pleasure_formula"] = body.strip()
        elif '原型' in h or '模式' in h:
            data["archetype"] = body.strip()
        elif '节奏' in h or '特征' in h:
            data["rhythm"] = body.strip()

    # 成功因子（## 之前或第一个 ## 段落中的编号列表）
    pre_section = re.match(r'(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if pre_section:
        factors = re.findall(r'\d+[.、]\s*(.*?)(?=\n\d+[.、]|\n##|\Z)', pre_section.group(1), re.DOTALL)
        if factors:
            data["success_factors"] = [f.strip().lstrip('-* "「') for f in factors]

    # fallback: 单行格式
    if not data["pleasure_formula"]:
        sf_match = re.search(r'(?:爽点|公式)[：:]\s*(.*?)(?=\n)', text)
        if sf_match:
            data["pleasure_formula"] = sf_match.group(1).strip()
    if not data["archetype"]:
        arch_match = re.search(r'(?:原型|模式)[：:]\s*(.*?)(?=\n)', text)
        if arch_match:
            data["archetype"] = arch_match.group(1).strip()
    if not data["rhythm"]:
        rhythm_match = re.search(r'(?:节奏|特征)[：:]\s*(.*?)(?=\n)', text)
        if rhythm_match:
            data["rhythm"] = rhythm_match.group(1).strip()

    return data


def build_character_variables(characters):
    """从 characters 数组生成扁平变量映射。
    
    产出 {男主名}, {女主名} 等，可直接用于 prompt 替换。
    优先用 tag_short（男主角→男主），fallback 到原始 tag。
    同名角色只取第一个（写在前的是核心角色）。
    """
    vars_map = {}
    seen_tags = set()
    for ch in characters:
        tag = ch.get("tag_short", ch.get("tag", ""))
        name = ch.get("name", "")
        if tag and tag not in seen_tags:
            vars_map[f"{tag}名"] = name
            seen_tags.add(tag)
    return vars_map


def extract(config_or_dir):
    """主入口：读取 settings/*.md 生成 book_data.json。"""
    if isinstance(config_or_dir, dict):
        rewrites_dir = config_or_dir.get("rewrites_dir", "")
    else:
        rewrites_dir = config_or_dir

    rewrites_dir = Path(rewrites_dir)
    settings_dir = rewrites_dir / "settings"

    # 读取各文件
    files_used = []
    texts = {}
    for fname in ["book_info.md", "characters.md", "plot.md", "world.md", "source_analysis.md"]:
        fpath = settings_dir / fname
        text = read_file(fpath)
        if text:
            texts[fname] = text
            files_used.append(f"settings/{fname}")

    if not texts.get("characters.md"):
        # fallback: 从 concept.md 提取
        concept_text = read_file(rewrites_dir / "concept.md")
        if concept_text:
            texts["characters.md"] = concept_text
            files_used.append("concept.md (fallback)")

    if not texts:
        print("[FAIL] 未找到 settings/*.md 或 concept.md")
        return None

    # 构建 JSON
    data = {
        "schema_version": 1,
        "book_info": {},
        "characters": [],
        "conflicts": {"source": {"types": [], "description": ""}, "new": {"types": [], "description": ""}, "peel_points": []},
        "world": {"era": "", "category": "", "settings": {}, "places": []},
        "plot": {"main_arc": "", "conflict_escalation": "", "emotion_cores": {}, "numerical": {}, "suspense": []},
        "source_analysis": {"success_factors": [], "pleasure_formula": "", "archetype": "", "rhythm": ""},
        "meta": {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "extracted_from": files_used,
            "character_variables": {}
        }
    }

    # 逐一解析
    for fname, text in texts.items():
        if fname == "book_info.md":
            data["book_info"] = parse_book_info(text) or data["book_info"]
        elif fname == "characters.md":
            data["characters"] = parse_characters(text) or data["characters"]
        elif fname == "plot.md":
            plot_data = parse_plot(text)
            conflicts = parse_conflicts(text)
            data["plot"] = plot_data
            data["conflicts"] = conflicts
        elif fname == "world.md":
            data["world"] = parse_world(text) or data["world"]
        elif fname == "source_analysis.md":
            data["source_analysis"] = parse_source_analysis(text) or data["source_analysis"]

    # 生成角色变量映射
    data["meta"]["character_variables"] = build_character_variables(data["characters"])

    # 写入
    out_path = rewrites_dir / "book_data.json"
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"[OK] book_data.json ({len(data['characters'])} 角色, "
          f"{len(data['meta']['character_variables'])} 变量) → {out_path}")
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="从 settings/*.md 提取 book_data.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rewrites-dir", help="仿写项目目录")
    group.add_argument("--config", help="pipeline 配置文件路径")
    args = parser.parse_args()

    if args.config:
        config = json.loads(Path(args.config).read_text(encoding='utf-8'))
        extract(config)
    else:
        extract(args.rewrites_dir)
