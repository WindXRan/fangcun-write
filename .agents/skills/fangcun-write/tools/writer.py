"""
fangcun-write: 通用写章模块

完整流程：写章 → dispatch_fix（trim/expand/polish） → validate → 不通过则重试
"""

import os
import re
from pathlib import Path


def _setup_imports():
    """设置导入路径，返回需要的模块"""
    import sys
    analyze_tools = Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"
    novel_tools = Path(__file__).parent.parent.parent / "fangcun-novel" / "tools"
    for d in [str(analyze_tools), str(novel_tools)]:
        if d not in sys.path:
            sys.path.insert(0, d)
    from lib.api_client import call_llm
    from prompt_meta import safe_format
    from prompt_loader import load_prompt
    return call_llm, safe_format, load_prompt


def get_writer_dirs(config):
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    return {
        "rewrites_dir": rewrites_dir,
        "chapters_dir": rewrites_dir / "chapters",
        "guides_dir": rewrites_dir / "guides",
        "analysis_dir": rewrites_dir / "analysis",
    }


def _load_prompt_template(mode, action="write"):
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / mode / f"{action}.md"
    if not prompt_file.exists():
        prompt_file = prompts_dir / f"{action}.md"
    if not prompt_file.exists():
        return "你是一个专业的小说写手。请根据以下要求写作。"
    content = prompt_file.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def _load_system_prompt(mode):
    """加载系统提示词（始终用根目录 system.md，不用模式目录）"""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / "system.md"
    if prompt_file.exists():
        content = prompt_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content.strip()
    return ""


def _load_characters(config):
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    candidates = [
        rewrites_dir / "analysis" / "characters.md",
        rewrites_dir / "characters.md",
        rewrites_dir / "settings" / "characters.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "（无角色卡）"


def _load_previous_chapters(chapters_dir, current_ch, max_chapters=3):
    context_parts = []
    for i in range(max(1, current_ch - max_chapters), current_ch):
        ch_file = chapters_dir / f"ch_{i:03d}.txt"
        if ch_file.exists():
            content = ch_file.read_text(encoding="utf-8")
            context_parts.append(f"【第{i}章】\n{content[-500:]}")
    return "\n\n".join(context_parts)


def _load_guide(guides_dir, ch_num):
    candidates = [
        guides_dir / f"plot_{ch_num:03d}.md",
        guides_dir / f"plot_{ch_num}.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "（无章纲）"


def _load_source_text(config, ch_num):
    source_dir = Path(config.get("source_dir", ""))
    if not source_dir:
        return None
    cache_dir = source_dir / "_cache" / "chapters"
    candidates = [
        cache_dir / f"第{ch_num:03d}章.txt",
        cache_dir / f"第{ch_num}章.txt",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def _build_variables(config, ch_num, mode, **extra):
    dirs = get_writer_dirs(config)
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    guide = _load_guide(dirs["guides_dir"], ch_num)
    guide_content = guide if guide != "（无章纲）" else ""
    characters_full = _load_characters(config)
    characters_brief = _extract_character_brief(characters_full, ch_num)
    source_chars = len(source_text.replace(" ", "").replace("\n", "")) if source_text else 0

    variables = {
        "book_name": config.get("book_name", ""),
        "ch_num": str(ch_num), "N": str(ch_num), "N03d": f"{ch_num:03d}",
        "plot_guide": guide_content, "创作指令": guide_content, "guide": guide_content,
        "新书名": config.get("book_name", ""),
        "作者名": config.get("author_name", ""),
        "源书名": config.get("source_book_name", ""),
        "源文字数": str(source_chars or config.get("source_chars", 2500)),
        "源文句长": str(config.get("source_sent_len", 15)),
        "源文短句比": str(config.get("source_short_ratio", 0.3)),
        "源文段长": str(config.get("source_para_len", 60)),
        "源文对话比": str(config.get("source_dialog_ratio", 40)),
        "源文代词密度": str(config.get("source_pronoun_density", 0.05)),
        "源文标点": config.get("source_punctuation", ""),
        "genre": config.get("genre", ""),
        "女主名": config.get("female_lead", ""),
        "男主名": config.get("male_lead", ""),
        "世界观": config.get("worldview", "（未设定）"),
        "文笔指纹": config.get("writing_fingerprint", "（未提取，自由发挥）"),
        "风格类型": config.get("style_type", "（未指定）"),
        "场景运作机制": config.get("scene_mechanism", "（未指定）"),
        "信息释放时机": config.get("info_release", "（未指定）"),
        "角色行为卡片": characters_brief,
        "全局结构": config.get("global_structure", "（未指定）"),
        "改写原则": config.get("rewrite_principles", "（未指定）"),
        "目标字数": str(source_chars or config.get("source_chars", 2500)),
        "目标字数_min": str(int((source_chars or config.get("source_chars", 2500)) * 0.9)),
        "目标字数_max": str(int((source_chars or config.get("source_chars", 2500)) * 1.1)),
    }
    variables["characters"] = characters_brief
    variables["角色约束"] = characters_brief
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num)
    variables["prev_context"] = prev_context if prev_context else "（第一章，无前文）"
    variables["source_text"] = source_text if source_text else "（无源文）"
    if extra:
        variables.update(extra)
    return variables


def _extract_character_brief(characters_full, ch_num):
    if not characters_full or characters_full == "（无角色卡）":
        return "（无角色卡）"
    if len(characters_full) < 5000:
        return characters_full
    return characters_full[:5000] + "\n\n（...更多角色详见 characters.md）"


# ============================================================
# Post-processing: dispatch_fix + validate（移植自 fangcun-novel）
# ============================================================

def _get_text_chars(text):
    """获取去空白后的字数"""
    return len(re.sub(r'\s', '', text))


def _dispatch_fix(config, ch_num, text, mode, call_llm, safe_format):
    """写后修复：按问题类型派发 trim/expand/polish，每章必 polish。"""
    from lib.text_metrics import count_metrics
    
    chars = _get_text_chars(text)
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    src_metrics = count_metrics(source_text) if source_text else None
    our_metrics = count_metrics(text)
    
    # 字数超标 → trim
    if chars > 3000:
        print(f"    [FIX] ch{ch_num:03d} 字数超标 {chars} → trim")
        result = _do_trim(config, ch_num, text, mode, call_llm, safe_format)
        if result:
            text = result
            chars = _get_text_chars(text)
            our_metrics = count_metrics(text)  # 重新计算
    
    # 字数不足 → expand
    elif chars < 2000:
        print(f"    [FIX] ch{ch_num:03d} 字数不足 {chars} → expand")
        result = _do_expand(config, ch_num, text, mode, call_llm, safe_format)
        if result:
            text = result
            chars = _get_text_chars(text)
            our_metrics = count_metrics(text)  # 重新计算
    
    # 检查是否需要 polish（AI路标词/代词密度/句长偏离）
    polish_reason = None
    if src_metrics:
        limit = max(src_metrics.get("ai_markers", 0) + 1, 1)
        if our_metrics.get("ai_markers", 0) > limit:
            polish_reason = f"AI路标词 {our_metrics['ai_markers']}处 (源文{src_metrics['ai_markers']})"
        if not polish_reason and src_metrics.get("pronoun_density", 0) > 0:
            ratio = our_metrics["pronoun_density"] / max(src_metrics["pronoun_density"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                polish_reason = f"代词密度偏离 {ratio:.1f}x"
        if not polish_reason and src_metrics.get("sent_len_stddev", 0) > 0:
            ratio = our_metrics["sent_len_stddev"] / max(src_metrics["sent_len_stddev"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                polish_reason = f"句长偏离 {ratio:.1f}x"
    
    if not polish_reason:
        polish_reason = "风格对齐"
    
    print(f"    [POLISH] ch{ch_num:03d} ({polish_reason})")
    result = _do_polish(config, ch_num, text, mode, call_llm, safe_format, polish_reason)
    if result:
        text = result
    
    return text


def _do_trim(config, ch_num, text, mode, call_llm, safe_format):
    """执行 trim（带二次校验）"""
    chars = _get_text_chars(text)
    target_chars = int(config.get("source_chars", 2500))
    need_cut = chars - target_chars
    prompt_template = _load_prompt_template(mode, "trim")
    prompt = safe_format(prompt_template, {
        "content": text, "内容": text,
        "target_chars": str(target_chars), "目标字数": str(target_chars),
        "当前字数": str(chars), "需删减": str(need_cut),
        "N": str(ch_num), "N03d": f"{ch_num:03d}",
    })
    try:
        result = call_llm(config, "trim-chapter", prompt,
                         system_prompt=f"精简到{target_chars}字左右，不能少于{int(target_chars*0.85)}字，不能多于{int(target_chars*1.1)}字。保留剧情。",
                         max_tokens=int(target_chars * 2))
        if result:
            result_chars = _get_text_chars(result)
            # 砍太多或砍太少 → 用原文
            if result_chars < target_chars * 0.8 or result_chars > chars * 0.95:
                print(f"    [WARN] trim 结果异常 ({result_chars}/{target_chars})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] trim 失败: {e}")
        return None


def _do_expand(config, ch_num, text, mode, call_llm, safe_format):
    """执行 expand（带二次校验）"""
    chars = _get_text_chars(text)
    target_chars = int(config.get("source_chars", 2500))
    prompt_template = _load_prompt_template(mode, "expand")
    prompt = safe_format(prompt_template, {
        "content": text, "orig_chars": str(chars),
        "target_chars": str(target_chars),
        "min_chars": str(int(target_chars * 0.9)),
        "max_chars": str(int(target_chars * 1.1)),
    })
    try:
        result = call_llm(config, "expand-chapter", prompt,
                         system_prompt=f"扩写到{target_chars}字左右，不能超过{int(target_chars*1.1)}字。",
                         max_tokens=int(target_chars * 1.5))
        if result:
            result_chars = _get_text_chars(result)
            # 加太多 → 用原文
            if result_chars > target_chars * 1.3:
                print(f"    [WARN] expand 加太多 ({result_chars}/{target_chars})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] expand 失败: {e}")
        return None


def _do_polish(config, ch_num, text, mode, call_llm, safe_format, reason=""):
    """执行 polish（对比源文风格）"""
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    chars = _get_text_chars(text)
    prompt_template = _load_prompt_template(mode, "polish")
    prompt = safe_format(prompt_template, {
        "content": text,
        "source_text": source_text or "（无源文，通用润色）",
        "源文句长": str(config.get("source_sent_len", 15)),
        "源文对话比": str(config.get("source_dialog_ratio", 40)),
        "源文段长": str(config.get("source_para_len", 60)),
        "min_chars": str(int(chars * 0.9)),
        "max_chars": str(int(chars * 1.1)),
    })
    try:
        return call_llm(config, "polish-chapter", prompt,
                       system_prompt=f"润色，修正风格。{reason}",
                       max_tokens=int(chars * 1.5))
    except Exception as e:
        print(f"    [WARN] polish 失败: {e}")
        return None


def _validate_chapter(config, ch_num, text, mode):
    """验证单章质量。返回 (pass: bool, issues: list)。
    
    移植自 fangcun-novel phases/validate.py validate_one。
    """
    from lib.text_metrics import count_metrics
    
    issues = []
    our_metrics = count_metrics(text)
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    src_metrics = count_metrics(source_text) if source_text else None
    
    chars = _get_text_chars(text)
    target = int(config.get("source_chars", 2500))
    
    # 1. 字数检查（±15%）
    if target > 0:
        deviation = (chars - target) / target
        if deviation > 0.15:
            issues.append(f"字数超标 {chars}/{target} (+{deviation:.0%})")
        elif deviation < -0.15:
            issues.append(f"字数不足 {chars}/{target} ({deviation:.0%})")
    
    # 2. AI路标词（源文+1）
    if src_metrics:
        limit = max(src_metrics.get("ai_markers", 0) + 1, 1)
        if our_metrics.get("ai_markers", 0) > limit:
            issues.append(f"AI路标词 {our_metrics['ai_markers']}处 (上限{limit})")
    
    # 3. 代词密度（源文±50%）
    if src_metrics and src_metrics.get("pronoun_density", 0) > 0:
        ratio = our_metrics["pronoun_density"] / src_metrics["pronoun_density"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"代词密度 {ratio:.1f}x 偏离源文")
    
    # 4. 句长标准差（源文±50%）
    if src_metrics and src_metrics.get("sent_len_stddev", 0) > 0:
        ratio = our_metrics["sent_len_stddev"] / src_metrics["sent_len_stddev"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"句长标准差 {ratio:.1f}x 偏离源文")
    
    # 5. 台词抄袭检测（连续8字匹配）
    if source_text:
        try:
            from lib.plagiarism import find_plagiarism
            plagiarisms = find_plagiarism(text, source_text)
            if plagiarisms:
                issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
                for p in plagiarisms[:3]:
                    issues.append(f"  '{p['text'][:20]}...' ({p['length']}字)")
        except ImportError:
            pass
    
    # 6. 结构性抄袭检测（换皮检验）
    if source_text:
        try:
            from lib.plagiarism import check_structural_plagiarism
            struct_result = check_structural_plagiarism(text, source_text)
            if struct_result["is_plagiarism"]:
                issues.append(f"结构性抄袭 ({struct_result['score']:.0%}): {struct_result['reason']}")
        except ImportError:
            pass
    
    passed = len(issues) == 0
    return passed, issues


# ============================================================
# 主入口：write_chapter（含 dispatch_fix + validate + 重试）
# ============================================================

def write_chapter(config, ch_num, mode="imitation", context=None, auto_fix=True, max_retries=2):
    """写单章：写章 → dispatch_fix → validate → 不通过则重试。
    
    使用 fangcun-novel 的 prompt_loader.load_prompt() 加载 prompt，
    自动处理 book_data.json 注入、文件引用嵌入、变量替换。
    """
    call_llm, safe_format, load_prompt = _setup_imports()
    fix_config = {**config, "_current_ch_num": ch_num}
    last_issues = []
    
    # prompt 文件路径
    prompts_dir = Path(__file__).parent.parent / "prompts"
    write_prompt = prompts_dir / mode / "write.md"
    if not write_prompt.exists():
        write_prompt = prompts_dir / "write.md"
    rewrite_prompt = prompts_dir / mode / "rewrite.md"
    if not rewrite_prompt.exists():
        rewrite_prompt = prompts_dir / "rewrite.md"
    
    # 基础目录（prompt_loader 需要）
    base_dir = config.get("base_dir", str(Path(__file__).parent.parent.parent.parent))
    rewrites_dir = config.get("rewrites_dir", "")
    
    # 构建变量（fangcun-novel run_one 同款）
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    source_chars = len(source_text.replace(" ", "").replace("\n", "")) if source_text else 0
    target_chars = source_chars if source_chars > 0 else int(config.get("source_chars", 2500))
    
    # 加载 plot_guide 内容（核心！）
    dirs = get_writer_dirs(config)
    guide_content = _load_guide(dirs["guides_dir"], ch_num)
    
    # 加载角色卡
    characters_full = _load_characters(config)
    
    replacements = {
        "新书名": config.get("book_name", ""),
        "N": str(ch_num),
        "N03d": f"{ch_num:03d}",
        "作者名": config.get("author_name", ""),
        "源书名": config.get("source_book_name", ""),
        "源文字数": str(source_chars),
        "目标字数": str(target_chars),
        "目标字数_min": str(int(target_chars * 0.9)),
        "目标字数_max": str(int(target_chars * 1.1)),
        # 核心变量：plot_guide 内容
        "plot_guide": guide_content,
        "创作指令": guide_content,
        "guide": guide_content,
        # 角色卡
        "角色约束": characters_full,
        "角色行为卡片": characters_full,
        "characters": characters_full,
        # 风格约束（从 config 读取）
        "风格类型": config.get("style_type", ""),
        "场景运作机制": config.get("scene_mechanism", ""),
        "信息释放时机": config.get("info_release", ""),
        "文笔指纹": config.get("writing_fingerprint", ""),
        "全局结构": config.get("global_structure", ""),
        "改写原则": config.get("rewrite_principles", ""),
        "世界观": config.get("worldview", ""),
        "源文句长": str(config.get("source_sent_len", 15)),
        "源文对话比": str(config.get("source_dialog_ratio", 40)),
        "源文段长": str(config.get("source_para_len", 60)),
    }
    if context:
        replacements["context"] = context
    
    system_prompt = _load_system_prompt(mode)
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                # 重试：用 rewrite prompt
                replacements["失败原因"] = "\n".join(last_issues)
                replacements["reason"] = "\n".join(last_issues)
                prompt = load_prompt(
                    str(rewrite_prompt), base_dir,
                    replacements=replacements, mode="api",
                    rewrites_dir=rewrites_dir
                )
                result = call_llm(config, f"rewrite-chapter-{mode}", prompt,
                                 system_prompt=system_prompt, max_tokens=4096)
            else:
                # 首次：用 write prompt（prompt_loader 自动嵌入 book_data + 文件引用）
                prompt = load_prompt(
                    str(write_prompt), base_dir,
                    replacements=replacements, mode="api",
                    rewrites_dir=rewrites_dir
                )
                result = call_llm(config, f"write-chapter-{mode}", prompt,
                                 system_prompt=system_prompt, max_tokens=4096)
        except Exception as e:
            print(f"    [ERROR] ch{ch_num:03d} 写章失败: {e}")
            return None
        
        if not result:
            return None
        
        # dispatch_fix（trim/expand/polish）
        if auto_fix:
            result = _dispatch_fix(fix_config, ch_num, result, mode, call_llm, safe_format)
        
        # validate
        passed, issues = _validate_chapter(config, ch_num, result, mode)
        
        if passed:
            if attempt > 0:
                print(f"    [OK] ch{ch_num:03d} 重试第{attempt}次通过验证")
            return result
        
        last_issues = issues
        if attempt < max_retries:
            print(f"    [RETRY] ch{ch_num:03d} 验证不通过 ({', '.join(issues[:2])})，重试 {attempt+1}/{max_retries}")
        else:
            print(f"    [WARN] ch{ch_num:03d} 重试{max_retries}次仍不通过: {', '.join(issues[:2])}")
            return result


# ============================================================
# 独立函数：trim/polish/expand/rewrite（供 pipeline 和其他引擎调用）
# ============================================================

def trim_chapter(config, ch_num, mode="imitation"):
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    result = _do_trim(config, ch_num, text, mode, call_llm, safe_format)
    return result


def polish_chapter(config, ch_num, mode="imitation"):
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    result = _do_polish(config, ch_num, text, mode, call_llm, safe_format, "风格对齐")
    return result


def expand_chapter(config, ch_num, mode="imitation", target_chars=None):
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    result = _do_expand(config, ch_num, text, mode, call_llm, safe_format)
    return result


def rewrite_chapter(config, ch_num, mode="imitation", reason=""):
    call_llm, safe_format, load_prompt = _setup_imports()
    prompts_dir = Path(__file__).parent.parent / "prompts"
    rewrite_prompt = prompts_dir / mode / "rewrite.md"
    if not rewrite_prompt.exists():
        rewrite_prompt = prompts_dir / "rewrite.md"
    base_dir = config.get("base_dir", str(Path(__file__).parent.parent.parent.parent))
    rewrites_dir = config.get("rewrites_dir", "")
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    source_chars = len(source_text.replace(" ", "").replace("\n", "")) if source_text else 0
    target_chars = source_chars if source_chars > 0 else int(config.get("source_chars", 2500))
    replacements = {
        "新书名": config.get("book_name", ""),
        "N": str(ch_num), "N03d": f"{ch_num:03d}",
        "作者名": config.get("author_name", ""),
        "源书名": config.get("source_book_name", ""),
        "源文字数": str(source_chars),
        "目标字数": str(target_chars),
        "目标字数_min": str(int(target_chars * 0.9)),
        "目标字数_max": str(int(target_chars * 1.1)),
        "失败原因": reason or "（无具体原因，整章重写）",
        "reason": reason or "（无具体原因，整章重写）",
    }
    system_prompt = _load_system_prompt(mode)
    try:
        prompt = load_prompt(str(rewrite_prompt), base_dir, replacements=replacements, mode="api", rewrites_dir=rewrites_dir)
        return call_llm(config, f"rewrite-chapter-{mode}", prompt, system_prompt=system_prompt, max_tokens=4096)
    except Exception as e:
        print(f"    [ERROR] rewrite 失败: {e}")
        return None
