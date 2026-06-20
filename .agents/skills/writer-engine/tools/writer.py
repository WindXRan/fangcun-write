"""
writer-engine: 通用写章模块

提供 write/trim/polish/expand/rewrite 函数，供其他引擎调用。
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


def _load_prompt_template(prompt_name):
    """加载prompt模板"""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_file = prompts_dir / f"{prompt_name}.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return "你是一个专业的小说写手。请根据以下要求写作。"


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


def _build_variables(config, ch_num, characters, guide, prev_context, context=None, extra=None):
    """构建通用变量映射"""
    variables = {
        "book_name": config.get("book_name", ""),
        "ch_num": str(ch_num),
        "characters": characters,
        "guide": guide if guide != "（无章纲）" else "（无章纲，自由发挥）",
        "prev_context": prev_context if prev_context else "（第一章，无前文）",
        "context": context or "",
    }
    if extra:
        variables.update(extra)
    return variables


def _auto_fix(config, content, call_llm, safe_format):
    """自动修复字数问题"""
    chars = len(content.replace(" ", "").replace("\n", ""))
    min_chars, max_chars = 1800, 3000
    
    if min_chars <= chars <= max_chars:
        return content
    
    if chars < min_chars:
        target_chars = 2500
        prompt_template = _load_prompt_template("expand")
        prompt = safe_format(prompt_template, {"content": content, "orig_chars": str(chars), "target_chars": str(target_chars)})
        try:
            return call_llm(config, "expand-chapter", prompt, system_prompt="你是一个专业的小说写手，擅长扩写。", max_tokens=int(target_chars * 1.5))
        except Exception as e:
            print(f"    [WARN] 扩写失败: {e}")
            return content
    
    if chars > max_chars:
        target_chars = 2500
        prompt_template = _load_prompt_template("trim")
        prompt = safe_format(prompt_template, {"content": content, "target_chars": str(target_chars)})
        try:
            return call_llm(config, "trim-chapter", prompt, system_prompt="你是一个专业的小说编辑，擅长精简文字。", max_tokens=int(target_chars * 2))
        except Exception as e:
            print(f"    [WARN] 精简失败: {e}")
            return content
    
    return content


def write_chapter(config, ch_num, context=None, auto_fix=True):
    """写单章（含自动修复）"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    
    characters = _load_characters(config)
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num)
    guide = _load_guide(dirs["guides_dir"], ch_num)
    
    prompt_template = _load_prompt_template("write")
    variables = _build_variables(config, ch_num, characters, guide, prev_context, context)
    prompt = safe_format(prompt_template, variables)
    
    try:
        result = call_llm(config, "write-chapter", prompt,
                         system_prompt="你是一个专业的小说写手。续写时必须保持原作风格和角色一致性。不要废话，直接写正文。",
                         max_tokens=4096)
        if auto_fix and result:
            result = _auto_fix(config, result, call_llm, safe_format)
        return result
    except Exception as e:
        print(f"    [ERROR] 写章失败: {e}")
        return None


def trim_chapter(config, ch_num):
    """精简章节"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    target_chars = int(len(original.replace(" ", "").replace("\n", "")) * 0.8)
    
    prompt_template = _load_prompt_template("trim")
    prompt = safe_format(prompt_template, {"content": original, "target_chars": str(target_chars)})
    
    try:
        return call_llm(config, "trim-chapter", prompt,
                       system_prompt="你是一个专业的小说编辑，擅长精简文字。",
                       max_tokens=int(target_chars * 2))
    except Exception as e:
        print(f"    [ERROR] 精简失败: {e}")
        return None


def polish_chapter(config, ch_num):
    """润色章节"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    prompt_template = _load_prompt_template("polish")
    prompt = safe_format(prompt_template, {
        "content": original,
        "min_chars": str(int(original_chars * 0.9)),
        "max_chars": str(int(original_chars * 1.1)),
    })
    
    try:
        return call_llm(config, "polish-chapter", prompt,
                       system_prompt="你是一个专业的小说编辑，擅长润色文笔。",
                       max_tokens=int(original_chars * 1.5))
    except Exception as e:
        print(f"    [ERROR] 润色失败: {e}")
        return None


def expand_chapter(config, ch_num, target_chars=None):
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
    
    prompt_template = _load_prompt_template("expand")
    prompt = safe_format(prompt_template, {
        "content": original,
        "orig_chars": str(original_chars),
        "target_chars": str(target_chars),
    })
    
    try:
        return call_llm(config, "expand-chapter", prompt,
                       system_prompt="你是一个专业的小说写手，擅长扩写。",
                       max_tokens=int(target_chars * 1.5))
    except Exception as e:
        print(f"    [ERROR] 扩写失败: {e}")
        return None


def rewrite_chapter(config, ch_num, reason=""):
    """重写章节"""
    call_llm, safe_format = _setup_imports()
    dirs = get_writer_dirs(config)
    
    characters = _load_characters(config)
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num)
    guide = _load_guide(dirs["guides_dir"], ch_num)
    
    prompt_template = _load_prompt_template("rewrite")
    variables = _build_variables(config, ch_num, characters, guide, prev_context, 
                                 extra={"reason": reason or "（无具体原因，整章重写）"})
    prompt = safe_format(prompt_template, variables)
    
    try:
        return call_llm(config, "rewrite-chapter", prompt,
                       system_prompt="你是一个专业的小说写手。重写时必须解决上述问题，保持角色一致性。",
                       max_tokens=4096)
    except Exception as e:
        print(f"    [ERROR] 重写失败: {e}")
        return None
