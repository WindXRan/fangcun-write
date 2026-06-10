"""
统一审改系统 v3（编辑模式）

流程：
  1. 分批审核：LLM 一次看 10-20 章，发现跨章一致性问题
  2. 合并报告：全局去重、排序、汇总
  3. 制定任务：每章合并所有来源的问题，生成精确修复指令
  4. 分配执行：机械修复并行 + LLM修复分批（带上下文）

用法：
    python unified_fixer.py --config xxx.json [--start 1] [--end 188]
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = str(Path(__file__).parent)
sys.path.insert(0, current_dir)

from lib.constants import AI_MARKERS, CORRUPT_MARKERS
from lib.text_metrics import count_metrics, get_body_chars
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text
from lib.api_client import get_api_url


# ============================================================
# Phase 1: 分批审核（LLM 一次看 N 章）
# ============================================================

BATCH_REVIEW_PROMPT = """你是资深女频网文编辑。请审稿以下 {count} 个章节（完整文本）。

【审稿维度】
1. 跨章一致性：人设是否前后一致，剧情是否连贯，风格是否统一
2. 单章质量：钩子、情绪、节奏
3. AI痕迹：路标词、直抒情、比喻堆砌
4. 台词雷同：与源文的相似度

【输出格式】
严格按 JSON 输出，不要加其他文字：
{{
  "chapters": {{
    "1": {{
      "score": 80,
      "issues": [
        {{"type": "ai_marker|plagiarism|metaphor|emotion|hook|character|rhythm|continuity",
          "severity": "high|medium|low",
          "desc": "问题描述",
          "fix": "修复建议"}}
      ]
    }},
    "2": {{ ... }}
  }},
  "cross_chapter_issues": [
    {{"chapters": [1,2,3], "desc": "跨章问题描述", "fix": "修复建议"}}
  ]
}}

【章节内容（完整）】
{chapters_text}

{source_context}"""


def build_chapters_text(config, chapter_nums):
    """构建多章文本（用于批量审核）。每章完整读取。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    parts = []
    for ch in chapter_nums:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if ch_file.exists():
            text = ch_file.read_text(encoding='utf-8')
            parts.append(f"=== 第{ch}章 ===\n{text}")
    return '\n\n'.join(parts)


def build_source_context(config, chapter_nums):
    """构建源文上下文（取首尾章 + 中间章）。"""
    samples = []
    picks = [chapter_nums[0]]
    if len(chapter_nums) > 2:
        picks.append(chapter_nums[len(chapter_nums)//2])
    if len(chapter_nums) > 1:
        picks.append(chapter_nums[-1])

    for ch in picks:
        src = get_source_text(config, ch)
        if src:
            samples.append(f"--- 源文第{ch}章 ---\n{src}")

    return '\n\n'.join(samples) if samples else ""


def review_batch_llm(api_key, api_url, model, config, chapter_nums):
    """LLM 批量审核一组章节。返回 {ch: {score, issues}} 和跨章问题。"""
    import requests

    chapters_text = build_chapters_text(config, chapter_nums)
    source_context = build_source_context(config, chapter_nums)

    prompt = BATCH_REVIEW_PROMPT.format(
        count=len(chapter_nums),
        chapters_text=chapters_text[:8000],
        source_context=source_context[:2000],
    )

    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是专业网文编辑，输出严格JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 8000,
            },
            timeout=120,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            m = re.search(r'\{[\s\S]*\}', content)
            if m:
                result = json.loads(m.group())
                return result.get("chapters", {}), result.get("cross_chapter_issues", [])
    except Exception as e:
        print(f"    [FAIL] LLM审核: {e}")

    return {}, []


# ============================================================
# Phase 1: 算法检查（纯本地）
# ============================================================

def review_chapter_algo(config, ch):
    """算法检查单章。返回 {score, issues}。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return {"score": 0, "issues": [{"type": "missing", "severity": "high", "desc": "文件不存在"}]}

    ch_text = ch_file.read_text(encoding='utf-8')
    metrics = count_metrics(ch_text)

    source_text = get_source_text(config, ch)
    src_metrics = count_metrics(source_text) if source_text else None
    src_chars = get_body_chars(source_text)

    issues = []
    score = 100

    # AI痕迹词
    ai_found = []
    for marker in AI_MARKERS:
        pattern = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        found = re.findall(pattern, ch_text)
        if found:
            ai_found.append(f"{marker}x{len(found)}")
    if ai_found:
        issues.append({"type": "ai_trace", "severity": "medium", "desc": f"AI痕迹词: {', '.join(ai_found)}", "fix": "删除", "auto_fixable": True})
        score -= 5 * len(ai_found)

    # AI路标词（与源文对比）
    if src_metrics:
        limit = max(src_metrics["ai_markers"] + 1, 1)
        if metrics["ai_markers"] > limit:
            issues.append({"type": "ai_marker", "severity": "high", "desc": f"AI路标词 {metrics['ai_markers']}处 (源文{src_metrics['ai_markers']})", "fix": "删除多余的路标词"})
            score -= 15

    # 比喻过多
    if src_metrics:
        limit = src_metrics["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append({"type": "metaphor", "severity": "medium", "desc": f"比喻过多 {metrics['metaphor']}处 (源文{src_metrics['metaphor']})", "fix": "删除多余比喻"})
            score -= 10

    # 直抒情
    if src_metrics:
        limit = max(src_metrics["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append({"type": "emotion", "severity": "medium", "desc": f"直抒情 {metrics['direct_emotion']}处 (源文{src_metrics['direct_emotion']})", "fix": "用动作细节代替"})
            score -= 10

    # 字数偏差
    if src_chars > 0:
        dev = (metrics["chars"] - src_chars) / src_chars
        if abs(dev) > 0.15:
            direction = "超标" if dev > 0 else "不足"
            issues.append({"type": "word_count", "severity": "high", "desc": f"字数{direction} {metrics['chars']}/{src_chars} ({dev:+.0%})", "fix": f"目标{int(src_chars*0.9)}~{int(src_chars*1.1)}字"})
            score -= 15

    # 台词雷同
    if source_text:
        plags = find_plagiarism(ch_text, source_text)
        if plags:
            desc = f"台词雷同 {len(plags)}处: " + ", ".join(f"'{p['text']}...'({p['length']}字)" for p in plags[:3])
            issues.append({"type": "plagiarism", "severity": "high", "desc": desc, "fix": "重写雷同台词"})
            score -= 15

    return {"score": max(0, score), "issues": issues}


# ============================================================
# Phase 2: 合并报告
# ============================================================

def merge_reports(algo_results, llm_results, cross_issues):
    """合并算法检查和LLM审核结果。

    algo_results: {ch: {score, issues}}
    llm_results: {ch_str: {score, issues}}
    cross_issues: [{chapters, desc, fix}]

    返回: {ch: {score, issues, sources}}
    """
    merged = {}

    # 先放算法结果
    for ch, data in algo_results.items():
        merged[ch] = {
            "score": data["score"],
            "issues": list(data["issues"]),
            "sources": ["algo"],
        }

    # 合并 LLM 结果
    for ch_str, data in llm_results.items():
        ch = int(ch_str)
        if ch not in merged:
            merged[ch] = {"score": data.get("score", 50), "issues": [], "sources": ["llm"]}
        else:
            merged[ch]["sources"].append("llm")
            # 取较低分
            merged[ch]["score"] = min(merged[ch]["score"], data.get("score", 50))

        # 合并 issues（去重：同类型+同描述不重复添加）
        existing_descs = {i["desc"][:30] for i in merged[ch]["issues"]}
        for issue in data.get("issues", []):
            if issue["desc"][:30] not in existing_descs:
                merged[ch]["issues"].append(issue)
                existing_descs.add(issue["desc"][:30])

    # 合并跨章问题
    for cross in cross_issues:
        for ch in cross.get("chapters", []):
            if ch in merged:
                merged[ch]["issues"].append({
                    "type": "continuity",
                    "severity": "medium",
                    "desc": f"[跨章] {cross['desc']}",
                    "fix": cross.get("fix", ""),
                })

    # 排序：high > medium > low
    sev_order = {"high": 0, "medium": 1, "low": 2}
    for ch in merged:
        merged[ch]["issues"].sort(key=lambda x: sev_order.get(x.get("severity", "low"), 9))

    return merged


# ============================================================
# Phase 3: 制定修复任务
# ============================================================

def generate_fix_plan(merged_report, config):
    """从合并报告生成修复任务计划。

    返回: {ch: {mechanical: [...], llm_issues: [...], target_chars, ...}}
    """
    plan = {}

    for ch, data in merged_report.items():
        if not data["issues"]:
            continue

        mechanical = []
        llm_issues = []

        for issue in data["issues"]:
            if issue.get("auto_fixable"):
                mechanical.append(issue)
            else:
                llm_issues.append(issue)

        # 只有需要 LLM 修复时才需要上下文
        source_text = None
        target_chars = 0
        if llm_issues:
            source_text = get_source_text(config, ch)
            target_chars = get_body_chars(source_text)

        plan[ch] = {
            "score": data["score"],
            "mechanical": mechanical,
            "llm_issues": llm_issues,
            "source_text": source_text,
            "target_chars": target_chars,
            "total_issues": len(data["issues"]),
        }

    return plan


# ============================================================
# Phase 4: 执行修复
# ============================================================

def fix_mechanical(text, tasks):
    """执行机械修复。返回 (text, count)。"""
    count = 0
    for task in tasks:
        if task["type"] == "ai_trace":
            for marker in AI_MARKERS:
                pattern = r'(?:^|[\n。！？])\s*' + re.escape(marker)
                found = re.findall(pattern, text)
                if found:
                    count += len(found)
                    text = re.sub(pattern, lambda m: m.group()[:1] if m.group() else '', text)
    if count > 0:
        text = re.sub(r'\n{3,}', '\n\n', text)
    return text, count


LLM_FIX_PROMPT = """你是资深女频网文写手。根据以下问题一次性修复。

【问题】
{issues_text}

{adjacent_context}

{source_context}

【原始章节（{orig_chars}字，目标{target_chars}字）】
{chapter_content}

【要求】
1. 一次性修复所有问题，只改有问题的地方
2. 字数：{min_chars}~{max_chars}字
3. 禁止出现：首先、其次、然后、最后、与此同时、值得注意的是、此外、综上所述
4. 用动作细节代替直抒情
5. 台词口语化
6. 直接输出完整章节"""


def get_adjacent_context(config, ch, chapters_dir):
    """获取相邻章节上下文（前一章结尾 + 后一章开头）。"""
    parts = []
    for offset, label in [(-1, "上一章结尾"), (1, "下一章开头")]:
        adj_ch = ch + offset
        if adj_ch < 1:
            continue
        adj_file = Path(chapters_dir) / f"ch_{adj_ch:03d}.txt"
        if adj_file.exists():
            adj_text = adj_file.read_text(encoding='utf-8')
            if offset == -1:
                # 取结尾 500 字
                parts.append(f"【{label}】\n...{adj_text[-500:]}")
            else:
                # 取开头 500 字
                parts.append(f"【{label}】\n{adj_text[:500]}...")
    return '\n\n'.join(parts)


def fix_chapter_task(config, ch, task, api_key, api_url, model, dry_run=False):
    """执行单章修复任务。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return {"ch": ch, "status": "missing"}

    ch_text = ch_file.read_text(encoding='utf-8')
    original = ch_text
    mech_count = 0
    llm_used = False

    # 1. 机械修复
    if task["mechanical"]:
        ch_text, mech_count = fix_mechanical(ch_text, task["mechanical"])

    # 2. LLM 修复（如有残留）
    if task["llm_issues"] and api_key:
        issues_text = '\n'.join(
            f"{i+1}. [{t.get('severity','')}] {t['desc']}" + (f"\n   → {t['fix']}" if t.get('fix') else "")
            for i, t in enumerate(task["llm_issues"])
        )

        adjacent = get_adjacent_context(config, ch, chapters_dir)
        source_context = ""
        if task["source_text"]:
            source_context = f"【源文参考】\n{task['source_text'][:1500]}"

        prompt = LLM_FIX_PROMPT.format(
            issues_text=issues_text,
            adjacent_context=adjacent,
            source_context=source_context,
            orig_chars=len(re.sub(r'\s', '', ch_text)),
            target_chars=task["target_chars"],
            min_chars=int(task["target_chars"] * 0.85),
            max_chars=int(task["target_chars"] * 1.15),
            chapter_content=ch_text,
        )

        import requests
        try:
            resp = requests.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是专业网文写手。只输出修改后的章节。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 8000,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                fixed = resp.json()["choices"][0]["message"]["content"]
                fixed_chars = len(re.sub(r'\s', '', fixed))
                # 验证：字数不能偏差太大
                if abs(fixed_chars - task["target_chars"]) / max(task["target_chars"], 1) < 0.3:
                    ch_text = fixed
                    llm_used = True
        except Exception as e:
            print(f"    [FAIL] ch{ch:03d} LLM: {e}")

    # 3. 保存
    if ch_text != original:
        if not dry_run:
            ch_file.write_text(ch_text, encoding='utf-8')
        return {
            "ch": ch,
            "status": "fixed",
            "mechanical": mech_count,
            "llm": llm_used,
            "orig_chars": len(re.sub(r'\s', '', original)),
            "new_chars": len(re.sub(r'\s', '', ch_text)),
        }

    return {"ch": ch, "status": "unchanged"}


# ============================================================
# 主流程
# ============================================================

def run_pipeline(config, start, end, api_key=None, api_url=None, model=None,
                 batch_size=10, workers=10, dry_run=False, skip_llm_review=False):
    """完整审改流程。"""

    chapters = list(range(start, end + 1))
    print(f"  章节范围: ch{start}-{end} ({len(chapters)}章)")

    # ========== Phase 1: 检查 ==========
    print(f"\n{'='*40}")
    print(f"Phase 1: 检查")
    print("="*40)

    # 1a. 算法检查（全部，并行）
    print(f"  算法检查 {len(chapters)} 章...")
    algo_results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(review_chapter_algo, config, ch): ch for ch in chapters}
        for f in as_completed(futures):
            ch = futures[f]
            algo_results[ch] = f.result()

    algo_pass = sum(1 for r in algo_results.values() if not r["issues"])
    algo_fail = len(algo_results) - algo_pass
    print(f"  算法检查完成: {algo_pass}通过, {algo_fail}有问题")

    # 1b. LLM 批量审核（只审有问题的章节，分批）
    llm_results = {}
    cross_issues = []
    problem_chapters = [ch for ch, r in algo_results.items() if r["issues"]]

    if problem_chapters and api_key and not skip_llm_review:
        print(f"  LLM审核 {len(problem_chapters)} 章（分批 {batch_size} 章/批）...")
        for i in range(0, len(problem_chapters), batch_size):
            batch = problem_chapters[i:i+batch_size]
            print(f"    批次 {i//batch_size+1}: ch{batch[0]:03d}-{batch[-1]:03d}")
            ch_data, cross = review_batch_llm(api_key, api_url, model, config, batch)
            llm_results.update(ch_data)
            cross_issues.extend(cross)
        print(f"  LLM审核完成: {len(llm_results)}章, {len(cross_issues)}个跨章问题")
    elif not api_key:
        print(f"  [SKIP] 未配置 API_KEY，跳过 LLM 审核")

    # ========== Phase 2: 合并 ==========
    print(f"\n{'='*40}")
    print(f"Phase 2: 合并报告")
    print("="*40)

    merged = merge_reports(algo_results, llm_results, cross_issues)
    total_issues = sum(len(d["issues"]) for d in merged.values())
    high_issues = sum(1 for d in merged.values() for i in d["issues"] if i.get("severity") == "high")
    print(f"  合并完成: {len(merged)}章有问题, {total_issues}个问题 (高危{high_issues})")

    # ========== Phase 3: 制定任务 ==========
    print(f"\n{'='*40}")
    print(f"Phase 3: 制定修复任务")
    print("="*40)

    plan = generate_fix_plan(merged, config)
    mech_total = sum(len(t["mechanical"]) for t in plan.values())
    llm_total = sum(1 for t in plan.values() if t["llm_issues"])
    print(f"  任务制定完成: {len(plan)}章, 机械{mech_total}处, LLM{llm_total}章")

    if dry_run:
        print(f"\n  [DRY-RUN] 不执行修复")
        return plan, merged

    # ========== Phase 4: 执行修复 ==========
    print(f"\n{'='*40}")
    print(f"Phase 4: 执行修复")
    print("="*40)

    results = {}
    done = 0
    total = len(plan)
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(fix_chapter_task, config, ch, task, api_key, api_url, model, dry_run): ch
            for ch, task in plan.items()
        }
        for f in as_completed(futures):
            ch = futures[f]
            try:
                results[ch] = f.result()
            except Exception as e:
                results[ch] = {"ch": ch, "status": "error"}
                print(f"    [ERROR] ch{ch:03d}: {e}")
            done += 1
            if done % max(1, total//10) == 0 or done == total:
                elapsed = time.time() - t_start
                fixed = sum(1 for r in results.values() if r.get("status") == "fixed")
                print(f"    [{done}/{total}] {elapsed:.0f}s | {fixed}章已修复")

    # ========== 摘要 ==========
    fixed = sum(1 for r in results.values() if r.get("status") == "fixed")
    unchanged = sum(1 for r in results.values() if r.get("status") == "unchanged")
    mech_done = sum(r.get("mechanical", 0) for r in results.values())
    llm_done = sum(1 for r in results.values() if r.get("llm"))

    elapsed = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"完成 | {elapsed:.0f}s")
    print("="*50)
    print(f"  检查: {algo_pass}通过 / {algo_fail}有问题")
    print(f"  修复: {fixed}章已修复 / {unchanged}章未变")
    print(f"  机械: {mech_done}处 / LLM: {llm_done}章")

    if fixed > 0:
        print(f"\n  修复详情:")
        for ch in sorted(r["ch"] for r in results.values() if r.get("status") == "fixed"):
            r = next(x for x in results.values() if x.get("ch") == ch)
            parts = []
            if r.get("mechanical"): parts.append(f"机械{r['mechanical']}处")
            if r.get("llm"): parts.append("LLM")
            print(f"    ch{ch:03d}: {'+'.join(parts)} ({r.get('orig_chars','?')}→{r.get('new_chars','?')}字)")

    return results, merged


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="统一审改系统 v3（编辑模式）")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=25, help="LLM审核每批章数（默认25）")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-llm-review", action="store_true", help="跳过LLM审核，只用算法检查")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    config.setdefault("base_dir", os.getcwd())

    # 自动检测章节范围
    if args.start is None or args.end is None:
        ch_dir = Path(config['rewrites_dir']) / 'chapters'
        if ch_dir.exists():
            nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in ch_dir.glob("ch_*.txt")]
            if nums:
                args.start = args.start or min(nums)
                args.end = args.end or max(nums)

    args.start = args.start or 1
    args.end = args.end or 10

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-chat")

    if not api_key:
        print("[WARN] 未配置 API_KEY，将跳过 LLM 审核和 LLM 修复")

    print(f"统一审改 v3 | ch{args.start}-{args.end} | batch={args.batch_size} | workers={args.workers}")

    results, merged = run_pipeline(
        config, args.start, args.end,
        api_key, api_url, model,
        batch_size=args.batch_size,
        workers=args.workers,
        dry_run=args.dry_run,
        skip_llm_review=args.skip_llm_review,
    )

    # 保存
    output = args.output or os.path.join(config['rewrites_dir'], 'compare', 'unified_review_fix.json')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "range": [args.start, args.end],
        "results": {str(k): v for k, v in (results or {}).items()},
        "merged_report": {str(k): v for k, v in (merged or {}).items()},
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n  结果已保存: {output}")


if __name__ == "__main__":
    main()
