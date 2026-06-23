"""
writer.py - 通用写作模块
提供 write/trim/expand/polish/rewrite 功能
"""

import os
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
    
    # 加载 prompt
    prompt_path = ".agents/skills/fangcun-novel/prompts/write-chapter.md"
    try:
        user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=rewrites_dir)
    except Exception as e:
        raise Exception(f"加载 prompt 失败: {e}")
    
    # 加载系统提示词（使用缓存）
    system_prompt_path = ".agents/skills/fangcun-novel/prompts/agent.md"
    system_prompt = _get_system_prompt(system_prompt_path)
    
    # 调用 LLM
    result = _call_llm(config, user_prompt, system_prompt)
    
    # 提取正文（去掉可能的 XML 标签）
    import re
    m = re.search(r'<chapter>([\s\S]*?)</chapter>', result)
    if m:
        result = m.group(1).strip()
    
    return result


def trim_chapter(config, ch, mode="imitation"):
    """精简章节（字数超标时调用）。"""
    # TODO: 实现精简逻辑
    return None


def expand_chapter(config, ch, mode="imitation"):
    """扩写章节（字数不足时调用）。"""
    # TODO: 实现扩写逻辑
    return None


def polish_chapter(config, ch, text, issue=""):
    """润色章节。"""
    # TODO: 实现润色逻辑
    return None


def rewrite_chapter(config, ch, mode="imitation"):
    """重写章节。"""
    # TODO: 实现重写逻辑
    return None
