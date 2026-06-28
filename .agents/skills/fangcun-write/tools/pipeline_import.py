"""
fangcun 源书导入+逆推一体化 pipeline。

一键完成：导入章节 → 标准化结构 → 逆推总纲/简介/标签/套路/卷纲。
"""
import os, sys, time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from importer import run_import


def step_import(book_name, author, source, channel, project_dir):
    """Step 1: 导入章节文件 → 标准项目结构。"""
    print("\n[1/4] 导入章节文件...")
    result = run_import(
        book_name=book_name, author=author, source=source,
        channel=channel, project_dir=project_dir,
    )
    if not result["success"]:
        print("  X 导入失败: " + result.get("error", "未知错误"))
        return None
    print("  V " + str(result["total_chapters"]) + " 章")
    return result


def step_pattern_analysis(project_dir, chapters=3):
    """Step 2: 逆推套路（前N章全本）。"""
    print("\n[2/4] 逆推套路（前" + str(chapters) + "章全本）...")
    from tool_executor import run_tool

    for ch in range(1, chapters + 1):
        print("  第" + str(ch) + "章...")
        run_tool("pattern-analysis", {
            "ch": ch,
            "user_input": "分析本章写作套路",
        }, project_dir)
    return True


def step_book_import(project_dir, book_name, total_chapters):
    """Step 3: 逆推总纲/简介/标签。"""
    print("\n[3/4] 逆推总纲/简介/标签...")
    from tool_executor import run_tool

    r = run_tool("book-import", {
        "book_name": book_name,
        "total_chapters": total_chapters,
        "user_input": "基于源文第1章逆向分析全书框架",
    }, project_dir)
    print("  V 已生成" if "完成" in r else "  W " + r[:100])
    return True


def step_volume_outline(project_dir, book_name=None, total_chapters=None):
    """Step 4: 逆推卷纲（已有则跳过）。"""
    vol_dir = Path(project_dir) / "正文" / "卷纲"
    vol_existing = list(vol_dir.glob("第*卷*.xml")) + list(vol_dir.glob("卷纲.xml"))
    if vol_existing:
        print("\n[4/4] 卷纲已存在，跳过")
        return True

    print("\n[4/4] 逆推卷纲...")
    from tool_executor import run_tool

    r = run_tool("volume-outline", {
        "book_name": book_name or "",
        "total_chapters": total_chapters or 0,
        "user_input": "设计全书卷纲",
    }, project_dir)
    print("  V 已生成" if "完成" in r else "  W " + r[:100])
    return True


def run_pipeline(book_name, author, source, channel="男频", project_dir=None):
    t0 = time.time()
    result = step_import(book_name, author, source, channel, project_dir)
    if not result:
        return False

    out_dir = result["project_dir"]
    total = result["total_chapters"]

    if not os.environ.get("API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("\nW 未设置 API_KEY，跳过逆推步骤")
        print("  项目结构已创建: " + out_dir)
        return True

    step_pattern_analysis(out_dir)
    step_book_import(out_dir, book_name, total)
    step_volume_outline(out_dir)

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print("  V 导入+逆推完成（" + str(int(elapsed)) + "s）")
    print("  输出: " + out_dir)
    print("  生成: 逆推总纲/简介/标签/卷纲/套路")
    print("=" * 60)
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="fangcun 源书导入+逆推 pipeline")
    parser.add_argument("book_name", help="书名")
    parser.add_argument("source", help="源路径（txt/epub/目录）")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--channel", default="男频", choices=["男频", "女频"])
    parser.add_argument("--project-dir", default=None, help="输出目录")
    args = parser.parse_args()

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
