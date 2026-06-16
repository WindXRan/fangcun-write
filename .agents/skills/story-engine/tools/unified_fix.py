"""
统一修复脚本 — 并行修复章节问题。

用法:
  python unified_fix.py --config configs/xxx.json --start 1 --end 10
  python unified_fix.py --config configs/xxx.json --start 1 --end 10 --dry-run
  python unified_fix.py --config configs/xxx.json --start 1 --end 10 --workers 5
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from unified_fixer import (
    run_pipeline, review_agent, dispatch_agent, fix_agent,
    summary_agent, ReviewResult, SummaryReport
)


def main():
    parser = argparse.ArgumentParser(description="统一修复 — 并行修复章节问题")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=None, help="起始章")
    parser.add_argument("--end", type=int, default=None, help="结束章")
    parser.add_argument("--batch-size", type=int, default=10, help="每 agent 审多少章")
    parser.add_argument("--workers", type=int, default=10, help="并行 agent 数")
    parser.add_argument("--dry-run", action="store_true", help="只审不修")
    parser.add_argument("--review-only", action="store_true", help="只审查，输出报告")
    parser.add_argument("--output", default=None, help="输出报告路径")
    args = parser.parse_args()

    # 加载配置
    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    cfg.setdefault("base_dir", os.getcwd())

    # 确定章节范围
    if args.start is None or args.end is None:
        ch_dir = Path(cfg['rewrites_dir']) / 'chapters'
        if ch_dir.exists():
            nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in ch_dir.glob("ch_*.txt")]
            if nums:
                args.start = args.start or min(nums)
                args.end = args.end or max(nums)
    args.start = args.start or 1
    args.end = args.end or 10

    print(f"\n{'='*50}")
    print(f"统一修复 | {cfg['book_name']} | ch{args.start}-{args.end}")
    print(f"{'='*50}")

    # 运行完整流程
    results, report = run_pipeline(
        cfg, args.start, args.end,
        batch_size=args.batch_size, workers=args.workers,
        dry_run=args.dry_run
    )

    # 输出报告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "config": args.config,
                "range": [args.start, args.end],
                "results": results,
                "report": report,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {output_path}")


if __name__ == "__main__":
    import re
    main()
