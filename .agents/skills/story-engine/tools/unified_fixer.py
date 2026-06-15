"""
多 Agent 审改系统 v5 — 混合架构

Agent 架构:
  1a. Batch Review Agents (scatter)   — N个并行，每人审 X 章 (algo+LLM, 7维全检)
  1b. Global Review Agents (scatter)  — 2个并行，通读全书关键章：人设一致性 + 全局节奏/伏笔
  2.  Summary Agent (gather)          — 合并两层结果，去重分级 P0/P1/P2
  3.  Dispatch Agent (plan)           — 按章生成修复任务
  4.  Fix Agents (scatter)            — N个并行，每人修分配到的任务
  5.  Collect Results (gather)        — 汇总报告

用法：
    python unified_fixer.py --config xxx.json
    python unified_fixer.py --config xxx.json --start 1 --end 188
"""

import os, re, json, time, argparse, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

from lib.constants import AI_MARKERS, AI_MARKER_PATTERN
from lib.text_metrics import count_metrics, get_body_chars
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text
from lib.api_client import get_api_url
from prompt_loader import load_system_prompt, load_prompt_str, tag_output, get_prompt_config_with_overrides


# ============================================================
# 数据契约 (Agent 间通信协议)
# ============================================================

@dataclass
class Issue:
    type: str            # ai_marker|plagiarism|metaphor|emotion|hook|word_count|ai_trace|continuity|character|rhythm
    severity: str        # high|medium|low
    priority: str = ""   # P0|P1|P2  (summary_agent 填写)
    desc: str = ""
    fix: str = ""
    auto_fixable: bool = False
    ch: int = 0          # 所属章

@dataclass
class ReviewResult:
    """单个 review agent 对一个 chapter batch 的输出"""
    chapters: dict[int, dict] = field(default_factory=dict)  # {ch: {score, issues:[Issue_dict], metrics:{}}}
    cross_issues: list[dict] = field(default_factory=list)

@dataclass
class SummaryReport:
    """summary_agent 输出"""
    chapters: dict[int, dict] = field(default_factory=dict)  # {ch: {score, issues:[Issue_dict]}}
    cross_issues: list[Issue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)  # {total_ch, p0, p1, p2, avg_score}

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

# 便利函数
def issue_dict(i):
    return {"type": i.type, "severity": i.severity, "priority": i.priority,
            "desc": i.desc, "fix": i.fix, "auto_fixable": i.auto_fixable, "ch": i.ch}


# ============================================================
# Agent 1: Review Agents (N 个并行，每批 X 章)
# ============================================================

# Prompt 见 prompts/unified-review.md，由 _llm_batch_review 加载


def review_agent(config, chapter_batch, api_key, api_url, model, agent_id=0):
    """单个审查 agent。在一批章节上运行 algo 检查 + LLM 批量审稿。

    Input:  config, chapter_batch (list[int]), api_key, api_url, model, agent_id
    Output: ReviewResult
    """
    result = ReviewResult()
    n = len(chapter_batch)
    done_algo = 0

    # ---- 1a: 算法检查 (所有章并行) ----
    with ThreadPoolExecutor(max_workers=len(chapter_batch)) as ex:
        futures = {ex.submit(_algo_check, config, ch): ch for ch in chapter_batch}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                result.chapters[ch] = f.result()
            except Exception as e:
                result.chapters[ch] = {"score": 0, "issues": [{"type": "error", "severity": "high", "desc": str(e)}]}
            done_algo += 1
            print(f"    [审查#{agent_id}] 算法检查: {done_algo}/{n} 章 (第{ch}章)", flush=True)

    # ---- 1b: LLM 批量审稿 (有问题的章) ----
    problem_chs = [ch for ch, d in result.chapters.items() if d.get("issues")]
    if problem_chs and api_key:
        print(f"    [审查#{agent_id}] LLM 审稿: {len(problem_chs)} 章...", flush=True)
        try:
            ch_data, cross = _llm_batch_review(config, problem_chs, api_key, api_url, model)
            for ch_str, data in ch_data.items():
                ch = int(ch_str)
                if ch in result.chapters:
                    existing = {i["desc"][:30] for i in result.chapters[ch].get("issues", [])}
                    for issue in data.get("issues", []):
                        if issue["desc"][:30] not in existing:
                            result.chapters[ch]["issues"].append(issue)
                            existing.add(issue["desc"][:30])
                    result.chapters[ch]["score"] = min(
                        result.chapters[ch].get("score", 100),
                        data.get("score", 50)
                    )
            result.cross_issues.extend(cross)
            print(f"    [审查#{agent_id}] LLM 审稿完成", flush=True)
        except Exception as e:
            print(f"    [审查#{agent_id}] LLM 审稿失败: {e}", flush=True)

    return result


def _algo_check(config, ch):
    """单章算法检查。"""
    ch_dir = Path(f"{config['rewrites_dir']}/chapters")
    ch_file = ch_dir / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return {"score": 0, "issues": [{"type": "missing", "severity": "high", "desc": "文件不存在", "auto_fixable": False}]}

    text = ch_file.read_text(encoding='utf-8')
    metrics = count_metrics(text)
    src = get_source_text(config, ch)
    src_metrics = count_metrics(src) if src else None
    src_chars = get_body_chars(src)

    issues = []
    score = 100

    # AI痕迹词 (句首)
    ai_traces = []
    for marker in AI_MARKERS:
        pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        found = re.findall(pat, text)
        if found:
            ai_traces.append(f"{marker}x{len(found)}")
    if ai_traces:
        issues.append({"type": "ai_trace", "severity": "medium",
                       "desc": f"AI痕迹词: {', '.join(ai_traces)}",
                       "fix": "删除句首路标词", "auto_fixable": True})
        score -= 5

    # AI路标词 vs 源文
    if src_metrics:
        limit = max(src_metrics["ai_markers"] + 1, 1)
        if metrics["ai_markers"] > limit:
            issues.append({"type": "ai_marker", "severity": "high",
                           "desc": f"AI路标词 {metrics['ai_markers']}处 (源文{src_metrics['ai_markers']})",
                           "fix": "删除多余的路标词", "auto_fixable": True})
            score -= 15

    # 比喻
    if src_metrics:
        limit = src_metrics["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append({"type": "metaphor", "severity": "medium",
                           "desc": f"比喻过多 {metrics['metaphor']}处 (源文{src_metrics['metaphor']})",
                           "fix": "删除多余比喻", "auto_fixable": False})
            score -= 10

    # 直抒情
    if src_metrics:
        limit = max(src_metrics["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append({"type": "emotion", "severity": "medium",
                           "desc": f"直抒情 {metrics['direct_emotion']}处 (源文{src_metrics['direct_emotion']})",
                           "fix": "用动作细节代替", "auto_fixable": False})
            score -= 10

    # 代词密度（朱雀防线）
    if src_metrics and src_metrics.get("pronoun_density", 0) > 0:
        ratio = metrics["pronoun_density"] / src_metrics["pronoun_density"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append({"type": "pronoun", "severity": "medium",
                           "desc": f"代词密度 {metrics['pronoun_density']}/千字 (源文{src_metrics['pronoun_density']})",
                           "fix": "交替使用名字/身份/零代词替代他/她", "auto_fixable": False})
            score -= 10

    # 句长标准差（朱雀防线）
    if src_metrics and src_metrics.get("sent_len_stddev", 0) > 0:
        ratio = metrics["sent_len_stddev"] / src_metrics["sent_len_stddev"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append({"type": "sentence_stddev", "severity": "medium",
                           "desc": f"句长标准差 {metrics['sent_len_stddev']} (源文{src_metrics['sent_len_stddev']})",
                           "fix": "交错长短句，避免句长均匀", "auto_fixable": False})
            score -= 10

    # 字数
    if src_chars > 0:
        dev = (metrics["chars"] - src_chars) / src_chars
        if abs(dev) > 0.15:
            direction = "超标" if dev > 0 else "不足"
            issues.append({"type": "word_count", "severity": "high",
                           "desc": f"字数{direction} {metrics['chars']}/{src_chars} ({dev:+.0%})",
                           "fix": f"目标{int(src_chars*0.9)}~{int(src_chars*1.1)}字",
                           "auto_fixable": False})
            score -= 15

    # 台词雷同
    if src:
        plags = find_plagiarism(text, src)
        if plags:
            desc = f"台词雷同 {len(plags)}处: " + ", ".join(f"'{p['text']}...'" for p in plags[:3])
            issues.append({"type": "plagiarism", "severity": "high",
                           "desc": desc, "fix": "重写雷同台词",
                           "auto_fixable": False})
            score -= 15

    return {"score": max(0, score), "issues": issues, "metrics": metrics,
            "chars": metrics["chars"], "src_chars": src_chars}


def _parse_review_output(text):
    """解析 markdown 格式的审稿输出。

    格式：
      ### 章节 N
      评分: XX
      问题:
      - 类型: X | 严重度: high|medium|low | 描述: X | 修复: X

      ### 跨章问题
      - 涉及章节: 1,2,3 | 类型: X | 严重度: X | 描述: X | 修复: X

    返回 ({ch_str: {score, issues}}, [{type, severity, desc, fix}])
    """
    chapters = {}
    cross = []

    # 解析 ### 章节 N 块
    ch_blocks = re.findall(r'###\s+章节\s+(\d+)\s*\n(.*?)(?=###\s+(?:章节|\u8de8\u7ae0\u95ee\u9898)|\Z)', text, re.DOTALL)
    for ch_str, body in ch_blocks:
        score_m = re.search(r'评分:\s*(\d+)', body)
        score = int(score_m.group(1)) if score_m else 50

        issues = []
        # 找到 问题: 后面的列表项
        in_issues = re.split(r'问题:', body, maxsplit=1)
        if len(in_issues) > 1:
            for line in in_issues[1].split('\n'):
                line = line.strip()
                m = re.match(r'-\s*类型:\s*(\S+)', line)
                if m:
                    typ = m.group(1)
                    sev = _extract_field(line, '严重度', 'medium')
                    desc = _extract_field(line, '描述', '')
                    fix = _extract_field(line, '修复', '')
                    issues.append({"type": typ, "severity": sev, "desc": desc, "fix": fix, "auto_fixable": False})

        chapters[ch_str] = {"score": score, "issues": issues}

    # 解析 ### 跨章问题 块
    cross_block = re.search(r'###\s+跨章问题\s*\n(.*?)(?=###|\Z)', text, re.DOTALL)
    if cross_block:
        for line in cross_block.group(1).split('\n'):
            line = line.strip()
            m = re.match(r'-\s*涉及章节:\s*([\d,]+)', line)
            if m:
                chs = [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
                typ = _extract_field(line, '类型', 'continuity')
                sev = _extract_field(line, '严重度', 'medium')
                desc = _extract_field(line, '描述', '')
                fix = _extract_field(line, '修复', '')
                cross.append({"chapters": chs, "type": typ, "severity": sev, "desc": desc, "fix": fix})

    return chapters, cross


def _extract_field(line, label, default):
    """从 '类型: X | 严重度: Y' 格式中提取字段值。"""
    m = re.search(re.escape(label) + r':\s*([^|]+)', line)
    return m.group(1).strip() if m else default


def _llm_batch_review(config, chapter_nums, api_key, api_url, model):
    """LLM 批量审稿一批章节。"""
    import requests

    prompt_template = load_prompt_str("unified-review.md")
    if not prompt_template:
        return {}, []

    # 章节文本
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    parts = []
    for ch in chapter_nums:
        cf = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if cf.exists():
            parts.append(f"=== 第{ch}章 ===\n{cf.read_text(encoding='utf-8')}")
    chapters_text = '\n\n'.join(parts)

    # 源文参考（首尾章+中间章）
    src_samples = []
    picks = [chapter_nums[0]]
    if len(chapter_nums) > 2:
        picks.append(chapter_nums[len(chapter_nums)//2])
    if len(chapter_nums) > 1:
        picks.append(chapter_nums[-1])
    for ch in picks:
        src = get_source_text(config, ch)
        if src:
            src_samples.append(f"--- 源文第{ch}章 ---\n{src[:1000]}")
    source_context = '\n\n'.join(src_samples)

    prompt = prompt_template.format(
        count=len(chapter_nums),
        chapters_text=chapters_text[:6000],
        source_context=source_context[:2000] if source_context else "（无）",
    )

    pc = get_prompt_config_with_overrides("unified-review.md", config)

    if config.get("debug"):
        from utils import debug_dump_prompt
        label = f"batch{chapter_nums[0]}-{chapter_nums[-1]}"
        debug_dump_prompt(config, "unified-review", chapter_nums[0],
                          "prompts/unified-review.md", "你是资深网文编辑。",
                          prompt, "unified-review", pc)

    resp = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": pc.get("model", model),
              "messages": [
            {"role": "system", "content": "你是资深网文编辑。"},
            {"role": "user", "content": prompt},
        ], "temperature": pc.get("temperature", 0.3),
           "max_tokens": pc.get("max_tokens", 8000)},
        timeout=120,
    )
    if resp.status_code != 200:
        raise Exception(f"API {resp.status_code}")

    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_review_output(content)


# ============================================================
# Agent 1b: Global Review Agents (2个并行，通读全书关键章)
# ============================================================

def _sample_global_chapters(config, start, end):
    """采样全书关键章：头2 + 四分位中点 + 尾2 → ~6章。"""
    total = end - start + 1
    if total <= 6:
        return list(range(start, end + 1))

    picks = [start, start + 1]  # 头2章
    # 三分位
    q1 = start + total // 4
    q2 = start + total // 2
    q3 = start + 3 * total // 4
    picks.extend([q1, q2, q3])
    picks.extend([end - 1, end])  # 尾2章
    return sorted(set(picks))


def _load_global_context(config, sampled_chapters):
    """为全局审查加载 context：角色设定 + 节奏图 + 章节样本。"""
    rewrites_dir = Path(config["rewrites_dir"])
    chapters_dir = rewrites_dir / "chapters"

    # 角色设定（从 concept.md 提取角色相关段）
    concept_path = rewrites_dir / "concept.md"
    character_profiles = ""
    if concept_path.exists():
        concept = concept_path.read_text(encoding="utf-8")
        # 提取角色相关段落（## 角色 或 ### 角色名 直到下一个 ##）
        char_sec = re.search(r'##\s*(?:角色|人设|人物).*?(?=##\s|\Z)', concept, re.DOTALL)
        if char_sec:
            character_profiles = char_sec.group(0)[:3000]

    # 全局节奏图（从 concept.md 提取）
    rhythm_map = ""
    rhythm_sec = re.search(r'##\s*(?:节奏|弧线|全局).*?(?=##\s|\Z)', concept, re.DOTALL)
    if rhythm_sec:
        rhythm_map = rhythm_sec.group(0)[:3000]

    # 章节样本
    parts = []
    for ch in sampled_chapters:
        cf = chapters_dir / f"ch_{ch:03d}.txt"
        if cf.exists():
            text = cf.read_text(encoding="utf-8")
            # 取头 500 字 + 尾 300 字（节省 token，保留关键信息）
            sample = text[:800]
            if len(text) > 1500:
                sample += f"\n\n...（中间省略 {len(text)-1500} 字）...\n\n" + text[-700:]
            parts.append(f"=== 第{ch}章 ===\n{sample}")
    chapters_sample = '\n\n'.join(parts)

    # 目录摘要（从 guides 目录提取 plot_guide 标题）
    guides_dir = rewrites_dir / "guides"
    toc_parts = []
    for ch in sorted(sampled_chapters):
        gf = guides_dir / f"plot_{ch}.md"
        if gf.exists():
            guide_text = gf.read_text(encoding="utf-8")
            # 提取第一行（通常是章节主题）
            first_line = guide_text.strip().split('\n')[0][:100]
            toc_parts.append(f"第{ch}章: {first_line}")
    toc_summary = '\n'.join(toc_parts) if toc_parts else "（无 guide）"

    return {
        "character_profiles": character_profiles or "（concept.md 中无角色设定段）",
        "rhythm_map": rhythm_map or "（concept.md 中无节奏段）",
        "chapters_sample": chapters_sample,
        "toc_summary": toc_summary,
    }


def _global_dimension_review(config, dimension, context, api_key, api_url, model):
    """单个全局审查 agent：读全书关键章，只审一个维度。

    dimension: "character" | "rhythm"
    """
    import requests

    prompt_name = f"unified-review-{dimension}.md"
    prompt_template = load_prompt_str(prompt_name)
    if not prompt_template:
        print(f"    [全局审查] prompt {prompt_name} 不存在，跳过", flush=True)
        return ReviewResult()

    # 格式化 prompt
    prompt = prompt_template.format(**context)

    pc = get_prompt_config_with_overrides(prompt_name, config)
    label = {"character": "人设一致性", "rhythm": "全局节奏/伏笔"}.get(dimension, dimension)

    # Debug: 保存全局审查 prompt
    if config.get("debug"):
        debug_dir = Path(config.get("rewrites_dir", ".")) / "_debug" / f"global-{dimension}"
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "prompt.md").write_text(
            f"# Global Review: {label}\n**Model**: {pc.get('model')}\n**Temp**: {pc.get('temperature')}\n\n---\n\n{prompt}",
            encoding="utf-8")

    print(f"    [全局审查] {label} — 审查中...", flush=True)
    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": pc.get("model", model),
                  "messages": [
                {"role": "system", "content": "你是资深网文编辑。只输出 JSON。"},
                {"role": "user", "content": prompt},
            ], "temperature": pc.get("temperature", 0.3),
               "max_tokens": pc.get("max_tokens", 8192)},
            timeout=180,
        )
        if resp.status_code != 200:
            raise Exception(f"API {resp.status_code}")

        content = resp.json()["choices"][0]["message"]["content"]
        result = _parse_global_review(content, dimension)
        n_ch = len(result.chapters)
        n_cross = len(result.cross_issues)
        print(f"    [全局审查] {label} → {n_ch} 章问题 + {n_cross} 跨章问题", flush=True)
        return result
    except Exception as e:
        print(f"    [全局审查] {label} 失败: {e}", flush=True)
        return ReviewResult()


def _parse_global_review(content, dimension):
    """解析全局审查的 JSON 输出。"""
    result = ReviewResult()
    try:
        # 提取 JSON
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return result
        data = json.loads(m.group(0))

        # 单章问题
        for issue in data.get("issues", []):
            ch = issue.get("ch", 0)
            if ch not in result.chapters:
                result.chapters[ch] = {"score": 100, "issues": []}
            result.chapters[ch]["issues"].append({
                "type": issue.get("type", dimension),
                "severity": issue.get("severity", "medium"),
                "desc": issue.get("desc", ""),
                "fix": issue.get("fix", ""),
                "auto_fixable": False,
            })
            # 降低分数反映问题严重度
            sev_penalty = {"high": 20, "medium": 10, "low": 5}
            result.chapters[ch]["score"] = max(0,
                result.chapters[ch]["score"] - sev_penalty.get(issue.get("severity", "low"), 10))

        # 跨章问题
        for ci in data.get("cross_issues", []):
            result.cross_issues.append({
                "chapters": ci.get("chapters", []),
                "type": ci.get("type", dimension),
                "severity": ci.get("severity", "medium"),
                "desc": ci.get("desc", ""),
                "fix": ci.get("fix", ""),
            })

    except Exception as e:
        print(f"    [全局审查] JSON 解析失败: {e}", flush=True)

    return result


def _run_global_reviews(config, start, end, api_key, api_url, model):
    """Layer 1b: 运行 2 个全局维度审查 agent（并行）。"""
    sampled = _sample_global_chapters(config, start, end)
    context = _load_global_context(config, sampled)

    dimensions = ["character", "rhythm"]
    results = []

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(_global_dimension_review, config, dim, context, api_key, api_url, model): dim
            for dim in dimensions
        }
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                print(f"    [全局审查] {futures[f]} 异常: {e}", flush=True)

    return results


# ============================================================
# Agent 2: Summary Agent (合并、分级 P0/P1/P2、跨章分析)
# ============================================================

_P0_TYPES = {"plagiarism", "continuity", "missing", "character", "timeline"}
_P1_TYPES = {"ai_marker", "emotion", "hook", "rhythm", "word_count"}
_P2_TYPES = {"metaphor", "ai_trace", "dialogue"}

def severity_to_priority(severity, type_):
    if type_ in _P0_TYPES:
        return "P0"
    if severity == "high":
        return "P0"
    if type_ in _P1_TYPES:
        return "P1"
    if severity == "medium" and type_ in _P2_TYPES:
        return "P2"
    if type_ in _P2_TYPES:
        return "P2"
    return "P1"  # fallback


def summary_agent(review_results: list[ReviewResult]) -> SummaryReport:
    """汇总 N 个 review agent 的输出。

    Input:  [ReviewResult, ...]
    Output: SummaryReport (去重、分级、跨章合并)
    """
    merged = {}
    all_cross = []

    for rr in review_results:
        for ch, data in rr.chapters.items():
            if ch not in merged:
                merged[ch] = {"score": 100, "issues": [], "sources": []}
            merged[ch]["sources"].append("algo")
            merged[ch]["score"] = min(merged[ch]["score"], data.get("score", 50))

            existing = {i["desc"][:30] for i in merged[ch]["issues"]}
            for issue in data.get("issues", []):
                if issue["desc"][:30] not in existing:
                    issue["priority"] = severity_to_priority(issue.get("severity", "low"), issue.get("type", ""))
                    merged[ch]["issues"].append(issue)
                    existing.add(issue["desc"][:30])

        all_cross.extend(rr.cross_issues)

    # 去重跨章问题 + 分级
    _ISSUE_FIELDS = {"type", "severity", "priority", "desc", "fix", "auto_fixable", "ch"}
    seen_cross = set()
    cross_list = []
    for c in all_cross:
        key = c.get("desc", "")[:60]
        if key not in seen_cross:
            c["priority"] = severity_to_priority(c.get("severity", "medium"), c.get("type", "continuity"))
            cross_list.append(Issue(**{k: v for k, v in c.items() if k in _ISSUE_FIELDS}))
            seen_cross.add(key)

    # 排序 per chapter: P0 > P1 > P2
    prio_order = {"P0": 0, "P1": 1, "P2": 2}
    for ch in merged:
        merged[ch]["issues"].sort(key=lambda i: prio_order.get(i.get("priority", "P2"), 9))

    # 统计
    total_p0 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P0")
    total_p1 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P1")
    total_p2 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P2")
    scores = [d["score"] for d in merged.values()]
    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    stats = {
        "total_ch": len(merged),
        "p0": total_p0,
        "p1": total_p1,
        "p2": total_p2,
        "total_issues": total_p0 + total_p1 + total_p2,
        "avg_score": avg_score,
    }

    return SummaryReport(chapters=merged, cross_issues=cross_list, stats=stats)


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


def fix_agent(config, task: FixTask, api_key, api_url, model, dry_run=False) -> FixResult:
    """执行一个修复任务（单章）。

    Input:  config, FixTask, api_key, api_url, model, dry_run
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
    if task.llm and api_key and not dry_run:
        llm_text = _fix_llm(config, task, text, api_key, api_url, model)
        if llm_text:
            text = llm_text
            llm_used = True

    if text == original:
        return FixResult(ch=task.ch, status="unchanged",
                         mech_count=mech_count,
                         orig_chars=len(re.sub(r'\s', '', original)),
                         new_chars=len(re.sub(r'\s', '', text)))

    if not dry_run:
        ch_file.write_text(tag_output(text, "unified-fix.md"), encoding='utf-8')

    return FixResult(ch=task.ch, status="fixed",
                     mech_count=mech_count, llm_used=llm_used,
                     orig_chars=len(re.sub(r'\s', '', original)),
                     new_chars=len(re.sub(r'\s', '', text)))


def _fix_mechanical(text, issues):
    """机械修复 AI 痕迹词。"""
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
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text, count


def _fix_llm(config, task, text, api_key, api_url, model):
    """LLM 修复。"""
    import requests
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

    # 读脱敏版源文（防数据泄漏，保留结构参考即可）
    from lib.source_stripper import strip_source_chapter
    source_text = strip_source_chapter(config, task.ch) or get_source_text(config, task.ch) or "（无源文）"

    prompt = prompt_template.format(
        issues_text=issues_text,
        adjacent_context=adj,
        orig_chars=len(re.sub(r'\s', '', text)),
        target_chars=task.target_chars or len(re.sub(r'\s', '', text)),
        min_chars=int((task.target_chars or len(re.sub(r'\s', '', text))) * 0.85),
        max_chars=int((task.target_chars or len(re.sub(r'\s', '', text))) * 1.15),
        chapter_content=text,
        源文全文=source_text,
    )

    pc = get_prompt_config_with_overrides("unified-fix.md", config)

    if config.get("debug"):
        from utils import debug_dump_prompt
        debug_dump_prompt(config, "unified-fix", task.ch,
                          "prompts/unified-fix.md", "你是资深网文写手。只输出修改后的章节。",
                          prompt, "unified-fix", pc)

    resp = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": pc.get("model", model), "messages": [
            {"role": "system", "content": "你是资深网文写手。只输出修改后的章节。"},
            {"role": "user", "content": prompt},
        ], "temperature": pc.get("temperature", 0.6),
           "max_tokens": pc.get("max_tokens", 8000)},
        timeout=120,
    )
    if resp.status_code == 200:
        fixed = resp.json()["choices"][0]["message"]["content"]
        fixed_chars = len(re.sub(r'\s', '', fixed))
        target = max(task.target_chars, 1)
        if abs(fixed_chars - target) / target < 0.3:
            return fixed
    return None


# ============================================================
# Orchestrator (多 agent 编排)
# ============================================================

def run_pipeline(cfg, start, end, api_key=None, api_url=None, model=None,
                 batch_size=10, workers=10, dry_run=False):
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
            ex.submit(review_agent, cfg, batch, api_key, api_url, model, agent_id=i): i
            for i, batch in enumerate(batches)
        }
        for f in as_completed(futures):
            try:
                review_results.append(f.result())
            except Exception as e:
                print(f"    [FAIL] Review Agent {futures[f]}: {e}")

    print(f"  {len(review_results)}/{len(batches)} 个审查 agent 完成")

    # ========== Step 1b: Global Review Agents (跨章维度审查) ==========
    if api_key:
        print(f"\n{'='*40}", flush=True)
        print(f"Step 1b: 全局审查 Agent (人设一致性 + 全局节奏/伏笔)", flush=True)
        print("="*40, flush=True)

        global_results = _run_global_reviews(cfg, start, end, api_key, api_url, model)
        review_results.extend(global_results)
    else:
        global_results = []

    # ========== Step 2: Gather — Summary Agent ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 2: 总结 Agent", flush=True)
    print("="*40, flush=True)

    summary = summary_agent(review_results)
    s = summary.stats
    print(f"  {s['total_ch']} 章有问题 | P0:{s['p0']} P1:{s['p1']} P2:{s['p2']} | 均分:{s['avg_score']}", flush=True)

    if summary.cross_issues:
        print(f"  跨章问题: {len(summary.cross_issues)}", flush=True)
        for ci in summary.cross_issues:
            print(f"    [{ci.priority}] {ci.desc}", flush=True)

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
        print(f"  ⚠ LLM 修复会调用模型改写，消耗 tokens", flush=True)

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

    print(f"\n  按 Enter 开始修复，或 Ctrl+C 取消...", end="", flush=True)
    try:
        input()
    except KeyboardInterrupt:
        print(f"\n  已取消", flush=True)
        return {}, {str(k): v for k, v in summary.chapters.items()}

    # ========== Step 4: Scatter — Fix Agents ==========
    print(f"\n{'='*40}", flush=True)
    print(f"Step 4: 修复 Agent ({len(tasks)} 任务)", flush=True)
    print("="*40, flush=True)

    results = {}
    done = 0
    total = len(tasks)
    with ThreadPoolExecutor(max_workers=min(workers, total or 1)) as ex:
        futures = {
            ex.submit(fix_agent, cfg, task, api_key, api_url, model, dry_run): ch
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

    # ========== Step 5: Gather — 最终报告 ==========
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

    if args.start is None or args.end is None:
        ch_dir = Path(cfg['rewrites_dir']) / 'chapters'
        if ch_dir.exists():
            nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in ch_dir.glob("ch_*.txt")]
            if nums:
                args.start = args.start or min(nums)
                args.end = args.end or max(nums)
    args.start = args.start or 1
    args.end = args.end or 10

    api_key = cfg.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(cfg)
    model = cfg.get("model", "deepseek-chat")

    if not api_key:
        print("[WARN] 未配置 API_KEY，将跳过 LLM 审核和修复")

    print(f"多 Agent 审改 v4 | ch{args.start}-{args.end} | batch={args.batch_size} | workers={args.workers}")

    results, merged = run_pipeline(
        cfg, args.start, args.end,
        api_key, api_url, model,
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
