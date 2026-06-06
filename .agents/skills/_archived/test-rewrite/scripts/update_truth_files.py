# -*- coding: utf-8 -*-
"""
真相文件更新脚本（确定性部分）
写章后自动更新 chapter_summaries.md，其余真相文件需要 LLM 更新。

用法:
    python update_truth_files.py <书名> <章号> "<章名>" "<摘要>" "<事件1>|<事件2>|<事件3>"

示例:
    python update_truth_files.py 我的都市人生 7 "重逢" "苏念在新公司遇到陆沉" "苏念入职|陆沉出现|两人对视"

参考 inkos settler-parser.ts 的结构化更新逻辑，
但 story-rewrite 场景下只做确定性追加，LLM 部分交给主 agent。
"""

import sys
import os
import re


def ensure_truth_files(book_name: str):
    """确保真相文件目录和文件存在。"""
    truth_dir = f"{book_name}/真相文件"
    os.makedirs(truth_dir, exist_ok=True)

    templates = {
        "current_state.md": "# 世界状态\n\n## 角色位置\n| 角色 | 当前位置 | 最后更新 |\n|------|---------|--------|\n\n## 关系网络\n| 角色A | 角色B | 关系状态 | 最后变化 |\n|-------|-------|---------|--------|\n\n## 已知信息\n| 角色 | 知道的事 | 来源 | 章节 |\n|------|---------|------|------|\n",
        "pending_hooks.md": "# 伏笔账本\n\n| hook_id | 内容 | 铺设章 | 预计回收 | 状态 | 优先级 |\n|---------|------|--------|---------|------|--------|\n",
        "chapter_summaries.md": "# 章节摘要\n\n| 章 | 章名 | 出场人物 | 关键事件 | 状态变化 | 伏笔动态 |\n|----|------|---------|---------|---------|--------|\n",
        "character_matrix.md": "# 角色交互矩阵\n\n## 相遇记录\n| 章 | 角色A | 角色B | 场景 | 信息交换 |\n|----|-------|-------|------|--------|\n\n## 信息边界\n| 角色 | 不知道的事 | 读者知道但角色不知道 |\n|------|-----------|-------------------|\n",
        "emotional_arcs.md": "# 情感弧线\n",
    }

    for filename, template in templates.items():
        path = os.path.join(truth_dir, filename)
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(template)
            print(f"  📝 创建: {path}")


def append_chapter_summary(book_name: str, chapter_num: int, chapter_name: str,
                           summary: str, events: list):
    """追加章节摘要到 chapter_summaries.md。"""
    path = f"{book_name}/真相文件/chapter_summaries.md"

    # 确保文件存在
    if not os.path.isfile(path):
        ensure_truth_files(book_name)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 格式化事件列表
    events_str = "、".join(events) if events else "—"

    # 构造新行
    new_row = f"| {chapter_num} | {chapter_name} | — | {summary} | — | — |\n"

    # 检查是否已有该章节
    existing_pattern = rf"^\|\s*{chapter_num}\s*\|"
    lines = content.split("\n")
    updated = False

    for i, line in enumerate(lines):
        if re.match(existing_pattern, line):
            lines[i] = new_row.rstrip()
            updated = True
            break

    if not updated:
        # 追加到文件末尾（在最后一个非空行后）
        lines.append(new_row.rstrip())

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    action = "更新" if updated else "追加"
    print(f"  ✅ {action} chapter_summaries.md: 第{chapter_num}章 {chapter_name}")


def append_pending_hook(book_name: str, chapter_num: int, hook_id: str,
                        hook_content: str, priority: str = "medium"):
    """追加伏笔到 pending_hooks.md。"""
    path = f"{book_name}/真相文件/pending_hooks.md"

    if not os.path.isfile(path):
        ensure_truth_files(book_name)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查 hook_id 是否已存在
    if f"| {hook_id} " in content or f"| {hook_id}|" in content:
        print(f"  ⚠️  伏笔 {hook_id} 已存在，跳过")
        return

    # 计算预计回收章
    recover_chapter = chapter_num + 10

    new_row = f"| {hook_id} | {hook_content} | 第{chapter_num}章 | ≤{recover_chapter}章 | open | {priority} |\n"

    with open(path, "a", encoding="utf-8") as f:
        f.write(new_row)

    print(f"  ✅ 追加伏笔 {hook_id}: {hook_content}")


def resolve_hook(book_name: str, hook_id: str, chapter_num: int):
    """标记伏笔为已回收。"""
    path = f"{book_name}/真相文件/pending_hooks.md"

    if not os.path.isfile(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换 open -> resolved
    patterns = [
        (rf"(\|\s*{hook_id}\s*\|[^|]*\|[^|]*\|[^|]*\|)\s*open\s*(\|)", rf"\1 resolved \2"),
    ]

    updated = content
    for old, new in patterns:
        updated = re.sub(old, new, updated)

    if updated != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"  ✅ 回收伏笔 {hook_id} (第{chapter_num}章)")
    else:
        print(f"  ⚠️  伏笔 {hook_id} 未找到或已回收")


def print_llm_reminder(book_name: str, chapter_num: int):
    """提示需要 LLM 更新的真相文件。"""
    print(f"\n📋 以下真相文件需要 LLM 更新（交给 Observer agent）:")
    print(f"  → {book_name}/真相文件/current_state.md")
    print(f"  → {book_name}/真相文件/character_matrix.md")
    print(f"  → {book_name}/真相文件/emotional_arcs.md")
    print(f"  → {book_name}/真相文件/pending_hooks.md (新增/状态变更)")


def main():
    if len(sys.argv) < 6:
        print("用法: python update_truth_files.py <书名> <章号> \"<章名>\" \"<摘要>\" \"<事件1>|<事件2>|...\"")
        print()
        print("示例:")
        print("  python update_truth_files.py 我的都市人生 7 \"重逢\" \"苏念遇到陆沉\" \"苏念入职|陆沉出现\"")
        print()
        print("扩展用法:")
        print("  --hook H007 \"公司门口的花是谁送的\" [priority]  # 追加伏笔")
        print("  --resolve H003                                  # 回收伏笔")
        sys.exit(1)

    book_name = sys.argv[1]
    chapter_num = int(sys.argv[2])
    chapter_name = sys.argv[3]
    summary = sys.argv[4]
    events_str = sys.argv[5]

    events = [e.strip() for e in events_str.split("|") if e.strip()]

    print(f"\n📖 更新《{book_name}》第{chapter_num}章真相文件\n")

    # 确保文件存在
    ensure_truth_files(book_name)

    # 追加章节摘要
    append_chapter_summary(book_name, chapter_num, chapter_name, summary, events)

    # 处理扩展参数
    i = 6
    while i < len(sys.argv):
        if sys.argv[i] == "--hook" and i + 2 < len(sys.argv):
            hook_id = sys.argv[i + 1]
            hook_content = sys.argv[i + 2]
            priority = sys.argv[i + 3] if i + 3 < len(sys.argv) and not sys.argv[i + 3].startswith("--") else "medium"
            append_pending_hook(book_name, chapter_num, hook_id, hook_content, priority)
            i += 4 if priority != "medium" else 3
        elif sys.argv[i] == "--resolve" and i + 1 < len(sys.argv):
            resolve_hook(book_name, sys.argv[i + 1], chapter_num)
            i += 2
        else:
            i += 1

    # 提示 LLM 更新
    print_llm_reminder(book_name, chapter_num)

    print("\n✅ 确定性更新完成\n")


if __name__ == "__main__":
    main()
