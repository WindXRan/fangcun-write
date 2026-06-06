# -*- coding: utf-8 -*-
"""
verify_chapter.py — 一键检查写章质量
用法: python verify_chapter.py <章节.txt> [de-ai_guide.md]

检查项：
1. 字数（word_count.py standard模式）
2. 句长/段长/短句比/对话占比/TTR（style_analyzer.py）
3. 如有 de-ai_guide，比对各指标偏差是否在±30%内
"""

import re
import sys
import json
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_count import count_chapter_words
from style_analyzer import analyze_style


TARGET_KEYS = [
    ("字数", "total_words", 0.15),
    ("句长均值", "sentence_avg", 0.30),
    ("短句<15", "short_sentence_ratio", 0.30),
    ("段长均值", "para_avg", 0.30),
    ("单句成段", "single_para_ratio", 0.30),
    ("对话占比", "dialogue_ratio", 0.30),
    ("TTR", "ttr", 0.30),
]


def parse_targets(guide_path: str) -> dict:
    """从 de-ai_guide.md 解析指纹目标值"""
    with open(guide_path, "r", encoding="utf-8") as f:
        text = f.read()

    targets = {}

    # 字数：2949字
    m = re.search(r"字数[：:]\s*(\d+)", text)
    if m:
        targets["total_words"] = int(m.group(1))

    # 句长均值/标准差：25.8 / 19.3
    m = re.search(r"句长均值[^：:]*[：:]\s*([\d.]+)", text)
    if m:
        targets["sentence_avg"] = float(m.group(1))

    # 短句(<15字)占比：36.3%
    m = re.search(r"短句[（(<][^）)>]*[）)>].*?[：:]\s*([\d.]+)", text)
    if m:
        targets["short_sentence_ratio"] = float(m.group(1))

    # 段长均值/范围：24.1字 / 0-70
    m = re.search(r"段长均值[^：:]*[：:]\s*([\d.]+)", text)
    if m:
        targets["para_avg"] = float(m.group(1))

    # 单句成段占比：79.8%
    m = re.search(r"单句成段[^：:]*[：:]\s*([\d.]+)", text)
    if m:
        targets["single_para_ratio"] = float(m.group(1))

    # 对话占比：17.7%
    m = re.search(r"对话占比[^：:]*[：:]\s*([\d.]+)", text)
    if m:
        targets["dialogue_ratio"] = float(m.group(1))

    # TTR词汇多样性：0.27 → 存为百分比 27.0
    m = re.search(r"TTR[^：:]*[：:]\s*([\d.]+)", text)
    if m:
        targets["ttr"] = float(m.group(1)) * 100

    return targets


def get_actual(chapter_path: str) -> dict:
    """读取章节文件，提取实际指纹"""
    with open(chapter_path, "r", encoding="utf-8") as f:
        text = f.read()

    result = {}
    result["total_words"] = count_chapter_words(text)

    profile = analyze_style(text)
    result["sentence_avg"] = profile["sentence_length"]["avg"]
    result["short_sentence_ratio"] = profile["sentence_distribution"]["short_ratio_lt15"] * 100
    result["para_avg"] = profile["paragraph_length"]["avg"]
    result["single_para_ratio"] = profile["paragraph_distribution"]["single_sentence_ratio"] * 100
    result["dialogue_ratio"] = profile["dialogue_ratio"] * 100
    result["ttr"] = profile["vocabulary_ttr"] * 100  # 转为百分比以对标

    return result


def _exact_sentence_counts(text):
    """统计精确的短/中/长句数量"""
    import re
    # 中文分句：句号/问号/感叹号/省略号/分号
    raw = re.split(r'(?<=[。！？…；])', text)
    sents = [s.strip() for s in raw if len(s.strip()) > 2]
    short = sum(1 for s in sents if len(s) < 15)
    medium = sum(1 for s in sents if 15 <= len(s) <= 30)
    long_ = sum(1 for s in sents if len(s) > 30)
    max_len = max((len(s) for s in sents), default=0)
    return short, medium, long_, len(sents), max_len


def _exact_para_single(text):
    """统计单句成段的精确数量"""
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    return sum(1 for p in paras if len(p) < 40 and '。' not in p)


def _exact_dialogue_count(text):
    """统计对话句数量（含引号的行）"""
    import re
    return len(re.findall(r'[""「]', text))


def _first_words_variety(text):
    """统计句首词多样性（去AI关键指标）"""
    import re
    sents = re.split(r'(?<=[。！？…])', text)
    firsts = [s.strip()[:4] for s in sents if len(s.strip()) > 3]
    unique = len(set(firsts)) if firsts else 0
    total = len(firsts) or 1
    return unique, total


def _conjunction_density(text):
    """统计连接词密度（AI过度使用的标志）"""
    conj = ['但是', '然而', '虽然', '不过', '而且', '并且', '所以', '因此', '因为', '如果', '那么']
    count = sum(text.count(c) for c in conj)
    return count


def _para_distribution(text):
    """段落长度分布：精确计数"""
    import re
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    short_p = sum(1 for p in paras if len(p) < 50)
    medium_p = sum(1 for p in paras if 50 <= len(p) <= 200)
    long_p = sum(1 for p in paras if len(p) > 200)
    return short_p, medium_p, long_p, len(paras)


def _punctuation_density(text):
    """标点符号使用密度"""
    punct = sum(1 for c in text if c in '，。！？、；：')
    sents = sum(1 for c in text if c in '。！？')
    return punct, sents


def _unique_first_words(text, n=10):
    """展示源文句首词样本"""
    import re
    sents = re.split(r'(?<=[。！？…])', text)
    firsts = []
    for s in sents:
        s = s.strip()
        if len(s) > 3:
            # 取前2字作为句首特征
            w = s[:4].lstrip('"\'"「『')
            if w:
                firsts.append(w)
    unique = list(dict.fromkeys(firsts))  # 去重保序
    return unique[:n]


def gen_guide(source_path: str, output_path: str):
    """生成 de-ai_guide：从源文提取人类写作特征作为写章参考"""
    with open(source_path, "r", encoding="utf-8") as f:
        text = f.read()

    wc = count_chapter_words(text)
    prof = analyze_style(text)

    short_c, medium_c, long_c, total_sent, max_len = _exact_sentence_counts(text)
    single_para_c = _exact_para_single(text)
    dialogue_c = _exact_dialogue_count(text)
    first_uniq, first_total = _first_words_variety(text)
    conj_count = _conjunction_density(text)
    short_p, medium_p, long_p, total_para = _para_distribution(text)
    punct_c, sent_c = _punctuation_density(text)
    first_samples = _unique_first_words(text)

    punct_per_sent = f"{punct_c / max(sent_c, 1):.1f}"
    first_rate = f"{first_uniq / max(first_total, 1) * 100:.0f}%"

    lines = [
        "## 源文写作特征（写章时对齐此节奏）",
        "",
        f"### 篇幅",
        f"- {wc}字 / {total_para}段 / {total_sent}句",
        "",
        f"### 句长分布",
        f"- 短句(<15字)：{short_c}句",
        f"- 中句(15-30字)：{medium_c}句",
        f"- 长句(>30字)：{long_c}句（最长{max_len}字）",
        f"- 标点密度：每句{punct_per_sent}个标点",
        "",
        f"### 段落节奏",
        f"- 短段(<50字)：{short_p}段",
        f"- 中段(50-200字)：{medium_p}段",
        f"- 长段(>200字)：{long_p}段",
        f"- 单句成段：{single_para_c}处",
        "",
        f"### 对话",
        f"- {dialogue_c}处引号",
        "",
        f"### 词汇特征",
        f"- 句首多样性：{first_rate}（{first_uniq}/{first_total}种），如「{'」/「'.join(first_samples)}」",
        f"- 连接词（但/然而/所以等）：{conj_count}次",
        f"- TTR：{prof['vocabulary_ttr']:.2f}",
        "",

    ]

    output = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"已生成: {output_path}")
    print(output)


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python verify_chapter.py <章节.txt> [de-ai_guide.md]    # 检查质量")
        print("  python verify_chapter.py --gen-guide <源文.txt> -o <输出.md>   # 生成指纹")
        sys.exit(1)

    # --gen-guide 模式
    if sys.argv[1] == "--gen-guide":
        if len(sys.argv) < 4 or sys.argv[3] != "-o":
            print("用法: python verify_chapter.py --gen-guide <源文.txt> -o <输出.md>")
            sys.exit(1)
        gen_guide(sys.argv[2], sys.argv[4])
        return

    # 检查模式
    chapter_path = sys.argv[1]
    guide_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(chapter_path):
        print(f"错误: 文件不存在 - {chapter_path}")
        sys.exit(1)

    actual = get_actual(chapter_path)
    targets = parse_targets(guide_path) if guide_path and os.path.exists(guide_path) else {}

    lines = []
    all_pass = True

    for label, key, tolerance in TARGET_KEYS:
        val = actual.get(key)
        target = targets.get(key)

        if val is not None:
            val_str = f"{val:.1f}" if isinstance(val, float) else str(val)
        else:
            val_str = "N/A"

        if target is not None:
            target_val = target
            dev = (val - target_val) / target_val if target_val != 0 else 0
            dev_pct = dev * 100
            within = abs(dev) <= tolerance
            mark = "OK" if within else "!!"
            if not within:
                all_pass = False
            lines.append(f"  [{mark}] {label}: 目标{target_val} | 实际{val_str} | 偏差{dev_pct:+.1f}%")
        else:
            lines.append(f"  [?] {label}: 实际{val_str} (无目标)")

    print("=== 章节质量检查 ===")
    print(f"文件: {os.path.basename(chapter_path)}")
    print(f"结果: {'PASS 全部通过' if all_pass else 'FAIL 有指标超限'}")
    print()
    print("\n".join(lines))
    print()
    print(f"回传: 均句长{actual.get('sentence_avg', '?'):.1f}/短句{actual.get('short_sentence_ratio', '?'):.0f}%/段长中位{actual.get('para_avg', '?'):.0f}")


if __name__ == "__main__":
    main()
