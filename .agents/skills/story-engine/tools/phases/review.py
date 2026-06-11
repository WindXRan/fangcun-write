"""Phase 4.5-5: 审稿和修复（委托 story-review）"""

import os
import sys
import subprocess
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)


def phase_review(config, start, end, batch_size=20, workers=5):
    """全文审稿：调用full_review.py进行分批审稿+汇总分析。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 4.5: 全文审稿 (ch{start}-{end})")
    print("=" * 50)

    config_file = config.get("config_file")
    if not config_file:
        print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        return

    cmd = [
        "python", ".agents/skills/story-review/tools/full_review.py",
        "--config", config_file,
        "--start", str(start),
        "--end", str(end),
        "--batch-size", str(batch_size),
        "--workers", str(workers)
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=1800)
        if result.returncode == 0:
            print("[OK] 全文审稿完成")
        else:
            print(f"[FAIL] 全文审稿失败: {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 全文审稿失败: {e}")


def phase_fix(config, start, end, workers=5):
    """全文修复：调用full_fix.py根据审稿报告并行修复章节。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 5: 全文修复 (ch{start}-{end})")
    print("=" * 50)

    config_file = config.get("config_file")
    if not config_file:
        print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        return

    cmd = [
        "python", ".agents/skills/story-review/tools/full_fix.py",
        "--config", config_file,
        "--start", str(start),
        "--end", str(end),
        "--workers", str(workers)
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=1800)
        if result.returncode == 0:
            print("[OK] 全文修复完成")
        else:
            print(f"[FAIL] 全文修复失败: {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 全文修复失败: {e}")
