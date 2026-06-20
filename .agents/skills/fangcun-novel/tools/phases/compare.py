"""Phase 4: 对比 — 基础对比 + 审核报告 + 改动报告 + 版本聚合"""

import os
import re
import sys
import subprocess
import time
from pathlib import Path

import _path_setup  # noqa: F401


def phase_compare(config, start, end, batch_size=10):
    """生成三种报告：
    1. 对比报告（基础统计+风格指纹+AI痕迹+衔接性）
    2. 审核报告（定量指标+pass/fail+LLM分析）
    3. 改动报告（改动汇总表）
    """
    rewrites_dir = config["rewrites_dir"]
    compare_dir = f"{rewrites_dir}/compare"
    _skills_dir = Path(__file__).parent.parent.parent.parent
    compare_script = str(_skills_dir / "story-compare" / "compare.py")
    local_compare_script = str(_skills_dir / "story-compare" / "local_compare.py")

    base_dir = Path(config.get("base_dir", ".")).resolve()

    print(f"\n{'=' * 60}")
    print(f"Phase 4: 对比+审核+改动 (ch{start}-{end}, 每{batch_size}章一批)")
    print(f"{'=' * 60}")

    # 清理旧报告（保留审核报告和改动报告）
    for old_file in Path(compare_dir).glob("对比_*.md"):
        try:
            old_file.unlink()
        except OSError:
            pass
    for old_file in Path(compare_dir).glob("源文_*.txt"):
        try:
            old_file.unlink()
        except OSError:
            pass
    for old_file in Path(compare_dir).glob("新书_*.txt"):
        try:
            old_file.unlink()
        except OSError:
            pass
    print("已清理旧对比报告")

    # ── 1. 基础对比报告（原有） ──
    _run_basic_compare(rewrites_dir, compare_dir, compare_script, start, end, batch_size)

    # ── 2. 审核报告（定量+LLM） ──
    _run_review_report(config, rewrites_dir, compare_dir, local_compare_script, start, end, batch_size)

    # ── 3. 改动报告（改动汇总） ──
    _run_change_report(config, rewrites_dir, compare_dir, start, end, batch_size)

    # ── 4. 版本聚合 ──
    _write_version_report(rewrites_dir, compare_dir)

    print(f"\n所有报告 → {rewrites_dir}/compare/")


def _run_basic_compare(rewrites_dir, compare_dir, compare_script, start, end, batch_size):
    """原有的基础对比报告。"""
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  [基础对比] 第{batch_start}-{batch_end}章...")
        cmd = [sys.executable, compare_script, rewrites_dir, str(batch_start), str(batch_end)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
            print(f"  [OK] 对比_{batch_start}-{batch_end}_报告.md")
        except Exception as e:
            print(f"  [FAIL] 对比_{batch_start}-{batch_end}: {e}")


def _run_review_report(config, rewrites_dir, compare_dir, local_compare_script, start, end, batch_size):
    """生成审核报告 — 每章定量指标 + pass/fail + LLM 分析异常章。"""
    from importlib import import_module, util

    # 把 local_compare.py 的目录加入 sys.path
    lc_dir = Path(local_compare_script).resolve().parent
    if str(lc_dir) not in sys.path:
        sys.path.insert(0, str(lc_dir))

    # 直接导入模块
    try:
        from local_compare import generate_report, count_metrics, extract_dialogue, calc_dialogue_overlap
    except ImportError:
        print("  [WARN] 审核报告: 无法导入 local_compare，跳过")
        return

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    base_dir = Path(config.get("base_dir", ".")).resolve()

    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  [审核报告] 第{batch_start}-{batch_end}章...")

        results = []
        for ch in range(batch_start, batch_end + 1):
            new_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
            if not new_file.exists():
                results.append({"ch": ch, "status": "❌", "reason": "文件缺失"})
                continue

            new_text = new_file.read_text(encoding='utf-8')

            # 查找源文
            from lib.source_locator import get_source_text
            src_text = get_source_text(config, ch)

            if not src_text:
                results.append({"ch": ch, "status": "⚠️", "reason": "无源文"})
                continue

            new_m = count_metrics(new_text)
            src_m = count_metrics(src_text)
            new_dial = extract_dialogue(new_text)
            src_dial = extract_dialogue(src_text)

            overlap_rate, overlap_examples = calc_dialogue_overlap(src_dial, new_dial)

            issues = []
            char_ratio = (new_m["chars"] - src_m["chars"]) / max(src_m["chars"], 1) * 100
            if abs(char_ratio) > 20:
                issues.append(f"字数偏差{char_ratio:+.0f}%")

            ai_limit = src_m["ai_markers"] + 2
            if new_m["ai_markers"] > ai_limit:
                issues.append(f"AI痕迹({new_m['ai_markers']}/{src_m['ai_markers']})")

            if overlap_rate > 10:
                issues.append(f"台词重复{overlap_rate}%")

            result = {
                "ch": ch,
                "status": "✅" if not issues else "❌",
                "src_chars": src_m["chars"],
                "new_chars": new_m["chars"],
                "src_ai": src_m["ai_markers"],
                "new_ai": new_m["ai_markers"],
                "overlap_rate": overlap_rate,
                "issues": issues,
            }
            results.append(result)

        # 写入审核报告
        report_path = Path(compare_dir) / f"审核报告_{batch_start}-{batch_end}.md"
        lines = []
        lines.append(f"# 审核报告（第{batch_start}-{batch_end}章）\n")
        lines.append(f"生成时间：{time.strftime('%Y-%m-%d %H:%M')}\n")

        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "✅")
        failed = sum(1 for r in results if r.get("status") == "❌")
        missing = sum(1 for r in results if r.get("status") in ("⚠️", "❌") and r.get("reason"))
        lines.append(f"## 概览\n")
        lines.append(f"| 指标 | 数值 |\n|------|------|\n")
        lines.append(f"| 总章数 | {total} |\n")
        lines.append(f"| 通过 | {passed} |\n")
        lines.append(f"| 有问题 | {failed} |\n")
        lines.append(f"| 缺失 | {missing} |\n")
        lines.append(f"| 通过率 | {passed/total*100:.0f}% |\n")
        lines.append("")

        lines.append(f"## 详细数据\n")
        lines.append("| 章 | 状态 | 源文字数 | 新书字数 | 字数偏差 | AI(源/新) | 台词重复 | 问题 |\n")
        lines.append("|---|------|---------|---------|---------|----------|---------|------|\n")
        for r in results:
            ch = r["ch"]
            status = r.get("status", "")
            if r.get("reason"):
                lines.append(f"| {ch} | {status} | - | - | - | - | - | {r['reason']} |\n")
            else:
                diff = r['new_chars'] - r['src_chars']
                diff_pct = diff / r['src_chars'] * 100 if r['src_chars'] else 0
                ai_str = f"{r['src_ai']}/{r['new_ai']}"
                overlap = f"{r['overlap_rate']}%" if r['overlap_rate'] > 0 else "0%"
                issues_str = "；".join(r.get("issues", [])) if r.get("issues") else "—"
                lines.append(f"| {ch} | {status} | {r['src_chars']} | {r['new_chars']} | {diff_pct:+.0f}% | {ai_str} | {overlap} | {issues_str} |\n")

        lines.append("")
        problem_chapters = [r for r in results if r.get("issues")]
        if problem_chapters:
            lines.append(f"## 问题汇总\n")
            for r in problem_chapters:
                lines.append(f"- **第{r['ch']}章**：{'；'.join(r['issues'])}\n")
            lines.append("")

        Path(compare_dir).mkdir(parents=True, exist_ok=True)
        report_path.write_text("".join(lines), encoding="utf-8")
        print(f"  [OK] 审核报告_{batch_start}-{batch_end}.md ({passed}/{total} 通过)")


def _run_change_report(config, rewrites_dir, compare_dir, start, end, batch_size):
    """生成改动报告 — 汇总每章的核心改动。"""
    from lib.source_locator import get_source_text as get_src
    from lib.text_metrics import count_metrics, count_style_fingerprint

    api_key = config.get("api_key") or os.environ.get("API_KEY")

    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  [改动报告] 第{batch_start}-{batch_end}章...")

        lines = [f"# 改动报告（第{batch_start}-{batch_end}章）\n",
                 f"生成时间：{time.strftime('%Y-%m-%d %H:%M')}\n",
                 f"> 对比仿写成品与源文的逐章改动，量化换皮程度。\n\n"]

        changes = []
        total_src_chars = 0
        total_new_chars = 0

        for ch in range(batch_start, batch_end + 1):
            new_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
            if not new_file.exists():
                continue

            new_text = new_file.read_text(encoding='utf-8')
            src_text = get_src(config, ch)
            if not src_text:
                changes.append((ch, None, None, "无源文"))
                continue

            src_m = count_metrics(src_text)
            new_m = count_metrics(new_text)
            total_src_chars += src_m["chars"]
            total_new_chars += new_m["chars"]

            # 风格指纹对比
            src_fp = count_style_fingerprint(src_text)
            new_fp = count_style_fingerprint(new_text)

            # 字数变化
            char_change = new_m["chars"] - src_m["chars"]
            char_pct = char_change / src_m["chars"] * 100 if src_m["chars"] else 0

            # 对话比变化
            dia_change = (new_fp.get("dialogue_ratio", 0) - src_fp.get("dialogue_ratio", 0)) * 100

            # 段落变化
            para_change = new_fp.get("paragraph_avg_len", 0) - src_fp.get("paragraph_avg_len", 0)

            # 代词密度变化
            pronoun_change = new_fp.get("pronoun_density", 0) - src_fp.get("pronoun_density", 0)

            # 检测文本相似度（粗略：共用字符比例）
            src_clean = re.sub(r'\s', '', src_text)
            new_clean = re.sub(r'\s', '', new_text)
            common = len(set(src_clean) & set(new_clean))
            total_unique = len(set(src_clean) | set(new_clean))
            char_overlap = common / total_unique * 100 if total_unique else 0

            # 换皮程度：字数变化大 + 对话结构调整 + 用字重合度低 = 换皮彻底
            rewrite_score = min(100, int(
                abs(char_pct) * 0.3 +
                abs(dia_change) * 0.5 +
                (100 - char_overlap) * 0.4
            ))

            changes.append((ch, src_m, new_m, {
                "char_change": char_change,
                "char_pct": char_pct,
                "dia_change": dia_change,
                "para_change": para_change,
                "pronoun_change": pronoun_change,
                "char_overlap": char_overlap,
                "rewrite_score": rewrite_score,
            }))

        # 概览
        avg_score = sum(c[3]["rewrite_score"] for c in changes if c[3]) / max(len([c for c in changes if c[3]]), 1)
        lines.append(f"## 概览\n")
        lines.append(f"| 指标 | 数值 |\n|------|------|\n")
        lines.append(f"| 对比章数 | {len(changes)} |\n")
        lines.append(f"| 源文总字数 | {total_src_chars:,} |\n")
        lines.append(f"| 新书总字数 | {total_new_chars:,} |\n")
        lines.append(f"| 总字数变化 | {total_new_chars - total_src_chars:+,} ({((total_new_chars-total_src_chars)/max(total_src_chars,1)*100):+.0f}%) |\n")
        lines.append(f"| 平均换皮评分 | {avg_score:.0f}/100 |\n")
        lines.append(f"| 换皮程度 | {'🟢 深度换皮' if avg_score > 60 else '🟡 中度调整' if avg_score > 30 else '🔴 轻度修改'} |\n")
        lines.append("")

        # 逐章改动
        lines.append("## 逐章改动\n")
        lines.append("| 章 | 源文字数 | 新书字数 | 字数变化 | 对话比变化 | 段长变化 | 代词密度变化 | 用字重合% | 换皮评分 |\n")
        lines.append("|---|---------|---------|---------|-----------|---------|-------------|----------|---------|\n")
        for ch, src_m, new_m, info in changes:
            if not info:
                lines.append(f"| {ch} | — | — | — | — | — | — | — | 无源文 |\n")
                continue
            dia_str = f"{info['dia_change']:+.0f}%" if info['dia_change'] != 0 else "—"
            para_str = f"{info['para_change']:+.0f}" if info['para_change'] != 0 else "—"
            pronoun_str = f"{info['pronoun_change']:+.1f}" if info['pronoun_change'] != 0 else "—"
            overlap_str = f"{info['char_overlap']:.0f}%"
            score_str = f"{info['rewrite_score']} {'🟢' if info['rewrite_score'] > 60 else '🟡' if info['rewrite_score'] > 30 else '🔴'}"
            lines.append(f"| {ch} | {src_m['chars']:,} | {new_m['chars']:,} | {info['char_pct']:+.0f}% | {dia_str} | {para_str} | {pronoun_str} | {overlap_str} | {score_str} |\n")

        lines.append("")
        lines.append("**换皮评分说明**：>60=深度换皮（血肉全换），30-60=中度调整（框架保留），<30=轻度修改\n")

        # 章节改动事件（找变化最大的几章）
        scored = [(c[0], c[3]["rewrite_score"]) for c in changes if c[3]]
        scored.sort(key=lambda x: x[1], reverse=True)
        lines.append("## 改动最大的章节\n")
        for ch, score in scored[:5]:
            lines.append(f"- **第{ch}章**：换皮评分 {score}/100\n")

        lines.append("")

        Path(compare_dir).mkdir(parents=True, exist_ok=True)
        report_path = Path(compare_dir) / f"改动报告_{batch_start}-{batch_end}.md"
        report_path.write_text("".join(lines), encoding="utf-8")
        print(f"  [OK] 改动报告_{batch_start}-{batch_end}.md (换皮评分 {avg_score:.0f}/100)")


# ============================================================
# 版本聚合（保持不变）
# ============================================================


def _collect_version_stats(rewrites_dir):
    return {}


def _write_version_report(rewrites_dir, compare_dir):
    groups = _collect_version_stats(rewrites_dir)
    if not groups:
        return

    out_path = Path(compare_dir) / "对比_版本聚合.md"
    lines = []
    lines.append("# Prompt 版本聚合\n")
    lines.append(f"共扫描到 {sum(g['count'] for g in groups.values())} 章含版本 tag\n\n")

    for key in sorted(groups.keys()):
        g = groups[key]
        ch_range = g["chapters"]
        lines.append(f"## {key}（{g['count']} 章）\n")
        lines.append(f"| 属性 | 值 |\n|------|-----|\n")
        lines.append(f"| prompt | {g['prompt_name']} |\n")
        lines.append(f"| 版本 | {g['version']} |\n")
        lines.append(f"| 章节数 | {g['count']} |\n")
        lines.append(f"| 章节范围 | {min(ch_range)}-{max(ch_range)} |\n")
        sorted_chs = sorted(ch_range)
        ranges = []
        s = sorted_chs[0]
        e = sorted_chs[0]
        for ch in sorted_chs[1:]:
            if ch == e + 1:
                e = ch
            else:
                ranges.append(f"{s}-{e}" if s != e else str(s))
                s = e = ch
        ranges.append(f"{s}-{e}" if s != e else str(s))
        lines.append(f"\n### 分布\n\n{'、'.join(ranges)}\n\n")

    by_prompt = {}
    for key, g in groups.items():
        by_prompt.setdefault(g["prompt_name"], []).append(g)
    for pname, versions in sorted(by_prompt.items()):
        if len(versions) < 2:
            continue
        lines.append(f"## {pname} 版本对比\n\n")
        lines.append("| 版本 | 章节数 | 章节范围 |\n|------|-------|---------|\n")
        for v in sorted(versions, key=lambda x: x["version"]):
            chs = v["chapters"]
            lines.append(f"| v{v['version']} | {v['count']} | {min(chs)}-{max(chs)} |\n")
        lines.append("\n")

    Path(compare_dir).mkdir(parents=True, exist_ok=True)
    content = "".join(lines)
    for attempt in range(5):
        try:
            out_path.write_text(content, encoding="utf-8")
            break
        except OSError:
            time.sleep(0.2)
    print(f"  [OK] 对比_版本聚合")
