"""
writer-engine: 通用写章模块

提供 write_chapter() 函数，供其他引擎调用。
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime


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
    
    # 如果没有找到模板，返回默认模板
    return "你是一个专业的小说写手。请根据以下要求写作。"


def write_chapter(config, ch_num, context=None, auto_fix=True):
    """
    写单章（含自动修复）。
    
    Args:
        config: 配置字典
        ch_num: 章节号
        context: 额外上下文（可选，用于续写等场景）
        auto_fix: 是否自动修复字数问题（默认True）
    
    Returns:
        str: 章节内容，失败返回 None
    """
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
    dirs = get_writer_dirs(config)
    
    # 读取角色卡
    characters = _load_characters(config)
    
    # 读取前文（最多3章）
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num, max_chapters=3)
    
    # 读取章纲
    guide = _load_guide(dirs["guides_dir"], ch_num)
    
    # 加载prompt模板
    prompt_template = _load_prompt_template("write")
    
    # 构建变量映射
    variables = {
        "book_name": config.get("book_name", ""),
        "ch_num": str(ch_num),
        "characters": characters[:1500],
        "guide": guide[:2000] if guide != "（无章纲）" else "（无章纲，自由发挥）",
        "prev_context": prev_context if prev_context else "（第一章，无前文）",
    }
    
    # 添加续写等额外上下文
    if context:
        variables["context"] = context[:1000]
    else:
        variables["context"] = ""
    
    # 替换变量
    prompt = safe_format(prompt_template, variables)
    
    # 调用 LLM
    try:
        result = call_llm(config, "write-chapter", prompt,
                         system_prompt="你是一个专业的小说写手。续写时必须保持原作风格和角色一致性。不要废话，直接写正文。",
                         max_tokens=4096)
        
        # 自动修复：字数检查
        if auto_fix and result:
            result = _auto_fix_chapter(config, ch_num, result, characters, guide, prev_context, context)
        
        return result
    except Exception as e:
        print(f"    [ERROR] 写章失败: {e}")
        return None


def _auto_fix_chapter(config, ch_num, content, characters, guide, prev_context, context=None):
    """自动修复章节（字数检查+trim/expand）"""
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
    # 计算字数
    chars = len(content.replace(" ", "").replace("\n", ""))
    
    # 目标字数范围
    min_chars = 1800
    max_chars = 3000
    
    # 如果字数在范围内，直接返回
    if min_chars <= chars <= max_chars:
        return content
    
    # 字数不足 → 扩写
    if chars < min_chars:
        target_chars = 2500
        prompt_template = _load_prompt_template("expand")
        variables = {
            "content": content,
            "orig_chars": str(chars),
            "target_chars": str(target_chars),
        }
        prompt = safe_format(prompt_template, variables)
        
        try:
            result = call_llm(config, "expand-chapter", prompt,
                             system_prompt="你是一个专业的小说写手，擅长扩写。",
                             max_tokens=int(target_chars * 1.5))
            return result
        except Exception as e:
            print(f"    [WARN] 扩写失败: {e}")
            return content
    
    # 字数超标 → 精简
    if chars > max_chars:
        target_chars = 2500
        prompt_template = _load_prompt_template("trim")
        variables = {
            "content": content,
            "target_chars": str(target_chars),
        }
        prompt = safe_format(prompt_template, variables)
        
        try:
            result = call_llm(config, "trim-chapter", prompt,
                             system_prompt="你是一个专业的小说编辑，擅长精简文字。",
                             max_tokens=int(target_chars * 2))
            return result
        except Exception as e:
            print(f"    [WARN] 精简失败: {e}")
            return content
    
    return content


def _load_characters(config):
    """加载角色卡"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    
    # 尝试多个位置
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
            # 只取最后500字作为上下文
            if len(content) > 500:
                content = "..." + content[-500:]
            context_parts.append(f"【第{i}章】\n{content}")
    return "\n\n".join(context_parts)


def _load_guide(guides_dir, ch_num):
    """加载章纲"""
    # 尝试多种文件名格式
    candidates = [
        guides_dir / f"plot_{ch_num:03d}.md",
        guides_dir / f"plot_{ch_num}.md",
    ]
    
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    
    return "（无章纲）"


def _build_write_prompt(config, ch_num, characters, guide, prev_context, context=None):
    """构建写章 prompt"""
    book_name = config.get("book_name", "")
    
    prompt = f"""你是一个专业的小说写手。请写《{book_name}》第{ch_num}章。

## 角色卡
{characters[:1500]}

## 章纲
{guide[:2000] if guide != "（无章纲）" else "（无章纲，自由发挥）"}

## 前文内容
{prev_context if prev_context else "（第一章，无前文）"}
"""
    
    # 添加续写等额外上下文
    if context:
        prompt += f"\n## 额外上下文\n{context[:1000]}\n"
    
    prompt += """
## 写作要求

1. **风格一致**：延续原作的文笔风格（对话比例、段长、描写特点）
2. **角色一致**：角色名字、性格、说话方式必须与原作一致
3. **情节连贯**：承接前文情节，不出现矛盾
4. **字数控制**：2000-3000字
5. **章末钩子**：每章结尾留一个钩子，吸引读者继续看

## 输出格式

第{ch_num}章 [章名]

[正文内容]

【字数：XXX字】
"""
    
    return prompt


def trim_chapter(config, ch_num):
    """
    精简章节（保留剧情，删冗余）。
    
    Args:
        config: 配置字典
        ch_num: 章节号
    
    Returns:
        str: 精简后的内容，失败返回 None
    """
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    # 目标字数：原文的80%
    target_chars = int(original_chars * 0.8)
    
    prompt_template = _load_prompt_template("trim")
    variables = {
        "content": original,
        "target_chars": str(target_chars),
    }
    prompt = safe_format(prompt_template, variables)
    
    try:
        result = call_llm(config, "trim-chapter", prompt,
                         system_prompt="你是一个专业的小说编辑，擅长精简文字。",
                         max_tokens=int(target_chars * 2))
        
        # 验证字数
        new_chars = len(result.replace(" ", "").replace("\n", ""))
        if abs(new_chars - target_chars) / target_chars > 0.3:
            print(f"    [WARN] 字数偏差过大: {new_chars}/{target_chars}")
        
        return result
    except Exception as e:
        print(f"    [ERROR] 精简失败: {e}")
        return None


def polish_chapter(config, ch_num):
    """
    润色章节（改文笔，不改内容）。
    
    Args:
        config: 配置字典
        ch_num: 章节号
    
    Returns:
        str: 润色后的内容，失败返回 None
    """
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    prompt_template = _load_prompt_template("polish")
    variables = {
        "content": original,
        "min_chars": str(int(original_chars * 0.9)),
        "max_chars": str(int(original_chars * 1.1)),
    }
    prompt = safe_format(prompt_template, variables)
    
    try:
        result = call_llm(config, "polish-chapter", prompt,
                         system_prompt="你是一个专业的小说编辑，擅长润色文笔。",
                         max_tokens=int(original_chars * 1.5))
        return result
    except Exception as e:
        print(f"    [ERROR] 润色失败: {e}")
        return None


def expand_chapter(config, ch_num, target_chars=None):
    """
    扩写章节（增加细节）。
    
    Args:
        config: 配置字典
        ch_num: 章节号
        target_chars: 目标字数（默认增加30%）
    
    Returns:
        str: 扩写后的内容，失败返回 None
    """
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
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
    variables = {
        "content": original,
        "orig_chars": str(original_chars),
        "target_chars": str(target_chars),
    }
    prompt = safe_format(prompt_template, variables)
    
    try:
        result = call_llm(config, "expand-chapter", prompt,
                         system_prompt="你是一个专业的小说写手，擅长扩写。",
                         max_tokens=int(target_chars * 1.5))
        return result
    except Exception as e:
        print(f"    [ERROR] 扩写失败: {e}")
        return None


def rewrite_chapter(config, ch_num, reason=""):
    """
    重写章节（整章重写）。
    
    Args:
        config: 配置字典
        ch_num: 章节号
        reason: 重写原因（可选）
    
    Returns:
        str: 重写后的内容，失败返回 None
    """
    import sys
    shared_engine = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
    shared_engine_llm = shared_engine / "llm"
    sys.path.insert(0, str(shared_engine))
    sys.path.insert(0, str(shared_engine_llm))
    
    from llm.api_client import call_llm
    from llm.prompt_meta import safe_format
    
    dirs = get_writer_dirs(config)
    
    # 读取角色卡
    characters = _load_characters(config)
    
    # 读取前文（最多3章）
    prev_context = _load_previous_chapters(dirs["chapters_dir"], ch_num, max_chapters=3)
    
    # 读取章纲
    guide = _load_guide(dirs["guides_dir"], ch_num)
    
    # 加载prompt模板
    prompt_template = _load_prompt_template("rewrite")
    
    # 构建变量映射
    variables = {
        "book_name": config.get("book_name", ""),
        "ch_num": str(ch_num),
        "characters": characters[:1500],
        "guide": guide[:2000] if guide != "（无章纲）" else "（无章纲，自由发挥）",
        "prev_context": prev_context if prev_context else "（第一章，无前文）",
        "reason": reason if reason else "（无具体原因，整章重写）",
    }
    
    # 替换变量
    prompt = safe_format(prompt_template, variables)
    
    # 调用 LLM
    try:
        result = call_llm(config, "rewrite-chapter", prompt,
                         system_prompt="你是一个专业的小说写手。重写时必须解决上述问题，保持角色一致性。不要废话，直接写正文。",
                         max_tokens=4096)
        return result
    except Exception as e:
        print(f"    [ERROR] 重写失败: {e}")
        return None
