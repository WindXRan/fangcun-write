"""风格定量指标：对全书源文跑 text_metrics，汇总为锚点数据。"""

import sys
import json
import statistics
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"))
from lib.text_metrics import count_metrics, count_style_fingerprint


def calc_book_metrics(source_dir):
    """对全书源文计算定量指标。"""
    source_dir = Path(source_dir)
    chapters = sorted(source_dir.glob("第*章*.txt"))
    
    if not chapters:
        print(f"  [FAIL] 未找到源文章节: {source_dir}")
        return None
    
    all_metrics = []
    all_fingerprints = []
    
    for ch_file in chapters:
        text = ch_file.read_text(encoding="utf-8")
        m = count_metrics(text)
        f = count_style_fingerprint(text)
        all_metrics.append(m)
        all_fingerprints.append(f)
    
    # 汇总
    def avg(key, data):
        vals = [d.get(key, 0) for d in data]
        return round(statistics.mean(vals), 2) if vals else 0

    def median(key, data):
        vals = [d.get(key, 0) for d in data]
        return round(statistics.median(vals), 2) if vals else 0

    def stddev(key, data):
        vals = [d.get(key, 0) for d in data]
        return round(statistics.stdev(vals), 2) if len(vals) > 1 else 0

    def _majority(key, data):
        """取众数（出现最多的值）。"""
        from collections import Counter
        vals = [d.get(key, "") for d in data if d.get(key)]
        if not vals:
            return ""
        return Counter(vals).most_common(1)[0][0]

    def _avg_punct(fingerprints):
        """汇总标点密度。"""
        excls = []
        ellips = []
        dashes = []
        for fp in fingerprints:
            ps = fp.get("punct_style", {})
            if isinstance(ps, dict):
                excls.append(ps.get("exclamation", 0))
                ellips.append(ps.get("ellipsis", 0))
                dashes.append(ps.get("dash", 0))
        return {
            "exclamation": round(statistics.mean(excls), 2) if excls else 0,
            "ellipsis": round(statistics.mean(ellips), 2) if ellips else 0,
            "dash": round(statistics.mean(dashes), 2) if dashes else 0,
        }
    
    summary = {
        "total_chapters": len(chapters),
        "chars": {
            "avg": avg("chars", all_metrics),
            "median": median("chars", all_metrics),
            "stddev": stddev("chars", all_metrics),
        },
        "sent_len": {
            "avg": avg("sent_len_stddev", all_metrics),
            "median": median("sent_len_stddev", all_metrics),
        },
        "para": {
            "avg_len": avg("para_avg", all_metrics),
            "avg_per_chapter": avg("avg_sent_per_para", all_metrics),
        },
        "dialogue": {
            "tag_density": avg("tag_density", all_metrics),
            "ratio": avg("dialogue_ratio", all_fingerprints),
        },
        "emotion": {
            "density": avg("emotion_density", all_fingerprints),
            "direct_emotion": avg("direct_emotion", all_metrics),
        },
        "ai_markers": avg("ai_markers", all_metrics),
        "metaphor": avg("metaphor", all_metrics),
        "psych_ratio": avg("psych_ratio", all_metrics),
        "single_sent_ratio": avg("single_sent_ratio", all_fingerprints),
        "punctuation": _avg_punct(all_fingerprints),
    }
    
    return summary


def format_metrics_report(summary):
    """格式化为可读的 markdown 报告。"""
    s = summary
    lines = []
    lines.append("## 定量风格锚点\n")
    lines.append(f"**样本**: {s['total_chapters']} 章\n")
    lines.append(f"- **章均字数**: {s['chars']['avg']}（中位数 {s['chars']['median']}，标准差 {s['chars']['stddev']}）")
    lines.append(f"- **对话比例**: {s['dialogue']['ratio']*100:.0f}%")
    lines.append(f"- **段落均长**: {s['para']['avg_len']} 字")
    
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="风格定量指标")
    parser.add_argument("source_dir", help="源文章节目录")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()
    
    summary = calc_book_metrics(args.source_dir)
    if not summary:
        return
    
    report = format_metrics_report(summary)
    print(report)
    
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\n[SAVED] {args.output}")
    
    # 同时保存 JSON
    json_path = args.output.replace(".md", ".json") if args.output else "style_metrics.json"
    Path(json_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {json_path}")


if __name__ == "__main__":
    main()
