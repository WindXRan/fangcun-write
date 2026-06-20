"""
writer-engine: 通用写章模块

支持两种模式：
- imitation（仿写）：有源文参照，对比源文质量指标
- continue（续写）：无源文，自由创作，延续前文风格
"""

import os
from pathlib import Path


def _setup_imports():
    """设置导入路径，返回需要的模块"""
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    return call_llm, safe_format


def get_writer_dirs(config):
    """获取写作相关的目录结构"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    return {
        "rewrites_dir": rewrites_dir,
        "chapters_dir": rewrites_dir / "chapters",
        "guides_dir": rewrites_dir / "guides",
        "analysis_dir": rewrites_dir / "analysis",
    }


def _load_prompt_template(mode, action="write"):
    """加载prompt模板（去掉frontmatter）
    
    Args:
        mode: "imitation" 或 "continue"
        action: "write", "trim", "polish", "expand", "rewrite"
    """
    prompts_dir = Path(__file__).parent.parent / "prompts"
    
    # 先找模式特定的模板
    prompt_file = prompts_dir / mode / f"{action}.md"
    if not prompt_file.exists():
        # 再找通用模板
        prompt_file = prompts_dir / f"{action}.md"
    if not prompt_file.exists():
        return "你是一个专业的小说写手。请根据以下要求写作。"
    
    content = prompt_file.read_text(encoding="utf-8")
    # 去掉 frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def _load_system_prompt(mode):
    """加载系统提示词"""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    
    # 先找模式特定的系统提示词
    prompt_file = prompts_dir / mode / "system.md"
    if prompt_file.exists():
        content = prompt_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content.strip()
    
    # 再找通用系统提示词
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
    """加载角色卡"""
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
    """加载前文"""
    context_parts = []
    for i in range(max(1, current_ch - max_chapters), current_ch):
        ch_file = chapters_dir / f"ch_{i:03d}.txt"
        if ch_file.exists():
            content = ch_file.read_text(encoding="utf-8")
            context_parts.append(f"【第{i}章】\n{content[-500:]}")
    return "\n\n".join(context_parts)


def _load_guide(guides_dir, ch_num):
    """加载章纲"""
    candidates = [
        guides_dir / f"plot_{ch_num:03d}.md",
        guides_dir / f"plot_{ch_num}.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "（无章纲）"


def _load_source_text(config, ch_num):
    """加载源文（仿写模式专用）"""
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
    """构建变量映射（兼容 story-engine 的 prompt 变量名）"""
    dirs = get_writer_dirs(config)
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    source_chars = len(source_text.replace(" ", "").replace("\n", "")) if source_text else 0
    
    variables = {
        # 基础变量
        "book_name": config.get("book_name", ""),
        "ch_num": str(ch_num),
        "N": str(ch_num),
        "N03d": f"{ch_num:03d}",
        # story-engine 兼容变量
        "新书名": config.get("book_name", ""),
        "作者名": config.get("author_name", ""),
        "源书名": config.get("source_book_name", ""),
        "源文字数": str(config.get("source_chars", 2500)),
        "源文句长": str(config.get("source_sent_len", 15)),
        "源文短句比": str(config.get("source_short_ratio", 0.3)),
        "源文段长": str(config.get("source_para_len", 60)),
        "源文对话比": str(config.get("source_dialog_ratio", 40)),
        "源文代词密度": str(config.get("source_pronoun_density", 0.05)),
        "源文标点": config.get("source_punctuation", ""),
        "genre": config.get("genre", ""),
        "女主名": config.get("female_lead", ""),
        "男主名": config.get("male_lead", ""),
        "世界观": config.get("worldview", ""),
        "文笔指纹": config.get("writing_fingerprint", ""),
        "风格类型": config.get("style_type", ""),
        "场景运作机制": config.get("scene_mechanism", ""),
        "信息释放时机": config.get("info_release", ""),
        "角色行为卡片": config.get("character_cards", ""),
        "全局结构": config.get("global_structure", ""),
        "改写原则": config.get("rewrite_principles", ""),
    }
    
    # 加载角色卡
    characters = _load_characters(config)
    variables["characters"] = characters
    variables["角色约束"] = characters  # story-engine 兼容
    
    # 加载章纲
    guide = _load_guide(dirs["guides_dir"], ch_num)
    variables["guide"] = guide if guide != "（无章纲）" else "（无章纲，自由发挥）"
    
    # 加载前文
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num)
    variables["prev_context"] = prev_context if prev_context else "（第一章，无前文）"
    
    # 仿写模式：加载源文
    if source_text:
        variables["source_text"] = source_text
    else:
        variables["source_text"] = "（无源文）"
    
    # 合并额外变量
    if extra:
        variables.update(extra)
    
    return variables


def _auto_fix(config, content, mode, call_llm, safe_format):
    """自动修复"""
    chars = len(content.replace(" ", "").replace("\n", ""))
    min_chars, max_chars = 1800, 3000
    
    # 字数检查
    if chars < min_chars:
        target_chars = 2500
        prompt_template = _load_prompt_template(mode, "expand")
        prompt = safe_format(prompt_template, {
            "content": content,
            "orig_chars": str(chars),
            "target_chars": str(target_chars),
            "min_chars": str(int(target_chars * 0.9)),
            "max_chars": str(int(target_chars * 1.1)),
        })
        try:
            return call_llm(config, "expand-chapter", prompt, system_prompt="扩写，保持风格一致。", max_tokens=int(target_chars * 1.5))
        except Exception as e:
            print(f"    [WARN] 扩写失败: {e}")
            return content
    
    if chars > max_chars:
        target_chars = 2500
        need_cut = chars - target_chars
        prompt_template = _load_prompt_template(mode, "trim")
        prompt = safe_format(prompt_template, {
            "content": content,
            "内容": content,
            "target_chars": str(target_chars),
            "目标字数": str(target_chars),
            "当前字数": str(chars),
            "需删减": str(need_cut),
        })
        try:
            return call_llm(config, "trim-chapter", prompt, system_prompt="精简，保留剧情。", max_tokens=int(target_chars * 2))
        except Exception as e:
            print(f"    [WARN] 精简失败: {e}")
            return content
    
    # 仿写模式：质量检查
    if mode == "imitation":
        quality_issue = _check_quality_imitation(config, content)
        if quality_issue:
            source_text = _load_source_text(config, config.get("_current_ch_num"))
            prompt_template = _load_prompt_template(mode, "polish")
            prompt = safe_format(prompt_template, {
                "content": content,
                "source_text": source_text or "（无源文）",
                "源文句长": str(config.get("source_sent_len", 15)),
                "源文对话比": str(config.get("source_dialog_ratio", 40)),
                "源文段长": str(config.get("source_para_len", 60)),
                "min_chars": str(int(chars * 0.9)),
                "max_chars": str(int(chars * 1.1)),
            })
            try:
                return call_llm(config, "polish-chapter", prompt, 
                               system_prompt=f"修复：{quality_issue}",
                               max_tokens=int(chars * 1.5))
            except Exception as e:
                print(f"    [WARN] 润色失败: {e}")
                return content
    
    return content


def _check_quality_imitation(config, content):
    """仿写模式质量检查（对比源文）"""
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    sys.path.insert(0, str(shared_engine))
    
    try:
        from analysis.text_metrics import count_metrics
    except ImportError:
        return None
    
    our_metrics = count_metrics(content)
    
    # 获取源文指标
    ch_num = config.get("_current_ch_num")
    source_text = _load_source_text(config, ch_num) if ch_num else None
    
    if source_text:
        src_metrics = count_metrics(source_text)
        
        # AI路标词检查
        limit = max(src_metrics.get("ai_markers", 0) + 1, 1)
        if our_metrics.get("ai_markers", 0) > limit:
            return "AI路标词过多"
        
        # 代词密度检查
        if src_metrics.get("pronoun_density", 0) > 0:
            ratio = our_metrics.get("pronoun_density", 0) / max(src_metrics["pronoun_density"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                return "代词密度偏离源文"
        
        # 句长偏离检查
        if src_metrics.get("sent_len_stddev", 0) > 0:
            ratio = our_metrics.get("sent_len_stddev", 0) / max(src_metrics["sent_len_stddev"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                return "句长节奏偏离源文"
    
    # 通用检查
    if our_metrics.get("ai_markers", 0) > 5:
        return "AI路标词过多"
    
    return None


def write_chapter(config, ch_num, mode="imitation", context=None, auto_fix=True):
    """写单章（含自动修复）
    
    Args:
        config: 配置字典
        ch_num: 章节号
        mode: "imitation"（仿写）或 "continue"（续写）
        context: 额外上下文
        auto_fix: 是否自动修复
    """
    call_llm, safe_format = _setup_imports()
    
    # 构建变量
    extra = {}
    if context:
        extra["context"] = context
    variables = _build_variables(config, ch_num, mode, **extra)
    
    # 加载prompt
    prompt_template = _load_prompt_template(mode, "write")
    prompt = safe_format(prompt_template, variables)
    
    # 加载system prompt
    system_prompt = _load_system_prompt(mode)
    
    # 传递当前章节号给_auto_fix
    fix_config = {**config, "_current_ch_num": ch_num}
    
    try:
        result = call_llm(config, f"write-chapter-{mode}", prompt,
                         system_prompt=system_prompt,
                         max_tokens=4096)
        if auto_fix and result:
            result = _auto_fix(fix_config, result, mode, call_llm, safe_format)
        return result
    except Exception as e:
        print(f"    [ERROR] 写章失败: {e}")
        return None


def trim_chapter(config, ch_num, mode="imitation"):
    """精简章节"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    current_chars = len(original.replace(" ", "").replace("\n", ""))
    target_chars = int(current_chars * 0.8)
    need_cut = current_chars - target_chars
    
    prompt_template = _load_prompt_template(mode, "trim")
    prompt = safe_format(prompt_template, {
        "content": original,
        "内容": original,
        "target_chars": str(target_chars),
        "目标字数": str(target_chars),
        "当前字数": str(current_chars),
        "需删减": str(need_cut),
        "N": str(ch_num),
        "N03d": f"{ch_num:03d}",
    })
    
    system_prompt = _load_system_prompt(mode)
    
    try:
        return call_llm(config, "trim-chapter", prompt,
                       system_prompt=system_prompt,
                       max_tokens=int(target_chars * 2))
    except Exception as e:
        print(f"    [ERROR] 精简失败: {e}")
        return None


def polish_chapter(config, ch_num, mode="imitation"):
    """润色章节（对比源文风格）"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    # 加载源文（仿写模式）
    source_text = _load_source_text(config, ch_num) if mode == "imitation" else None
    
    prompt_template = _load_prompt_template(mode, "polish")
    prompt = safe_format(prompt_template, {
        "content": original,
        "source_text": source_text or "（无源文，通用润色）",
        "源文句长": str(config.get("source_sent_len", 15)),
        "源文对话比": str(config.get("source_dialog_ratio", 40)),
        "源文段长": str(config.get("source_para_len", 60)),
        "min_chars": str(int(original_chars * 0.9)),
        "max_chars": str(int(original_chars * 1.1)),
    })
    
    system_prompt = _load_system_prompt(mode)
    
    try:
        return call_llm(config, "polish-chapter", prompt,
                       system_prompt=system_prompt,
                       max_tokens=int(original_chars * 1.5))
    except Exception as e:
        print(f"    [ERROR] 润色失败: {e}")
        return None


def expand_chapter(config, ch_num, mode="imitation", target_chars=None):
    """扩写章节"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    if target_chars is None:
        target_chars = int(original_chars * 1.3)
    
    prompt_template = _load_prompt_template(mode, "expand")
    prompt = safe_format(prompt_template, {
        "content": original,
        "orig_chars": str(original_chars),
        "target_chars": str(target_chars),
        "min_chars": str(int(target_chars * 0.9)),
        "max_chars": str(int(target_chars * 1.1)),
    })
    
    system_prompt = _load_system_prompt(mode)
    
    try:
        return call_llm(config, "expand-chapter", prompt,
                       system_prompt=system_prompt,
                       max_tokens=int(target_chars * 1.5))
    except Exception as e:
        print(f"    [ERROR] 扩写失败: {e}")
        return None


def rewrite_chapter(config, ch_num, mode="imitation", reason=""):
    """重写章节"""
    call_llm, safe_format = _setup_imports()
    
    extra = {"reason": reason or "（无具体原因，整章重写）"}
    variables = _build_variables(config, ch_num, mode, **extra)
    
    prompt_template = _load_prompt_template(mode, "rewrite")
    prompt = safe_format(prompt_template, variables)
    
    system_prompt = _load_system_prompt(mode)
    
    try:
        return call_llm(config, f"rewrite-chapter-{mode}", prompt,
                       system_prompt=system_prompt,
                       max_tokens=4096)
    except Exception as e:
        print(f"    [ERROR] 重写失败: {e}")
        return None
