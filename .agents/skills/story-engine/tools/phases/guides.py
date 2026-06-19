"""Phase 2: plot-guide 生成"""

import os
import re
import time
from pathlib import Path

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


# 模块级缓存：角色名映射
_name_map_cache = None


def _build_name_map(config):
    """从 characters.md 构建源文名→新名映射（模块级缓存）。支持合并条目如 高慧云/林秋敏。"""
    global _name_map_cache
    if _name_map_cache is not None:
        return _name_map_cache

    _name_map_cache = {}
    chars_path = Path(config.get("rewrites_dir", "")) / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = Path(config.get("rewrites_dir", "")) / "characters.md"
    if not chars_path.exists():
        return _name_map_cache

    chars_text = chars_path.read_text(encoding="utf-8")
    for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
        new_name = m.group(1).strip()
        old_names_raw = m.group(2).strip()
        # 拆分合并条目：高慧云/林秋敏 → [高慧云, 林秋敏]
        old_names = re.split(r'[/、]', old_names_raw)
        for old_name in old_names:
            old_name = old_name.strip()
            if old_name and old_name != new_name:
                _name_map_cache[old_name] = new_name

    return _name_map_cache


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


def _get_chapter_characters(config, ch_num):
    """从 events.json 提取本章出场角色，映射为新名。"""
    from file_io import load_events
    events = load_events(config)
    name_map = _build_name_map(config)

    # 找本章事件
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
                        # 替换为新名
                        chars.add(name_map.get(c, c))
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
    from file_io import load_events
    events = load_events(config)
    name_map = _build_name_map(config)

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
                        chars.add(name_map.get(c, c))
            break

    if not chars:
        return "（无角色信息）"

    # 读取角色卡文件
    cards_dir = Path(config.get("rewrites_dir", "")) / "characters"
    cards = []
    for name in sorted(chars):
        card_path = cards_dir / f"{name}.md"
        if card_path.exists():
            cards.append(card_path.read_text(encoding="utf-8"))
        else:
            # fallback: 从 characters.md 中提取该角色
            chars_path = Path(config.get("rewrites_dir", "")) / "settings" / "characters.md"
            if not chars_path.exists():
                chars_path = Path(config.get("rewrites_dir", "")) / "characters.md"
            if chars_path.exists():
                chars_text = chars_path.read_text(encoding="utf-8")
                m = re.search(rf'【{re.escape(name)}】[\s\S]*?(?=【[^】]|$)', chars_text)
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
        "新书名": config["book_name"],
        "N": n,
        "N_plus1": n_plus1,
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
    }

    # 需要源文字数时，脚本计算（API 无法跑 PowerShell）
    if prompt_type in ("plot-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars if src_chars > 0 else 1500  # 源文缺失则用默认值
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # plot-guide 注入源文全文（章纲需要完整分析结构和节拍）
    if prompt_type == "plot-guide" and chapter_num:
        source_text = get_source_text(config, chapter_num)
        if source_text:
            # 用全量角色映射替换源文角色名（不只本章出场角色）
            name_map = _build_name_map(config)
            if name_map:
                for old_name, new_name in name_map.items():
                    source_text = source_text.replace(old_name, new_name)
            replacements["源文全文"] = source_text
        else:
            replacements["源文全文"] = "（源文读取失败）"
        # 注入本章出场角色卡内容
        if "角色约束" not in replacements and chapter_num:
            replacements["角色约束"] = _load_character_cards(config, chapter_num)
        # 注入世界观（plot-guide 和 write-chapter 都需要）
        if "世界观" not in replacements:
            world_path = Path(config["rewrites_dir"]) / "world.md"
            if world_path.exists():
                replacements["世界观"] = world_path.read_text(encoding="utf-8")[:2000]
            else:
                replacements["世界观"] = "（世界观文件不存在，请参考源文设定）"

    # 写章时注入本章出场角色的卡内容
    if prompt_type == "write-chapter" and chapter_num:
        if "角色约束" not in replacements or replacements.get("角色约束") == "{角色行为卡片}":
            replacements["角色约束"] = _load_character_cards(config, chapter_num)
        # 注入世界观
        if "世界观" not in replacements:
            world_path = Path(config["rewrites_dir"]) / "world.md"
            if world_path.exists():
                replacements["世界观"] = world_path.read_text(encoding="utf-8")[:2000]
            else:
                replacements["世界观"] = "（世界观文件不存在，请参考源文设定）"
        # 源文风格指标（段长/对话比/代词密度，供仿写对齐用）
        src_text = get_source_text(config, chapter_num)
        if src_text:
            from lib.text_metrics import count_style_fingerprint
            fp = count_style_fingerprint(src_text)
            replacements["源文段长"] = str(int(fp.get("paragraph_avg_len", 40)))
            replacements["源文单句段比例"] = str(int(fp.get("single_sent_ratio", 0.5) * 100))
            replacements["源文对话比"] = str(int(fp.get("dialogue_ratio", 0.1) * 100))
            replacements["源文代词密度"] = str(fp.get("pronoun_density", 15))
            replacements["源文标点"] = fp.get("punct_style", "标点克制")
            
            # 注入文笔指纹（从 _cache/styles/ 读取，替换源文角色名）
            from file_io import load_style_text
            style_text = load_style_text(config, chapter_num)
            if style_text:
                # 替换源文角色名（防止 LLM 从文笔指纹中抄回源文名）
                name_map = _build_name_map(config)
                if name_map:
                    for old_name, new_name in name_map.items():
                        style_text = style_text.replace(old_name, new_name)
                replacements["文笔指纹"] = style_text
            else:
                replacements["文笔指纹"] = "（文笔指纹未提取）"
        else:
            replacements["源文段长"] = "40"; replacements["源文单句段比例"] = "50"
            replacements["源文对话比"] = "10"; replacements["源文代词密度"] = "15"
            replacements["源文标点"] = "标点克制"
            replacements["源文高光"] = ""
            replacements["文笔指纹"] = "（源文读取失败）"

    # 注入源书级产物（从 _cache/ 读取）
    if chapter_num:
        from file_io import get_chapter_event, get_skeleton_context, get_adaptation_principles
        # 注入源书级产物（替换源文角色名）
        name_map = _build_name_map(config)

        ch_event = get_chapter_event(config, chapter_num) or "（事件未提取）"
        skel_ctx = get_skeleton_context(config, chapter_num) or "（骨架未生成）"
        adapt_pr = get_adaptation_principles(config) or "（改编策略未生成）"

        # 替换源文角色名
        if name_map:
            for old_name, new_name in name_map.items():
                ch_event = ch_event.replace(old_name, new_name)
                skel_ctx = skel_ctx.replace(old_name, new_name)
                adapt_pr = adapt_pr.replace(old_name, new_name)

        replacements.setdefault("本章事件", ch_event)
        replacements.setdefault("全局结构", skel_ctx)
        replacements.setdefault("改写原则", adapt_pr)

    # 注入角色行为卡片（写章时需要）
    if prompt_type == "write-chapter" and "角色行为卡片" not in replacements:
        char_card = _load_char_card(config)
        replacements["角色行为卡片"] = char_card

    # 合并额外替换变量
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    if not system_prompt:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-generic.md"
        system_prompt = load_system_prompt(sp_name) or ""

    # XML 标签注入（drama-engine 同款，write-chapter 用 markdown+△ 格式不注入）
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

    # 计算 max_tokens（目标字数 × 1.6，防止超时）
    max_tokens = None
    if prompt_type in ("write-chapter", "trim-chapter", "expand-chapter", "polish-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars if src_chars > 100 else 1500
        max_tokens = int(target_chars * 1.6)

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


def _strip_source_text(plot_guide_text):
    """从 plot_guide 中去掉源文全文部分，防止 write-chapter 照抄。
    
    源文全文通常在"排除项"之后，以大段正文形式出现。
    只保留节拍映射、分析结果、排除项等结构化内容。
    """
    # 方式1：去掉"排除项"之后的所有内容（源文全文通常在最后）
    markers = ["## 排除项", "## 地点约束", "---\n\n第"]
    cut_pos = len(plot_guide_text)
    for marker in markers:
        pos = plot_guide_text.find(marker)
        if pos != -1:
            # 找到标记后，保留标记本身，去掉后面的大段文字
            if marker == "---\n\n第":
                cut_pos = min(cut_pos, pos)
            else:
                # 保留标记行，去掉标记后的内容
                end_of_line = plot_guide_text.find("\n", pos + len(marker))
                if end_of_line != -1:
                    # 检查标记后是否有大量文字（源文全文）
                    after = plot_guide_text[end_of_line:]
                    if len(after) > 500:  # 超过500字认为是源文全文
                        cut_pos = min(cut_pos, end_of_line)

    if cut_pos < len(plot_guide_text):
        return plot_guide_text[:cut_pos].rstrip()

    # 方式2：如果上面没找到，尝试去掉超过2000字的连续段落（源文全文特征）
    lines = plot_guide_text.split("\n")
    result = []
    buffer = []
    for line in lines:
        buffer.append(line)
        current_text = "\n".join(buffer)
        if len(current_text) > 2000:
            # 这段太长，可能是源文全文，截断
            result.append("（源文已省略，请根据以上节拍映射创作）")
            buffer = []
    if buffer:
        result.extend(buffer)

    return "\n".join(result)


def run_one_with_template(config, prompt_type, chapter_num=None, **kwargs):
    """包装 run_one，自动处理模板合并和 XML 提取。"""
    result = run_one(config, prompt_type, chapter_num, **kwargs)

    # prompts_only 跳过处理
    if config.get("prompts_only"):
        return result

    # XML 标签提取（drama-engine 同款）
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

