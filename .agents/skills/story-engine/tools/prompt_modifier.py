"""Prompt 自动修改器 — 根据 loop_engine 的建议自动调整 prompt 规则。

支持的操作:
  - 追加禁词到防AI列表
  - 追加禁词到情绪禁令
  - 强化某条规则（加粗/加⭐/加强调前缀）
  - Bump version + 记录 changelog

用法:
  python prompt_modifier.py --prompt system-generic.md --action add-emotion-ban --words "心揪,发紧"
  python prompt_modifier.py --prompt write-chapter.md --action strengthen --rule "段尾冲击"
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _read_prompt(name):
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt 不存在: {path}")
    return path.read_text(encoding="utf-8"), path


def _write_prompt(path, content):
    path.write_text(content, encoding="utf-8")


def _bump_version(content, changelog):
    """版本号 +1，追加 changelog。"""
    m = re.search(r'version:\s*(\d+)', content)
    if m:
        old_ver = int(m.group(1))
        content = content.replace(f"version: {old_ver}", f"version: {old_ver + 1}")

    # 追加 changelog
    cl_line = f"changelog: {changelog}"
    if re.search(r'changelog:', content):
        content = re.sub(r'changelog:.*', cl_line, content)
    else:
        # 在 version 后插入
        content = re.sub(r'(version:\s*\d+\n)', rf'\1{cl_line}\n', content)

    return content


def add_emotion_ban(name, words):
    """追加禁词到情绪禁令行。"""
    content, path = _read_prompt(name)

    # 找到情绪规则行
    pattern = r'(情绪[：:][^\n]+)'
    m = re.search(pattern, content)
    if m:
        line = m.group(1)
        # 检查是否已存在
        new_words = [w.strip() for w in words.split(",") if w.strip() not in line]
        if new_words:
            new_line = line.rstrip() + "/" + "/".join(new_words)
            content = content.replace(line, new_line)
    else:
        # 没有情绪规则行，在防AI后追加
        print(f"  [WARN] {name} 未找到情绪规则行，跳过")

    content = _bump_version(content, f"+情绪禁词: {words}")
    _write_prompt(path, content)
    print(f"  [OK] {name}: 追加情绪禁词 {words}")
    return content


def add_ai_ban(name, words):
    """追加禁词到防AI列表。"""
    content, path = _read_prompt(name)

    # 找到防AI路标词行
    pattern = r'(禁止.*?路标词[：:][^\n]+)'
    m = re.search(pattern, content)
    if m:
        line = m.group(1)
        new_words = [w.strip() for w in words.split(",") if w.strip() not in line]
        if new_words:
            new_line = line.rstrip() + "、" + "、".join(new_words)
            content = content.replace(line, new_line)

    content = _bump_version(content, f"+AI禁词: {words}")
    _write_prompt(path, content)
    print(f"  [OK] {name}: 追加AI禁词 {words}")
    return content


def strengthen_rule(name, rule_keyword):
    """强化某条规则——在前面加 ⚠️ 标记。"""
    content, path = _read_prompt(name)

    # 找到包含关键词的行
    lines = content.split('\n')
    modified = False
    for i, line in enumerate(lines):
        if rule_keyword in line and line.strip().startswith('-'):
            if '⚠️' not in line and '★' not in line:
                lines[i] = line.replace('- ', '- ⚠️ ', 1)
                modified = True
                break

    if modified:
        content = '\n'.join(lines)
        content = _bump_version(content, f"强化规则: {rule_keyword}")
        _write_prompt(path, content)
        print(f"  [OK] {name}: 强化规则 '{rule_keyword}'")
    else:
        print(f"  [SKIP] {name}: 未找到规则 '{rule_keyword}' 或已标记")

    return content


def adjust_word_control(name, min_pct=90, max_pct=110):
    """调整字数控制范围。"""
    content, path = _read_prompt(name)

    # 找到目标字数行
    pattern = r'目标 \{目标字数\} 字[^\n]*'
    m = re.search(pattern, content)
    if m:
        old = m.group(0)
        new = f"目标 {{目标字数}} 字（必须严格控制在 {min_pct}%~{max_pct}% 范围内，不到则扩写，超过则精简）"
        content = content.replace(old, new)

    content = _bump_version(content, f"字数控制收紧: {min_pct}%~{max_pct}%")
    _write_prompt(path, content)
    print(f"  [OK] {name}: 字数控制 {min_pct}%~{max_pct}%")
    return content


def main():
    parser = argparse.ArgumentParser(description="Prompt 自动修改器")
    parser.add_argument("--prompt", required=True, help="prompt 文件名 (如 system-generic.md)")
    parser.add_argument("--action", required=True,
                        choices=["add-emotion-ban", "add-ai-ban", "strengthen", "adjust-words"])
    parser.add_argument("--words", default="", help="追加的词 (逗号分隔)")
    parser.add_argument("--rule", default="", help="要强化的规则关键词")
    parser.add_argument("--min-pct", type=int, default=90)
    parser.add_argument("--max-pct", type=int, default=110)
    args = parser.parse_args()

    if args.action == "add-emotion-ban":
        add_emotion_ban(args.prompt, args.words)
    elif args.action == "add-ai-ban":
        add_ai_ban(args.prompt, args.words)
    elif args.action == "strengthen":
        strengthen_rule(args.prompt, args.rule)
    elif args.action == "adjust-words":
        adjust_word_control(args.prompt, args.min_pct, args.max_pct)


if __name__ == "__main__":
    main()
