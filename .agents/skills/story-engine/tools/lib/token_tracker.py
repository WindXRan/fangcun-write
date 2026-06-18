"""Token 用量追踪 — 按项目记录每次 API 调用的 token 消耗。
"""

import json
import os
from pathlib import Path
from datetime import datetime

_LOG_FILE = "_log/api_usage.jsonl"

# 模型单价（元/千 token）
_MODEL_PRICES = {
    "mimo-v2.5-pro": {"input": 0.004, "output": 0.012},
    "deepseek-v4-flash": {"input": 0.0005, "output": 0.002},
    "deepseek-chat": {"input": 0.004, "output": 0.012},
}


def log_usage(rewrites_dir, entry):
    """追加一条 API 调用记录。"""
    if not rewrites_dir:
        return
    path = Path(rewrites_dir) / _LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_usage(rewrites_dir):
    """读取全部 API 调用记录。"""
    path = Path(rewrites_dir) / _LOG_FILE
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def aggregate(records):
    """按 prompt_type 聚合 token 用量 + 调用次数。

    Returns:
        (phase_stats, total_stats)
        phase_stats: {prompt_type: {calls, prompt, completion, total, cost}}
        total_stats: {calls, prompt, completion, total, cost}
    """
    phases = {}
    total = {"calls": 0, "prompt": 0, "completion": 0, "total": 0, "cost": 0.0}

    for r in records:
        pt = r.get("prompt_type", "unknown")
        model = r.get("model", "unknown")
        prices = _MODEL_PRICES.get(model, {"input": 0.004, "output": 0.012})

        p = r.get("prompt_tokens", 0)
        c = r.get("completion_tokens", 0)
        cost = (p / 1000 * prices["input"]) + (c / 1000 * prices["output"])

        phases.setdefault(pt, {"calls": 0, "prompt": 0, "completion": 0, "total": 0, "cost": 0.0})
        phases[pt]["calls"] += 1
        phases[pt]["prompt"] += p
        phases[pt]["completion"] += c
        phases[pt]["total"] += p + c
        phases[pt]["cost"] += cost

        total["calls"] += 1
        total["prompt"] += p
        total["completion"] += c
        total["total"] += p + c
        total["cost"] += cost

    return phases, total


def format_report(records, total_cost=None):
    """生成可读的 Token 消耗报告（Markdown 格式）。"""
    if not records:
        return "# Token 消耗报告\n\n暂无数据（API 调用未记录）\n"

    phases, total = aggregate(records)
    lines = []
    lines.append("# Token 消耗报告\n")
    lines.append(f"总 API 调用次数：{total['calls']} 次\n")
    lines.append(f"总消耗：{total['total']:,} tokens（输入 {total['prompt']:,} + 输出 {total['completion']:,}）\n")

    cost = total_cost or total["cost"]
    lines.append(f"总费用：¥{cost:.4f}\n")

    lines.append("\n## 各阶段消耗\n\n")
    lines.append("| 阶段 | 调用次数 | 输入 tokens | 输出 tokens | 合计 tokens | 费用(元) |\n")
    lines.append("|------|---------|------------|-------------|------------|----------|\n")
    row_cost = 0
    for pt in sorted(phases.keys()):
        s = phases[pt]
        pct = s["total"] / total["total"] * 100 if total["total"] else 0
        lines.append(f"| {pt} | {s['calls']} | {s['prompt']:,} | {s['completion']:,} | {s['total']:,} ({pct:.1f}%) | ¥{s['cost']:.4f} |\n")
        row_cost += s["cost"]
    lines.append(f"| **合计** | **{total['calls']}** | **{total['prompt']:,}** | **{total['completion']:,}** | **{total['total']:,}** | **¥{cost:.4f}** |\n")

    if records:
        lines.append("\n## 时间分布\n\n")
        times = sorted([r.get("timestamp", "") for r in records if r.get("timestamp")])
        if len(times) >= 2:
            lines.append(f"- 首次调用：{times[0]}\n")
            lines.append(f"- 末次调用：{times[-1]}\n")
            try:
                t0 = datetime.fromisoformat(times[0])
                t1 = datetime.fromisoformat(times[-1])
                delta = t1 - t0
                hours = delta.total_seconds() / 3600
                lines.append(f"- 总耗时：{delta.total_seconds() / 60:.1f} 分钟 ({hours:.1f} 小时)\n")
            except Exception:
                pass

    return "".join(lines)
