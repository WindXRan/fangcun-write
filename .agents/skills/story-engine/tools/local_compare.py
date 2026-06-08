"""本地对比报告：脚本定量 + LLM定性（只分析异常章）"""
import os
import sys
import re
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API_URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = """你是资深网文编辑，负责检测仿写作品的抄袭风险。

对比两份文本，给出：
1. 核心差异（2句话）
2. 质量判断（哪个更好，各自的硬伤）
3. 抄袭风险等级（低/中/高）
4. 具体问题（哪里像）

只基于文本本身做判断，不要猜测哪版是仿写。"""


def call_api(api_key, model, user_prompt, max_tokens=2048):
    """调用 DeepSeek API。"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(API_URL, headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def llm_analyze_chapter(api_key, src_text, new_text, ch):
    """用LLM分析单章（只分析异常章）"""
    prompt = f"""请对比以下两份文本：

# 源文第{ch}章
{src_text[:3000]}

# 新书第{ch}章
{new_text[:3000]}

---
请从以下角度分析：
1. 核心差异（2句话）
2. 质量判断（哪个更好，各自的硬伤）
3. 抄袭风险（低/中/高），若有雷同指出具体哪里像"""

    try:
        result = call_api(api_key, "deepseek-v4-flash", prompt)
        return result
    except Exception as e:
        return f"分析失败：{e}"
    """统计章节的量化指标。"""
    body = text.strip()
    lines = body.split('\n')
    if lines and lines[0].startswith('第'):
        body = '\n'.join(lines[1:])

    clean = re.sub(r'\s', '', body)

    # 比喻检测
    metaphor_pattern = r'(?:就像|好像|像.{1,20}(?:一样|似的|般|一般)|仿佛.{1,20}(?:一样|似的|般|一般)?|犹如|恍如|宛如|好似)'

    return {
        "chars": len(clean),
        "dash": body.count('——'),
        "metaphor": len(re.findall(metaphor_pattern, body)),
        "ai_markers": len(re.findall(r'(?:首先|其次|然后|最后|与此同时|值得注意的是|此外|综上所述|总而言之)', body)),
        "direct_emotion": len(re.findall(r'(?:充满了|感到无比|心中涌起|不由得|不禁|忍不住)', body)),
    }


def extract_dialogue(text):
    """提取台词内容（引号内的文字）"""
    dialogues = re.findall(r'\u201c([^\u201d]*)\u201d', text)
    return [d.strip() for d in dialogues if len(d.strip()) >= 4]


def calc_dialogue_overlap(src_dialogues, new_dialogues):
    """计算台词重复率（6字以上连续匹配）"""
    if not src_dialogues or not new_dialogues:
        return 0, []

    overlap_count = 0
    overlap_examples = []

    for new_d in new_dialogues:
        for src_d in src_dialogues:
            # 检查是否有6字以上连续匹配
            for i in range(len(new_d) - 5):
                chunk = new_d[i:i+6]
                if chunk in src_d:
                    overlap_count += 1
                    if len(overlap_examples) < 3:
                        overlap_examples.append(chunk)
                    break

    overlap_rate = overlap_count / len(new_dialogues) * 100 if new_dialogues else 0
    return round(overlap_rate, 1), overlap_examples


def get_source_file(base_dir, author, source_book, ch):
    """查找源文章节文件"""
    import glob
    patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
        f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        f"novel-download-authors/{author}/{source_book}/源文/第{ch}章*.txt",
    ]
    for pat in patterns:
        for f in sorted(glob.glob(os.path.join(base_dir, pat))):
            return f
    return None


def generate_report(config, start, end, output_path=None, api_key=None):
    """生成本地对比报告"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    rewrites_dir = config.get("rewrites_dir", "")
    api_key = api_key or config.get("api_key") or os.environ.get("API_KEY")

    results = []

    for ch in range(start, end + 1):
        # 读取新书
        new_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
        if not new_file.exists():
            results.append({"ch": ch, "status": "缺失", "reason": "新书文件不存在"})
            continue

        new_text = new_file.read_text(encoding='utf-8')
        new_metrics = count_metrics(new_text)
        new_dialogues = extract_dialogue(new_text)

        # 读取源文
        src_file = get_source_file(base_dir, author, source_book, ch)
        if not src_file:
            results.append({
                "ch": ch, "status": "无源文",
                "new_chars": new_metrics["chars"],

            })
            continue

        src_text = Path(src_file).read_text(encoding='utf-8')
        src_metrics = count_metrics(src_text)
        src_dialogues = extract_dialogue(src_text)

        # 计算台词重复率
        overlap_rate, overlap_examples = calc_dialogue_overlap(src_dialogues, new_dialogues)

        # 判断问题
        issues = []
        char_diff = abs(new_metrics["chars"] - src_metrics["chars"])
        char_ratio = char_diff / src_metrics["chars"] * 100 if src_metrics["chars"] > 0 else 0

        if char_ratio > 20:
            issues.append(f"字数偏差{char_ratio:.0f}%")
        if new_metrics["ai_markers"] > src_metrics["ai_markers"] + 2:
            issues.append(f"AI痕迹({new_metrics['ai_markers']}处)")
        if overlap_rate > 10:
            issues.append(f"台词重复{overlap_rate}%")

        status = "✅" if not issues else "❌"

        result = {
            "ch": ch,
            "status": status,
            "src_chars": src_metrics["chars"],
            "new_chars": new_metrics["chars"],
            "char_diff": new_metrics["chars"] - src_metrics["chars"],
            "src_ai": src_metrics["ai_markers"],
            "new_ai": new_metrics["ai_markers"],
            "overlap_rate": overlap_rate,
            "overlap_examples": overlap_examples,
            "issues": issues,
            "llm_analysis": None,
        }

        # 对异常章节用LLM分析
        if issues and api_key:
            print(f"  [LLM] 分析第{ch}章...")
            result["llm_analysis"] = llm_analyze_chapter(api_key, src_text[:3000], new_text[:3000], ch)

        results.append(result)

    # 生成报告
    if not output_path:
        output_path = Path(rewrites_dir) / "compare" / f"本地对比_{start}-{end}.md"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# 本地对比报告（第{start}-{end}章）\n")
    lines.append(f"生成时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # 统计概览
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "✅")
    failed = sum(1 for r in results if r.get("status") == "❌")
    missing = sum(1 for r in results if r.get("status") in ("缺失", "无源文"))

    lines.append(f"## 概览\n")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总章数 | {total} |")
    lines.append(f"| 通过 | {passed} |")
    lines.append(f"| 有问题 | {failed} |")
    lines.append(f"| 缺失/无源文 | {missing} |")
    lines.append(f"| 通过率 | {passed/total*100:.0f}% |")
    lines.append("")

    # 详细表格
    lines.append(f"## 详细数据\n")
    lines.append(f"| 章 | 状态 | 源文字数 | 新书字数 | 差值 | AI(源/新) | 台词重复 | 问题 |")
    lines.append(f"|---|------|---------|---------|------|----------|---------|------|")

    for r in results:
        ch = r["ch"]
        status = r.get("status", "")
        if status in ("缺失", "无源文"):
            lines.append(f"| {ch} | {status} | - | {r.get('new_chars', '-')} | - | - | - | - | {r.get('reason', '')} |")
        else:
            issues_str = "；".join(r.get("issues", [])) or "无"
            overlap = f"{r['overlap_rate']}%" if r.get('overlap_rate', 0) > 0 else "0%"
            lines.append(f"| {ch} | {status} | {r['src_chars']} | {r['new_chars']} | {r['char_diff']:+d} | {r['src_ai']}/{r['new_ai']} | {overlap} | {issues_str} |")

    lines.append("")

    # 问题汇总
    problem_chapters = [r for r in results if r.get("issues")]
    if problem_chapters:
        lines.append(f"## 问题汇总\n")
        for r in problem_chapters:
            lines.append(f"- **第{r['ch']}章**：{'；'.join(r['issues'])}")
        lines.append("")

    # 台词重复详情
    overlap_chapters = [r for r in results if r.get("overlap_rate", 0) > 0]
    if overlap_chapters:
        lines.append(f"## 台词重复详情\n")
        for r in overlap_chapters:
            if r.get("overlap_examples"):
                examples = "、".join(f'「{e}」' for e in r["overlap_examples"])
                lines.append(f"- **第{r['ch']}章**（{r['overlap_rate']}%）：{examples}")
        lines.append("")

    # LLM分析详情（只对异常章）
    llm_chapters = [r for r in results if r.get("llm_analysis")]
    if llm_chapters:
        lines.append(f"## LLM定性分析（异常章）\n")
        for r in llm_chapters:
            lines.append(f"### 第{r['ch']}章")
            lines.append(f"定量问题：{'；'.join(r.get('issues', []))}")
            lines.append(f"\n{r['llm_analysis']}\n")
        lines.append("")

    report = "\n".join(lines)
    output_path.write_text(report, encoding='utf-8')

    print(f"报告已生成：{output_path}")
    print(f"通过：{passed}/{total}，问题：{failed}/{total}")

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="本地对比报告（定量+LLM定性）")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=10, help="结束章")
    parser.add_argument("--output", help="输出文件路径（可选）")
    parser.add_argument("--api-key", help="API Key（可选，默认从环境变量读取）")
    parser.add_argument("--no-llm", action="store_true", help="禁用LLM分析（只做定量）")

    args = parser.parse_args()

    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)

    config["base_dir"] = os.path.dirname(args.config)

    api_key = None if args.no_llm else (args.api_key or config.get("api_key") or os.environ.get("API_KEY"))

    generate_report(config, args.start, args.end, args.output, api_key)
