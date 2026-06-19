"""文本指标计算器。

算法锚点: count_style_fingerprint() — 10 项，纯正则
LLM 分析: style-analyze prompt — 正反面写法规则

朱雀防线: 代词密度/句长标准差/词汇多样性 — 比对源文，防 AI 句法均匀
"""

import re
import math
from .constants import AI_MARKER_PATTERN, METAPHOR_PATTERN, DIRECT_EMOTION_PATTERN

PRONOUN_PATTERN = r'[她他它]'


def count_metrics(text):
    """统计文本的量化指标（用于算法审查）。"""
    body = _strip_title(text)
    clean = re.sub(r'\s', '', body)
    total = max(len(clean), 1)

    sents = re.split(r'[。！？!?\n]', body)
    sent_lens = [len(re.sub(r'\s', '', s)) for s in sents if re.sub(r'\s', '', s)]
    n_sents = max(len(sent_lens), 1)
    avg_sent = sum(sent_lens) / n_sents
    var_sent = sum((l - avg_sent) ** 2 for l in sent_lens) / n_sents

    # 段落信息
    paras = [p for p in body.split('\n') if p.strip()]
    para_lens = [len(re.sub(r'\s', '', p)) for p in paras]
    para_avg = round(sum(para_lens) / max(len(para_lens), 1), 1)
    para_var = sum((l - para_avg) ** 2 for l in para_lens) / max(len(para_lens), 1) if para_lens else 0
    para_stddev = round(math.sqrt(para_var), 1)
    para_sent_counts = []
    for p in paras:
        p_sents = re.split(r'[。！？!?\n]', p)
        p_sent_lens = [len(re.sub(r'\s', '', s)) for s in p_sents if re.sub(r'\s', '', s)]
        para_sent_counts.append(len(p_sent_lens))
    avg_sent_per_para = round(sum(para_sent_counts) / max(len(para_sent_counts), 1), 1)

    # 对话标签密度
    dialogue_lines = len(re.findall(r'[」""\u201c\u201d]\s*[\u4e00-\u9fff]{0,4}(?:说|道|问|答|喊|叫)', body))
    total_dialogue = body.count('\u201c') + body.count('"') + body.count('「')
    tag_density = round(dialogue_lines / max(total_dialogue, 1), 2)

    # 连续排比（≥3 段以相同结构开头）
    para_starts = [re.sub(r'\s', '', p)[:3] for p in paras if len(re.sub(r'\s', '', p)) >= 3]
    max_consecutive = 0
    current = 1
    for i in range(1, len(para_starts)):
        if para_starts[i] == para_starts[i-1]:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 1

    # 心理词占比
    psych_words = re.findall(r'心想|暗道|觉得|感到|心[中里]|不由|忍不[住下]', body)
    psych_ratio = round(len(psych_words) / max(total, 1), 4)

    # 重复描写密度
    trigrams = [clean[i:i+3] for i in range(len(clean)-2)]
    unique_bigrams = set()
    repeat_count = 0
    seen = set()
    for t in trigrams:
        if t in seen:
            repeat_count += 1
        else:
            seen.add(t)
    repeat_density = round(repeat_count / max(total, 1) * 1000, 2)

    return {
        "chars": total,
        "dash": body.count('——'),
        "metaphor": len(re.findall(METAPHOR_PATTERN, body)),
        "ai_markers": len(re.findall(AI_MARKER_PATTERN, body)),
        "direct_emotion": len(re.findall(DIRECT_EMOTION_PATTERN, body)),
        "pronoun_density": round(len(re.findall(PRONOUN_PATTERN, clean)) / total * 1000, 1),
        "sent_len_stddev": round(math.sqrt(var_sent), 1),
        "tag_density": tag_density,
        "max_consecutive": max_consecutive,
        "psych_ratio": psych_ratio,
        "avg_sent_per_para": avg_sent_per_para,
        "para_avg": para_avg,
        "para_stddev": para_stddev,
        "repeat_density": repeat_density,
    }


def count_style_fingerprint(text):
    """段落为核心的风格指纹。

    返回: {chars, dialogue_ratio, paragraph_avg_len, single_sent_ratio,
           avg_sent_per_para, pronoun_density, ttr, punct_style, opening_type, closing_type}
    """
    body = _strip_title(text)
    clean = re.sub(r'\s', '', body)
    total = max(len(clean), 1)

    # 对话：引号行 + 无引号对话（说/道/问/喊/叫 等言说动词）
    lines = body.split('\n')
    dia_lines = 0
    for l in lines:
        if re.search(r'[「『""\u201c\u201d\'\u2018\u2019]', l):
            dia_lines += 1
        elif re.search(r'(?:说|道|问|喊|叫|骂|吼|答|嚷|喝)[：:]|^[^。！？\n]{2,20}[！？](?:$|\n)|(?:说道|问道|喊道|笑道|怒道|叹道|冷声道)', l):
            dia_lines += 1
    dia_ratio = round(dia_lines / max(len(lines), 1), 2)

    # 段落（核心指标）
    paras = [p for p in body.split('\n') if p.strip()]
    para_lens = [len(re.sub(r'\s', '', p)) for p in paras]
    para_avg = round(sum(para_lens) / max(len(para_lens), 1), 1)
    
    # 分段风格（单句段比例、平均每段句数）
    para_sent_counts = []
    for p in paras:
        p_sents = re.split(r'[。！？!?\n]', p)
        p_sent_lens = [len(re.sub(r'\s', '', s)) for s in p_sents if re.sub(r'\s', '', s)]
        para_sent_counts.append(len(p_sent_lens))
    single_sent_ratio = round(sum(1 for c in para_sent_counts if c == 1) / max(len(para_sent_counts), 1), 2)
    avg_sent_per_para = round(sum(para_sent_counts) / max(len(para_sent_counts), 1), 1)

    # 代词密度（防朱雀：AI 过度使用他/她/它）
    pronoun_count = len(re.findall(r'[她他它]', clean))
    pronoun_density = round(pronoun_count / total * 1000, 1)

    # 词汇多样性（字符级 TTR，朱雀检测指标）
    ttr = round(len(set(clean)) / total, 4)

    # 标点指纹
    punct = _classify_punct(body, total)

    return {
        "chars": total,
        "dialogue_ratio": dia_ratio,
        "paragraph_avg_len": para_avg,
        "para_stddev": round(math.sqrt(sum((l - para_avg) ** 2 for l in para_lens) / max(len(para_lens), 1)), 1) if para_lens else 0,
        "single_sent_ratio": single_sent_ratio,
        "avg_sent_per_para": avg_sent_per_para,
        "pronoun_density": pronoun_density,
        "ttr": ttr,
        "punct_style": punct,
    }


def format_style_anchors(fp):
    """段落核心锚点 → 紧凑描述。"""
    parts = []
    if fp.get("paragraph_avg_len"):
        parts.append(f"段长{fp['paragraph_avg_len']:.0f}字")
    if fp.get("para_stddev"):
        parts.append(f"段长差{fp['para_stddev']:.1f}")
    if fp.get("single_sent_ratio") is not None:
        parts.append(f"单句段{fp['single_sent_ratio']:.0%}")
    if fp.get("dialogue_ratio") is not None:
        parts.append(f"对话{fp['dialogue_ratio']:.0%}")
    if fp.get("pronoun_density") is not None:
        parts.append(f"代词密度{fp['pronoun_density']}/千字")
    if fp.get("ttr"):
        parts.append(f"词汇丰富度{fp['ttr']:.2f}")
    if fp.get("punct_style"):
        parts.append(fp["punct_style"])
    return '，'.join(parts)


# ---- 内部 ----

def _strip_title(text):
    body = text.strip()
    lines = body.split('\n')
    if lines and lines[0].startswith('第'):
        body = '\n'.join(lines[1:])
    return body


def _classify_punct(body, total):
    """标点风格指纹。"""
    dash_d = body.count('——') / total * 1000
    ellip_d = (body.count('…') + body.count('...')) / total * 1000
    excl_d = (body.count('！') + body.count('!')) / total * 1000

    tags = []
    if dash_d > 1.5:
        tags.append("多用破折号")
    if ellip_d > 1:
        tags.append("多用省略号")
    if excl_d > 0.8:
        tags.append("多用感叹号")
    if not tags:
        tags.append("标点克制")
    return '，'.join(tags)


def get_body_chars(text):
    if not text:
        return 0
    return len(re.sub(r'\s', '', _strip_title(text)))
