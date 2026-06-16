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


def _collect_metrics(config, start, end, chapters_subdir=None):
    """收集当前产出所有指标（validate + unified review）。"""
    if chapters_subdir:
        chapters_dir = Path(config["rewrites_dir"]) / chapters_subdir / "chapters"
    else:
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
        passed, report, metrics = validate_one(config, ch)
        chapters[ch] = {"passed": passed, "report": report, "metrics": metrics}

        # 按问题严重度扣分
        iss = report.count("*ISSUE*")
        score = 100 - iss * 10 if passed else 50
        score = max(0, min(100, score))
        scores.append(score)

        total_issues += iss
        total_ai += len(re.findall(r'AI|ai_marker|路标', report))
        total_plag += len(re.findall(r'雷同|plagiarism|台词', report))
        total_emo += len(re.findall(r'直抒|emotion', report))

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
            from lib.api_client import get_api_url
            tasks, report = unified_run(
                config, start, end, api_key=api_key,
                api_url=get_api_url(config), model=config.get("model", "deepseek-v4-flash"),
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


def _strengthen_prompts_from_issues(p0_issues):
    """根据 P0 问题映射到具体 prompt 规则，精准强化。"""
    changes = []
    seen = set()

    for iss in p0_issues:
        typ = iss.get("type", "")
        desc = iss.get("desc", "")

        # 映射表
        if typ in ("character", "人设漂移", "character_drift"):
            key = "character"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "write-chapter.md",
                    "action": "强化角色行为约束",
                    "reason": desc[:80],
                    "apply": lambda: _strengthen_prompt_rule("write-chapter.md", "角色行为约束"),
                })

        elif typ in ("plagiarism", "台词雷同", "plagiarism_text"):
            key = "plagiarism"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "system-generic.md",
                    "action": "强化换皮规则",
                    "reason": desc[:80],
                    "apply": lambda: _strengthen_prompt_rule("system-generic.md", "剥掉人名地名"),
                })

        elif typ in ("emotion", "直抒情", "emotion_tell"):
            key = "emotion"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "system-generic.md",
                    "action": "追加情绪禁词",
                    "reason": desc[:80],
                    "apply": lambda: _add_words_to_prompt("system-generic.md", "情绪", "泛起的,涌动的,发紧的"),
                })

        elif typ in ("ai_marker", "ai_trace", "AI路标"):
            key = "ai"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "system-generic.md",
                    "action": "追加AI禁词",
                    "reason": desc[:80],
                    "apply": lambda: _add_words_to_prompt("system-generic.md", "路标词", "紧接着,转眼间,片刻后"),
                })

        elif typ in ("word_count", "字数"):
            key = "wordcount"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "write-chapter.md",
                    "action": "收紧字数控制",
                    "reason": desc[:80],
                    "apply": lambda: _strengthen_prompt_rule("write-chapter.md", "目标"),
                })

        elif typ in ("emotion_stage", "感情跳跃", "情感阶段"):
            key = "emotion_stage"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "write-chapter.md",
                    "action": "加感情渐进约束",
                    "reason": desc[:80],
                    "apply": lambda: _add_words_to_prompt("write-chapter.md", "写作要求", "感情发展不跳跃(陌生→在意→暧昧→确认)"),
                })

        elif typ in ("continuity", "连贯性", "节奏"):
            key = "continuity"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "plot-guide.md",
                    "action": "强化节拍衔接",
                    "reason": desc[:80],
                    "apply": lambda: _strengthen_prompt_rule("plot-guide.md", "本章自洽与前章连贯"),
                })

        elif typ in ("rhythm", "节奏断层"):
            key = "rhythm"
            if key not in seen:
                seen.add(key)
                changes.append({
                    "prompt": "write-chapter.md",
                    "action": "强化段落节奏规则",
                    "reason": desc[:80],
                    "apply": lambda: _strengthen_prompt_rule("write-chapter.md", "段尾"),
                })

    # Apply changes
    for c in changes:
        try:
            c["apply"]()
        except Exception as e:
            print(f"  [WARN] 应用失败: {c['prompt']} {c['action']}: {e}")

    return changes


def _save_prompt_snapshot():
    """备份所有 prompt 文件内容。"""
    prompts_dir = Path(".agents/skills/story-engine/prompts")
    snapshot = {}
    for f in prompts_dir.glob("*.md"):
        snapshot[f.name] = f.read_text(encoding="utf-8")
    return snapshot


def _restore_prompt_snapshot(snapshot):
    """从备份恢复 prompt 文件。"""
    prompts_dir = Path(".agents/skills/story-engine/prompts")
    for name, content in snapshot.items():
        (prompts_dir / name).write_text(content, encoding="utf-8")


def _strengthen_prompt_rule(prompt_name, keyword):
    """强化 prompt 正文中的某条规则——加粗标记。跳过YAML头。"""
    prompts_dir = Path(".agents/skills/story-engine/prompts")
    path = prompts_dir / prompt_name
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")
    sep_count = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            sep_count += 1
            continue
        if sep_count < 2:  # 跳过 YAML frontmatter
            continue
        if keyword in line and "**" not in line and line.strip():
            lines[i] = f"**{line.strip()}**"
            break
    path.write_text("\n".join(lines), encoding="utf-8")


def _add_words_to_prompt(prompt_name, keyword, words):
    """在 prompt 中包含关键词的行追加词。"""
    prompts_dir = Path(".agents/skills/story-engine/prompts")
    path = prompts_dir / prompt_name
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if keyword in line:
            new_words = [w for w in words.split(",") if w not in line]
            if new_words:
                content = content.replace(line, line.rstrip() + "/" + "/".join(new_words))
            break
    path.write_text(content, encoding="utf-8")


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

    config["debug"] = False  # loop 模式必须调 API，否则空转

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return

    # 输出目录
    loop_dir = Path(config["rewrites_dir"]) / "_loop"
    loop_dir.mkdir(parents=True, exist_ok=True)
    history_path = loop_dir / "_history.json"
    history = LoopHistory(config=config_path, chapter_range=[start, end],
                          started=time.strftime("%Y-%m-%d %H:%M:%S"))

    print(f"Loop Engine | {config['book_name']} | ch{start}-{end} | max {max_loops} 轮")
    progress_path = loop_dir / "_progress.md"

    def _log(msg):
        print(msg)
        with open(progress_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    progress_path.write_text(f"# Loop Progress\n\n**开始**: {time.strftime('%H:%M:%S')}\n\n", encoding="utf-8")

    # Prompt 迭代：写章→审查→分析规则失效→强化prompt→重写
    from phases.style_extract import phase_style_extract
    from phases.guides import phase_guides
    from phases.write import phase_write
    from unified_fixer import run_pipeline as unified_run
    from lib.api_client import get_api_url

    api_url = get_api_url(config)
    prev_p0 = float('inf')
    best_p0 = float('inf')
    best_prompt_state = None

    for loop_num in range(1, max_loops + 1):
        round_dir = loop_dir / f"loop_{loop_num}"
        round_dir.mkdir(parents=True, exist_ok=True)
        _log(f"\n---")
        _log(f"## Loop #{loop_num}/{max_loops}")

        # [1] Write with current prompts (备份旧章后清除，确保新prompt生效)
        if loop_num > 1:
            import shutil
            for d in ["chapters", "guides", "styles"]:
                p = Path(config["rewrites_dir"]) / d
                if p.exists():
                    # 备份到 _loop/loop_{N}/（当前轮次目录）
                    backup = round_dir / d
                    backup.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(p, backup, dirs_exist_ok=True)
                    shutil.rmtree(p)
        _log("写章...")
        t0 = time.time()
        phase_style_extract(config, start, end, workers=config.get("workers", 5))
        phase_guides(config, start, end, workers=config.get("workers", 5))
        phase_write(config, start, end, workers=config.get("workers", 5))
        _log(f"写章: {time.time()-t0:.0f}s")

        # [2] Review
        _log("审查...")
        tasks, report = unified_run(
            config, start, end, api_key=api_key, api_url=api_url,
            model=config.get("model", "deepseek-v4-flash"),
            batch_size=max(5, (end - start + 1) // 2),
            workers=3, dry_run=True,
        )
        p0 = sum(1 for ch_data in report.values()
                 for iss in ch_data.get("issues", []) if iss.get("priority") == "P0")
        p1 = sum(1 for ch_data in report.values()
                 for iss in ch_data.get("issues", []) if iss.get("priority") == "P1")
        _log(f"P0:{p0} P1:{p1}")

        # [3] Collect P0 issues and their types
        p0_issues = []
        for ch_str, ch_data in report.items():
            for iss in ch_data.get("issues", []):
                if iss.get("priority") == "P0":
                    p0_issues.append({"ch": ch_str, **iss})

        # Save review
        json.dump({"p0": p0, "p1": p1, "issues": p0_issues, "versions": _get_prompt_versions()},
                  (round_dir / "review.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

        # Convergence
        if p0 == 0:
            _log("P0=0 收敛！")
            break
        if p0 > prev_p0 or (p0 == prev_p0 and loop_num > 2):
            _log(f"P0 未改善 ({prev_p0}→{p0})，已达极限")
            break

        # Track best
        if p0 < best_p0:
            best_p0 = p0
            best_prompt_state = _get_prompt_versions()

        # [4] Smart editor
        _prompt_backup = _save_prompt_snapshot()
        _log("智能编辑分析...")
        try:
            from prompt_improver import smart_edit_loop
            result = smart_edit_loop(config, start, end, api_key, api_url, loop_num)
        except Exception as e:
            _log(f"智能编辑失败: {e}，恢复 prompt 快照")
            _restore_prompt_snapshot(_prompt_backup)
            continue
        _log(result["feedback"][:500])
        (round_dir / "feedback.md").write_text(result["feedback"], encoding="utf-8")
        for p in result["changes"]:
            _log(f"  [{p}] updated")

        if not result["changes"]:
            _log("智能编辑判断无需修改, 收敛")
            break

        prev_p0 = p0

    _log(f"\n完成: {loop_num}轮")
    print(f"\n进度 & 编辑意见: {progress_path}")
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
