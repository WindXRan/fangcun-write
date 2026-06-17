"""metrics 历史快照 + 版本间 diff。

每次 validate 跑完自动存一份快照到 metrics_history.json。
python tools/metrics_history.py --diff 查看最后一次的指标变化。
"""

import json
import re
from datetime import datetime
from pathlib import Path

_HISTORY_FILE = "metrics_history.json"


def _collect_prompt_snapshot(rewrites_dir):
    """从 chapters/ 文件末行提取 prompt 版本分布。"""
    return {}


def save_snapshot(rewrites_dir, chapter_metrics):
    """追加一条 metrics 快照。

    Args:
        rewrites_dir: 项目 rewrites 目录
        chapter_metrics: [{ch, chars, metaphor, ai_markers, direct_emotion, status}, ...]
    """
    path = Path(rewrites_dir) / _HISTORY_FILE
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "prompts": _collect_prompt_snapshot(rewrites_dir),
        "chapters": chapter_metrics,
    }
    # 聚合统计
    if chapter_metrics:
        ok = [c for c in chapter_metrics if c.get("status") == "PASS"]
        entry["summary"] = {
            "total": len(chapter_metrics),
            "pass": len(ok),
            "fail": len(chapter_metrics) - len(ok),
            "avg_chars": sum(c["chars"] for c in chapter_metrics) / len(chapter_metrics),
            "avg_metaphor": sum(c["metaphor"] for c in chapter_metrics) / len(chapter_metrics),
            "avg_ai_markers": sum(c["ai_markers"] for c in chapter_metrics) / len(chapter_metrics),
            "avg_direct_emotion": sum(c["direct_emotion"] for c in chapter_metrics) / len(chapter_metrics),
            "avg_pronoun_density": sum(c.get("pronoun_density", 0) for c in chapter_metrics) / len(chapter_metrics),
            "avg_sent_len_stddev": sum(c.get("sent_len_stddev", 0) for c in chapter_metrics) / len(chapter_metrics),
        }

    history.append(entry)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def get_history(rewrites_dir):
    """读取全部历史快照。"""
    path = Path(rewrites_dir) / _HISTORY_FILE
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(val, old=None):
    """格式化数值，如果有 old 则显示变化方向。"""
    s = f"{val:.1f}"
    if old is not None:
        diff = val - old
        if abs(diff) < 0.01:
            s += "  —"
        elif diff > 0:
            s += f"  +{diff:.1f}  \u2191"
        else:
            s += f"  {diff:.1f}  \u2193"
    return s


def print_diff(rewrites_dir):
    """对比最后两次快照，打印变化表。"""
    history = get_history(rewrites_dir)
    if len(history) < 2:
        print("[INFO] 需要至少 2 次 validate 记录才能对比")
        return

    a, b = history[-2], history[-1]
    print(f"\n{'=' * 55}")
    print(f"Prompt 版本对比")
    print(f"  v1: {a['timestamp']}")
    print(f"  v2: {b['timestamp']}")
    print(f"{'=' * 55}")

    # Prompt 版本变化
    print(f"\n--- Prompt 分布 ---")
    all_keys = sorted(set(list(a.get("prompts", {}).keys()) + list(b.get("prompts", {}).keys())))
    changed_prompts = []
    for k in all_keys:
        va = a.get("prompts", {}).get(k, 0)
        vb = b.get("prompts", {}).get(k, 0)
        if va != vb:
            changed_prompts.append(k)
            print(f"  {k}: {va}章 \u2192 {vb}章")
        else:
            print(f"  {k}: {va}章    {vb}章")

    # 指标变化
    sa, sb = a.get("summary"), b.get("summary")
    if not sa or not sb:
        print("\n[WARN] 快照缺少聚合数据")
        return

    print(f"\n--- 指标变化 ---")
    print(f"{'指标':<20} {'v1':>8} {'v2':>8} {'变化':>8}")
    print("-" * 50)
    for key, label in [("avg_chars", "字数"), ("avg_metaphor", "比喻/章"),
                       ("avg_ai_markers", "AI路标词/章"), ("avg_direct_emotion", "直抒情/章"),
                       ("avg_pronoun_density", "代词密/千字"), ("avg_sent_len_stddev", "句长标准差")]:
        va = sa.get(key, 0)
        vb = sb.get(key, 0)
        diff = vb - va
        if key == "avg_chars":
            arrow = " \u2191" if diff > 0 else (" \u2193" if diff < 0 else "  \u2014")
            print(f"{label:<20} {va:>8.0f} {vb:>8.0f} {diff:>+8.0f}{arrow}")
        else:
            better = diff < 0  # AI词/比喻/直抒情 少是好
            arrow = " \u2713" if (diff < 0 and better) else (" \u2717" if diff > 0 else "  \u2014")
            print(f"{label:<20} {va:>8.2f} {vb:>8.2f} {diff:>+8.2f}{arrow}")

    # 通过率
    print(f"\n--- 通过率 ---")
    pa, fa = sa["pass"], sa["fail"]
    pb, fb = sb["pass"], sb["fail"]
    ra = pa / sa["total"] * 100 if sa["total"] else 0
    rb = pb / sb["total"] * 100 if sb["total"] else 0
    arrow = '\u2191' if rb > ra else '\u2193'
    print(f"  v1: {pa}/{sa['total']} ({ra:.0f}%)  |  v2: {pb}/{sb['total']} ({rb:.0f}%)"
          + (f"  {arrow}" if rb != ra else ""))

    return changed_prompts


_DEGRADE_THRESHOLDS = {
    "pass_rate_drop": 0.05,
    "ai_markers_rise": 0.5,
    "emotion_rise": 0.5,
    "metaphor_rise": 0.5,
    "pronoun_deviation": 2.0,
    "sent_stddev_deviation": 2.0,
}


def auto_rollback_if_degraded(rewrites_dir):
    """检查最后两次 validate 结果，退化时自动 git checkout 回滚 prompt。"""
    history = get_history(rewrites_dir)
    if len(history) < 2:
        return False

    a, b = history[-2], history[-1]
    sa, sb = a.get("summary"), b.get("summary")
    if not sa or not sb:
        return False

    degrade_reasons = []

    ra = sa["pass"] / sa["total"] if sa["total"] else 1
    rb = sb["pass"] / sb["total"] if sb["total"] else 0
    if rb < ra - _DEGRADE_THRESHOLDS["pass_rate_drop"]:
        degrade_reasons.append(f"通过率 {ra:.0%}→{rb:.0%}")

    ai_diff = sb["avg_ai_markers"] - sa["avg_ai_markers"]
    if ai_diff > _DEGRADE_THRESHOLDS["ai_markers_rise"]:
        degrade_reasons.append(f"AI路标词 +{ai_diff:.1f}/章")

    em_diff = sb["avg_direct_emotion"] - sa["avg_direct_emotion"]
    if em_diff > _DEGRADE_THRESHOLDS["emotion_rise"]:
        degrade_reasons.append(f"直抒情 +{em_diff:.1f}/章")

    pd_diff = abs(sb.get("avg_pronoun_density", 0) - sa.get("avg_pronoun_density", 0))
    if pd_diff > _DEGRADE_THRESHOLDS["pronoun_deviation"]:
        degrade_reasons.append(f"代词密度偏移 {pd_diff:.1f}/千字")

    ss_diff = abs(sb.get("avg_sent_len_stddev", 0) - sa.get("avg_sent_len_stddev", 0))
    if ss_diff > _DEGRADE_THRESHOLDS["sent_stddev_deviation"]:
        degrade_reasons.append(f"句长标准差偏移 {ss_diff:.1f}")

    if not degrade_reasons:
        return False

    old_prompts = a.get("prompts", {})
    new_prompts = b.get("prompts", {})
    changed = []
    for key in set(list(old_prompts.keys()) + list(new_prompts.keys())):
        if old_prompts.get(key) != new_prompts.get(key):
            name = key.rsplit("@", 1)[0]
            if name and name not in changed:
                changed.append(name)

    if not changed:
        return False

    print("\n" + "!" * 50)
    print(f"[DEGRADE] {'; '.join(degrade_reasons)}")
    print(f"[ROLLBACK] 回滚 {', '.join(changed)}")

    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    rolled_back = []
    for name in changed:
        path = prompts_dir / name
        if not path.exists():
            continue
        try:
            import subprocess
            subprocess.run(["git", "checkout", "--", str(path)], capture_output=True, text=True,
                           encoding="utf-8", cwd=path.parent)
            rolled_back.append(name)
        except Exception as e:
            print(f"  [FAIL] git checkout {name}: {e}")

    if not rolled_back:
        return False

    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"),
             "event": "auto_rollback", "reason": "; ".join(degrade_reasons),
             "rolled_back": rolled_back, "reverted_to": old_prompts}
    hp = Path(rewrites_dir) / _HISTORY_FILE
    hd = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else []
    hd.append(entry)
    hp.write_text(json.dumps(hd, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ROLLBACK] 完成: {', '.join(rolled_back)}")
    print("!" * 50)
    return True


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--diff":
        changed = print_diff(sys.argv[2])
        if changed and ("--auto-rollback" in sys.argv or "-r" in sys.argv):
            auto_rollback_if_degraded(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "--auto-rollback":
        auto_rollback_if_degraded(sys.argv[2])
    else:
        print("用法:")
        print("  python tools/metrics_history.py --diff <rewrites_dir> [--auto-rollback]")
        print("  python tools/metrics_history.py --auto-rollback <rewrites_dir>")
