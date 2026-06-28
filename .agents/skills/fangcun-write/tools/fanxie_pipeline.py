"""
fangcun 仿写全流程管线。
一键导入源文 → 分析源文 → 生成仿写项目 → 写仿文章节。

用法：
    python fanxie_pipeline.py ^
        --source projects/洪荒准圣 ^
        --target projects/洪荒准圣仿写 ^
        --chapters 1-5
"""
import sys, glob, os
sys.path.insert(0, os.path.dirname(__file__))
from tool_executor import run_tool, init_project

def read_source_chapter(source_dir: str, ch: int) -> str:
    """读取源文第N章内容"""
    for pat in [f"第{ch}章*.txt", f"第{ch}章*.xml",
                f"**/第{ch}章*.txt", f"**/第{ch}章*.xml"]:
        files = glob.glob(f"{source_dir}/正文/正文/{pat}") or glob.glob(f"{source_dir}/{pat}")
        if files:
            with open(files[0], encoding='utf-8') as f:
                return f.read()
    return ""

def fanxie_pipeline(source_dir: str, target_dir: str, chapters: list[int], channel: str = "男频"):
    """仿写全流程"""

    # ─── 阶段1：源文分析 ───
    print("=" * 50)
    print("阶段1/6：导入源文项目")
    print("=" * 50)
    r = run_tool("book-import-raw", {
        "book_name": os.path.basename(source_dir.rstrip("/\\")),
        "source": source_dir,
        "channel": channel,
    }, source_dir)
    print(r[:200])

    print("\n阶段2/6：生成源文总纲/简介/标签")
    r = run_tool("book-import", {
        "book_name": os.path.basename(source_dir.rstrip("/\\")),
        "total_chapters": max(chapters) if chapters else 1,
    }, source_dir)
    print(r[:200])

    print("\n阶段3/6：套路分析（前5章）")
    for ch in chapters[:5]:
        text = read_source_chapter(source_dir, ch)
        if text:
            r = run_tool("pattern-analysis", {
                "user_input": text,
                "story_name": os.path.basename(source_dir.rstrip("/\\")),
                "chapter_number": ch,
            }, source_dir)
            print(f"  第{ch}章: {r[:100]}")

    # ─── 阶段2：仿写项目创建 ───
    print("\n" + "=" * 50)
    print("阶段4/6：创建仿写项目")
    print("=" * 50)
    init_project(target_dir)
    r = run_tool("open-book", {
        "story_name": f"仿写：{os.path.basename(source_dir.rstrip('/\\\\'))}",
        "channel": channel,
    }, target_dir)
    print(r[:200])

    # ─── 阶段3：写章 ───
    print("\n" + "=" * 50)
    print(f"阶段5/6：生成章纲（共{len(chapters)}章）")
    print("=" * 50)
    for ch in chapters:
        r = run_tool("plot-guide-nanpin" if channel == "男频" else "plot-guide-nvpin", {
            "chapter_number": ch,
            "story_name": f"仿写：{os.path.basename(source_dir.rstrip('/\\\\'))}",
            "channel": channel,
        }, target_dir)
        print(f"  第{ch}章纲: {r[:100]}")

    print("\n" + "=" * 50)
    print(f"阶段6/6：写正文（共{len(chapters)}章）")
    print("=" * 50)
    for ch in chapters:
        text = read_source_chapter(source_dir, ch)
        r = run_tool("write-chapter", {
            "source_book": os.path.basename(source_dir.rstrip("/\\")),
            "chapter_number": ch,
            "story_name": f"仿写：{os.path.basename(source_dir.rstrip('/\\\\'))}",
            "channel": channel,
            "target_words": "3000",
            "target_words_min": "2500",
            "target_words_max": "3500",
        }, target_dir)
        print(f"  第{ch}章: {r[:100]}")

    print("\n✅ 仿写管线完成")
    print(f"   源文: {source_dir}")
    print(f"   仿写: {target_dir}")
    print(f"   章节: {len(chapters)} 章")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="仿写全流程管线")
    parser.add_argument("--source", required=True, help="源文项目目录")
    parser.add_argument("--target", required=True, help="仿写项目目录")
    parser.add_argument("--chapters", default="1", help="章节范围，如 1-5")
    parser.add_argument("--channel", default="男频", help="目标频道")
    args = parser.parse_args()

    # 解析章节范围
    if "-" in args.chapters:
        start, end = args.chapters.split("-")
        chapters = list(range(int(start), int(end) + 1))
    else:
        chapters = [int(args.chapters)]

    fanxie_pipeline(args.source, args.target, chapters, args.channel)
