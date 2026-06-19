"""
多 Agent 审改系统 v5 — 修复 + 编排层

Agent 架构:
  3.  Dispatch Agent (plan)           — 按章生成修复任务
  4.  Fix Agents (scatter)            — N个并行，每人修分配到的任务
  5.  Collect Results (gather)        — 汇总报告

用法：
    python unified_fixer.py --config xxx.json
    python unified_fixer.py --config xxx.json --start 1 --end 188
"""

import os, re, json, time, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict

from lib.source_locator import get_source_text
from lib.text_metrics import get_body_chars
from lib.constants import AI_MARKERS, AI_MARKER_PATTERN
from prompt_meta import load_system_prompt, load_prompt_str, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from unified_review import Issue, ReviewResult, SummaryReport, review_agent, summary_agent, generate_p012_report
try:
    from logger import setup_pipeline_log
except ImportError:
    setup_pipeline_log = lambda cfg: None

@dataclass
class FixTask:
    """dispatch_agent 输出的单个修复任务"""
    ch: int
    mechanical: list[Issue] = field(default_factory=list)
    llm: list[Issue] = field(default_factory=list)
    target_chars: int = 0

@dataclass
class FixResult:
    """fix agent 输出"""
    ch: int
    status: str           # fixed|unchanged|error|missing
    mech_count: int = 0
    llm_used: bool = False
    orig_chars: int = 0
    new_chars: int = 0
    error: str = ""


# ============================================================
# Agent 3: Dispatch Agent (按章生成修复任务)
# ============================================================

def dispatch_agent(config, report: SummaryReport) -> dict[int, FixTask]:
    """将 summary 转为修复任务，每章一个 FixTask。

    Input:  config, SummaryReport
    Output: {ch: FixTask}
    """
    tasks = {}
    for ch, data in report.chapters.items():
        if not data["issues"]:
            continue
        _ISSUE_FIELDS = {"type", "severity", "priority", "desc", "fix", "auto_fixable", "ch"}
        mech = [Issue(**{k: v for k, v in i.items() if k in _ISSUE_FIELDS}) for i in data["issues"] if i.get("auto_fixable")]
        llm_list = [Issue(**{k: v for k, v in i.items() if k in _ISSUE_FIELDS}) for i in data["issues"] if not i.get("auto_fixable")]

        target = 0
        if llm_list:
            src = get_source_text(config, ch)
            target = get_body_chars(src)

        tasks[ch] = FixTask(ch=ch, mechanical=mech, llm=llm_list, target_chars=target)

    return tasks


# ============================================================
# Agent 4: Fix Agents (执行机械+LLM修复)
# ============================================================

# Prompt 见 prompts/unified-fix.md，由 _fix_llm 加载


def fix_agent(config, task: FixTask, dry_run=False) -> FixResult:
    """执行一个修复任务（单章）。

    Input:  config, FixTask, dry_run
    Output: FixResult
    """
    ch_dir = Path(f"{config['rewrites_dir']}/chapters")
    ch_file = ch_dir / f"ch_{task.ch:03d}.txt"
    if not ch_file.exists():
        return FixResult(ch=task.ch, status="missing")

    text = ch_file.read_text(encoding='utf-8')
    original = text
    mech_count = 0
    llm_used = False

    # 机械修复
    if task.mechanical:
        text, mech_count = _fix_mechanical(text, task.mechanical)

    # LLM 修复
    if task.llm and not dry_run:
        llm_text = _fix_llm(config, task, text)
        if llm_text:
            text = llm_text
            llm_used = True

    if text == original:
        return FixResult(ch=task.ch, status="unchanged",
                         mech_count=mech_count,
                         orig_chars=len(re.sub(r'\s', '', original)),
                         new_chars=len(re.sub(r'\s', '', text)))

    if not dry_run:
        ch_file.write_text(text, encoding='utf-8')

    return FixResult(ch=task.ch, status="fixed",
                     mech_count=mech_count, llm_used=llm_used,
                     orig_chars=len(re.sub(r'\s', '', original)),
                     new_chars=len(re.sub(r'\s', '', text)))


def _fix_mechanical(text, issues):
    """机械修复 AI 痕迹词 + 角色名漂移 + 梗重复。"""
    count = 0
    for iss in issues:
        if iss.type == "ai_trace":
            for marker in AI_MARKERS:
                pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
                found = re.findall(pat, text)
                if found:
                    count += len(found)
                    text = re.sub(pat, lambda m: m.group()[:1] if m.group() else '', text)
        elif iss.type == "ai_marker":
            found = re.findall(AI_MARKER_PATTERN, text)
            if found:
                count += len(found)
                text = re.sub(AI_MARKER_PATTERN, '', text)
        elif iss.type == "char_name_drift":
            # 角色名漂移修复：将变体替换为标准名
            # 例如：将"张三哥"替换为"张三"
            desc = iss.desc
            if "被写成" in desc:
                parts = desc.split("被写成")
                if len(parts) == 2:
                    standard = parts[0].strip().strip("'")
                    variant = parts[1].strip().strip("'")
                    if variant in text:
                        count += text.count(variant)
                        text = text.replace(variant, standard)
        elif iss.type == "trope_repetition":
            # 梗重复：这里不做自动修复，需要LLM处理
            pass
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text, count


def _fix_llm(config, task, text):
    """LLM 修复。"""
    from lib.api_client import call_llm
    print(f"      [修复] 第{task.ch}章 LLM 修复中...", flush=True)

    prompt_template = load_prompt_str("unified-fix.md")
    if not prompt_template:
        return None

    issues_text = '\n'.join(
        f"{i+1}. [{iss.severity}] {iss.desc}" + (f"\n   → {iss.fix}" if iss.fix else "")
        for i, iss in enumerate(task.llm)
    )

    ch_dir = Path(f"{config['rewrites_dir']}/chapters")
    adj_parts = []
    for offset, label in [(-1, "上一章结尾"), (1, "下一章开头")]:
        adj_ch = task.ch + offset
        if adj_ch < 1:
            continue
        adj_file = ch_dir / f"ch_{adj_ch:03d}.txt"
        if adj_file.exists():
            adj_t = adj_file.read_text(encoding='utf-8')
            adj_parts.append(f"【{label}】\n{adj_t[-500:]}" if offset == -1 else f"【{label}】\n{adj_t[:500]}")
    adj = '\n\n'.join(adj_parts)

    # 读源文
    source_text = get_source_text(config, task.ch) or "（无源文）"

    prompt = safe_format(prompt_template, {
        "issues_text": issues_text,
        "adjacent_context": adj,
        "orig_chars": str(len(re.sub(r'\s', '', text))),
        "target_chars": str(task.target_chars or len(re.sub(r'\s', '', text))),
        "min_chars": str(int((task.target_chars or len(re.sub(r'\s', '', text))) * 0.85)),
        "max_chars": str(int((task.target_chars or len(re.sub(r'\s', '', text))) * 1.15)),
        "chapter_content": text,
        "源文全文": source_text,
    })

    sp_name = get_system_prompt_name("unified-fix.md") or "system-generic.md"
    sys_prompt = load_system_prompt(sp_name) or ""

    if config.get("debug"):
        from utils import debug_dump_prompt
        pc = get_prompt_config_with_overrides("unified-fix.md", config)
        debug_dump_prompt(config, "unified-fix", task.ch,
                          "prompts/unified-fix.md", sys_prompt,
                          prompt, sp_name, pc)

    try:
        fixed = call_llm(config, "unified-fix", prompt, sys_prompt)
        # 提取修复后章节
        if "## 修复后章节" in fixed:
            fixed = fixed.split("## 修复后章节")[-1].strip()
        elif "## 修复策略" in fixed:
            parts = fixed.split("## 修复策略")
            if len(parts) > 1:
                fixed = parts[-1].strip()
        if fixed.startswith("```"):
            fixed = fixed.split("\n", 1)[-1]
        if fixed.endswith("```"):
            fixed = fixed.rsplit("```", 1)[0]
        fixed = fixed.strip()

        fixed_chars = len(re.sub(r'\s', '', fixed))
        target = max(task.target_chars, 1)
        if abs(fixed_chars - target) / target < 0.3:
            return fixed
        return None
    except Exception as e:
        print(f"      [修复] 第{task.ch}章 LLM 修复失败: {e}", flush=True)
        return None


def run_pipeline(cfg, start, end, batch_size=10, workers=10, dry_run=False):
    """多 Agent 审改流程。

    Flow:
      1. Scatter: N 个 review agent 并行，每批 batch_size 章
      2. Gather: summary_agent 合并去重分级
      3. Plan: dispatch_agent 生成修复任务
      4. Scatter: N 个 fix agent 并行，每人修一批任务
      5. Gather: 收集结果，打印报告
    """
    chapters = list(range(start, end + 1))
    t_start = time.time()
    print(f"  章节范围: ch{start}-{end} ({len(chapters)}章) | batch={batch_size} | workers={workers}", flush=True)

    # ========== Step 1: Scatter — Review Agents ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 1: 审查 Agent ({len(chapters)} 章, {batch_size} 章/agent)", flush=True)
    print("="*40, flush=True)

    batches = [chapters[i:i+batch_size] for i in range(0, len(chapters), batch_size)]
    review_results = []
    print(f"  {len(batches)} 个审查 agent 并行启动")
    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as ex:
        futures = {
            ex.submit(review_agent, cfg, batch, agent_id=i): i
            for i, batch in enumerate(batches)
        }
        for f in as_completed(futures):
            try:
                review_results.append(f.result())
            except Exception as e:
                print(f"    [FAIL] Review Agent {futures[f]}: {e}")

    print(f"  {len(review_results)}/{len(batches)} 个审查 agent 完成")

    # ========== Step 2: Gather — Summary Agent ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 2: 总结 Agent", flush=True)
    print("="*40, flush=True)

    summary = summary_agent(review_results, config=cfg)
    s = summary.stats
    print(f"  {s['total_ch']} 章有问题 | P0:{s['p0']} P1:{s['p1']} P2:{s['p2']} | 均分:{s['avg_score']}", flush=True)

    if summary.cross_issues:
        print(f"  跨章问题: {len(summary.cross_issues)}", flush=True)
        for ci in summary.cross_issues:
            print(f"    [{ci.priority}] {ci.desc}", flush=True)

    # 生成 P0/P1/P2 问题合集报告
    report_path = os.path.join(cfg.get('rewrites_dir', ''), 'compare', 'p012_issues_report.md')
    if cfg.get('rewrites_dir'):
        generate_p012_report(summary, report_path)

    if not summary.chapters:
        print("  ✓ 无问题，无需修复", flush=True)
        return {}, {str(k): v for k, v in summary.chapters.items()}

    # ========== Step 3: Plan — Dispatch Agent ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 3: 派任务 Agent", flush=True)
    print("="*40, flush=True)

    tasks = dispatch_agent(cfg, summary)
    mech_total = sum(len(t.mechanical) for t in tasks.values())
    llm_total = sum(1 for t in tasks.values() if t.llm)
    print(f"  {len(tasks)} 章需修复 | 机械修复 {mech_total} 处 | LLM 修复 {llm_total} 章", flush=True)

    if dry_run:
        print(f"\n  [DRY-RUN] 不执行修复", flush=True)
        return tasks, {str(k): v for k, v in summary.chapters.items()}

    # ========== 确认环节 ==========
    print(f"\n{'='*50}", flush=True)
    print(f"  修复计划预览", flush=True)
    print("="*50, flush=True)
    print(f"  需修复: {len(tasks)} / {len(chapters)} 章", flush=True)
    print(f"  机械修复: {mech_total} 处 (AI痕迹词/路标词 — 自动删)", flush=True)
    print(f"  LLM 修复: {llm_total} 章 (需模型改写)", flush=True)
    print(f"  无问题跳过: {len(chapters) - len(tasks)} 章", flush=True)
    if llm_total > 0:
        print(f"  [WARN] LLM 修复会调用模型改写，消耗 tokens", flush=True)

    # 按类型分组展示问题分布
    type_count = {}
    for ch, task in sorted(tasks.items()):
        for iss in task.mechanical + task.llm:
            t = iss.type
            type_count.setdefault(t, {"count": 0, "chapters": []})
            type_count[t]["count"] += 1
            if ch not in type_count[t]["chapters"]:
                type_count[t]["chapters"].append(ch)
    if type_count:
        print(f"\n  问题分布:")
        order = {"plagiarism": "台词雷同", "word_count": "字数偏差", "character": "人设漂移",
                 "hook": "钩子不足", "emotion": "直抒情过多", "metaphor": "比喻过多",
                 "ai_marker": "AI路标词", "ai_trace": "AI痕迹词", "continuity": "连贯性",
                 "rhythm": "节奏", "dialogue": "对话", "missing": "文件缺失"}
        for t, info in sorted(type_count.items(), key=lambda x: -x[1]["count"]):
            label = order.get(t, t)
            ch_list = info["chapters"][:5]
            more = f"...共{len(info['chapters'])}章" if len(info['chapters']) > 5 else ""
            print(f"    {label}: {info['count']} 处 (第{','.join(map(str,ch_list))}章{more})", flush=True)

    print(f"  [AUTO] 开始修复", flush=True)

    # ========== Step 4: Scatter — Fix Agents ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 4: 修复 Agent ({len(tasks)} 任务)", flush=True)
    print("="*40, flush=True)

    results = {}
    done = 0
    total = len(tasks)
    with ThreadPoolExecutor(max_workers=min(workers, total or 1)) as ex:
        futures = {
            ex.submit(fix_agent, cfg, task, dry_run): ch
            for ch, task in tasks.items()
        }
        for f in as_completed(futures):
            ch = futures[f]
            try:
                results[ch] = f.result()
            except Exception as e:
                results[ch] = FixResult(ch=ch, status="error", error=str(e))
            done += 1
            fixed = sum(1 for r in results.values() if r.status == "fixed")
            status = results[ch].status
            status_icon = {"fixed": "✓", "unchanged": "~", "missing": "✗", "error": "!"}.get(status, "?")
            print(f"    [{done}/{total}] {status_icon} 第{ch}章 → {status} | {fixed} 章已修复 | {time.time()-t_start:.0f}s", flush=True)

    # ========== Step 5: 二次审查（只审改过的章） ==========
    fixed_chs = [ch for ch, r in results.items() if r.status == "fixed"]
    if fixed_chs and not dry_run:
        print(f"\n{'='*40}", flush=True)
        print(f"Step 5: 二次审查 ({len(fixed_chs)} 章改过)", flush=True)
        print("="*40, flush=True)

        # 只审改过的章
        re_review = review_agent(cfg, fixed_chs, agent_id="re-check")
        new_issues = []
        for ch, data in re_review.chapters.items():
            for iss in data.get("issues", []):
                if iss.get("type") not in ("missing",):
                    new_issues.append({"ch": ch, **iss})

        if new_issues:
            print(f"  发现 {len(new_issues)} 个新问题，修复中...", flush=True)
            # 生成修复任务
            re_tasks = {}
            for iss in new_issues:
                ch = iss["ch"]
                if ch not in re_tasks:
                    re_tasks[ch] = FixTask(ch=ch)
                if iss.get("auto_fixable"):
                    re_tasks[ch].mechanical.append(Issue(**{k: v for k, v in iss.items() if k != "ch"}))
                else:
                    re_tasks[ch].llm.append(Issue(**{k: v for k, v in iss.items() if k != "ch"}))

            # 修复
            re_results = {}
            with ThreadPoolExecutor(max_workers=min(workers, len(re_tasks))) as ex:
                futures = {
                    ex.submit(fix_agent, cfg, task, False): ch
                    for ch, task in re_tasks.items()
                }
                for f in as_completed(futures):
                    ch = futures[f]
                    try:
                        re_results[ch] = f.result()
                    except Exception as e:
                        re_results[ch] = FixResult(ch=ch, status="error", error=str(e))

            re_fixed = sum(1 for r in re_results.values() if r.status == "fixed")
            print(f"  二次修复: {re_fixed} 章", flush=True)
        else:
            print(f"  无新问题", flush=True)

    # ========== Step 6: 最终报告 ==========
    fixed = sum(1 for r in results.values() if r.status == "fixed")
    unchanged = sum(1 for r in results.values() if r.status == "unchanged")
    missing = sum(1 for r in results.values() if r.status == "missing")
    mech_done = sum(r.mech_count for r in results.values())
    llm_done = sum(1 for r in results.values() if r.llm_used)
    errors = sum(1 for r in results.values() if r.status == "error")

    print(f"\n{'='*50}", flush=True)
    print(f"完成 | {time.time()-t_start:.0f}s", flush=True)
    print("="*50, flush=True)
    print(f"  P0:{s['p0']}  P1:{s['p1']}  P2:{s['p2']}", flush=True)
    print(f"  修复: {fixed} 章已修 / {unchanged} 章未变 / {missing} 缺失 / {errors} 错误", flush=True)
    print(f"  机械: {mech_done} 处 / LLM: {llm_done} 章", flush=True)

    return {str(k): asdict(v) for k, v in results.items()}, {str(k): v for k, v in summary.chapters.items()}


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="多 Agent 审改系统 v4")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=10, help="每 agent 审多少章")
    parser.add_argument("--workers", type=int, default=10, help="并行 agent 数")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    cfg.setdefault("base_dir", os.getcwd())

    # 加入 pipeline 日志采集
    setup_pipeline_log(cfg)

    if args.start is None or args.end is None:
        ch_dir = Path(cfg['rewrites_dir']) / 'chapters'
        if ch_dir.exists():
            nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in ch_dir.glob("ch_*.txt")]
            if nums:
                args.start = args.start or min(nums)
                args.end = args.end or max(nums)
    args.start = args.start or 1
    args.end = args.end or 10

    print(f"多 Agent 审改 v4 | ch{args.start}-{args.end} | batch={args.batch_size} | workers={args.workers}")

    results, merged = run_pipeline(
        cfg, args.start, args.end,
        batch_size=args.batch_size,
        workers=args.workers,
        dry_run=args.dry_run,
    )

    output = args.output or os.path.join(cfg['rewrites_dir'], 'compare', 'unified_review_fix.json')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    def _safe(val):
        if isinstance(val, (FixTask, FixResult)):
            return asdict(val)
        if isinstance(val, Issue):
            return asdict(val)
        return val
    Path(output).write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "range": [args.start, args.end],
        "results": {str(k): _safe(v) for k, v in (results or {}).items()},
        "merged_report": merged,
    }, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(f"\n  结果已保存: {output}")


if __name__ == "__main__":
    main()
