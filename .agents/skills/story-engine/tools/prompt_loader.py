"""
统一 Prompt 加载器：Agent/API 双模式兼容。

设计原则：
- 同一套 prompt 文件，两种模式通用
- Agent 模式：prompt 原样返回，Agent 自行 Read 文件
- API 模式：自动解析 prompt 中的【标签】路径引用，将文件内容嵌入 prompt
- book_data.json: 如果 rewrites_dir 中存在，自动从中提取 {变量} 用于替换
- config/: 配置驱动，根据 channel/genre/pleasure 加载对应配置

文件引用规范（prompt 中使用）：
  【标签】相对/路径/文件.md   →  输入文件（会被嵌入）
  【输出】路径/文件.md         →  输出文件（保留路径，不嵌入）
  【模板】路径/模板.md         →  模板文件（会被嵌入）
"""

import re
import os
import json
from pathlib import Path


# 需要嵌入内容的标签（输入类），不包含的标签只保留路径引用
EMBED_TAGS = {"源文", "弧线", "弧线参考", "设定", "新书设定", "plot_guide", "模板", "旧真相", "本章正文", "下章正文", "原文", "样板库", "热梗素材", "频道配置", "题材配置", "爽点配置"}

# 不需要嵌入的标签（输出/指令类）
PASS_THROUGH_TAGS = {"输出", "回传"}

# 文件引用正则：【标签】路径（路径不含空格或含空格但合理）
FILE_REF_PATTERN = re.compile(r'【(.+?)】(.+?\.(?:md|txt|json|ps1))', re.MULTILINE)

# 配置目录（相对于 story-engine）
CONFIG_DIR = "config"

# 品类级联警告缓存（防并行刷屏）
_cascade_warned = set()


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
    """加载 book_data.json，返回 dict 或 None。
    
    book_data.json 由 extract_book_data.py 从 settings/*.md 提取生成。
    包含 meta.character_variables 等可直接用于 prompt 替换的数据。
    """
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
    """加载频道配置（女频/男频）。
    
    配置文件位置：.agents/skills/story-engine/config/channel/{channel}.json
    """
    base_dir = Path(__file__).parent.parent  # story-engine 目录
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
    """从频道配置构建 {变量} → 值 的替换映射。
    
    用于注入到 prompt 中，让 AI 知道当前频道的偏好。
    """
    config = load_channel_config(channel)
    if not config:
        return {}
    
    replacements = {}
    replacements["channel"] = config.get("channel", "未知")
    replacements["highlights"] = "、".join(config.get("highlights", []))
    replacements["conflict_priorities"] = "、".join(config.get("conflict_priorities", []))
    
    # 节奏比例
    rhythm = config.get("rhythm", {})
    rhythm_parts = [f"{k}{v}%" for k, v in rhythm.items()]
    replacements["rhythm"] = " / ".join(rhythm_parts)
    
    return replacements


def make_book_data_replacements(book_data):
    """从 book_data.json 构建 {变量} → 值 的替换映射。
    
    优先级：
    1. meta.character_variables（{男主名}, {女主名} 等）
    2. 后续可扩展（书名、作者等）
    """
    replacements = {}
    if not book_data:
        return replacements
    
    # 角色变量（最高优先级）
    char_vars = book_data.get("meta", {}).get("character_variables", {})
    replacements.update(char_vars)
    
    # book_info 字段（低优先级，不覆盖已有值）
    book_info = book_data.get("book_info", {})
    if book_info.get("name") and "新书名" not in replacements:
        replacements["新书名"] = book_info["name"]
    if book_info.get("author") and "作者名" not in replacements:
        replacements["作者名"] = book_info["author"]
    if book_info.get("genre") and "题材" not in replacements:
        replacements["题材"] = book_info["genre"]
    
    return replacements


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
        if tag in EMBED_TAGS or any(tag.startswith(p) for p in EMBED_TAGS):
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


def load_prompt(prompt_path, base_dir, replacements=None, mode="agent", rewrites_dir=None):
    """
    统一入口：加载 prompt，支持 agent/api 双模式 + 品类级联。

    Args:
        prompt_path: prompt 文件路径（相对于 base_dir 或绝对路径）
        base_dir: 项目根目录
        replacements: {变量名: 值} 字典，可含 "genre" 字段触发品类级联
        mode: "agent" | "api"
        rewrites_dir: 仿写项目目录，用于自动加载 book_data.json 中的变量

    Returns:
        (system_prompt, user_prompt) 元组

    Agent 模式：返回原始 prompt（agent 自己读文件）
    API 模式：嵌入所有引用文件的内容

    品类级联（已弃用，保留代码兼容）：
        如果 prompts/write-chapter.{genre}.md 存在会追加，但我们现在不维护品类文件。
        品类差异靠 {源文全文} 直接喂给 LLM，不靠手写规则。
    """
    prompt_file = resolve_path(base_dir, prompt_path)

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_file}")

    raw_text = prompt_file.read_text(encoding='utf-8')
    # 去掉 frontmatter
    _, raw_text = _parse_frontmatter(raw_text)

    # 品类级联：加载通用文件后，追加品类特化文件
    genre = (replacements or {}).get("genre", "")
    if genre:
        genre_file = prompt_file.with_name(f"{prompt_file.stem}.{genre}{prompt_file.suffix}")
        if genre_file.exists():
            genre_text = genre_file.read_text(encoding='utf-8')
            raw_text += "\n\n" + genre_text
        else:
            # 品类文件不存在时仅首次警告
            global _cascade_warned
            if genre not in _cascade_warned:
                _cascade_warned.add(genre)
                print(f"  [CASCADE] 品类文件 {genre_file.name} 不存在，使用通用 prompt")

    # 合并 book_data.json 的变量（低优先级，不覆盖传入的 replacements）
    merged = {}
    if rewrites_dir:
        book_data = load_book_data(rewrites_dir)
        merged = make_book_data_replacements(book_data)
    if replacements:
        merged.update(replacements)

    if mode == "api":
        # API 模式：嵌入文件内容
        user_prompt = embed_files(raw_text, base_dir, merged)
    else:
        # Agent 模式：只做变量替换
        user_prompt = raw_text
        if merged:
            for key, value in merged.items():
                user_prompt = user_prompt.replace(f'{{{key}}}', str(value))

    # system prompt 由调用方提供，或从 prompt 中分离
    return user_prompt


_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


def _parse_frontmatter(text):
    """解析 YAML frontmatter，返回 (meta: dict, body: str)。

    meta 至少包含 version (int) 和 changelog (str)。
    其他字段（type/phase/required_vars/defaults 等）按 JSON 解析。
    """
    meta = {"version": 1, "changelog": ""}
    m = _FRONTMATTER_RE.match(text)
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


def _make_tag(name, version):
    return f"<!-- prompt: {name}@{version} -->"


def load_system_prompt(name):
    """加载 prompts/ 目录下的系统 prompt 文件。返回去掉 frontmatter 的正文。"""
    p = _PROMPTS_DIR / name
    if not p.exists():
        return ""
    _, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
    return body.strip()


def load_prompt_str(name, with_tag=False):
    """从 prompts/ 按名加载 prompt，去掉 frontmatter。

    Args:
        name: 文件名（如 "write-chapter.md"）
        with_tag: 是否在末尾追加版本 tag

    Returns:
        body (str) 或 (body, version) 元组（如果 with_tag=True）
    """
    p = _PROMPTS_DIR / name
    if not p.exists():
        return ("", 0) if with_tag else ""
    meta, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
    if with_tag:
        return body.strip(), meta["version"]
    return body.strip()


def get_prompt_meta(name):
    """读取 prompts/{name} 文件的 frontmatter，返回 meta 字典。"""
    p = _PROMPTS_DIR / name
    if not p.exists():
        return {}
    meta, _ = _parse_frontmatter(p.read_text(encoding="utf-8"))
    return meta


def validate_prompt_variables(name, replacements):
    """校验 prompt 所需变量是否已提供，缺失则 fail fast。

    从 prompt 文件的 frontmatter 读取 required_vars，
    对照 replacements 检查，缺的报错。
    """
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
    """返回 prompt 文件 frontmatter 中的默认调用参数。

    可在 config.json 的 prompt_overrides 中按 prompt 名覆盖。
    覆盖优先级: config.prompt_overrides > frontmatter.defaults > 代码级默认值（由调用方处理）
    """
    meta = get_prompt_meta(name)
    return dict(meta.get("defaults", {}))


def get_prompt_config_with_overrides(name, config):
    """读取 prompt 默认调用参数，合并 config.json 的 prompt_overrides 覆盖。"""
    cfg = get_prompt_config(name)
    overrides = (config or {}).get("prompt_overrides", {}).get(name, {})
    cfg.update(overrides)
    return cfg


def get_system_prompt_name(user_prompt_name):
    """返回 prompt 文件 frontmatter 中关联的 system prompt 文件名。
    
    如果未配置，返回 None。
    """
    meta = get_prompt_meta(user_prompt_name)
    return meta.get("system_prompt")


def get_prompt_version(name):
    """读取 prompts/{name} 文件的 frontmatter，返回 version 号。"""
    return get_prompt_meta(name).get("version", 0)


def prompt_tag(name):
    """生成 HTML 注释格式的版本 tag。"""
    return _make_tag(name, get_prompt_version(name))


def tag_output(content, prompt_name):
    """给输出内容末尾追加 prompt 版本 tag。

    Args:
        content: 原始输出内容
        prompt_name: prompt 文件名（如 "write-chapter.md"）

    Returns:
        末尾追加了版本 tag 的内容
    """
    tag = _make_tag(prompt_name, get_prompt_version(prompt_name))
    return content.rstrip("\n") + "\n" + tag + "\n"


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


def _get_git_diff_summary(path):
    """自动提取 prompt 的 git diff 摘要作为 changelog。

    只统计 frontmatter 之外的实质内容变化，跳过版本号变更。
    变化行少时展示具体变化，变化多时只统计行数。
    """
    try:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--unified=1", "--", str(path)],
            capture_output=True, text=True, encoding="utf-8",
        )
        diff = result.stdout.strip()
        if not diff:
            return ""
        # 解析 hunk，跳过 frontmatter（第一个 `---` 之前的内容）
        lines = diff.splitlines()

        # 收集真实 +/- 行（跳过 hunk header、---/+++、和 frontmatter）
        plus, minus = [], []
        in_content = False
        for l in lines:
            if l.startswith('@@'):
                in_content = True
                continue
            if not in_content:
                continue
            if l.startswith('+++') or l.startswith('---'):
                continue
            if l.startswith('+') and not l.startswith('+++'):
                plus.append(l[1:])
            elif l.startswith('-') and not l.startswith('---'):
                minus.append(l[1:])

        total_changed = max(len(plus), len(minus))
        if total_changed <= 4:
            parts = []
            if minus:
                parts.append(f"删: {minus[0][:80]}")
            if plus:
                parts.append(f"加: {plus[0][:80]}")
            return "自动diff: " + " | ".join(parts) if parts else ""
        # 太多变化，统计行数
        # 猜测变更类型
        p_sum = sum(len(l) for l in plus)
        m_sum = sum(len(l) for l in minus)
        return f"自动diff: +{len(plus)}/-{len(minus)} 行 (+{p_sum}/-{m_sum} 字符) 请见 git diff"
    except Exception:
        return ""


def bump_prompt_version(name, changelog_msg=""):
    """递增 prompt 版本号 + 自动记录 diff。

    不传 changelog_msg 时自动从 git diff 生成 changelog。

    Args:
        name: 文件名（如 "write-chapter.md"）
        changelog_msg: 可选，手动描述的变更说明

    Returns:
        (旧版本, 新版本) 元组，文件不存在返回 (0, 0)
    """
    p = _PROMPTS_DIR / name
    if not p.exists():
        print(f"[WARN] prompt 文件不存在: {name}")
        return 0, 0

    # 自动生成 changelog
    if not changelog_msg:
        changelog_msg = _get_git_diff_summary(p)
        if not changelog_msg:
            changelog_msg = "版本更新"

    text = p.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        new_text = f"---\nversion: 1\nchangelog: {changelog_msg}\n---\n\n{text}"
        p.write_text(new_text, encoding="utf-8")
        print(f"[OK] {name}: 添加 frontmatter, version=1")
        return 0, 1

    old_version = 1
    new_lines = []
    changed = False
    for line in m.group(1).split('\n'):
        if line.startswith("version:"):
            try:
                old_version = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            new_lines.append(f"version: {old_version + 1}")
            changed = True
        elif line.startswith("changelog:"):
            new_lines.append(f"changelog: {changelog_msg}")
            changed = True
        else:
            new_lines.append(line)

    if not changed:
        new_lines.append(f"version: {old_version + 1}")
        new_lines.append(f"changelog: {changelog_msg}")

    new_frontmatter = '\n'.join(new_lines)
    new_text = f"---\n{new_frontmatter}\n---\n{text[m.end():]}"
    p.write_text(new_text, encoding="utf-8")
    print(f"[OK] {name}: {old_version} → {old_version + 1}")
    if changelog_msg:
        print(f"  changelog: {changelog_msg}")
    return old_version, old_version + 1


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "bump":
        name = sys.argv[2]
        msg = sys.argv[3] if len(sys.argv) > 3 else ""
        bump_prompt_version(name, msg)
    elif len(sys.argv) >= 2:
        base = os.getcwd()
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
    else:
        print("用法: python prompt_loader.py <prompt_path> [mode=api|agent]")
        print("  或: python prompt_loader.py bump <prompt_name> [changelog_msg]")
