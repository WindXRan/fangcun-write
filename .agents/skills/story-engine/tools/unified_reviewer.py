"""
统一审查器：一次排查所有问题，输出结构化 JSON 报告。

合并的检查项：
1. 字数偏差（对标源文 ±15%）
2. 比喻句过多（源文+3）
3. AI路标词（源文+1）
4. 直抒情过多（源文+2）
5. 台词雷同（8字以上连续匹配）
6. AI痕迹词（句首路标词）
7. LLM审稿（钩子/情绪/人设/节奏）

输出格式：统一 JSON，每章一个 entry，issue 带 type/severity/auto_fixable。
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径
current_dir = str(Path(__file__).parent)
story_tools_dir = str(Path(__file__).parent.parent.parent / 'story-tools')
sys.path.insert(0, current_dir)
sys.path.insert(0, story_tools_dir)

from lib.constants import AI_MARKERS, AI_MARKER_PATTERN, METAPHOR_PATTERN, DIRECT_EMOTION_PATTERN
from lib.text_metrics import count_metrics, get_body_chars
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text
from lib.api_client import get_api_url


# ============================================================
# Issue 数据结构
# ============================================================

ISSUE_TYPES = {
    "word_count": "字数偏差",
    "metaphor": "比喻过多",
    "ai_marker": "AI路标词",
    "direct_emotion": "直抒情过多",
    "plagiarism": "台词雷同",
    "ai_trace": "AI痕迹词",
    "hook": "开篇钩子",
    "emotion": "情绪浓度",
    "dialogue": "台词问题",
    "character": "人设问题",
    "rhythm": "节奏问题",
    "continuity": "连贯性问题",
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def make_issue(itype, severity, description, fix_instruction="", auto_fixable=False, details=None):
    """创建标准 issue 对象。"""
    return {
        "type": itype,
        "severity": severity,
        "description": description,
        "fix_instruction": fix_instruction,
        "auto_fixable": auto_fixable,
        "details": details or {},
    }


# ============================================================
# 量化检查（使用共享模块）
# ============================================================

# 兼容别名：保持旧代码的调用方式
count_chapter_metrics = count_metrics
find_plagiarisms = find_plagiarism


def get_source_metrics(get_source_text_fn, config, ch):
    """获取源文指标。"""
    text = get_source_text_fn(config, ch)
    if text:
        return count_metrics(text), text
    return None, None


def find_ai_traces(text):
    """查找句首AI痕迹词。返回 [{marker, count}]。"""
    found = []
    for marker in AI_MARKERS:
        pattern = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        matches = re.findall(pattern, text)
        if matches:
            found.append({"marker": marker, "count": len(matches)})
    return found


def check_quantitative(config, ch, ch_text, get_source_text_fn):
    """量化检查单章，返回 issue 列表。"""
    issues = []
    metrics = count_chapter_metrics(ch_text)
    src_text = get_source_text_fn(config, ch)
    src = count_chapter_metrics(src_text) if src_text else None

    # 1. 字数检查
    target = 0
    if src_text:
        src_lines = src_text.strip().split('\n')
        if src_lines and src_lines[0].startswith('第'):
            src_text_body = '\n'.join(src_lines[1:])
        else:
            src_text_body = src_text
        target = len(re.sub(r'\s', '', src_text_body))

    if target > 0:
        deviation = (metrics["chars"] - target) / target
        if abs(deviation) > 0.15:
            severity = "high" if abs(deviation) > 0.25 else "medium"
            direction = "超标" if deviation > 0 else "不足"
            issues.append(make_issue(
                "word_count", severity,
                f"字数{direction} {metrics['chars']}/{target} ({deviation:+.0%})",
                f"目标字数: {int(target*0.9)}~{int(target*1.1)}",
                auto_fixable=False,
            ))
        elif abs(deviation) > 0.10:
            issues.append(make_issue(
                "word_count", "low",
                f"字数偏差 {metrics['chars']}/{target} ({deviation:+.0%})",
                auto_fixable=False,
            ))

    # 2. 比喻句检查
    if src:
        limit = src["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append(make_issue(
                "metaphor", "medium",
                f"比喻过多 {metrics['metaphor']}处 (源文{src['metaphor']}, 上限{limit})",
                "删除或替换多余的比喻句",
                auto_fixable=False,
            ))

    # 3. AI路标词
    if src:
        limit = max(src["ai_markers"] + 1, 1)
        if metrics["ai_markers"] > limit:
            issues.append(make_issue(
                "ai_marker", "high",
                f"AI路标词 {metrics['ai_markers']}处 (源文{src['ai_markers']}, 上限{limit})",
                "删除句首的首先/其次/然后/最后等路标词",
                auto_fixable=True,
            ))

    # 4. 直抒情
    if src:
        limit = max(src["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append(make_issue(
                "direct_emotion", "medium",
                f"直抒情 {metrics['direct_emotion']}处 (源文{src['direct_emotion']}, 上限{limit})",
                "将直白的情感描写改为动作/细节暗示",
                auto_fixable=False,
            ))

    # 5. 台词雷同
    if src_text:
        plagiarisms = find_plagiarisms(ch_text, src_text)
        if plagiarisms:
            details = [{"text": p["text"], "length": p["length"]} for p in plagiarisms[:5]]
            issues.append(make_issue(
                "plagiarism", "high",
                f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）",
                "重写雷同台词，保持意思但换表达方式",
                auto_fixable=False,
                details={"matches": details},
            ))

    # 6. AI痕迹词
    ai_traces = find_ai_traces(ch_text)
    if ai_traces:
        total = sum(t["count"] for t in ai_traces)
        if total > 0:
            issues.append(make_issue(
                "ai_trace", "medium",
                f"AI痕迹词 {total}处: {', '.join(t['marker'] + '×' + str(t['count']) for t in ai_traces)}",
                "删除句首的AI痕迹词",
                auto_fixable=True,
                details={"traces": ai_traces},
            ))

    return issues, metrics


# ============================================================
# LLM 审稿（可选，批量调用）
# ============================================================

LLM_REVIEW_PROMPT = """你是资深女频网文编辑。请对以下章节进行审稿。

【审稿维度】
1. 开篇钩子：前500字是否有冲突/悬念
2. 情绪浓度：是否有起伏，不能太平淡
3. 人设一致性：角色行为是否符合设定
4. 节奏感：是否有张有弛

【输出格式】
严格按JSON格式输出，不要加其他文字：
{{
  "chapters": {{
    "1": {{"score": 75, "issues": [{{"type": "hook", "severity": "high", "description": "...", "fix_instruction": "..."}}]}},
    "2": {{"score": 80, "issues": []}}
  }}
}}

【章节内容】
{chapters_text}

{source_context}"""


def review_batch_llm(api_key, api_url, model, chapters_data, source_texts=None):
    """LLM 批量审核多章，返回 {ch: (issues, score)}。"""
    import requests

    # 拼接章节文本（35章×2000字≈7万字，截断到5万字以内）
    parts = []
    for ch, ch_text in chapters_data:
        parts.append(f"=== 第{ch}章 ===\n{ch_text[:2000]}")
    chapters_text = "\n\n".join(parts)[:50000]

    source_context = ""
    if source_texts:
        samples = []
        for ch, src in source_texts.items():
            if src:
                samples.append(f"【第{ch}章源文】\n{src[:500]}")
        source_context = "\n\n".join(samples)[:8000]
        if source_context:
            source_context = "【源文（供参考风格，不要仿写内容）】\n" + source_context

    prompt = LLM_REVIEW_PROMPT.format(
        chapters_text=chapters_text,
        source_context=source_context,
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
                "max_tokens": 16000,
            },
            timeout=180,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                out = {}
                for ch_str, ch_data in result.get("chapters", {}).items():
                    ch_num = int(ch_str)
                    issues = []
                    for item in ch_data.get("issues", []):
                        issues.append(make_issue(
                            item.get("type", "unknown"),
                            item.get("severity", "medium"),
                            item.get("description", ""),
                            item.get("fix_instruction", ""),
                            auto_fixable=False,
                        ))
                    out[ch_num] = (issues, ch_data.get("score", 0))
                return out
    except Exception as e:
        print(f"  [WARN] LLM批量审稿失败: {e}")
    return {}


# ============================================================
# 统一审查器
# ============================================================

def review_chapter_algo(config, ch, get_source_text_fn):
    """单章算法审查（不含 LLM）。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return {
            "ch": ch,
            "status": "missing",
            "score": 0,
            "metrics": {},
            "issues": [make_issue("other", "high", "文件不存在")],
        }

    ch_text = ch_file.read_text(encoding='utf-8')
    issues, metrics = check_quantitative(config, ch, ch_text, get_source_text_fn)
    issues.sort(key=lambda x: SEVERITY_ORDER.get(x["severity"], 9))

    high_count = sum(1 for i in issues if i["severity"] == "high")
    medium_count = sum(1 for i in issues if i["severity"] == "medium")
    score = 100 - high_count * 15 - medium_count * 5
    score = max(0, min(100, score))

    return {
        "ch": ch,
        "status": "FAIL" if high_count > 0 or score < 60 else "PASS",
        "score": score,
        "metrics": metrics,
        "issues": issues,
    }


def review_all(config, start, end, get_source_text_fn, api_key=None, api_url=None, model=None, llm=False, workers=5, batch_size=35):
    """审查所有章节：算法检查 + LLM 批量审稿。"""
    chapters = list(range(start, end + 1))

    # ========== Phase 1: 算法检查（并行） ==========
    print(f"  算法检查 {len(chapters)} 章...")
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(review_chapter_algo, config, ch, get_source_text_fn): ch for ch in chapters}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                results[ch] = f.result()
            except Exception as e:
                results[ch] = {"ch": ch, "status": "error", "score": 0, "metrics": {}, "issues": [make_issue("other", "high", str(e))]}

    algo_pass = sum(1 for r in results.values() if r.get("status") == "PASS")
    algo_fail = len(results) - algo_pass
    print(f"  算法检查完成: {algo_pass}通过, {algo_fail}有问题")

    # ========== Phase 2: LLM 批量审稿 ==========
    if llm and api_key:
        # 读取所有章节文本
        chapters_dir = f"{config['rewrites_dir']}/chapters"
        chapters_data = []
        source_texts = {}
        for ch in chapters:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if ch_file.exists():
                ch_text = ch_file.read_text(encoding='utf-8')
                chapters_data.append((ch, ch_text))
                src = get_source_text_fn(config, ch)
                if src:
                    source_texts[ch] = src

        # 分批调用 LLM
        print(f"  LLM 批量审稿 {len(chapters_data)} 章（{batch_size}章/批）...")
        for i in range(0, len(chapters_data), batch_size):
            batch = chapters_data[i:i+batch_size]
            batch_nums = [c[0] for c in batch]
            print(f"    批次 {i//batch_size+1}: ch{batch_nums[0]:03d}-{batch_nums[-1]:03d}")
            llm_results = review_batch_llm(api_key, api_url, model, batch, source_texts)
            for ch_num, (llm_issues, llm_score) in llm_results.items():
                if ch_num in results:
                    results[ch_num]["issues"].extend(llm_issues)
                    # 重算分数
                    all_issues = results[ch_num]["issues"]
                    high_count = sum(1 for i2 in all_issues if i2["severity"] == "high")
                    medium_count = sum(1 for i2 in all_issues if i2["severity"] == "medium")
                    score = llm_score - high_count * 10 - medium_count * 3
                    results[ch_num]["score"] = max(0, min(100, score))
                    results[ch_num]["status"] = "FAIL" if high_count > 0 or results[ch_num]["score"] < 60 else "PASS"
        print(f"  LLM 审稿完成")
    elif llm:
        print(f"  [SKIP] 未配置 API_KEY，跳过 LLM 审稿")

    return results


def save_report(results, output_path):
    """保存审查报告为 JSON。"""
    report = {
        "version": 1,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results.values() if r["status"] == "PASS"),
            "fail": sum(1 for r in results.values() if r["status"] == "FAIL"),
            "missing": sum(1 for r in results.values() if r["status"] == "missing"),
            "avg_score": round(sum(r["score"] for r in results.values()) / max(len(results), 1), 1),
            "total_issues": sum(len(r["issues"]) for r in results.values()),
            "high_issues": sum(1 for r in results.values() for i in r["issues"] if i["severity"] == "high"),
        },
        "chapters": {str(k): v for k, v in sorted(results.items())},
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def print_summary(report):
    """打印审查摘要。"""
    s = report["summary"]
    print(f"\n{'=' * 50}")
    print(f"审查完成")
    print("=" * 50)
    print(f"  总章数: {s['total']}")
    print(f"  通过: {s['pass']} | 失败: {s['fail']} | 缺失: {s['missing']}")
    print(f"  平均分: {s['avg_score']}")
    print(f"  总问题: {s['total_issues']} (高危: {s['high_issues']})")

    # 打印问题最多的章节
    problem_chapters = [
        (ch, r) for ch, r in report["chapters"].items()
        if r["status"] == "FAIL"
    ]
    problem_chapters.sort(key=lambda x: len(x[1]["issues"]), reverse=True)

    if problem_chapters:
        print(f"\n  问题最多的章节:")
        for ch, r in problem_chapters[:5]:
            issue_types = [ISSUE_TYPES.get(i["type"], i["type"]) for i in r["issues"]]
            print(f"    ch{int(ch):03d}: {r['score']}分, {len(r['issues'])}个问题 [{', '.join(issue_types)}]")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="统一审查器")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=None, help="结束章（默认自动检测）")
    parser.add_argument("--output", default=None, help="输出报告路径（默认 compare/unified_review.json）")
    parser.add_argument("--llm", action=argparse.BooleanOptionalAction, default=True, help="LLM审稿（默认开启，--no-llm 关闭）")
    parser.add_argument("--batch-size", type=int, default=35, help="LLM批量审稿每批章数（默认35）")
    parser.add_argument("--workers", type=int, default=5, help="算法检查并行数")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("base_dir", os.getcwd())

    # 自动检测章节范围
    if args.end is None:
        chapters_dir = Path(config['rewrites_dir']) / 'chapters'
        if chapters_dir.exists():
            files = list(chapters_dir.glob("ch_*.txt"))
            if files:
                nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in files]
                args.end = max(nums)
                print(f"自动检测到最大章节: {args.end}")
        if args.end is None:
            args.end = 10

    # 获取源文函数
    def get_source_text_fn(cfg, ch):
        import glob as g
        author = cfg.get('author', '')
        source_book = cfg.get('source_book', '')
        base_dir = cfg.get('base_dir', '.')
        patterns = [
            f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
            f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        ]
        for pat in patterns:
            for f in sorted(g.glob(os.path.join(base_dir, pat))):
                return Path(f).read_text(encoding='utf-8')
        return None

    # API 配置
    api_key = None
    api_url = None
    model = None
    if args.llm:
        api_key = config.get("api_key") or os.environ.get("API_KEY")
        api_url = get_api_url(config)
        model = config.get("model", "deepseek-chat")
        if not api_key:
            print("[WARN] 未配置 API_KEY，跳过 LLM 审稿")
            args.llm = False

    # 输出路径
    output = args.output or os.path.join(config['rewrites_dir'], 'compare', 'unified_review.json')

    print(f"统一审查 | ch{args.start}-{args.end} | LLM={'on' if args.llm else 'off'}")

    t0 = time.time()
    results = review_all(config, args.start, args.end, get_source_text_fn, api_key, api_url, model, args.llm, args.workers, args.batch_size)
    report = save_report(results, output)
    print_summary(report)
    print(f"  报告已保存: {output}")
    print(f"  耗时: {time.time()-t0:.0f}s")

    return report


if __name__ == "__main__":
    main()
