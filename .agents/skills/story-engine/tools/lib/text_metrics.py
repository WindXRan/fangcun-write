"""文本指标计算器：统计字数、比喻、AI词、直抒情等量化指标。"""

import re
from .constants import AI_MARKER_PATTERN, METAPHOR_PATTERN, DIRECT_EMOTION_PATTERN


def count_metrics(text):
    """统计文本的量化指标。

    返回:
        {
            "chars": int,          # 正文字数（去空白）
            "dash": int,           # 破折号数量
            "metaphor": int,       # 比喻句数量
            "ai_markers": int,     # AI 路标词数量
            "direct_emotion": int, # 直抒情数量
        }
    """
    body = text.strip()
    lines = body.split('\n')
    # 跳过标题行
    if lines and lines[0].startswith('第'):
        body = '\n'.join(lines[1:])

    clean = re.sub(r'\s', '', body)

    return {
        "chars": len(clean),
        "dash": body.count('——'),
        "metaphor": len(re.findall(METAPHOR_PATTERN, body)),
        "ai_markers": len(re.findall(AI_MARKER_PATTERN, body)),
        "direct_emotion": len(re.findall(DIRECT_EMOTION_PATTERN, body)),
    }


def get_body_chars(text):
    """获取正文字符数（去空白，跳过标题行）。"""
    if not text:
        return 0
    lines = text.strip().split('\n')
    body = '\n'.join(lines[1:]) if lines and lines[0].startswith('第') else text
    return len(re.sub(r'\s', '', body))
