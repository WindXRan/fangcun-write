"""文本指标计算器。

算法锚点: count_metrics() + count_style_fingerprint() — 轻量，纯正则
LLM 分析: style-analyze prompt — 让 AI 写出来像人
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
    """4 个核心锚点，纯正则，<20ms。"""
    body = _strip_title(text)
    clean = re.sub(r'\s', '', body)
    total = max(len(clean), 1)

    # 句长
    sents = re.split(r'[。！？!?\n]', body)
    sent_lens = [len(re.sub(r'\s', '', s)) for s in sents if re.sub(r'\s', '', s)]
    avg_sent = round(sum(sent_lens) / max(len(sent_lens), 1), 1)

    # 对话占比
    lines = body.split('\n')
    dia_lines = sum(1 for l in lines if re.search(r'[「『""""‘’]', l))
    dia_ratio = round(dia_lines / max(len(lines), 1), 2)

    # 开头/结尾类型
    opening = _classify_opening(body)
    closing = _classify_closing(body)

    return {
        "chars": total,
        "sentence_avg_len": avg_sent,
        "dialogue_ratio": dia_ratio,
        "opening_type": opening,
        "closing_type": closing,
    }


def format_style_anchors(fp):
    """4 个锚点 → 一句话。"""
    return (
        f"句长均值 {fp.get('sentence_avg_len', '?')} 字/句，"
        f"对话占比约 {fp.get('dialogue_ratio', 0):.0%}，"
        f"开头: {fp.get('opening_type', '?')}，"
        f"结尾: {fp.get('closing_type', '?')}"
    )


# ---- 内部 ----

def _strip_title(text):
    body = text.strip()
    lines = body.split('\n')
    if lines and lines[0].startswith('第'):
        body = '\n'.join(lines[1:])
    return body


def _classify_opening(body):
    sents = re.split(r'[。！？!?\n]', body)
    head = ''.join(sents[:3])
    if re.search(r'[「『""""‘’]', head[:50]):
        return "dialogue"
    if re.search(r'(?:突然|猛地|一把|伸手|脚步|转身|推开|睁[开眼]|坐起|站起)', head[:80]):
        return "action"
    if re.search(r'(?:心想|暗道|觉得|感到|心[中里])', head[:80]):
        return "inner"
    return "narrative"


def _classify_closing(body):
    sents = re.split(r'[。！？!?\n]', body)
    tail = ''.join(sents[-5:]) if len(sents) >= 5 else ''.join(sents)
    if re.search(r'(?:突然|忽然|猛地|就在这时|却[不见没]|竟然|居然|难道)', tail[-100:]):
        return "cliffhanger"
    if re.search(r'(?:心[中里]|眼泪|笑[了着]|温暖|幸福|难过|终于)', tail[-100:]):
        return "emotion"
    if re.search(r'(?:转身|离去|走[了出]|回头|关上|推开|停下|沉默)', tail[-100:]):
        return "action_cut"
    return "neutral"


def get_body_chars(text):
    if not text:
        return 0
    return len(re.sub(r'\s', '', _strip_title(text)))
