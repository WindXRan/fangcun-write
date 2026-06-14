"""文本指标计算器。

算法锚点: count_style_fingerprint() — 7 项，纯正则
LLM 分析: style-analyze prompt — 正反面写法规则
"""

import re
from .constants import AI_MARKER_PATTERN, METAPHOR_PATTERN, DIRECT_EMOTION_PATTERN


def count_metrics(text):
    """统计文本的量化指标（用于算法审查）。"""
    body = _strip_title(text)
    clean = re.sub(r'\s', '', body)
    return {
        "chars": len(clean),
        "dash": body.count('——'),
        "metaphor": len(re.findall(METAPHOR_PATTERN, body)),
        "ai_markers": len(re.findall(AI_MARKER_PATTERN, body)),
        "direct_emotion": len(re.findall(DIRECT_EMOTION_PATTERN, body)),
    }


def count_style_fingerprint(text):
    """7 个锚点，纯正则，<30ms。

    返回: {chars, sentence_avg_len, sentence_short_ratio, dialogue_ratio,
           paragraph_avg_len, punct_style, opening_type, closing_type}
    """
    body = _strip_title(text)
    clean = re.sub(r'\s', '', body)
    total = max(len(clean), 1)

    # 句法
    sents = re.split(r'[。！？!?\n]', body)
    sent_lens = [len(re.sub(r'\s', '', s)) for s in sents if re.sub(r'\s', '', s)]
    n_sents = max(len(sent_lens), 1)
    avg_sent = round(sum(sent_lens) / n_sents, 1)
    short_ratio = round(sum(1 for l in sent_lens if l < 8) / n_sents, 2)

    # 对话：引号行 + 无引号对话（说/道/问/喊/叫 等言说动词）
    lines = body.split('\n')
    dia_lines = 0
    for l in lines:
        if re.search(r'[「『""""‘’]', l):
            dia_lines += 1
        elif re.search(r'(?:说|道|问|喊|叫|骂|吼|答|嚷|喝)[：:]|^[^。！？\n]{2,20}[！？](?:$|\n)|(?:说道|问道|喊道|笑道|怒道|叹道|冷声道)', l):
            dia_lines += 1
    dia_ratio = round(dia_lines / max(len(lines), 1), 2)

    # 段落
    paras = [p for p in body.split('\n') if p.strip()]
    para_lens = [len(re.sub(r'\s', '', p)) for p in paras]
    para_avg = round(sum(para_lens) / max(len(para_lens), 1), 1)

    # 标点指纹
    punct = _classify_punct(body, total)

    # 开头/结尾
    opening = _classify_opening(body)
    closing = _classify_closing(body)

    return {
        "chars": total,
        "sentence_avg_len": avg_sent,
        "sentence_short_ratio": short_ratio,
        "dialogue_ratio": dia_ratio,
        "paragraph_avg_len": para_avg,
        "punct_style": punct,
        "opening_type": opening,
        "closing_type": closing,
    }


def format_style_anchors(fp):
    """7 个锚点 → 紧凑描述。"""
    parts = []
    if fp.get("sentence_avg_len"):
        parts.append(f"句长{fp['sentence_avg_len']}字/句, 短句(<8字)占{fp.get('sentence_short_ratio',0):.0%}")
    if fp.get("dialogue_ratio") is not None:
        parts.append(f"对话{fp['dialogue_ratio']:.0%}")
    if fp.get("paragraph_avg_len"):
        parts.append(f"段均{fp['paragraph_avg_len']:.0f}字")
    if fp.get("punct_style"):
        parts.append(fp["punct_style"])
    parts.append(f"开头:{fp.get('opening_type','?')} 结尾:{fp.get('closing_type','?')}")
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


def _classify_opening(body):
    sents = re.split(r'[。！？!?\n]', body)
    head = ''.join(sents[:3])
    if re.search(r'[「『""""‘’]', head[:50]):
        return "dialogue"
    if re.search(r'(?:突然|猛地|一把|伸手|脚步|转身|推开|睁[开眼]|坐起|站起|爬起|回头)', head[:80]):
        return "action"
    if re.search(r'(?:心想|暗道|觉得|感到|心[中里]|不由|忍不[住下])', head[:80]):
        return "inner"
    if re.search(r'(?:阳光|月光|风|雨|雪|夜|天[空色]|房间|窗外|街道|空气|灯光)', head[:80]):
        return "description"
    return "narrative"


def _classify_closing(body):
    sents = re.split(r'[。！？!?\n]', body)
    tail = ''.join(sents[-5:]) if len(sents) >= 5 else ''.join(sents)
    if re.search(r'(?:突然|忽然|猛地|就在这时|却[不见没]|竟然|居然|难道)', tail[-100:]):
        return "cliffhanger"
    if re.search(r'(?:心[中里]|眼泪|笑[了着]|温暖|幸福|难过|痛苦|终于|原来)', tail[-100:]):
        return "emotion"
    if re.search(r'(?:转身|离去|走[了出]|回头|关上|推开|停下|沉默|没说)', tail[-100:]):
        return "action_cut"
    return "neutral"


def get_body_chars(text):
    if not text:
        return 0
    return len(re.sub(r'\s', '', _strip_title(text)))
