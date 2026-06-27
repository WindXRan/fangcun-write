"""
fangcun-analyze: 长篇拆文管道。

用法:
    python analyze.py --book-dir projects/作者/书名/_cache/chapters --out 拆文库/书名

管道:
    0. 概要提取
    1. 黄金三章拆解  → golden-chapters.xml preset
    2. 逐章提取事件  → extract_events()   (并行 Python)
    3. 故事骨架      → skeleton.xml preset
    4. 设定/角色     → character-extract.xml preset
    5. 拆文报告      → analysis-report.xml preset
    6. 文风分析      → style-analysis.xml preset
"""

import os, sys, re, time, json
from pathlib import Path

# 确保 tools/ 和 .agents/tools/ 在路径中
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
import _path_setup  # noqa: F401 — 注入 .agents/tools/

from writer import run_preset, save_multifile_output
from source_analysis import extract_events, load_events, get_novel_chapters, get_novel_text


def build_config(book_name, author, chapter_dir, out_dir, api_key, model):
    """构建管道配置。全部输出进 projects/{作者}/{书名}/。"""
    base = str(_HERE.parent.parent.parent.parent)
    proj = f"projects/{author}/{book_name}"
    return {
        "book_name": book_name,
        "author": author,
        "source_book": book_name,
        "project_dir": proj,
        "source_dir": str(chapter_dir),
        "base_dir": base,
        "analyze_dir": proj,
        "api_key": api_key,
        "model": model,
        "total_chapters": 192,
    }


def stage0_summary(config):
    """Stage 0: 生成全书概要 + 章节索引。"""
    print("\n[Stage 0] 生成概要...")
    chapters = get_novel_chapters(config)
    total = len(chapters)
    print(f"  识别到 {total} 章")
    # 读前三章写迷你概览
    first3 = []
    for i in range(1, min(4, total + 1)):
        text = get_novel_text(config, i)
        first_line = text.strip().split("\n")[0][:80] if text else ""
        first3.append(f"第{i}章: {first_line}...")
    summary = f"# {config['book_name']}\n\n总章数：{total}\n\n## 前三章预览\n" + "\n".join(first3)
    out = Path(config["analyze_dir"]) / "概要.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(summary, encoding="utf-8")
    print(f"  → {out}")
    return total


def stage1_golden(config):
    """Stage 1: 黄金三章拆解（用 preset）。"""
    print("\n[Stage 1] 黄金三章拆解...")
    for ch in range(1, 4):
        text = get_novel_text(config, ch)
        if not text:
            print(f"  第{ch}章不存在，跳过")
            continue
        print(f"  拆解第{ch}章...")
        try:
            result = run_preset(config, "golden-chapters", ch=ch)
            if result and not result.startswith("[BLOCKED]"):
                save_multifile_output(result, Path(config["analyze_dir"]))
                print(f"  ✓ 第{ch}章完成")
            else:
                print(f"  ⚠ 第{ch}章跳过: {result[:100]}")
        except Exception as e:
            print(f"  ✗ 第{ch}章失败: {e}")


def stage2_events(config):
    """Stage 2: 逐章事件提取（并行 Python，不读 preset）。"""
    print("\n[Stage 2] 逐章提取事件...")
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("  ✗ 未设置 API_KEY")
        return
    events = extract_events(
        config,
        api_key=api_key,
        api_url=config.get("api_base_url", "https://api.deepseek.com"),
        model=config.get("model", "deepseek-chat"),
        prompt_text="提取本章核心事件，包含：出场角色、核心冲突、情绪变化、关键信息释放。",
        workers=config.get("workers", 5),
    )
    print(f"  完成: {len(events)} 章事件")


def stage3_skeleton(config):
    """Stage 3: 故事骨架（用 skeleton.xml preset）。"""
    print("\n[Stage 3] 故事骨架...")
    events_text = _get_events_text(config)
    if not events_text:
        print("  ⚠ 无事件表，跳过")
        return
    try:
        result = run_preset(config, "skeleton", ch=0)
        if result and not result.startswith("[BLOCKED]"):
            save_multifile_output(result, Path(config["analyze_dir"]))
            print("  ✓ 骨架完成")
    except Exception as e:
        print(f"  ✗ 骨架失败: {e}")


def stage4_characters(config):
    """Stage 4: 角色/设定提取（用 character-extract.xml preset）。"""
    print("\n[Stage 4] 角色/设定提取...")
    events = load_events(config)
    if not events:
        print("  ⚠ 无事件表，跳过")
        return
    try:
        result = run_preset(config, "character-extract", ch=0)
        if result and not result.startswith("[BLOCKED]"):
            save_multifile_output(result, Path(config["analyze_dir"]))
            print("  ✓ 角色/设定完成")
    except Exception as e:
        print(f"  ✗ 角色提取失败: {e}")


def stage5_report(config):
    """Stage 5: 拆文报告（用 analysis-report.xml preset）。"""
    print("\n[Stage 5] 拆文报告...")
    try:
        result = run_preset(config, "analysis-report", ch=0)
        if result and not result.startswith("[BLOCKED]"):
            save_multifile_output(result, Path(config["analyze_dir"]))
            print("  ✓ 报告完成")
    except Exception as e:
        print(f"  ✗ 报告失败: {e}")


def stage6_style(config):
    """Stage 6: 文风分析（用 style-analysis.xml preset）。"""
    print("\n[Stage 6] 文风分析...")
    # 对前 3 章+随机 5 章做风格采样
    for ch in range(1, 4):
        try:
            result = run_preset(config, "style-analysis", ch=ch, start=1, end=3)
            if result and not result.startswith("[BLOCKED]"):
                save_multifile_output(result, Path(config["analyze_dir"]))
                print(f"  ✓ 第{ch}章文风采样完成")
                break  # 一次输出完整分析就够了
        except Exception as e:
            print(f"  ✗ 文风分析失败: {e}")
            break


def _get_events_text(config):
    """获取事件表文本。"""
    from source_io import load_events as _le
    events = _le(config)
    if not events:
        return ""
    lines = []
    for e in events[:50]:  # 取前 50 章够骨架分析
        eid = e.get("id", "?")
        core = e.get("核心事件", e.get("event", ""))
        if core:
            lines.append(f"第{eid}章: {core[:120]}")
    return "\n".join(lines)


def run_all(config):
    """跑完整管道。"""
    total = stage0_summary(config)
    stage1_golden(config)
    stage2_events(config)
    stage3_skeleton(config)
    stage4_characters(config)
    stage5_report(config)
    stage6_style(config)
    print("\n=== 拆文完成 ===")
    print(f"  输出目录: {config['analyze_dir']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="fangcun 拆文管道")
    parser.add_argument("--book", required=True, help="书名")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--chapters", required=True, help="原文目录路径")
    parser.add_argument("--out", default=None, help="输出目录（默认 拆文库/{书名}）")
    parser.add_argument("--api-key", default=None, help="API Key")
    parser.add_argument("--model", default="deepseek-chat", help="模型")
    parser.add_argument("--workers", type=int, default=192, help="Stage 2 并行数（默认全开）")
    parser.add_argument("--stage", default="all", help="指定阶段: all/0/1/2/...")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("API_KEY")
    if not api_key:
        print("请设置 API_KEY 环境变量或 --api-key")
        sys.exit(1)

    out_dir = args.out or f"拆文库/{args.book}"
    config = build_config(args.book, args.author, args.chapters, out_dir, api_key, args.model)
    config["workers"] = args.workers

    stages = {
        "0": stage0_summary,
        "1": stage1_golden,
        "2": stage2_events,
        "3": stage3_skeleton,
        "4": stage4_characters,
        "5": stage5_report,
        "6": stage6_style,
    }

    if args.stage == "all":
        run_all(config)
    else:
        fn = stages.get(args.stage)
        if fn:
            fn(config)
        else:
            print(f"未知阶段: {args.stage}，可选: all/0/1/2/3/4/5/6")
