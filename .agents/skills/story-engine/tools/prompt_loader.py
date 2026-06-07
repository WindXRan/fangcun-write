"""
统一 Prompt 加载器：Agent/API 双模式兼容。

设计原则：
- 同一套 prompt 文件，两种模式通用
- Agent 模式：prompt 原样返回，Agent 自行 Read 文件
- API 模式：自动解析 prompt 中的【标签】路径引用，将文件内容嵌入 prompt

文件引用规范（prompt 中使用）：
  【标签】相对/路径/文件.md    →  输入文件（会被嵌入）
  【输出】路径/文件.md         →  输出文件（保留路径，不嵌入）
  【模板】路径/模板.md         →  模板文件（会被嵌入）
"""

import re
import os
from pathlib import Path


# 需要嵌入内容的标签（输入类），不包含的标签只保留路径引用
EMBED_TAGS = {"源文", "弧线", "弧线参考", "设定", "新书设定", "风格数据", "plot_guide", "style_guide", "模板", "旧真相", "本章正文", "下章正文", "原文"}

# 不需要嵌入的标签（输出/指令类）
PASS_THROUGH_TAGS = {"输出", "回传"}

# 文件引用正则：【标签】路径（路径不含空格或含空格但合理）
FILE_REF_PATTERN = re.compile(r'【(.+?)】(.+?\.(?:md|txt|json|ps1))', re.MULTILINE)


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


def embed_files(prompt_text, base_dir, extra_replacements=None):
    """
    将 prompt 中引用的文件内容嵌入。

    对每个【标签】路径引用：
    - 如果标签在 EMBED_TAGS 中 → 读取文件，替换为【标签_content】...【/标签_content】
    - 否则保留原样

    Args:
        prompt_text: 原始 prompt 模板
        base_dir: 项目根目录（用于解析相对路径）
        extra_replacements: 额外的 {key: value} 替换

    Returns:
        嵌入文件内容后的 prompt
    """
    # 先做变量替换（{新书名}, {N} 等）
    if extra_replacements:
        for key, value in extra_replacements.items():
            prompt_text = prompt_text.replace(f'{{{key}}}', str(value))

    refs = extract_file_refs(prompt_text)

    # 从后往前替换，避免位置偏移
    result = prompt_text
    for tag, path, start, end in reversed(refs):
        if tag in EMBED_TAGS:
            abs_path = resolve_path(base_dir, path)
            content = load_file_content(abs_path)

            # 构建替换文本
            replacement = (
                f"【{tag}】{path}\n"
                f"<!-- {tag}_content START -->\n"
                f"{content}\n"
                f"<!-- {tag}_content END -->"
            )
            result = result[:start] + replacement + result[end:]

    return result


def load_prompt(prompt_path, base_dir, replacements=None, mode="agent"):
    """
    统一入口：加载 prompt，支持 agent/api 双模式。

    Args:
        prompt_path: prompt 文件路径（相对于 base_dir 或绝对路径）
        base_dir: 项目根目录
        replacements: {变量名: 值} 字典
        mode: "agent" | "api"

    Returns:
        (system_prompt, user_prompt) 元组

    Agent 模式：返回原始 prompt（agent 自己读文件）
    API 模式：嵌入所有引用文件的内容
    """
    prompt_file = resolve_path(base_dir, prompt_path)

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_file}")

    raw_text = prompt_file.read_text(encoding='utf-8')

    if mode == "api":
        # API 模式：嵌入文件内容
        user_prompt = embed_files(raw_text, base_dir, replacements)
    else:
        # Agent 模式：只做变量替换
        user_prompt = raw_text
        if replacements:
            for key, value in replacements.items():
                user_prompt = user_prompt.replace(f'{{{key}}}', str(value))

    # system prompt 由调用方提供，或从 prompt 中分离
    return user_prompt


def get_output_path(prompt_text, replacements=None):
    """
    从 prompt 中提取【输出】路径。
    用于确定生成内容的保存位置。
    """
    # 先替换变量
    text = prompt_text
    if replacements:
        for key, value in replacements.items():
            text = text.replace(f'{{{key}}}', str(value))

    match = re.search(r'【输出】(.+?)(?:\n|$)', text)
    if match:
        return match.group(1).strip()
    return None


# ============================================================
# 测试
# ============================================================
if __name__ == '__main__':
    import sys
    base = os.getcwd()

    if len(sys.argv) < 2:
        print("用法: python prompt_loader.py <prompt_path> [mode=api|agent]")
        sys.exit(1)

    prompt_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "api"

    result = load_prompt(
        prompt_path, base,
        replacements={"新书名": "测试书", "N": "1", "作者名": "测试作者", "源书名": "测试源文"},
        mode=mode
    )
    print(f"=== Mode: {mode} ===")
    print(result[:3000])
    if len(result) > 3000:
        print(f"\n... (总长 {len(result)} 字符)")
