"""Loop Engine — 全自动 prompt 迭代优化。

用法:
  python loop_engine.py --config xxx.json --start 1 --end 10 --max-loops 5

流程:
  1. 写章 (当前 prompt version)
  2. 校验 (validate + 算法指标)
  3. 对比 (vs 最优记录)
  4. 决策 (保留/回滚/建议修改)
  5. 版本 (自动 bump + 记录 history)
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class LoopMetrics:
    """单轮循环的指标快照。"""
    loop: int
    timestamp: str
    prompt_versions: dict  # {prompt_name: version}
    chapters: dict  # {ch: {score, issues_count, chars, ai_markers, plagiarism, emotion}}
    summary: dict    # {total_ch, avg_score, total_issues, ai_markers, plagiarism_count, emotion_count, chars_deviation}

@dataclass
class LoopHistory:
    """循环历史记录。"""
    config: str
    chapter_range: list
    started: str
    best_loop: int = 0
    best_score: float = 0
    loops: list = field(default_factory=list)
    prompt_changelog: list = field(default_factory=list)


def _collect_metrics(config, start, end):
    """收集当前产出所有指标（validate + unified review）。"""
    chapters_dir = Path(config["rewrites_dir"]) / "chapters"

    chapters = {}
    total_issues = 0
    total_ai = 0
    total_plag = 0
    total_emo = 0
    scores = []

    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        from phases.validate import validate_one
        result = validate_one(config, ch)
        chapters[ch] = result

        issues = result.get("issues", [])
        total_issues += len(issues)
        total_ai += sum(1 for i in issues if "AI" in str(i))
        total_plag += sum(1 for i in issues if "雷同" in str(i) or "plagiarism" in str(i))
        total_emo += sum(1 for i in issues if "直抒" in str(i) or "emotion" in str(i))
        scores.append(result.get("score", 100))

    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    # 字数偏差
    from utils import count_source_chars, get_body_chars
    dev_total = 0
    for ch in range(start, end + 1):
        cf = chapters_dir / f"ch_{ch:03d}.txt"
        if cf.exists():
            src = count_source_chars(config, ch)
            body = get_body_chars(cf.read_text(encoding='utf-8'))
            if src > 0:
                dev_total += abs(body - src) / src
    avg_dev = round(dev_total / max(len(chapters), 1) * 100, 1)

    # Unified review (dry-run: 只审不改)
    review_stats = {"p0": 0, "p1": 0, "p2": 0, "cross_issues": 0}
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if api_key:
        try:
            from unified_fixer import run_pipeline as unified_run
            tasks, report = unified_run(
                config, start, end, api_key=api_key,
                api_url=None, model=config.get("model", "deepseek-v4-flash"),
                batch_size=max(5, (end - start + 1) // 2),
                workers=2, dry_run=True,
            )
            for ch_data in report.values():
                for iss in ch_data.get("issues", []):
                    p = iss.get("priority", "P2")
                    if p in review_stats:
                        review_stats[p] += 1
            # 跨章问题
            review_stats["cross_issues"] = sum(
                1 for ch_data in report.values()
                for iss in ch_data.get("issues", [])
                if iss.get("type") in ("character", "continuity", "rhythm")
            )
        except Exception as e:
            print(f"        审改跳过: {e}")

    return LoopMetrics(
        loop=0,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        prompt_versions=_get_prompt_versions(),
        chapters=chapters,
        summary={
            "total_ch": len(chapters),
            "avg_score": avg_score,
            "total_issues": total_issues,
            "ai_markers": total_ai,
            "plagiarism_count": total_plag,
            "emotion_count": total_emo,
            "chars_deviation_pct": avg_dev,
            "p0": review_stats["p0"],
            "p1": review_stats["p1"],
            "p2": review_stats["p2"],
            "cross_issues": review_stats["cross_issues"],
        }
    )


def _get_prompt_versions():
    """读取当前所有 prompt 的 version。"""
    prompts_dir = Path(".agents/skills/story-engine/prompts")
    versions = {}
    for f in sorted(prompts_dir.glob("*.md")):
        text = f.read_text(encoding='utf-8')
        m = re.search(r'version:\s*(\d+)', text)
        if m:
            versions[f.stem] = int(m.group(1))
    return versions


def _compare_metrics(current: LoopMetrics, best: LoopMetrics):
    """对比两轮指标，返回改进/退化的维度。"""
    s = current.summary
    b = best.summary

    improved = []
    degraded = []

    checks = [
        ("avg_score", "均分", True),
        ("total_issues", "问题数", False),
        ("ai_markers", "AI痕迹", False),
        ("plagiarism_count", "台词雷同", False),
        ("emotion_count", "直抒情", False),
        ("chars_deviation_pct", "字数偏差%", False),
        ("p0", "审改P0", False),
        ("p1", "审改P1", False),
        ("cross_issues", "跨章问题", False),
    ]

    for key, label, higher_better in checks:
        cv = s.get(key, 0)
        bv = b.get(key, 0)
        if bv == 0:
            continue
        delta = (cv - bv) / bv * 100
        if abs(delta) < 3:  # <3% 不算显著变化
            continue
        if higher_better:
            (improved if delta > 0 else degraded).append((label, delta))
        else:
            (improved if delta < 0 else degraded).append((label, delta))

    return improved, degraded


def _suggest_prompt_changes(improved, degraded, current_metrics):
    """根据指标变化建议 prompt 修改。"""
    suggestions = []
    for label, delta in degraded:
        if "台词雷同" in label:
            suggestions.append({
                "prompt": "write-chapter.md",
                "action": "强化换皮规则",
                "detail": "在写作要求中加入'每写完一段检查是否与源文有连续4字相同'",
                "severity": "high" if delta > 20 else "medium",
            })
        elif "AI痕迹" in label:
            suggestions.append({
                "prompt": "system-generic.md",
                "action": "扩充防AI词表",
                "detail": f"AI痕迹增加{delta:.0f}%，建议追加禁用词或强化句首限制",
                "severity": "high" if delta > 30 else "medium",
            })
        elif "直抒情" in label:
            suggestions.append({
                "prompt": "system-generic.md",
                "action": "强化情绪禁令",
                "detail": "在情绪规则中加入更多禁用词（心揪/发紧/发闷/涌起）",
                "severity": "high" if delta > 20 else "medium",
            })
        elif "字数偏差" in label:
            suggestions.append({
                "prompt": "write-chapter.md",
                "action": "调整字数控制",
                "detail": f"字数偏差{delta:.0f}%，考虑调整目标字数范围或max_tokens",
                "severity": "medium" if abs(delta) < 30 else "high",
            })
        elif "问题数" in label:
            suggestions.append({
                "prompt": "write-chapter.md",
                "action": "综合质量下降",
                "detail": f"总问题数增加{delta:.0f}%，建议重跑或回滚到上一版prompt",
                "severity": "high",
            })
        elif "审改" in label or "跨章" in label:
            suggestions.append({
                "prompt": "unified-review.md",
                "action": "审改质量退化",
                "detail": f"{label}增加{delta:.0f}%，unified-review prompt 需加强该维度审查力度",
                "severity": "high" if "P0" in label else "medium",
            })

    return suggestions


def _print_report(loop_num, metrics, improved, degraded, suggestions, best_loop):
    """打印本轮循环报告。"""
    s = metrics.summary
    print(f"\n{'='*60}")
    print(f"  Loop #{loop_num} 报告" + (" ★ 最优" if loop_num == best_loop else ""))
    print(f"{'='*60}")
    print(f"  {s['total_ch']}章 | 均分:{s['avg_score']} | 问题:{s['total_issues']}")
    print(f"  AI痕迹:{s['ai_markers']} | 雷同:{s['plagiarism_count']} | 直抒:{s['emotion_count']} | 字数偏差:{s['chars_deviation_pct']}%")
    print(f"  审改: P0:{s.get('p0',0)} P1:{s.get('p1',0)} P2:{s.get('p2',0)} | 跨章:{s.get('cross_issues',0)}")

    if improved:
        print(f"\n  ▲ 改进: {', '.join(f'{l}({d:+.0f}%)' for l, d in improved)}")
    if degraded:
        print(f"  ▼ 退化: {', '.join(f'{l}({d:+.0f}%)' for l, d in degraded)}")

    if suggestions:
        print(f"\n  → 建议修改:")
        for sug in suggestions:
            icon = "!!" if sug["severity"] == "high" else "! "
            print(f"    {icon} [{sug['prompt']}] {sug['action']}: {sug['detail']}")

    if not improved and not degraded:
        print(f"  → 无显著变化，可考虑下一轮或结束迭代")


def run_loop(config_path, start, end, max_loops=5, auto_apply=False):
    """主循环：跑→测→比→改→版本。"""
    config = json.loads(open(config_path, encoding='utf-8').read())
    base_dir = config.get("base_dir", os.getcwd())
    config.setdefault("base_dir", base_dir)

    # 对齐路径
    rw = config.get("rewrites_dir", "")
    if rw and not Path(rw).is_absolute():
        config["rewrites_dir"] = str(Path(base_dir) / rw)

    config["debug"] = True  # loop 模式自动启用 debug

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return

    history_path = Path(config["rewrites_dir"]) / "_loop_history.json"
    history = LoopHistory(config=config_path, chapter_range=[start, end],
                          started=time.strftime("%Y-%m-%d %H:%M:%S"))

    print(f"Loop Engine | {config['book_name']} | ch{start}-{end} | max {max_loops} 轮")
    print(f"  初始 prompt versions: {_get_prompt_versions()}")

    best_metrics = None

    for loop_num in range(1, max_loops + 1):
        print(f"\n{'─'*60}")
        print(f"  Loop #{loop_num}/{max_loops}")
        print(f"{'─'*60}")

        # 1. WRITE
        print(f"  [1/4] 写章...")
        from phases.write import phase_write
        t0 = time.time()
        phase_write(config, start, end, workers=config.get("workers", 5))
        print(f"        写章耗时 {time.time()-t0:.0f}s")

        # 2. MEASURE
        print(f"  [2/4] 校验...")
        metrics = _collect_metrics(config, start, end)
        metrics.loop = loop_num

        # 3. COMPARE
        print(f"  [3/4] 对比...")
        if best_metrics is None:
            best_metrics = metrics
            history.best_loop = loop_num
            history.best_score = metrics.summary["avg_score"]
            print(f"        首轮 → 设为基线")
        else:
            improved, degraded = _compare_metrics(metrics, best_metrics)
            suggestions = _suggest_prompt_changes(improved, degraded, metrics)

            s = metrics.summary
            better = s["avg_score"] > best_metrics.summary["avg_score"]

            if better or not degraded:
                # 保留
                best_metrics = metrics
                history.best_loop = loop_num
                history.best_score = s["avg_score"]
                print(f"        保留本轮 (均分 {s['avg_score']} vs 最优 {best_metrics.summary['avg_score']})")

            _print_report(loop_num, metrics, improved, degraded, suggestions, history.best_loop)

        # 4. RECORD
        history.loops.append(asdict(metrics))

        # 5. AUTO-BUMP (if improved and auto mode)
        if loop_num == history.best_loop and loop_num > 1 and auto_apply:
            print(f"  [4/4] Auto-bump...")
            from prompt_loader import bump_prompt
            bump_prompt("write-chapter.md", f"loop#{loop_num} auto-optimize")
            history.prompt_changelog.append({
                "loop": loop_num,
                "action": "bump write-chapter.md",
                "reason": f"均分 {metrics.summary['avg_score']} (vs prev {best_metrics.summary.get('avg_score', 0)})",
            })

        # 6. SAVE history
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(json.dumps(asdict(history), ensure_ascii=False, indent=2), encoding="utf-8")

        # 收敛检查
        if loop_num >= 3 and best_metrics.summary["avg_score"] >= 90 and best_metrics.summary["total_issues"] <= 2:
            print(f"\n  ✓ 收敛 (均分≥90, 问题≤2)，结束迭代")
            break

    print(f"\n{'='*60}")
    print(f"  迭代完成 | {len(history.loops)} 轮 | 最优: Loop #{history.best_loop} (均分 {history.best_score})")
    print(f"  历史: {history_path}")
    print(f"{'='*60}")

    return history


def main():
    parser = argparse.ArgumentParser(description="Loop Engine — 全自动 prompt 迭代")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--max-loops", type=int, default=5)
    parser.add_argument("--auto-apply", action="store_true", help="自动应用 prompt 修改 (默认仅建议)")
    args = parser.parse_args()

    run_loop(args.config, args.start, args.end, args.max_loops, args.auto_apply)


if __name__ == "__main__":
    main()
