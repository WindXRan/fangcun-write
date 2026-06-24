"""交付报告生成 — Markdown 格式的各章节报告模块。"""

import os
import re
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime

import _path_setup  # noqa: F401
from lib.token_tracker import get_usage, aggregate, format_report
from state_manager import StateManager


def file_hash(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


def fmt_size(n):
    for unit in ["B", "KB", "MB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def risk_badge(val, thresholds):
    if val <= thresholds[0]:
        return "✅ 正常"
    if val <= thresholds[1]:
        return "👌 可接受"
    return "⚠️ 偏高"


def collect_metrics(rewrites_dir):
    chapters_dir = Path(rewrites_dir) / "chapters"
    metrics = []
    if not chapters_dir.exists():
        return metrics
    from lib.text_metrics import count_metrics
    for f in sorted(chapters_dir.glob("ch_*.txt")):
        try:
            text = f.read_text(encoding="utf-8")
            m = count_metrics(text)
            m["file"] = f.name
            metrics.append(m)
        except Exception:
            pass
    return metrics


def plagiarism_summary(rewrites_abs, config, metrics):
    from lib.plagiarism import find_plagiarism
    from utils import get_source_text
    plag_count = 0
    total = 0
    chapters_dir = Path(rewrites_abs) / "chapters"
    for ch_file in sorted(chapters_dir.glob("ch_*.txt")):
        total += 1
        try:
            ch_num = int(ch_file.stem.split("_")[1])
            new_text = ch_file.read_text(encoding="utf-8")
            src_text = get_source_text(config, ch_num)
            if src_text and find_plagiarism(new_text, src_text, min_gram=8):
                plag_count += 1
        except Exception:
            pass
    if total == 0:
        return ""
    pct = plag_count / total * 100
    return f"- **台词雷同检测**：{plag_count}/{total} 章 ({pct:.0f}%) 存在 8 字以上连续匹配{' ⚠️' if pct > 5 else ' ✅'}\n"


def build_report(config, rewrites_abs, output_dir, metrics, html_copied=False):
    """构建完整的 03_交付报告.md。"""
    usage_records = get_usage(str(rewrites_abs))
    sm = StateManager(str(rewrites_abs))
    state = sm.load()
    source_book = config.get("source_book", "源文")
    new_book = config.get("book_name", "仿写书")
    author = config.get("author", "")
    out = Path(output_dir)

    parts = []
    parts.append(f"# 交付报告 — 《{new_book}》\n\n")
    parts.append(f"**源文**：《{source_book}》（作者：{author}）  \n")
    parts.append(f"**仿写成品**：《{new_book}》  \n")
    parts.append(f"**生成日期**：{datetime.now().strftime('%Y-%m-%d')}  \n")
    parts.append(f"**成品校验**：`{file_hash(out / f'01_成品_{new_book}.txt')}`\n\n")

    # === 一、总体概览 ===
    parts.append("---\n## 一、总体概览\n\n")
    parts.append(_build_overview(metrics, usage_records, state, config, rewrites_abs))

    # === 二、Token 消耗 ===
    parts.append("\n---\n## 二、Token 消耗\n\n")
    parts.append(_build_token_report(usage_records))

    # === 三、时间统计 ===
    parts.append("\n---\n## 三、时间统计\n\n")
    parts.append(_build_timing_report(state))

    # === 四、质量指标 ===
    parts.append("\n---\n## 四、质量指标\n\n")
    parts.append(_build_quality_short(metrics))
    parts.append("\n<details>\n<summary>点击展开每章明细</summary>\n\n")
    parts.append(_build_quality_detail(metrics))
    parts.append("\n</details>\n")

    # === 五、AI 痕迹风险评估 ===
    parts.append("\n---\n## 五、AI 痕迹风险评估\n\n")
    parts.append(_build_risk_assessment(metrics))

    # === 六、审查结果 ===
    last_review = state.get("last_review")
    if last_review:
        parts.append("\n---\n## 六、审查结果\n\n")
        parts.append(f"| 指标 | 数值 |\n|------|------|\n")
        parts.append(f"| 平均分 | {last_review.get('avg_score', 'N/A')} |\n")
        parts.append(f"| 通过 | {last_review.get('pass', 0)} 章 |\n")
        parts.append(f"| 失败 | {last_review.get('fail', 0)} 章 |\n")
        parts.append(f"| 问题总数 | {last_review.get('total_issues', 0)} |\n")
        parts.append(f"| 高优先级 | {last_review.get('high_issues', 0)} |\n")

    # === 七、文件清单 ===
    parts.append("\n---\n## 七、文件清单\n\n")
    parts.append(_build_file_list(out))

    return "".join(parts)


def _build_overview(metrics, usage_records, state, config, rewrites_abs):
    lines = []
    if metrics:
        total_chars = sum(m["chars"] for m in metrics)
        avg_ai = sum(m["ai_markers"] for m in metrics) / len(metrics)
        avg_chars = total_chars / len(metrics)
        lines.append(f"- **总章节**：{len(metrics)} 章\n")
        lines.append(f"- **总字数**：{total_chars:,}\n")
        lines.append(f"- **平均字数/章**：{avg_chars:.0f}\n")
        lines.append(f"- **AI路标词/章**：{avg_ai:.1f}\n")
        lines.append(plagiarism_summary(rewrites_abs, config, metrics))

    _, total_token = aggregate(usage_records) if usage_records else (None, {"total": 0, "cost": 0.0})
    lines.append(f"- **Token 消耗**：{total_token['total']:,}（约 ¥{total_token['cost']:.2f}）\n")

    elapsed = _calc_elapsed(state)
    if elapsed:
        lines.append(f"- **总耗时**：{elapsed:.0f} 分钟 ({elapsed/60:.1f} 小时)\n")

    return "".join(lines)


def _calc_elapsed(state):
    total = 0
    for info in state.get("phases", {}).values():
        s, f = info.get("started"), info.get("finished")
        if s and f:
            try:
                total += (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds() / 60
            except Exception:
                pass
    return total


def _build_token_report(usage_records):
    lines = []
    if usage_records:
        lines.append(format_report(usage_records))

        # 按模型拆分
        by_model = {}
        for r in usage_records:
            m = r.get("model", "unknown")
            by_model.setdefault(m, {"calls": 0, "prompt": 0, "completion": 0, "cost": 0.0})
            prices = {"deepseek-v4-pro": (0.004, 0.012), "deepseek-v4-flash": (0.0005, 0.002)}
            pi, po = prices.get(m, (0.004, 0.012))
            by_model[m]["calls"] += 1
            by_model[m]["prompt"] += r.get("prompt_tokens", 0)
            by_model[m]["completion"] += r.get("completion_tokens", 0)
            by_model[m]["cost"] += (r.get("prompt_tokens", 0) / 1000 * pi) + (r.get("completion_tokens", 0) / 1000 * po)

        if len(by_model) > 1:
            lines.append("\n### 按模型拆分\n\n")
            lines.append("| 模型 | 调用次数 | 输入 tokens | 输出 tokens | 费用(元) |\n")
            lines.append("|------|---------|------------|-------------|----------|\n")
            total_cost = 0
            for m in sorted(by_model.keys()):
                d = by_model[m]
                total_cost += d["cost"]
                lines.append(f"| {m} | {d['calls']} | {d['prompt']:,} | {d['completion']:,} | ¥{d['cost']:.4f} |\n")
            lines.append(f"| **合计** | | | | **¥{total_cost:.4f}** |\n")
    else:
        lines.append("（尚未记录 Token 消耗，下次 API 调用后自动生成）\n")
    return "".join(lines)


def _build_timing_report(state):
    lines = []
    phases = state.get("phases", {})
    if not phases:
        return "（无阶段数据）\n"

    order = ["prep", "open_book", "extract", "guides", "write", "validate",
             "postfix", "compare", "trim", "rewrite", "polish", "expand"]
    lines.append("| 阶段 | 状态 | 耗时(分钟) |\n|------|------|-----------|\n")
    total_mins = 0
    for pname in order:
        info = phases.get(pname)
        if not info:
            continue
        s, f = info.get("started"), info.get("finished")
        dur = ""
        if s and f:
            try:
                mins = (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds() / 60
                dur = f"{mins:.1f}"
                total_mins += mins
            except Exception:
                pass
        lines.append(f"| {pname} | {info.get('status', '?')} | {dur} |\n")
    lines.append(f"\n**总耗时**：{total_mins:.1f} 分钟 ({total_mins/60:.1f} 小时)\n")

    chapters = state.get("chapters", {})
    if chapters:
        total = len(chapters)
        ok = sum(1 for c in chapters.values() if c.get("status") in ("completed", "approved"))
        fail = sum(1 for c in chapters.values() if c.get("status") == "failed")
        lines.append(f"\n**章节完成**：{ok}/{total} 成功，{fail} 失败\n")

    runs = state.get("runs", [])
    if runs:
        lines.append(f"\n**执行轮次**：{len(runs)} 次\n")
        for r in runs[-5:]:
            lines.append(f"- {r.get('phase')} ch{r.get('range')} ok={r.get('ok')} fail={r.get('fail')}\n")
    return "".join(lines)


def _build_quality_short(metrics):
    if not metrics:
        return "（无章节数据）\n"
    total_chars = sum(m["chars"] for m in metrics)
    avg_ai = sum(m["ai_markers"] for m in metrics) / len(metrics)
    avg_emotion = sum(m["direct_emotion"] for m in metrics) / len(metrics)
    avg_metaphor = sum(m["metaphor"] for m in metrics) / len(metrics)
    avg_pronoun = sum(m.get("pronoun_density", 0) for m in metrics) / len(metrics)
    avg_chars = total_chars / len(metrics)
    low, high = avg_chars * 0.8, avg_chars * 1.2
    outliers = sum(1 for m in metrics if m["chars"] < low or m["chars"] > high)

    lines = []
    lines.append("| 指标 | 数值 | 评估 |\n|------|------|------|\n")
    lines.append(f"| 总章节 | {len(metrics)} | — |\n")
    lines.append(f"| 总字数 | {total_chars:,} | — |\n")
    lines.append(f"| 均章字数 | {avg_chars:.0f} | — |\n")
    lines.append(f"| 字数偏差>20% | {outliers} 章 ({outliers/len(metrics)*100:.0f}%) | {risk_badge(outliers/len(metrics)*100, [15, 30])} |\n")
    lines.append(f"| AI路标词/章 | {avg_ai:.1f} | {risk_badge(avg_ai, [1, 3])} |\n")
    lines.append(f"| 直抒情/章 | {avg_emotion:.1f} | {risk_badge(avg_emotion, [2, 5])} |\n")
    lines.append(f"| 比喻/章 | {avg_metaphor:.1f} | {risk_badge(avg_metaphor, [1, 5])} |\n")
    lines.append(f"| 代词密度/千字 | {avg_pronoun:.1f} | {risk_badge(avg_pronoun, [30, 60])} |\n")
    return "".join(lines)


def _build_quality_detail(metrics):
    if not metrics:
        return ""
    lines = ["| 章节 | 字数 | 比喻 | AI词 | 直抒情 | 代词/千字 | 句长σ |\n",
             "|------|------|------|-------|--------|-----------|-------|\n"]
    for m in metrics[:500]:
        lines.append(f"| {m['file']} | {m['chars']} | {m['metaphor']} | {m['ai_markers']} | "
                     f"{m['direct_emotion']} | {m['pronoun_density']} | {m['sent_len_stddev']} |\n")
    if len(metrics) > 500:
        lines.append(f"| ... 共 {len(metrics)} 章，仅展示前 500 章 |\n")
    return "".join(lines)


def _build_risk_assessment(metrics):
    if not metrics:
        return "（无数据）\n"
    avg_ai = sum(m["ai_markers"] for m in metrics) / len(metrics)
    avg_emotion = sum(m["direct_emotion"] for m in metrics) / len(metrics)
    avg_metaphor = sum(m["metaphor"] for m in metrics) / len(metrics)
    avg_pronoun = sum(m.get("pronoun_density", 0) for m in metrics) / len(metrics)

    lines = []
    lines.append("| 风险维度 | 检测项 | 标准 | 结果 |\n")
    lines.append("|----------|--------|------|------|\n")
    lines.append(f"| AI路标词 | `因此/然而/总之` 等 | ≤源文+1 | {avg_ai:.1f}/章 {'✅' if avg_ai <= 1 else '⚠️' if avg_ai <= 3 else '❌'} |\n")
    lines.append(f"| 直抒情感 | `她感到/她心里/一股暖流` | ≤源文+2 | {avg_emotion:.1f}/章 {'✅' if avg_emotion <= 2 else '⚠️' if avg_emotion <= 5 else '❌'} |\n")
    lines.append(f"| 比喻密度 | `像/仿佛/如同` 等 | ≤源文+3 | {avg_metaphor:.1f}/章 {'✅' if avg_metaphor <= 1 else '⚠️' if avg_metaphor <= 5 else '❌'} |\n")
    lines.append(f"| 代词密度 | 她/他/它 频率 | 接近源文 | {avg_pronoun:.1f}/千字 {'✅' if avg_pronoun <= 30 else '⚠️' if avg_pronoun <= 60 else '❌'} |\n")
    return "".join(lines)


def _build_file_list(output_dir):
    out = Path(output_dir)
    lines = ["| 文件 | 大小 | SHA256 |\n|------|------|--------|\n"]
    for f in sorted(out.iterdir()):
        if f.is_file() and f.suffix in (".md", ".txt", ".html"):
            lines.append(f"| {f.name} | {fmt_size(f.stat().st_size)} | `{file_hash(f)}` |\n")
    for d in sorted(out.iterdir()):
        if d.is_dir():
            nf = len(list(d.rglob("*")))
            lines.append(f"| {d.name}/ | {nf} 个文件 | — |\n")
    return "".join(lines)
