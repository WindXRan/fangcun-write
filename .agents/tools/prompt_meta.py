"""Prompt 元数据：frontmatter 解析 + meta 访问 + 基础加载。"""

import os
import re
import json
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def parse_frontmatter(text):
    """解析 YAML frontmatter，返回 (meta: dict, body: str)。

    meta 至少包含 version (int) 和 changelog (str)。
    其他字段（type/phase/required_vars/defaults 等）按 JSON 解析。
    """
    if text.startswith('\ufeff'):
        text = text[1:]
    meta = {"version": 1, "changelog": ""}
    m = FRONTMATTER_RE.match(text)
    if not m:
        return meta, text
    body = text[m.end():]
    for line in m.group(1).split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        key, _, val = line.partition(':')
        key = key.strip()
        val = val.strip()
        if key == "version":
            try:
                meta["version"] = int(val)
            except ValueError:
                pass
        elif key == "changelog":
            meta["changelog"] = val
        elif val.startswith('[') or val.startswith('{'):
            try:
                meta[key] = json.loads(val)
            except json.JSONDecodeError:
                meta[key] = val
        elif val in ("true", "false"):
            meta[key] = val == "true"
        else:
            meta[key] = val
    return meta, body


def safe_format(text: str, replacements: dict) -> str:
    """安全替换 {key} 变量，不触发 .format() 的 KeyError/IndexError。"""
    for key, value in replacements.items():
        text = text.replace(f'{{{key}}}', str(value))
    return text


def load_system_prompt(name, visited=None):
    """加载 prompts/ 目录下的系统 prompt 文件，递归解析 system_prompt 链。"""
    if visited is None:
        visited = set()
    if name in visited:
        return ""
    visited.add(name)
    p = PROMPTS_DIR / name
    if not p.exists():
        return ""
    meta, body = parse_frontmatter(p.read_text(encoding="utf-8"))
    parent = meta.get("system_prompt", "")
    if parent:
        parent_body = load_system_prompt(parent, visited)
        if parent_body:
            return parent_body + "\n\n" + body.strip()
    return body.strip()


def load_prompt_str(name, with_tag=False):
    """从 tasks/ 或 prompts/ 按名加载 prompt，去掉 frontmatter。"""
    # 优先 tasks/
    p = TASKS_DIR / name
    if not p.exists():
        p = PROMPTS_DIR / name
    if not p.exists():
        return ("", 0) if with_tag else ""
    meta, body = parse_frontmatter(p.read_text(encoding="utf-8"))
    if with_tag:
        return body.strip(), meta["version"]
    return body.strip()


def get_prompt_meta(name):
    """读取 prompt 文件的 frontmatter，返回 meta 字典。"""
    p = TASKS_DIR / name
    if not p.exists():
        p = PROMPTS_DIR / name
    if not p.exists():
        return {}
    meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
    return meta


def validate_prompt_variables(name, replacements):
    """校验 prompt 所需变量是否已提供，缺失则 fail fast。"""
    meta = get_prompt_meta(name)
    required = meta.get("required_vars", [])
    if not required:
        return
    missing = [v for v in required if v not in (replacements or {})]
    if missing:
        raise ValueError(
            f"[PROMPT] {name} 缺少必要变量: {', '.join(missing)}\n"
            f"  required: {required}\n"
            f"  provided: {list((replacements or {}).keys())}"
        )


def get_prompt_config(name):
    """返回 prompt 文件 frontmatter 中的默认调用参数。"""
    meta = get_prompt_meta(name)
    return dict(meta.get("defaults", {}))


def get_prompt_config_with_overrides(name, config):
    """读取 prompt 默认调用参数，合并 config.json 的 prompt_overrides 覆盖。"""
    cfg = get_prompt_config(name)
    overrides = (config or {}).get("prompt_overrides", {}).get(name, {})
    cfg.update(overrides)
    return cfg


def get_system_prompt_name(user_prompt_name):
    """返回 prompt 文件 frontmatter 中关联的 system prompt 文件名。"""
    meta = get_prompt_meta(user_prompt_name)
    return meta.get("system_prompt")


def get_prompt_version(name):
    """读取 prompts/{name} 文件的 frontmatter，返回 version 号。"""
    return get_prompt_meta(name).get("version", 0)
