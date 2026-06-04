"""
style_analyzer.py — 文风统计指纹提取
复刻 inkos style-analyzer.ts，纯算法，零 LLM，确定性输出。

用法：
  python style_analyzer.py <txt文件路径> [--name 源名] [--json]

输出：
  - 终端打印统计结果
  - 同目录下生成 style_profile.json
"""

import re
import json
import sys
import os
from collections import Counter
from typing import Any

# 导入统一字数统计模块
try:
    from word_counter import count_words, get_word_stats
except ImportError:
    # 如果导入失败，使用本地定义
    def count_words(text: str) -> int:
        """统计汉字数量（与番茄小说一致）"""
        if not text:
            return 0
        chinese_chars = re.sub(r'[^\u4e00-\u9fff]', '', text)
        return len(chinese_chars)
    
    def get_word_stats(text: str) -> dict:
        """获取详细字数统计"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        return {'chinese_chars': chinese_chars, 'total_chars': len(text)}


# ── 修辞模式正则（与 inkos 对齐）──────────────────────────────

RHETORICAL_PATTERNS = [
    ("比喻(像/如/仿佛)", re.compile(r"[像如仿佛似](?:是|同|一般|一样)")),
    ("排比", re.compile(r"[，。；]([^，。；]{2,6})[，。；]\1")),
    ("反问", re.compile(r"难道|怎么可能|岂不是|何尝不")),
    ("夸张", re.compile(r"天崩地裂|惊天动地|翻天覆地|震耳欲聋")),
    ("拟人", re.compile(r"[风雨雪月花树草石](?:在|像|仿佛).*?(?:笑|哭|叹|呻|吟|怒|舞)")),
    ("短句节奏", re.compile(r"[。！？][^。！？]{1,8}[。！？]")),
]

# ── AI 痕迹检测 ──────────────────────────────────────────────

AI_TELLS = [
    ("路标词", re.compile(r"首先|其次|最后|总而言之|综上所述|值得注意的是")),
    ("二分对照", re.compile(r"一方面.{1,20}另一方面")),
    ("协作口吻", re.compile(r"让我们|接下来|现在我们")),
    ("高频副词", re.compile(r"微微|轻轻|淡淡|缓缓")),
    ("说道", re.compile(r"她说道|他说道|她轻声道|他低声道")),
]


def split_sentences(text: str) -> list[str]:
    """按中文句号/感叹号/问号分句（不按换行分句）"""
    # 先把换行符替换为空格
    text = text.replace('\n', ' ')
    # 按句号、感叹号、问号分句
    parts = re.split(r"[。！？]", text)
    return [s.strip() for s in parts if s.strip()]


def count_chinese_chars(text: str) -> int:
    """统计纯汉字数量（不含标点）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def split_paragraphs(text: str) -> list[str]:
    """按空行分段"""
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def calc_stats(values: list[int]) -> dict[str, float]:
    """计算均值、标准差"""
    if not values:
        return {"avg": 0, "stddev": 0}
    avg = sum(values) / len(values)
    if len(values) < 2:
        return {"avg": round(avg, 1), "stddev": 0}
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    stddev = variance ** 0.5
    return {"avg": round(avg, 1), "stddev": round(stddev, 1)}


def analyze_style(text: str, source_name: str = "") -> dict[str, Any]:
    """分析文本风格，返回统计指纹"""

    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    # ── 句长统计（纯汉字数）──
    sentence_lengths = [count_chinese_chars(s) for s in sentences]
    sentence_stats = calc_stats(sentence_lengths)

    # ── 段长统计（纯汉字，与句长口径一致）──
    paragraph_lengths = [count_chinese_chars(p) for p in paragraphs]
    para_stats = calc_stats(paragraph_lengths)
    para_min = min(paragraph_lengths) if paragraph_lengths else 0
    para_max = max(paragraph_lengths) if paragraph_lengths else 0

    # ── 词汇多样性 TTR ──
    chars = re.sub(r"[\s\n\r\u3002\uff01\uff1f\u3001\uff1a\uff1b\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300a\u300b\d]", "", text)
    unique_chars = set(chars)
    ttr = round(len(unique_chars) / len(chars), 3) if chars else 0

    # ── 高频句首模式（前2字，top5）──
    opening_counter: Counter[str] = Counter()
    for s in sentences:
        if len(s) >= 2:
            opening_counter[s[:2]] += 1
    top_patterns = [
        f"{pattern}...({count}次)"
        for pattern, count in opening_counter.most_common(5)
        if count >= 3
    ]

    # ── 修辞特征 ──
    rhetorical_features = []
    for name, pattern in RHETORICAL_PATTERNS:
        matches = pattern.findall(text)
        if len(matches) >= 2:
            rhetorical_features.append(f"{name}({len(matches)}处)")

    # ── AI 痕迹 ──
    ai_tells = []
    for name, pattern in AI_TELLS:
        matches = pattern.findall(text)
        if matches:
            ai_tells.append(f"{name}({len(matches)}处)")

    # ── 对话占比（对话汉字数 / 总汉字数）──
    dialogue_chars = 0
    # 中文双引号对话 ""
    for m in re.finditer(r"\u201c([^\u201d]*)\u201d", text):
        dialogue_chars += count_chinese_chars(m.group(1))
    # 中文单引号对话 ''
    for m in re.finditer(r"\u2018([^\u2019]*)\u2019", text):
        dialogue_chars += count_chinese_chars(m.group(1))
    # 中文书名号对话 「」
    for m in re.finditer(r"\u300c([^\u300d]*)\u300d", text):
        dialogue_chars += count_chinese_chars(m.group(1))
    # 英文双引号对话 ""
    for m in re.finditer(r'"([^"]*)"', text):
        dialogue_chars += count_chinese_chars(m.group(1))
    # 中文破折号对话 ——
    for m in re.finditer(r"\u2014\u2014([^\u2014\u2014]*)\u2014\u2014", text):
        dialogue_chars += count_chinese_chars(m.group(1))
    total_chinese = count_chinese_chars(text)
    dialogue_ratio = round(dialogue_chars / total_chinese, 3) if total_chinese else 0

    # ── 短句/长句占比 ──
    short_sentences = sum(1 for l in sentence_lengths if l < 15)
    long_sentences = sum(1 for l in sentence_lengths if l > 60)
    total_sentences = len(sentence_lengths) if sentence_lengths else 1
    short_ratio = round(short_sentences / total_sentences, 3)
    long_ratio = round(long_sentences / total_sentences, 3)

    # ── 单句成段占比 ──
    single_sentence_paras = sum(1 for p in paragraphs if len(split_sentences(p)) == 1)
    single_para_ratio = round(single_sentence_paras / len(paragraphs), 3) if paragraphs else 0

    # ── 段长分布 ──
    short_paras = sum(1 for l in paragraph_lengths if l < 50)
    medium_paras = sum(1 for l in paragraph_lengths if 50 <= l <= 200)
    long_paras = sum(1 for l in paragraph_lengths if l > 200)
    total_paras = len(paragraphs) if paragraphs else 1

    # 使用统一字数统计（与番茄一致）
    word_stats = get_word_stats(text)
    total_words = word_stats['chinese_chars']

    return {
        "source_name": source_name,
        "total_chars": len(text),
        "total_words": total_words,
        "total_sentences": len(sentences),
        "total_paragraphs": len(paragraphs),

        "sentence_length": {
            "avg": sentence_stats["avg"],
            "stddev": sentence_stats["stddev"],
        },
        "paragraph_length": {
            "avg": para_stats["avg"],
            "stddev": para_stats["stddev"],
            "min": para_min,
            "max": para_max,
        },
        "vocabulary_ttr": ttr,
        "dialogue_ratio": dialogue_ratio,

        "sentence_distribution": {
            "short_ratio_lt15": short_ratio,
            "long_ratio_gt60": long_ratio,
        },
        "paragraph_distribution": {
            "short_lt50": round(short_paras / total_paras, 3),
            "medium_50_200": round(medium_paras / total_paras, 3),
            "long_gt200": round(long_paras / total_paras, 3),
            "single_sentence_ratio": single_para_ratio,
        },

        "top_opening_patterns": top_patterns,
        "rhetorical_features": rhetorical_features,
        "ai_tells": ai_tells,
    }


def format_report(profile: dict[str, Any]) -> str:
    """格式化为可读报告"""
    lines = [
        f"═══ 文风统计指纹 ═══",
        f"源文件：{profile['source_name'] or '(未命名)'}",
        f"总字符数：{profile['total_chars']}",
        f"字数（番茄标准）：{profile['total_words']}",
        f"总句数：{profile['total_sentences']}",
        f"总段数：{profile['total_paragraphs']}",
        "",
        "── 句长 ──",
        f"  均值：{profile['sentence_length']['avg']} 字",
        f"  标准差：{profile['sentence_length']['stddev']}",
        f"  短句(<15字)占比：{profile['sentence_distribution']['short_ratio_lt15'] * 100:.1f}%",
        f"  长句(>60字)占比：{profile['sentence_distribution']['long_ratio_gt60'] * 100:.1f}%",
        "",
        "── 段长 ──",
        f"  均值：{profile['paragraph_length']['avg']} 字",
        f"  范围：{profile['paragraph_length']['min']}-{profile['paragraph_length']['max']}",
        f"  短段(<50字)：{profile['paragraph_distribution']['short_lt50'] * 100:.1f}%",
        f"  中段(50-200字)：{profile['paragraph_distribution']['medium_50_200'] * 100:.1f}%",
        f"  长段(>200字)：{profile['paragraph_distribution']['long_gt200'] * 100:.1f}%",
        f"  单句成段占比：{profile['paragraph_distribution']['single_sentence_ratio'] * 100:.1f}%",
        "",
        "── 词汇 ──",
        f"  TTR（词汇多样性）：{profile['vocabulary_ttr']}",
        f"  对话占比：{profile['dialogue_ratio'] * 100:.1f}%",
    ]

    if profile["top_opening_patterns"]:
        lines.append("")
        lines.append("── 高频句首 ──")
        for p in profile["top_opening_patterns"]:
            lines.append(f"  {p}")

    if profile["rhetorical_features"]:
        lines.append("")
        lines.append("── 修辞特征 ──")
        for f in profile["rhetorical_features"]:
            lines.append(f"  {f}")

    if profile["ai_tells"]:
        lines.append("")
        lines.append("── AI 痕迹 ──")
        for t in profile["ai_tells"]:
            lines.append(f"  [!] {t}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python style_analyzer.py <txt文件> [--name 源名] [--json]")
        sys.exit(1)

    filepath = sys.argv[1]
    source_name = ""
    output_json = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--name" and i + 1 < len(sys.argv):
            source_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--json":
            output_json = True
            i += 1
        else:
            i += 1

    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    if not source_name:
        source_name = os.path.basename(filepath)

    profile = analyze_style(text, source_name)

    if output_json:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        print(format_report(profile))


if __name__ == "__main__":
    main()
