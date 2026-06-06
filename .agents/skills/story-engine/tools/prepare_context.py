# -*- coding: utf-8 -*-
"""
prepare_context.py — 合并写作上下文为一个文件
用法: python prepare_context.py <目标路径> <plot_guide.md> <全书弧线.md> <新书设定.md> [真相.md]
"""

import sys
import os

SECTIONS = [
    ("情节骨架", None),        # 由argv决定
    ("全书弧线", None),
    ("新书设定", None),
    ("当前真相状态", None),
]


def main():
    if len(sys.argv) < 5:
        print("用法: python prepare_context.py <输出.md> <plot_guide.md> <全书弧线.md> <新书设定.md> [真相.md]")
        sys.exit(1)

    output_path = sys.argv[1]
    files = {
        "情节骨架": sys.argv[2],
        "全书弧线": sys.argv[3],
        "新书设定": sys.argv[4],
    }
    truth_path = sys.argv[5] if len(sys.argv) > 5 else None
    if truth_path:
        files["当前真相状态"] = truth_path

    parts = []
    for label, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            parts.append(f"## {label}\n\n{content.strip()}")
        else:
            parts.append(f"## {label}\n\n（文件不存在）")

    output = "\n\n".join(parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"已生成: {output_path} ({len(output)}字)")


if __name__ == "__main__":
    main()
