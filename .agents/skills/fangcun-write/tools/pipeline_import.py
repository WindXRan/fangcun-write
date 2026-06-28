"""
fangcun 源书导入+拆解一体化 pipeline。

一键完成：导入章节 → 标准化结构 → 生成总纲/简介/标签/套路分析/卷纲。

用法:
    python pipeline_import.py "书名" "源路径" --author "作者" --channel 男频
    python pipeline_import.py "洪荒准圣" ./raw_chapters --author "佚名"
"""
import os, sys, json, time
from pathlib import Path

# 确保 tools/ 在路径中
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from importer import run_import, detect_source


def step_import(book_name, author, source, channel, project_dir):
    """Step 1: 导入章节文件 → 标准项目结构。"""
    print("\n[1/4] 导入章节文件...")
    result = run_import(
        book_name=book_name, author=author, source=source,
        channel=channel, project_dir=project_dir,
    )
    if not result["success"]:
        print(f"  ✗ 导入失败: {result.get('error')}")
        return None
    print(f"  ✓ {result['total_chapters']} 章 → {result['project_dir']}")
    return result


def step_pattern_analysis(project_dir, chapters=3):
    """Step 2: 套路分析（前 N 章）。"""
    print(f"\n[2/4] 套路分析（前{chapters}章）...")
    from tool_executor import run_tool

    for ch in range(1, chapters + 1):
        print(f"  分析第{ch}章...", end=" ")
        r = run_tool("pattern-analysis", {
            "ch": ch,
            "user_input": f"分析本章的写作套路",
        }, project_dir)
        print("✓" if "完成" in r else f"⚠ {r[:60]}")
    return True


def step_book_import(project_dir, book_name, total_chapters):
    """Step 3: 生成总纲/简介/标签。"""
    print("\n[3/4] 生成总纲/简介/标签...")
    from tool_executor import run_tool

    # 先读前三章做素材
    chap_dir = Path(project_dir) / "正文" / "正文"
    first3 = []
    for f in sorted(chap_dir.glob("第*.txt"))[:3]:
        text = f.read_text(encoding="utf-8", errors="replace")[:500]
        first3.append(f"第{f.stem}: {text[:100]}...")

    r = run_tool("book-import", {
        "book_name": book_name,
        "total_chapters": total_chapters,
        "user_input": f"基于以下前三章生成全书总纲/简介/标签：\n\n" + "\n\n".join(first3),
    }, project_dir)
    if "完成" in r:
        print(f"  ✓ 总纲/简介/标签已生成")
    else:
        print(f"  ⚠ {r[:100]}")
    return True


def step_volume_outline(project_dir, book_name, total_chapters):
    """Step 4: 卷纲。"""
    print("\n[4/4] 生成卷纲...")
    from tool_executor import run_tool

    r = run_tool("volume-outline", {
        "book_name": book_name,
        "total_chapters": total_chapters,
        "user_input": f"为《{book_name}》设计分卷结构",
    }, project_dir)
    if "完成" in r:
        print(f"  ✓ 卷纲已生成")
    else:
        print(f"  ⚠ {r[:100]}")
    return True


def run_pipeline(book_name, author, source, channel="男频", project_dir=None):
    """执行完整导入+拆解 pipeline。"""
    t0 = time.time()

    # Step 1: 导入
    result = step_import(book_name, author, source, channel, project_dir)
    if not result:
        return False

    out_dir = result["project_dir"]
    total = result["total_chapters"]

    # 检查 API key
    if not os.environ.get("API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("\n⚠ 未设置 API_KEY，跳过需要 API 调用的步骤")
        print(f"  项目结构已创建在: {out_dir}")
        print(f"  后续可手动运行: python -m tools.pipeline_import --step-only api \"{book_name}\" \"{source}\"")
        return True

    # Step 2-4: 需要 API 的分析步骤
    step_pattern_analysis(out_dir)
    step_book_import(out_dir, book_name, total)
    step_volume_outline(out_dir, book_name, total)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ✓ 导入+拆解完成（{elapsed:.0f}s）")
    print(f"  输出: {out_dir}")
    print(f"  章节: {total} 章")
    print(f"  生成: 总纲/简介/标签/套路分析/卷纲")
    print(f"{'='*60}")
    return True


# ─── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="fangcun 源书导入+拆解一体化 pipeline")
    parser.add_argument("book_name", help="书名")
    parser.add_argument("source", help="源路径（txt/epub/目录）")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--channel", default="男频", choices=["男频", "女频"])
    parser.add_argument("--project-dir", default=None, help="输出目录")
    parser.add_argument("--step-only", default=None,
                        help="只跑指定步骤: import/pattern/book-import/volume/api")
    args = parser.parse_args()

    if args.step_only == "import":
        r = step_import(args.book_name, args.author, args.source, args.channel, args.project_dir)
        sys.exit(0 if r else 1)
    elif args.step_only == "api":
        # 只跑需要 API 的步骤（假设导入已完成）
        r1 = step_pattern_analysis(args.project_dir or f"projects/{args.book_name}")
        r2 = step_book_import(args.project_dir or f"projects/{args.book_name}", args.book_name, 0)
        r3 = step_volume_outline(args.project_dir or f"projects/{args.book_name}", args.book_name, 0)
        sys.exit(0 if r1 and r2 and r3 else 1)

    success = run_pipeline(
        book_name=args.book_name,
        author=args.author,
        source=args.source,
        channel=args.channel,
        project_dir=args.project_dir,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
