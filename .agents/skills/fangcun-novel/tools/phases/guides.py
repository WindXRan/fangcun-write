"""Phase 2: plot-guide 生成"""

import os
import re
import time
from pathlib import Path

import _path_setup  # noqa: F401
from utils import (
    get_total_chapters, count_source_chars, batch_run, debug_dump_prompt,
    get_source_text
)
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from prompt_loader import load_prompt

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


# 模块级缓存：角色名映射 + 首次出场映射
_name_map_cache = None
_char_first_ch_cache = None


def _parse_event_chars(event_text, name_map):
    """从事件字符串提取角色名，映射为新名。
    
    事件格式：| 第X章 标题 | 角色1、角色2 | 事件 | ...
    返回 set([新名, ...])
    """
    parts = event_text.split("|")
    if len(parts) < 3:
        return set()
    raw = parts[2].strip()
    if not raw:
        return set()
    chars = set()
    for c in re.split(r"[、，,]", raw):
        c = c.strip()
        if c:
            chars.add(name_map.get(c, c))
    return chars


def _apply_name_map(text, name_map):
    """用 name_map 替换 text 中的源文角色名，长名优先避免重叠错误。"""
    if not name_map:
        return text
    for old_name, new_name in sorted(name_map.items(), key=lambda x: -len(x[0])):
        text = text.replace(old_name, new_name)
    return text


def _parse_name_mapping_line(line):
    """从 characters.md 单行解析角色名映射。
    
    格式：**【新名】**（源文对应：旧名1/旧名2）
    返回 (新名, [旧名列表]) 或 None
    """
    if '源文对应' not in line:
        return None
    m = re.search(r'【(.+?)】', line)
    if not m:
        return None
    new_name = m.group(1).strip()
    m2 = re.search(r'源文对应[：:]\s*(.+)', line)
    if not m2:
        return None
    old_names_raw = m2.group(1).rstrip('）)').strip()
    old_names = re.split(r'[/、]', old_names_raw)
    return new_name, [n.strip() for n in old_names if n.strip()]


def _build_name_map(config):
    """从 characters.md 构建源文名→新名映射（模块级缓存）。支持合并条目如 高慧云/林秋敏。"""
    global _name_map_cache
    if _name_map_cache is not None:
        return _name_map_cache

    _name_map_cache = {}
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.is_absolute():
        rewrites_dir = Path(config.get("base_dir", ".")) / rewrites_dir
    chars_path = rewrites_dir / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = rewrites_dir / "characters.md"
    if not chars_path.exists():
        return _name_map_cache

    chars_text = chars_path.read_text(encoding="utf-8")
    for line in chars_text.split('\n'):
        parsed = _parse_name_mapping_line(line)
        if not parsed:
            continue
        new_name, old_names = parsed
        for old_name in old_names:
            if old_name != new_name:
                _name_map_cache[old_name] = new_name

    return _name_map_cache


def _get_chapter_characters(config, ch_num):
    """从 events.json 提取本章出场角色，映射为新名。"""
    from source_io import load_events
    events = load_events(config)
    name_map = _build_name_map(config)

    chars = set()
    for e in events:
        if e.get("id") == ch_num or e.get("chapter_index") == ch_num:
            chars |= _parse_event_chars(e.get("event", ""), name_map)

    if not chars:
        # fallback: 返回全部映射角色名
        name_map = _build_name_map(config)
        return "、".join(sorted(set(name_map.values()))) if name_map else ""

    return "、".join(sorted(chars))


def _load_character_cards(config, ch_num):
    """加载本章出场角色的卡内容（从 characters/ 目录读取独立文件）。"""
    global _char_first_ch_cache
    if _char_first_ch_cache is None:
        from source_io import load_events
        events = load_events(config)
        name_map = _build_name_map(config)
        _char_first_ch_cache = {}
        for e in events:
            ch = e.get("id") or e.get("chapter_index")
            for new_name in _parse_event_chars(e.get("event", ""), name_map):
                if new_name not in _char_first_ch_cache:
                    _char_first_ch_cache[new_name] = ch

    char_first_ch = _char_first_ch_cache

    chars_str = _get_chapter_characters(config, ch_num)
    if not chars_str:
        return "（无角色信息）"
    chars = set(chars_str.split("、"))

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
                m = re.search(rf'【{re.escape(name)}】[\s\S]*?(?=【[^】]|$)', chars_text)
                if m:
                    cards.append(m.group(0).strip())

    return "\n\n".join(cards) if cards else "（无角色信息）"


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def phase_guides(config, start, end, workers=5, state_mgr=None):
    """生成 plot_guide（含文笔指纹提取）。"""
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


def _base_replacements(config, chapter_num):
    """构建基本信息替换变量。"""
    n = str(chapter_num) if chapter_num else "1"
    return {
        "新书名": config["book_name"],
        "N": n,
        "N_plus1": str(chapter_num + 1) if chapter_num else "2",
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(get_total_chapters(config)),
    }


def _add_word_count(config, chapter_num, prompt_type, replacements):
    """注入字数/句长指标。"""
    if not chapter_num:
        return
    if prompt_type in ("plot-guide", "write-chapter"):
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars if src_chars > 0 else 1500
        replacements.setdefault("源文字数", str(src_chars))
        replacements.setdefault("目标字数", str(target_chars))
        replacements.setdefault("目标字数_min", str(int(target_chars * 0.9)))
        replacements.setdefault("目标字数_max", str(int(target_chars * 1.1)))
        src_text = get_source_text(config, chapter_num)
        if src_text and "源文句长" not in replacements:
            from lib.text_metrics import count_metrics
            replacements["源文句长"] = str(int(count_metrics(src_text).get("avg_sent_len", 25)))
    elif prompt_type in ("trim-chapter", "expand-chapter"):
        replacements.setdefault("目标字数", "2500")
        replacements.setdefault("目标字数_min", "2000")
        replacements.setdefault("目标字数_max", "3000")


def _load_world(config):
    """读取世界观设定。"""
    world_path = Path(config["rewrites_dir"]) / "world.md"
    if world_path.exists():
        return world_path.read_text(encoding="utf-8")[:2000]
    return "（世界观文件不存在，请参考源文设定）"


def _add_plot_guide_replacements(config, chapter_num, replacements):
    """plot-guide 特有：源文全文 + 角色卡 + 世界观。"""
    if not chapter_num:
        return
    source_text = get_source_text(config, chapter_num)
    if source_text:
        name_map = _build_name_map(config)
        replacements["源文全文"] = _apply_name_map(source_text, name_map)
    else:
        replacements["源文全文"] = "（源文读取失败）"
    replacements.setdefault("角色约束", _load_character_cards(config, chapter_num))
    replacements.setdefault("世界观", _load_world(config))


def _add_write_chapter_replacements(config, chapter_num, replacements):
    """write-chapter 特有：风格指标 + 文笔指纹 + 世界观 + 角色卡。"""
    if not chapter_num:
        return
    replacements.setdefault("角色约束", _load_character_cards(config, chapter_num))
    replacements.setdefault("世界观", _load_world(config))

    src_text = get_source_text(config, chapter_num)
    if not src_text:
        # 源文读取失败，填充默认值
        defaults = {"源文段长": "40", "源文单句段比例": "50", "源文对话比": "10",
                     "源文代词密度": "15", "源文标点": "标点克制", "源文高光": "",
                     "文笔指纹": "（源文读取失败）"}
        for k, v in defaults.items():
            replacements.setdefault(k, v)
        replacements.setdefault("信息释放时机", "（源文读取失败）")
        replacements.setdefault("场景运作机制", "（源文读取失败）")
        return

    from lib.text_metrics import count_style_fingerprint
    fp = count_style_fingerprint(src_text)
    replacements.setdefault("源文段长", str(int(fp.get("paragraph_avg_len", 40))))
    replacements.setdefault("源文单句段比例", str(int(fp.get("single_sent_ratio", 0.5) * 100)))
    replacements.setdefault("源文对话比", str(int(fp.get("dialogue_ratio", 0.1) * 100)))
    replacements.setdefault("源文代词密度", str(fp.get("pronoun_density", 15)))
    replacements.setdefault("源文标点", fp.get("punct_style", "标点克制"))

    from source_io import load_style_text
    style_text = load_style_text(config, chapter_num)
    if not style_text:
        replacements.setdefault("文笔指纹", "（文笔指纹未提取）")
        return

    style_text = _apply_name_map(style_text, _build_name_map(config))
    filtered = [l for l in style_text.split("\n") if not re.match(r'^\s*(例句|例|示例)[：:]', l.strip())]
    style_text = "\n".join(filtered)
    replacements["文笔指纹"] = style_text

    info_m = re.search(r'## 信息释放时机.*?(?=\n## |\Z)', style_text, re.DOTALL)
    replacements.setdefault("信息释放时机", info_m.group(0).strip() if info_m else "（信息释放时机未提取）")

    scene_m = re.search(r'## 场景运作机制.*?(?=\n## 信息释放时机|\Z)', style_text, re.DOTALL)
    replacements.setdefault("场景运作机制", scene_m.group(0).strip() if scene_m else "（场景运作机制未提取）")


def _add_common_replacements(config, chapter_num, replacements):
    """通用替换：风格类型（所有 prompt 都需要）。"""
    concept_path = Path(config["rewrites_dir"]) / "concept.md"
    if not concept_path.exists():
        replacements.setdefault("风格类型", "（concept.md 不存在）")
        return
    text = concept_path.read_text(encoding="utf-8")
    m = re.search(r'##\s*\d*\.?\s*风格类型\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if m:
        replacements.setdefault("风格类型", m.group(1).strip())
        return
    pos = re.search(r'定位[：:]\s*(.+)', text)
    if pos:
        replacements.setdefault("风格类型", f"题材类型：{pos.group(1).strip()}")
    else:
        replacements.setdefault("风格类型", "（风格类型未提取，请参考源文基调）")


def _add_source_products(config, chapter_num, replacements):
    """注入源书级产物：事件 / 骨架 / 改编策略。"""
    if not chapter_num:
        return
    from source_io import get_chapter_event, get_skeleton_context, get_adaptation_principles
    name_map = _build_name_map(config)
    replacements.setdefault("本章事件", _apply_name_map(get_chapter_event(config, chapter_num) or "（事件未提取）", name_map))
    replacements.setdefault("全局结构", _apply_name_map(get_skeleton_context(config, chapter_num) or "（骨架未生成）", name_map))
    replacements.setdefault("改写原则", _apply_name_map(get_adaptation_principles(config) or "（改编策略未生成）", name_map))


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, 
            system_prompt=None, extra_replacements=None, retry_context=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。
    
    Args:
        retry_context: 重试时附带的修正提示（如"代词密度偏离源文"），注入 system_prompt
    """
    from lib.api_client import call_llm, get_api_url

    prompts_dir = config.get("prompts_dir", str(Path(__file__).parent.parent.parent / "prompts"))
    base_dir = config.get("base_dir", os.getcwd())

    replacements = _base_replacements(config, chapter_num)
    _add_word_count(config, chapter_num, prompt_type, replacements)

    if prompt_type == "plot-guide":
        _add_plot_guide_replacements(config, chapter_num, replacements)
    elif prompt_type == "write-chapter":
        _add_write_chapter_replacements(config, chapter_num, replacements)

    _add_common_replacements(config, chapter_num, replacements)
    _add_source_products(config, chapter_num, replacements)

    if prompt_type == "write-chapter" and "角色行为卡片" not in replacements:
        replacements["角色行为卡片"] = _load_char_card(config)

    # 合并额外替换变量
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

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

    # === Debug: 保存最终发给 API 的完整 prompt ===
    if config.get("debug") and chapter_num and chapter_num <= 3:
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
        "新书名": config.get("book_name", ""),
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
        # 替换源文角色名（LLM 产出中可能残留源文角色名）
        name_map = _build_name_map(config)
        result = _apply_name_map(result, name_map)

    return result





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

