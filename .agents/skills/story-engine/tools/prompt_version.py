"""Prompt 版本管理：tag 生成 + 版本 bump + CLI 入口。"""

import os
import re
import subprocess
from pathlib import Path

import _path_setup  # noqa: F401
from prompt_meta import _PROMPTS_DIR, _FRONTMATTER_RE, get_prompt_version


def _make_tag(name, version):
    return f"<!-- prompt: {name}@{version} -->"


def prompt_tag(name):
    """生成 HTML 注释格式的版本 tag。"""
    return _make_tag(name, get_prompt_version(name))


def tag_output(content, prompt_name):
    """给输出内容末尾追加 prompt 版本 tag。"""
    tag = _make_tag(prompt_name, get_prompt_version(prompt_name))
    return content.rstrip("\n") + "\n" + tag + "\n"


def get_output_path(prompt_text, replacements=None):
    """从 prompt 中提取【输出】路径。"""
    text = prompt_text
    if replacements:
        from prompt_meta import safe_format
        text = safe_format(text, replacements)
    match = re.search(r'【输出】(.+?)(?:\n|$)', text)
    if match:
        return match.group(1).strip()
    return None


def _get_git_diff_summary(path):
    """自动提取 prompt 的 git diff 摘要作为 changelog。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=1", "--", str(path)],
            capture_output=True, text=True, encoding="utf-8",
        )
        diff = result.stdout.strip()
        if not diff:
            return ""
        lines = diff.splitlines()
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
        p_sum = sum(len(l) for l in plus)
        m_sum = sum(len(l) for l in minus)
        return f"自动diff: +{len(plus)}/-{len(minus)} 行 (+{p_sum}/-{m_sum} 字符) 请见 git diff"
    except Exception:
        return ""


def bump_prompt_version(name, changelog_msg=""):
    """递增 prompt 版本号 + 自动记录 diff。

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
        from prompt_loader import load_prompt
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
        print("用法: python prompt_version.py <prompt_path> [mode=api|agent]")
        print("  或: python prompt_version.py bump <prompt_name> [changelog_msg]")
