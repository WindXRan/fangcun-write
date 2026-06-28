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
    print("  V " + str(result["total_chapters"]) + " 章 → " + result["project_dir"])
    return result


def step_pattern_analysis(project_dir, chapters=5):
    """Step 2: 逆推套路（采样全本）。"""
    print("\n[2/4] 逆推套路（采样全本）...")
    from tool_executor import run_tool

    chap_dir = Path(project_dir) / "正文" / "正文"
    all_chs = sorted(chap_dir.glob("第*.txt"))
    total = len(all_chs)
    if total == 0:
        print("  W 无章节文件")
        return False

    # 采样：首章 + 25%/50%/75%/尾章
    samples = [1]
    for pct in [0.25, 0.50, 0.75]:
        idx = max(2, min(total - 1, int(total * pct)))
        if idx not in samples:
            samples.append(idx)
    if total not in samples:
        samples.append(total)
    samples = sorted(set(samples))

    source_texts = []
    for ch in samples:
        for f in all_chs:
            stem = f.stem
            if stem.startswith("第" + str(ch) + "章") or stem.startswith("第" + str(ch) + " "):
                text = f.read_text(encoding="utf-8", errors="replace")
                source_texts.append("=== 第" + str(ch) + "章 ===\n" + text[:3000])
                break

    combined = "\n\n".join(source_texts)
    print("  采样 " + str(len(samples)) + " 章: " + str(samples) + "（共" + str(total) + "章）")

    r = run_tool("pattern-analysis", {
        "ch": 1,
        "源文对照": combined,
        "user_input": "基于以上采样章节分析全书写作套路",
    }, project_dir)
    print("  V" if "完成" in r else "  W " + r[:60])
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
    if "完成" in r:
        print("  V 已生成")
    else:
        print("  W " + r[:100])
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
    if "完成" in r:
        print("  V 已生成")
    else:
        print("  W " + r[:100])
    return True


def run_pipeline(book_name, author, source, channel="男频", project_dir=None):
    """执行完整导入+逆推 pipeline。"""
    t0 = time.time()

    # Step 1
    result = step_import(book_name, author, source, channel, project_dir)
    if not result:
        return False

    out_dir = result["project_dir"]
    total = result["total_chapters"]

    if not os.environ.get("API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        print("\nW 未设置 API_KEY，跳过 API 步骤")
        print("  项目结构已创建在: " + out_dir)
        print("  后续可跑「导入拆解」补全")
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
