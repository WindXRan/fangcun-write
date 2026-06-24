"""
writer.py - 通用写作模块
提供 write/trim/expand/polish/rewrite 功能
"""

import os
import re
import sys
from pathlib import Path

# 全局缓存system prompt，避免重复读取文件
_system_prompt_cache = {}

def _get_system_prompt(system_prompt_path):
    """获取system prompt（带缓存）"""
    if system_prompt_path not in _system_prompt_cache:
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, encoding='utf-8') as f:
                _system_prompt_cache[system_prompt_path] = f.read()
        else:
            _system_prompt_cache[system_prompt_path] = None
    return _system_prompt_cache[system_prompt_path]


def _call_llm(config, prompt, system_prompt=None):
    """调用 LLM API（支持prefix caching）"""
    import requests
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY")
    
    api_url = config.get("api_base_url", "https://api.deepseek.com/v1") + "/chat/completions"
    model = config.get("model", "deepseek-chat")
    
    # DeepSeek prefix caching: 相同的system prompt会自动缓存
    # 确保system prompt在最前面，user prompt结构一致
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 4096,
        "stream": False
    }
    
    resp = requests.post(api_url, headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def write_chapter(config, ch, mode="imitation", auto_fix=True):
    """写章。调用 LLM 生成正文。"""
    from prompt_loader import load_prompt
    from phases.guides_name import _build_name_map_text, _load_character_cards
    
    rewrites_dir = config.get("rewrites_dir", "")
    base_dir = config.get("base_dir", ".")
    
    # 构建替换变量
    replacements = {
        "N": str(ch),
        "N03d": f"{ch:03d}",
        "新书名": Path(rewrites_dir).name,
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }
    
    # 注入 name_map（从 characters.md 提取）
    try:
        name_map_text = _build_name_map_text(config)
        if name_map_text:
            replacements["name_map"] = name_map_text
    except Exception as e:
        print(f"  [WARN] name_map 注入失败: {e}")
    
    # 注入角色卡（只注入本章出场角色，对齐 events.json）
    try:
        char_cards = _load_character_cards(config, ch)
        replacements["characters"] = char_cards or "（无角色信息）"
    except Exception as e:
        print(f"  [WARN] 角色卡注入失败: {e}")
    except Exception as e:
        print(f"  [WARN] 角色卡注入失败: {e}")

    # 注入字数目标（基于源文字数）
    try:
        from utils import get_source_text
        src = get_source_text(config, ch)
        if src:
            src_chars = len(src.replace("\n", "").replace(" ", "").replace("\r", ""))
        else:
            src_chars = config.get("target_word_count", 2500)
        target = max(int(src_chars), 1500) if src_chars else 2500
        replacements.setdefault("目标字数", str(target))
        replacements.setdefault("目标字数_min", str(int(target * 0.8)))
        replacements.setdefault("目标字数_max", str(int(target * 1.2)))
    except Exception:
        replacements.setdefault("目标字数", "2500")
        replacements.setdefault("目标字数_min", "2000")
        replacements.setdefault("目标字数_max", "3000")
    
    # 加载 prompt
    prompts_dir = config.get("prompts_dir", ".agents/skills/fangcun-write/prompts")
    prompt_path = f"{prompts_dir}/write-chapter.md"
    try:
        user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=rewrites_dir)
    except Exception as e:
        raise Exception(f"加载 prompt 失败: {e}")
    
    # 加载系统提示词：文风分析优先（源文风格对标），带缓存省 token
    analyze_dir = config.get("analyze_dir", "")
    style_prompt = None

    # 1. 拆文库文风分析（最佳）
    if analyze_dir:
        sp = Path(analyze_dir) / "文风分析.md"
        if sp.exists():
            key = str(sp)
            if key not in _system_prompt_cache:
                _system_prompt_cache[key] = sp.read_text(encoding="utf-8")
            style_prompt = _system_prompt_cache[key]

    # 2. 自动生成的文笔指纹（次选）
    if not style_prompt:
        sp = Path(rewrites_dir) / "book_style_profile.md"
        if sp.exists():
            key = str(sp)
            if key not in _system_prompt_cache:
                _system_prompt_cache[key] = sp.read_text(encoding="utf-8")
            style_prompt = _system_prompt_cache[key]

    # 3. 通用 agent（兜底）
    system_prompt = style_prompt or _get_system_prompt(f"{prompts_dir}/agent.md")
    
    # 通过统一 API 入口调用（自动处理 debug 和 prompts_only）
    from lib.api_client import call_llm
    result = call_llm(config, "write-chapter", user_prompt, system_prompt=system_prompt, ch=ch)
    
    # prompts_only 模式返回占位符，不继续处理
    if config.get("prompts_only"):
        return result

    # 提取正文（去掉可能的 XML 标签）
    import re
    m = re.search(r'<chapter>([\s\S]*?)</chapter>', result)
    if m:
        result = m.group(1).strip()
    
    return result


def _load_chapter_text(config, ch):
    """加载章节文本。"""
    from pathlib import Path
    rewrites_dir = config.get("rewrites_dir", "")
    ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        raise FileNotFoundError(f"章节文件不存在: {ch_file}")
    return ch_file.read_text(encoding='utf-8')


def _save_chapter_text(config, ch, text):
    """保存章节文本。"""
    from pathlib import Path
    rewrites_dir = config.get("rewrites_dir", "")
    ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
    ch_file.parent.mkdir(parents=True, exist_ok=True)
    ch_file.write_text(text, encoding='utf-8')


def _call_llm_with_prompt(config, prompt_type, user_prompt, system_prompt=None, ch=None):
    """调用 LLM API（使用统一的 api_client）。"""
    try:
        from lib.api_client import call_llm
        return call_llm(config, prompt_type, user_prompt, system_prompt=system_prompt, ch=ch)
    except ImportError:
        # fallback: 直接调用 _call_llm
        return _call_llm(config, user_prompt, system_prompt)


def trim_chapter(config, ch, mode="imitation"):
    """精简章节（字数超标时调用）。目标：减少 20-30% 字数，保留核心情节。"""
    text = _load_chapter_text(config, ch)
    current_chars = len(text.replace('\n', '').replace(' ', ''))
    target_chars = int(current_chars * 0.75)
    
    prompt = f"""请精简以下章节内容，目标字数约{target_chars}字（当前{current_chars}字）。

要求：
1. 保留核心情节和关键对话
2. 删除冗余描写和重复内容
3. 合并相似段落
4. 保持故事连贯性

章节内容：
{text}"""
    
    result = _call_llm_with_prompt(config, "trim-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


def expand_chapter(config, ch, mode="imitation"):
    """扩写章节（字数不足时调用）。目标：增加 30-50% 字数。"""
    text = _load_chapter_text(config, ch)
    current_chars = len(text.replace('\n', '').replace(' ', ''))
    target_chars = int(current_chars * 1.4)
    
    prompt = f"""请扩写以下章节内容，目标字数约{target_chars}字（当前{current_chars}字）。

要求：
1. 增加环境描写和心理描写
2. 丰富对话内容和互动细节
3. 补充情节过渡和铺垫
4. 保持原有故事框架不变

章节内容：
{text}"""
    
    result = _call_llm_with_prompt(config, "expand-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


def polish_chapter(config, ch, text=None, issue=""):
    """润色章节。改进文笔，不改情节。"""
    if text is None:
        text = _load_chapter_text(config, ch)
    
    issue_hint = f"\n特别注意修正以下问题：{issue}" if issue else ""
    
    prompt = f"""请润色以下章节内容，改进文笔质量。

要求：
1. 保持情节和对话内容不变
2. 优化句式结构，避免单调
3. 改善用词，增强表现力
4. 调整节奏，增强可读性
5. 减少AI痕迹（如过于工整的排比、模式化表达）{issue_hint}

章节内容：
{text}"""
    
    result = _call_llm_with_prompt(config, "polish-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


def rewrite_chapter(config, ch, mode="imitation", reason=""):
    """重写章节。保留章纲，重新生成正文。"""
    from pathlib import Path
    rewrites_dir = config.get("rewrites_dir", "")
    
    # 加载章纲
    guide_file = Path(rewrites_dir) / "guides" / f"plot_{ch}.md"
    guide_text = ""
    if guide_file.exists():
        guide_text = guide_file.read_text(encoding='utf-8')
    
    reason_hint = f"\n重写原因：{reason}" if reason else ""
    
    prompt = f"""请根据以下章纲重写第{ch}章正文。

要求：
1. 严格按照章纲的场景设计写作
2. 实现章纲中的关键台词和情节
3. 保持故事连贯性
4. 目标字数：2000-3000字{reason_hint}

章纲：
{guide_text}"""
    
    result = _call_llm_with_prompt(config, "rewrite-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result
