"""文笔指纹和风格模块。

管理源文风格指纹、文笔指纹文本、高光提取等。
"""

import re
from pathlib import Path

from utils import get_source_text

# 模块级缓存：源文风格指纹 {ch: fingerprint_dict}
_style_fingerprint_cache = {}


def _get_style_fingerprint(config, ch):
    """获取源文风格指纹（模块级缓存）。"""
    if ch in _style_fingerprint_cache:
        return _style_fingerprint_cache[ch]

    src_text = get_source_text(config, ch)
    if not src_text:
        return None

    from lib.text_metrics import count_style_fingerprint
    fp = count_style_fingerprint(src_text)
    _style_fingerprint_cache[ch] = fp
    return fp


# 模块级缓存：文笔指纹文本（映射后） {ch: style_text}
_style_text_cache = {}


def _get_style_text_mapped(config, ch):
    """获取文笔指纹文本，替换源文名字，保留风格信息。"""
    if ch in _style_text_cache:
        return _style_text_cache[ch]

    from file_io import load_style_text
    from guides_name import _build_name_map
    style_text = load_style_text(config, ch)
    if not style_text:
        _style_text_cache[ch] = None
        return None

    # 替换源文角色名（包括昵称）
    name_map = _build_name_map(config)
    if name_map:
        # 添加昵称映射
        extended_map = dict(name_map)
        # 从 characters.md 提取昵称映射
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for line in chars_text.split('\n'):
                if '→' in line and '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2:
                        old_nick = parts[0]
                        new_nick = parts[1]
                        if old_nick and new_nick and old_nick != new_nick:
                            extended_map[old_nick] = new_nick
        
        # 替换所有名字
        for old_name, new_name in extended_map.items():
            style_text = style_text.replace(old_name, new_name)

    # 保留<style_deep>部分，去掉例句行
    filtered_lines = []
    in_style_deep = False
    for line in style_text.split("\n"):
        # 跟踪<style_deep>部分
        if '<style_deep>' in line:
            in_style_deep = True
        if '</style_deep>' in line:
            in_style_deep = False
            filtered_lines.append(line)
            continue
        
        # 在<style_deep>内，保留所有内容（包括例子）
        if in_style_deep:
            filtered_lines.append(line)
            continue
        
        # 在<style_deep>外，去掉例句行
        if re.match(r'^\s*(例句|例|示例)[：:]', line.strip()):
            continue
        filtered_lines.append(line)
    
    style_text = "\n".join(filtered_lines)

    _style_text_cache[ch] = style_text
    return style_text


def _extract_highlights(src_text, max_chars=300):
    """从源文提取情绪密度最高的段落作为参考。"""
    if not src_text:
        return ""
    
    # 按段落分割
    paragraphs = [p.strip() for p in src_text.split('\n') if p.strip() and len(p.strip()) > 20]
    if not paragraphs:
        return ""
    
    # 情绪关键词权重
    emotion_words = {
        '哭': 3, '泪': 3, '怕': 2, '紧': 2, '慌': 2, '急': 2, '抖': 2,
        '死': 3, '命': 2, '血': 3, '痛': 2, '苦': 2, '惨': 2,
        '笑': 1, '喜': 1, '乐': 1, '甜': 1, '暖': 1,
        '怒': 2, '恨': 2, '骂': 2, '打': 2, '摔': 2,
        '空': 2, '饿': 2, '冷': 2, '黑': 1, '暗': 1,
    }
    
    # 计算每段的情绪分数
    scored = []
    for p in paragraphs:
        score = sum(emotion_words.get(w, 0) for w in p if w in emotion_words)
        # 对话加分（有引号）
        if '"' in p or '"' in p or '「' in p:
            score += 2
        # 短句加分（节奏感）
        short_sents = len([s for s in p.split('。') if 0 < len(s) < 20])
        score += short_sents
        scored.append((score, p))
    
    # 按分数排序，取前几段
    scored.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    total = 0
    for score, p in scored:
        if total + len(p) > max_chars:
            break
        result.append(p)
        total += len(p)
    
    return '\n\n'.join(result[:3])  # 最多3段


def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    from utils import get_source_text
    from lib.text_metrics import count_metrics
    text = get_source_text(config, ch)
    if text:
        return count_metrics(text)
    return None
