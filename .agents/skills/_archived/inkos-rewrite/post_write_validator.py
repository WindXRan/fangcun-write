"""
post_write_validator.py — 写后验证器
复刻 inkos 的 ai-tells.ts + post-write-validator.ts + long-span-fatigue.ts
纯算法，零 LLM，确定性输出。

用法：
  python post_write_validator.py <txt文件或目录> [--json] [--lang zh|en]

功能：
  1. AI 痕迹检测（4 维度）
  2. 写后规则验证（15+ 规则）
  3. 统计指纹（句长/段长/TTR/修辞/对话占比）

输出：
  - 终端打印验证报告
  - 同目录下生成 validation_report.json
"""

import re
import json
import sys
import os
import math
from collections import Counter
from typing import Any

# 导入统一字数统计模块
try:
    from word_counter import count_words, get_word_stats
except ImportError:
    # 如果导入失败，使用本地定义
    def count_words(text: str) -> int:
        """统计字数（与番茄小说一致：所有非空格字符）"""
        if not text:
            return 0
        return len(re.sub(r'[\s\n\r]', '', text))
    
    def get_word_stats(text: str) -> dict:
        """获取详细字数统计"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        word_count = len(re.sub(r'[\s\n\r]', '', text))
        return {'chinese_chars': chinese_chars, 'total_chars': len(text), 'word_count': word_count}


# ── AI 痕迹检测（ai-tells.ts）────────────────────────────────

HEDGE_WORDS_ZH = ["似乎", "可能", "或许", "大概", "某种程度上", "一定程度上", "在某种意义上"]
TRANSITION_WORDS_ZH = ["然而", "不过", "与此同时", "另一方面", "尽管如此", "话虽如此", "但值得注意的是"]


def detect_ai_tells(content: str) -> list[dict[str, str]]:
    """检测 AI 生成痕迹（4 维度）"""
    issues = []

    # dim 20: 段落等长
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    if len(paragraphs) >= 3:
        lengths = [len(p) for p in paragraphs]
        mean = sum(lengths) / len(lengths)
        if mean > 0:
            variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
            cv = math.sqrt(variance) / mean
            if cv < 0.15:
                issues.append({
                    "severity": "warning",
                    "category": "段落等长",
                    "description": f"段落长度变异系数仅{cv:.3f}（阈值<0.15），段落长度过于均匀",
                    "suggestion": "增加段落长度差异：短段落用于节奏加速或冲击，长段落用于沉浸描写",
                })

    # dim 21: 套话密度
    total_chars = len(content)
    if total_chars > 0:
        hedge_count = sum(len(re.findall(word, content)) for word in HEDGE_WORDS_ZH)
        hedge_density = hedge_count / (total_chars / 1000)
        if hedge_density > 3:
            issues.append({
                "severity": "warning",
                "category": "套话密度",
                "description": f"套话词密度{hedge_density:.1f}次/千字（阈值>3），语气过于模糊犹豫",
                "suggestion": "用确定性叙述替代模糊表达",
            })

    # dim 22: 公式化转折
    transition_counts = {}
    for word in TRANSITION_WORDS_ZH:
        count = len(re.findall(word, content))
        if count > 0:
            transition_counts[word] = count
    repeated = [(w, c) for w, c in transition_counts.items() if c >= 3]
    if repeated:
        detail = "、".join(f'"{w}"×{c}' for w, c in repeated)
        issues.append({
            "severity": "warning",
            "category": "公式化转折",
            "description": f"转折词重复使用：{detail}",
            "suggestion": "用情节自然转折替代转折词",
        })

    # dim 23: 列表式结构
    sentences = [s.strip() for s in re.split(r"[。！？\n]", content) if len(s.strip()) > 2]
    if len(sentences) >= 3:
        max_consecutive = 1
        current = 1
        for i in range(1, len(sentences)):
            if sentences[i][:2] == sentences[i - 1][:2]:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 1
        if max_consecutive >= 3:
            issues.append({
                "severity": "info",
                "category": "列表式结构",
                "description": f"检测到{max_consecutive}句连续以相同开头的句子",
                "suggestion": "变换句式开头，打破列表感",
            })

    return issues


# ── 写后验证（post-write-validator.ts）───────────────────────

SURPRISE_MARKERS = ["仿佛", "忽然", "竟然", "猛地", "猛然", "不禁", "宛如"]

META_NARRATION_PATTERNS = [
    re.compile(r"到这里[，,]?算是"),
    re.compile(r"接下来[，,]?(?:就是|将会|即将)"),
    re.compile(r"(?:后面|之后)[，,]?(?:会|将|还会)"),
    re.compile(r"(?:故事|剧情)(?:发展)?到了"),
    re.compile(r"读者[，,]?(?:可能|应该|也许)"),
    re.compile(r"我们[，,]?(?:可以|不妨|来看)"),
]

REPORT_TERMS = [
    "核心动机", "信息边界", "信息落差", "核心风险", "利益最大化",
    "当前处境", "行为约束", "性格过滤", "情绪外化", "锚定效应",
    "沉没成本", "认知共鸣",
]

SERMON_WORDS = ["显然", "毋庸置疑", "不言而喻", "众所周知", "不难看出"]

COLLECTIVE_SHOCK_PATTERNS = [
    re.compile(r"(?:全场|众人|所有人|在场的人)[，,]?(?:都|全|齐齐|纷纷)?(?:震惊|惊呆|倒吸凉气|目瞪口呆|哗然|惊呼)"),
    re.compile(r"(?:全场|一片)[，,]?(?:寂静|哗然|沸腾|震动)"),
]


def validate_post_write(content: str, fatigue_words: list[str] | None = None) -> list[dict[str, str]]:
    """写后规则验证（15+ 规则）"""
    violations = []

    # 1. 禁止句式: "不是…而是…"
    if re.search(r"不是[^，。！？\n]{0,30}[，,]?\s*而是", content):
        violations.append({
            "rule": "禁止句式", "severity": "error",
            "description": "出现了「不是……而是……」句式",
            "suggestion": "改用直述句",
        })

    # 2. 禁止破折号
    if "——" in content:
        violations.append({
            "rule": "禁止破折号", "severity": "error",
            "description": "出现了破折号「——」",
            "suggestion": "用逗号或句号断句",
        })

    # 3. 转折/惊讶标记词密度
    marker_count = sum(len(re.findall(w, content)) for w in SURPRISE_MARKERS)
    marker_limit = max(1, len(content) // 3000)
    if marker_count > marker_limit:
        detail = "、".join(f'"{w}"×{len(re.findall(w, content))}' for w in SURPRISE_MARKERS if re.findall(w, content))
        violations.append({
            "rule": "转折词密度", "severity": "warning",
            "description": f"转折/惊讶标记词共{marker_count}次（上限{marker_limit}次），明细：{detail}",
            "suggestion": "改用具体动作或感官描写传递突然性",
        })

    # 4. 高疲劳词
    if fatigue_words:
        for word in fatigue_words:
            count = len(re.findall(re.escape(word), content))
            if count > 1:
                violations.append({
                    "rule": "高疲劳词", "severity": "warning",
                    "description": f'高疲劳词"{word}"出现{count}次（上限1次/章）',
                    "suggestion": f'替换多余的"{word}"为同义但不同形式的表达',
                })

    # 5. 元叙事
    for pattern in META_NARRATION_PATTERNS:
        match = pattern.search(content)
        if match:
            violations.append({
                "rule": "元叙事", "severity": "warning",
                "description": f'出现编剧旁白式表述："{match.group()}"',
                "suggestion": "删除元叙事，让剧情自然展开",
            })
            break

    # 6. 分析报告术语
    found_terms = [t for t in REPORT_TERMS if t in content]
    if found_terms:
        violations.append({
            "rule": "报告术语", "severity": "error",
            "description": f'正文中出现分析报告术语：{", ".join(found_terms)}',
            "suggestion": "用口语化表达替代",
        })

    # 7. 章节号指称
    chapter_refs = re.findall(r"第\s*\d+\s*章", content)
    if chapter_refs:
        unique = list(set(chapter_refs))
        violations.append({
            "rule": "章节号指称", "severity": "error",
            "description": f'正文中出现了章节号指称：{", ".join(unique)}',
            "suggestion": '改成自然表达："那天晚上"、"仓库出事那次"',
        })

    # 8. 作者说教
    found_sermons = [w for w in SERMON_WORDS if w in content]
    if found_sermons:
        violations.append({
            "rule": "作者说教", "severity": "warning",
            "description": f'出现说教词：{", ".join(found_sermons)}',
            "suggestion": "删除说教词，让读者自己从情节中判断",
        })

    # 9. 全场震惊
    for pattern in COLLECTIVE_SHOCK_PATTERNS:
        match = pattern.search(content)
        if match:
            violations.append({
                "rule": "集体反应", "severity": "warning",
                "description": f'出现集体反应套话："{match.group()}"',
                "suggestion": "改写成1-2个具体角色的身体反应",
            })
            break

    # 10. 连续了字
    sentences = [s.strip() for s in re.split(r"[。！？]", content) if len(s.strip()) > 2]
    max_consecutive_le = 0
    current = 0
    for s in sentences:
        if "了" in s:
            current += 1
            max_consecutive_le = max(max_consecutive_le, current)
        else:
            current = 0
    if max_consecutive_le >= 6:
        violations.append({
            "rule": "连续了字", "severity": "warning",
            "description": f'检测到{max_consecutive_le}句连续包含"了"字，节奏拖沓',
            "suggestion": '保留最有力的一个「了」，其余改为无「了」句式',
        })

    # 11. 段落过长
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    long_paras = [p for p in paragraphs if len(p) > 300]
    if len(long_paras) >= 2:
        violations.append({
            "rule": "段落过长", "severity": "warning",
            "description": f"{len(long_paras)}个段落超过300字，不适合手机阅读",
            "suggestion": "长段落拆分为3-5行的短段落",
        })

    # 12. 段落过碎
    narrative_paras = [p for p in paragraphs if not re.match(r'^[""「『]', p)]
    short_paras = [p for p in narrative_paras if len(p) < 35]
    if narrative_paras and len(short_paras) / len(narrative_paras) >= 0.6 and len(short_paras) >= 4:
        violations.append({
            "rule": "段落过碎", "severity": "warning",
            "description": f"{len(narrative_paras)}个段落里有{len(short_paras)}个不足35字",
            "suggestion": "把相邻的动作、观察、反应适当并段",
        })

    # 13. 连续短段
    max_consecutive_short = 0
    current = 0
    for p in narrative_paras:
        if len(p) < 35:
            current += 1
            max_consecutive_short = max(max_consecutive_short, current)
        else:
            current = 0
    if max_consecutive_short >= 3:
        violations.append({
            "rule": "连续短段", "severity": "warning",
            "description": f"连续出现{max_consecutive_short}个不足35字的短段",
            "suggestion": "把连续的碎动作重新编组",
        })

    return violations


# ── 跨章重复检测 ─────────────────────────────────────────────

def detect_cross_chapter_repetition(current: str, recent: str) -> list[dict[str, str]]:
    """检测跨章重复短语"""
    if not recent or len(recent) < 100:
        return []

    chars_curr = re.sub(r"[\s\n\r]", "", current)
    chars_recent = re.sub(r"[\s\n\r]", "", recent)

    phrase_counts: Counter[str] = Counter()
    for i in range(len(chars_curr) - 5):
        phrase = chars_curr[i:i + 6]
        if re.match(r"^[\u4e00-\u9fff]{6}$", phrase):
            phrase_counts[phrase] += 1

    cross_repeats = []
    for phrase, count in phrase_counts.items():
        if count >= 2 and phrase in chars_recent:
            cross_repeats.append(f'"{phrase}"(×{count})')

    if len(cross_repeats) >= 3:
        return [{
            "rule": "跨章重复", "severity": "warning",
            "description": f"{len(cross_repeats)}个重复短语在近期章节中也出现过：{'、'.join(cross_repeats[:5])}",
            "suggestion": "变换动作描写和场景用语，避免跨章节机械重复",
        }]
    return []


# ── 统计指纹 ─────────────────────────────────────────────────

RHETORICAL_PATTERNS = [
    ("比喻(像/如/仿佛)", re.compile(r"[像如仿佛似](?:是|同|一般|一样)")),
    ("排比", re.compile(r"[，。；]([^，。；]{2,6})[，。；]\1")),
    ("反问", re.compile(r"难道|怎么可能|岂不是|何尝不")),
    ("夸张", re.compile(r"天崩地裂|惊天动地|翻天覆地|震耳欲聋")),
    ("拟人", re.compile(r"[风雨雪月花树草石](?:在|像|仿佛).*?(?:笑|哭|叹|呻|吟|怒|舞)")),
    ("短句节奏", re.compile(r"[。！？][^。！？]{1,8}[。！？]")),
]


def analyze_style(text: str) -> dict[str, Any]:
    """统计指纹分析"""
    sentences = [s.strip() for s in re.split(r"[。！？\n]", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # 句长
    sent_lengths = [len(s) for s in sentences]
    sent_avg = sum(sent_lengths) / len(sent_lengths) if sent_lengths else 0
    sent_stddev = math.sqrt(sum((l - sent_avg) ** 2 for l in sent_lengths) / len(sent_lengths)) if len(sent_lengths) > 1 else 0

    # 段长
    para_lengths = [len(p) for p in paragraphs]
    para_avg = sum(para_lengths) / len(para_lengths) if para_lengths else 0

    # TTR
    chars = re.sub(r"[\s\n\r\u3002\uff01\uff1f\u3001\uff1a\uff1b\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300a\u300b\d]", "", text)
    ttr = round(len(set(chars)) / len(chars), 3) if chars else 0

    # 对话占比
    dialogue_chars = 0
    for m in re.finditer(r"\u201c([^\u201d]*)\u201d", text):
        dialogue_chars += len(m.group(1))
    dialogue_ratio = round(dialogue_chars / len(text), 3) if text else 0

    # 短句/长句占比
    short_ratio = sum(1 for l in sent_lengths if l < 15) / len(sent_lengths) if sent_lengths else 0
    long_ratio = sum(1 for l in sent_lengths if l > 60) / len(sent_lengths) if sent_lengths else 0

    # 单句成段占比
    single_para = sum(1 for p in paragraphs if len([s for s in re.split(r"[。！？]", p) if s.strip()]) == 1)
    single_ratio = round(single_para / len(paragraphs), 3) if paragraphs else 0

    # 高频句首
    opening_counter: Counter[str] = Counter()
    for s in sentences:
        if len(s) >= 2:
            opening_counter[s[:2]] += 1
    top_patterns = [f"{p}...({c}次)" for p, c in opening_counter.most_common(5) if c >= 3]

    # 修辞
    rhetorical = []
    for name, pattern in RHETORICAL_PATTERNS:
        matches = pattern.findall(text)
        if len(matches) >= 2:
            rhetorical.append(f"{name}({len(matches)}处)")

    return {
        "sentence_length": {"avg": round(sent_avg, 1), "stddev": round(sent_stddev, 1)},
        "paragraph_length": {"avg": round(para_avg), "min": min(para_lengths) if para_lengths else 0, "max": max(para_lengths) if para_lengths else 0},
        "vocabulary_ttr": ttr,
        "dialogue_ratio": dialogue_ratio,
        "short_sentence_ratio": round(short_ratio, 3),
        "long_sentence_ratio": round(long_ratio, 3),
        "single_sentence_para_ratio": single_ratio,
        "top_opening_patterns": top_patterns,
        "rhetorical_features": rhetorical,
    }


# ── 主函数 ───────────────────────────────────────────────────

def validate_file(filepath: str) -> dict[str, Any]:
    """对单个文件执行全部验证"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    ai_tells = detect_ai_tells(content)
    post_write = validate_post_write(content)
    style = analyze_style(content)

    # 使用统一字数统计（与番茄一致：所有非空格字符）
    word_stats = get_word_stats(content)
    total_words = word_stats['word_count']

    all_issues = ai_tells + post_write
    errors = [i for i in all_issues if i.get("severity") == "error"]
    warnings = [i for i in all_issues if i.get("severity") == "warning"]

    return {
        "file": os.path.basename(filepath),
        "total_chars": len(content),
        "total_words": total_words,
        "chinese_chars": word_stats['chinese_chars'],
        "word_stats": word_stats,
        "style": style,
        "issues": all_issues,
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "total": len(all_issues),
            "pass": len(errors) == 0,
        },
    }


def format_report(result: dict[str, Any]) -> str:
    """格式化验证报告"""
    lines = [
        f"═══ 写后验证报告 ═══",
        f"文件：{result['file']}",
        f"总字符数：{result['total_chars']}",
        f"字数（番茄标准）：{result['total_words']}",
        "",
        "── 统计指纹 ──",
        f"  句长均值：{result['style']['sentence_length']['avg']} 字 (σ={result['style']['sentence_length']['stddev']})",
        f"  段长均值：{result['style']['paragraph_length']['avg']} 字",
        f"  TTR：{result['style']['vocabulary_ttr']}",
        f"  对话占比：{result['style']['dialogue_ratio'] * 100:.1f}%",
        f"  短句占比：{result['style']['short_sentence_ratio'] * 100:.1f}%",
        f"  单句成段：{result['style']['single_sentence_para_ratio'] * 100:.1f}%",
    ]

    if result["style"]["top_opening_patterns"]:
        lines.append(f"  高频句首：{', '.join(result['style']['top_opening_patterns'])}")
    if result["style"]["rhetorical_features"]:
        lines.append(f"  修辞特征：{', '.join(result['style']['rhetorical_features'])}")

    lines.append("")
    lines.append("── 验证结果 ──")
    lines.append(f"  错误：{result['summary']['errors']}")
    lines.append(f"  警告：{result['summary']['warnings']}")
    lines.append(f"  状态：{'PASS' if result['summary']['pass'] else 'FAIL'}")

    if result["issues"]:
        lines.append("")
        lines.append("── 问题明细 ──")
        for issue in result["issues"]:
            sev = issue.get("severity", "?").upper()
            cat = issue.get("category") or issue.get("rule", "?")
            desc = issue.get("description", "")
            sugg = issue.get("suggestion", "")
            lines.append(f"  [{sev}] {cat}: {desc}")
            if sugg:
                lines.append(f"         → {sugg}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python post_write_validator.py <txt文件或目录> [--json]")
        sys.exit(1)

    target = sys.argv[1]
    output_json = "--json" in sys.argv

    files = []
    if os.path.isdir(target):
        for f in sorted(os.listdir(target)):
            if f.endswith(".txt") and not f.endswith("_style_profile.json"):
                files.append(os.path.join(target, f))
    elif os.path.isfile(target):
        files = [target]
    else:
        print(f"错误: {target} 不存在")
        sys.exit(1)

    results = []
    for filepath in files:
        result = validate_file(filepath)
        results.append(result)

    # 输出
    outpath = os.path.splitext(files[0])[0] + "_validation.json" if len(files) == 1 else os.path.join(target, "validation_report.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(results if len(results) > 1 else results[0], f, ensure_ascii=False, indent=2)

    if output_json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(format_report(result))
            print()
        print(f"已保存: {outpath}")


if __name__ == "__main__":
    main()
