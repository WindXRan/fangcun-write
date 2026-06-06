# -*- coding: utf-8 -*-
"""
写章前文件验证脚本
检查所有必需文件是否存在，确保写章流程不会因缺失文件中断。

用法:
    python validate_files.py <书名> <章号> [--mode {a,b}]

示例:
    python validate_files.py 我的都市人生 15
    python validate_files.py 我的都市人生 15 --mode b
"""

import sys
import os
import json
import glob as glob_mod


def calc_range(chapter_num: int) -> tuple:
    """计算10章窗口范围: 第15章 -> (11, 20)"""
    start = ((chapter_num - 1) // 10) * 10 + 1
    end = start + 9
    return start, end


def check_file(path: str, label: str) -> bool:
    """检查单个文件是否存在，打印结果。"""
    exists = os.path.isfile(path)
    status = "✅" if exists else "❌"
    print(f"  {status} {label}: {path}")
    return exists


def check_dir(path: str, label: str) -> bool:
    """检查目录是否存在且非空。"""
    exists = os.path.isdir(path) and len(os.listdir(path)) > 0
    status = "✅" if exists else "❌"
    print(f"  {status} {label}: {path}")
    return exists


def validate(book_name: str, chapter_num: int, mode: str = "a") -> bool:
    """验证所有必需文件，返回是否全部通过。"""
    all_ok = True

    print(f"\n📖 验证《{book_name}》第{chapter_num}章 (Mode {mode.upper()})\n")

    # --- 设定文件 ---
    print("[设定文件]")
    all_ok &= check_file(f"{book_name}/设定/新书概念.md", "新书概念")
    all_ok &= check_file(f"{book_name}/设定/story_bible.md", "世界观")

    # --- 真相文件 ---
    print("\n[真相文件]")
    truth_dir = f"{book_name}/真相文件"
    for name in ["current_state.md", "pending_hooks.md", "chapter_summaries.md",
                  "character_matrix.md", "emotional_arcs.md"]:
        all_ok &= check_file(f"{truth_dir}/{name}", name)

    # --- 正文目录 ---
    print("\n[正文目录]")
    text_dir = f"{book_name}/正文"
    os.makedirs(text_dir, exist_ok=True)
    print(f"  ✅ 正文目录: {text_dir}")

    # --- Mode A: 10章窗口文件 ---
    if mode == "a":
        start, end = calc_range(chapter_num)
        label = f"{start}-{end}"

        print(f"\n[Mode A: 窗口 {label}]")

        # 章纲
        outline = f"{book_name}/大纲/章纲_{label}.md"
        all_ok &= check_file(outline, f"章纲_{label}.md")

        # 风格指南
        style_guide = f"novel-download-authors/*/*/蒸馏/mode-a/style_guide_{label}.md"
        matches = glob_mod.glob(style_guide)
        if matches:
            print(f"  ✅ 风格指南: {matches[0]}")
        else:
            # 也检查项目根目录下的可能位置
            alt_guide = f"{book_name}/大纲/style_guide_{label}.md"
            if os.path.isfile(alt_guide):
                print(f"  ✅ 风格指南: {alt_guide}")
            else:
                print(f"  ❌ 风格指南: 未找到 style_guide_{label}.md")
                all_ok = False

        # 风格指纹 (每章一个)
        profile_pattern = f"novel-download-authors/*/*/蒸馏/mode-a/style_profile_{chapter_num}.json"
        matches = glob_mod.glob(profile_pattern)
        if matches:
            print(f"  ✅ 风格指纹: style_profile_{chapter_num}.json")
        else:
            alt_pattern = f"novel-download-authors/*/*/蒸馏/mode-b/style_profile_{chapter_num}.json"
            matches = glob_mod.glob(alt_pattern)
            if matches:
                print(f"  ✅ 风格指纹: style_profile_{chapter_num}.json (mode-b)")
            else:
                print(f"  ❌ 风格指纹: 未找到 style_profile_{chapter_num}.json")
                all_ok = False

    # --- Mode B: 单章文件 ---
    elif mode == "b":
        print(f"\n[Mode B: 第{chapter_num}章]")

        # 风格指纹
        profile_pattern = f"novel-download-authors/*/*/蒸馏/mode-b/style_profile_{chapter_num}.json"
        matches = glob_mod.glob(profile_pattern)
        if matches:
            print(f"  ✅ 风格指纹: style_profile_{chapter_num}.json")
        else:
            print(f"  ❌ 风格指纹: 未找到 style_profile_{chapter_num}.json")
            all_ok = False

        # 源文 (Mode B 子agent需要读源文)
        source_pattern = f"novel-download-authors/*/*/源文/第{chapter_num}章.txt"
        matches = glob_mod.glob(source_pattern)
        if matches:
            print(f"  ✅ 源文: 第{chapter_num}章.txt")
        else:
            print(f"  ⚠️  源文: 未找到第{chapter_num}章.txt (可选)")

    # --- 已完成章节检查 (防止覆盖) ---
    print("\n[已完成章节]")
    existing = f"{book_name}/正文/第{chapter_num}章.txt"
    if os.path.isfile(existing):
        size = os.path.getsize(existing)
        print(f"  ⚠️  第{chapter_num}章.txt 已存在 ({size} bytes)，继续写将覆盖")
    else:
        print(f"  ✅ 第{chapter_num}章.txt 不存在，可以写入")

    # --- 总结 ---
    print("\n" + "=" * 40)
    if all_ok:
        print("✅ 验证通过，所有必需文件就绪")
    else:
        print("❌ 验证失败，请先补齐缺失文件")
    print()

    return all_ok


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python validate_files.py <书名> <章号> [--mode {a,b}]")
        print("示例: python validate_files.py 我的都市人生 15")
        sys.exit(1)

    book_name = sys.argv[1]
    chapter_num = int(sys.argv[2])

    mode = "a"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1].lower()

    ok = validate(book_name, chapter_num, mode)
    sys.exit(0 if ok else 1)
