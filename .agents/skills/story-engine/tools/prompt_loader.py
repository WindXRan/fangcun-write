"""
统一 Prompt 加载器：Agent/API 双模式兼容。

设计原则：
- 同一套 prompt 文件，两种模式通用
- Agent 模式：prompt 原样返回，Agent 自行 Read 文件
- API 模式：自动解析 prompt 中的【标签】路径引用，将文件内容嵌入 prompt
- book_data.json: 如果 rewrites_dir 中存在，自动从中提取 {变量} 用于替换

文件引用规范（prompt 中使用）：
  【标签】相对/路径/文件.md   →  输入文件（会被嵌入）
  【输出】路径/文件.md         →  输出文件（保留路径，不嵌入）
  【模板】路径/模板.md         →  模板文件（会被嵌入）
"""

import os
import re
import sys
import json
from pathlib import Path

# 确保导入 story-engine 的 prompt_meta（而非 source-engine 的）
_story_engine_tools = str(Path(__file__).resolve().parent)
if _story_engine_tools not in sys.path:
    sys.path.insert(0, _story_engine_tools)
from prompt_meta import _parse_frontmatter, safe_format


# 需要嵌入内容的标签（输入类），不包含的标签只保留路径引用
EMBED_TAGS = {"源文", "弧线", "弧线参考", "设定", "新书设定", "plot_guide", "模板", "旧真相", "本章正文", "下章正文", "原文", "热梗素材", "频道配置", "题材配置", "爽点配置"}

# 不需要嵌入的标签（输出/指令类）
PASS_THROUGH_TAGS = {"输出", "回传"}

# 文件引用正则：【标签】路径（路径不含空格或含空格但合理）
FILE_REF_PATTERN = re.compile(r'【(.+?)】(.+?\.(?:md|txt|json|ps1))', re.MULTILINE)

# 配置目录（相对于 story-engine）
CONFIG_DIR = "config"


def resolve_path(base_dir, ref_path):
    """将 prompt 中的相对路径解析为绝对路径。"""
    p = Path(ref_path)
    if p.is_absolute():
        return p
    return (Path(base_dir) / ref_path).resolve()


def extract_file_refs(prompt_text):
    """从 prompt 中提取所有【标签】路径引用。
    返回 [(标签, 路径, 起始位置), ...]
    """
    refs = []
    for match in FILE_REF_PATTERN.finditer(prompt_text):
        tag = match.group(1).strip()
        path = match.group(2).strip()
        refs.append((tag, path, match.start(), match.end()))
    return refs


def load_file_content(file_path):
    """安全读取文件内容。"""
    try:
        p = Path(file_path)
        if p.exists():
            return p.read_text(encoding='utf-8')
        return f"[文件不存在: {file_path}]"
    except Exception as e:
        return f"[读取失败: {file_path} — {e}]"


def load_book_data(rewrites_dir):
    """加载 book_data.json，返回 dict 或 None。"""
    if not rewrites_dir:
        return None
    path = Path(rewrites_dir) / "book_data.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] book_data.json 读取失败: {e}")
        return None


def load_channel_config(channel="female"):
    """加载频道配置（女频/男频）。"""
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "config" / "channel" / f"{channel}.json"
    if not config_path.exists():
        print(f"  [WARN] 频道配置不存在: {config_path}")
        return {}
    try:
        return json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] 频道配置读取失败: {e}")
        return {}


def make_channel_replacements(channel="female"):
    """从频道配置构建 {变量} → 值 的替换映射。"""
    config = load_channel_config(channel)
    if not config:
        return {}
    replacements = {}
    replacements["channel"] = config.get("channel", "未知")
    replacements["highlights"] = "、".join(config.get("highlights", []))
    replacements["conflict_priorities"] = "、".join(config.get("conflict_priorities", []))
    rhythm = config.get("rhythm", {})
    rhythm_parts = [f"{k}{v}%" for k, v in rhythm.items()]
    replacements["rhythm"] = " / ".join(rhythm_parts)
    return replacements


def make_book_data_replacements(book_data):
    """从 book_data.json 构建 {变量} → 值 的替换映射。"""
    replacements = {}
    if not book_data:
        return replacements
    char_vars = book_data.get("meta", {}).get("character_variables", {})
    replacements.update(char_vars)
    book_info = book_data.get("book_info", {})
    if book_info.get("name") and "新书名" not in replacements:
        replacements["新书名"] = book_info["name"]
    if book_info.get("author") and "作者名" not in replacements:
        replacements["作者名"] = book_info["author"]
    return replacements


def embed_files(prompt_text, base_dir, extra_replacements=None):
    """将 prompt 中引用的文件内容嵌入。"""
    if extra_replacements:
        prompt_text = safe_format(prompt_text, extra_replacements)

    refs = extract_file_refs(prompt_text)
    result = prompt_text
    for tag, path, start, end in reversed(refs):
        if tag in EMBED_TAGS or any(tag.startswith(p) for p in EMBED_TAGS):
            abs_path = resolve_path(base_dir, path)
            content = load_file_content(abs_path)
            replacement = (
                f"【{tag}】{path}\n"
                f"<!-- {tag}_content START -->\n"
                f"{content}\n"
                f"<!-- {tag}_content END -->"
            )
            result = result[:start] + replacement + result[end:]
    return result


def load_prompt(prompt_path, base_dir, replacements=None, mode="agent", rewrites_dir=None):
    """统一入口：加载 prompt，支持 agent/api 双模式 + 品类级联。

    Args:
        prompt_path: prompt 文件路径
        base_dir: 项目根目录
        replacements: {变量名: 值} 字典
        mode: "agent" | "api"
        rewrites_dir: 仿写项目目录，用于自动加载 book_data.json 中的变量

    Returns:
        str: 处理后的 prompt 文本
    """
    prompt_file = resolve_path(base_dir, prompt_path)
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_file}")

    raw_text = prompt_file.read_text(encoding='utf-8')
    _, raw_text = _parse_frontmatter(raw_text)

    merged = {}
    if rewrites_dir:
        book_data = load_book_data(rewrites_dir)
        merged = make_book_data_replacements(book_data)
    if replacements:
        merged.update(replacements)

    if mode == "api":
        user_prompt = embed_files(raw_text, base_dir, merged)
    else:
        user_prompt = raw_text
        if merged:
            user_prompt = safe_format(user_prompt, merged)

    return user_prompt
