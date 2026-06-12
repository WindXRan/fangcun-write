"""Phase 6: 统一审查+修复（新系统）"""

import os
import json
import time
from pathlib import Path


def phase_unified_check(config, start, end, workers=10, batch_size=25, state_mgr=None):
    """统一检查：算法+LLM分批审核，只检查不修复。"""
    print(f"\n{'=' * 50}")
    print(f"统一检查 (ch{start}-{end})")
    print("=" * 50)

    from unified_fixer import run_pipeline

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions"
    model = config.get("model", "deepseek-chat")

    results, merged = run_pipeline(
        config, start, end, api_key, api_url, model,
        batch_size=batch_size, workers=workers, dry_run=True,
    )

    if state_mgr and merged:
        for ch, data in merged.items():
            state_mgr.save_review_result(ch, data.get("score", 0), data.get("issues", []))
        state_mgr.save()

    return merged


def phase_unified_fix(config, start, end, workers=10, batch_size=25, dry_run=False):
    """统一审改：分批审核→合并→制定任务→执行修复。"""
    print(f"\n{'=' * 50}")
    print(f"统一审改 (ch{start}-{end}, dry_run={dry_run})")
    print("=" * 50)

    from unified_fixer import run_pipeline

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions"
    model = config.get("model", "deepseek-chat")

    if not api_key:
        print("[WARN] 未配置 API_KEY，将跳过 LLM 审核和修复")

    results, merged = run_pipeline(
        config, start, end, api_key, api_url, model,
        batch_size=batch_size, workers=workers, dry_run=dry_run,
    )

    # 保存
    output = os.path.join(config['rewrites_dir'], 'compare', 'unified_review_fix.json')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": {str(k): v for k, v in (results or {}).items()},
        "merged": {str(k): v for k, v in (merged or {}).items()},
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  结果已保存: {output}")

    return results


def phase_unified_review_fix(config, start, end, workers=10, batch_size=25, state_mgr=None):
    """统一审改（推荐）：分批审核→合并→制定任务→执行修复。"""
    results = phase_unified_fix(config, start, end, workers=workers, batch_size=batch_size, dry_run=False)

    if state_mgr and results:
        for ch, r in (results or {}).items():
            if isinstance(r, dict) and r.get("status") == "fixed":
                state_mgr.chapter_completed(ch, model="mixed", retries=0)
        state_mgr.save()

    return results
