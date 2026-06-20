"""
风格分析器：自动提取文风指纹

参考inkos的style-analyzer设计：
- 句式特点
- 对话风格
- 描写特点
- 情感表达方式
- 高频词/句式
"""

import re
from pathlib import Path
from typing import Dict, List, Optional


def analyze_style(text: str, max_chars: int = 10000) -> Dict:
    """分析文本风格，返回风格特征字典"""
    # 限制分析长度
    if len(text) > max_chars:
        text = text[:max_chars]
    
    result = {
        "句式特点": _analyze_sentence_patterns(text),
        "对话风格": _analyze_dialogue_style(text),
        "描写特点": _analyze_description_style(text),
        "情感表达": _analyze_emotion_style(text),
        "高频词": _extract_high_freq_words(text),
        "段落结构": _analyze_paragraph_structure(text),
    }
    
    return result


def _analyze_sentence_patterns(text: str) -> str:
    """分析句式特点"""
    lines = []
    
    # 计算平均句长
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        lines.append(f"平均句长：{avg_len:.0f}字")
    
    # 短句比例
    short_sents = [s for s in sentences if len(s) < 15]
    if sentences:
        short_ratio = len(short_sents) / len(sentences)
        lines.append(f"短句比例：{short_ratio:.0%}")
    
    # 长句比例
    long_sents = [s for s in sentences if len(s) > 40]
    if sentences:
        long_ratio = len(long_sents) / len(sentences)
        lines.append(f"长句比例：{long_ratio:.0%}")
    
    return '；'.join(lines) if lines else "（数据不足）"


def _analyze_dialogue_style(text: str) -> str:
    """分析对话风格"""
    lines = []
    
    # 对话比例
    dialogue_chars = len(re.findall(r'["「].*?["」]', text))
    total_chars = len(re.sub(r'\s', '', text))
    if total_chars > 0:
        dialogue_ratio = dialogue_chars / total_chars
        lines.append(f"对话比例：{dialogue_ratio:.0%}")
    
    # 对话标签
    tag_patterns = [
        (r'说', '说'),
        (r'道', '道'),
        (r'问', '问'),
        (r'答', '答'),
        (r'喊', '喊'),
        (r'叫', '叫'),
    ]
    
    tags_found = []
    for pattern, name in tag_patterns:
        count = len(re.findall(pattern, text))
        if count > 0:
            tags_found.append(f"{name}({count})")
    
    if tags_found:
        lines.append(f"对话标签：{', '.join(tags_found[:5])}")
    
    return '；'.join(lines) if lines else "（数据不足）"


def _analyze_description_style(text: str) -> str:
    """分析描写特点"""
    lines = []
    
    # 五感描写
    senses = {
        '视觉': re.findall(r'看|见|望|视|盯|瞧|瞅|瞥', text),
        '听觉': re.findall(r'听|闻|声|响|音|噪', text),
        '嗅觉': re.findall(r'嗅|闻|味|气|香|臭', text),
        '触觉': re.findall(r'摸|触|感|觉|冷|热|软|硬', text),
        '味觉': re.findall(r'尝|味|甜|苦|辣|咸|酸', text),
    }
    
    senses_found = []
    for sense, matches in senses.items():
        if len(matches) > 2:
            senses_found.append(f"{sense}({len(matches)})")
    
    if senses_found:
        lines.append(f"五感描写：{', '.join(senses_found)}")
    
    # 环境描写
    env_patterns = re.findall(r'阳光|月光|灯光|风|雨|雪|云|天|地|山|水|树|花', text)
    if len(env_patterns) > 5:
        lines.append(f"环境描写：{len(env_patterns)}处")
    
    return '；'.join(lines) if lines else "（数据不足）"


def _analyze_emotion_style(text: str) -> str:
    """分析情感表达方式"""
    lines = []
    
    # 直接情感词
    direct_emotion = re.findall(r'高兴|生气|难过|害怕|紧张|兴奋|失望|愤怒|悲伤|快乐', text)
    if direct_emotion:
        lines.append(f"直接情感词：{len(direct_emotion)}处")
    
    # 动作表达情感
    action_emotion = re.findall(r'攥|捏|握|踢|打|摔|推|拉|扯|拽', text)
    if action_emotion:
        lines.append(f"动作表达：{len(action_emotion)}处")
    
    # 心理描写
   心理描写 = re.findall(r'心想|暗想|心想道|心里想|暗自', text)
    if 心理描写:
        lines.append(f"心理描写：{len(心理描写)}处")
    
    return '；'.join(lines) if lines else "（数据不足）"


def _extract_high_freq_words(text: str, top_n: int = 10) -> List[str]:
    """提取高频词"""
    # 简单的词频统计（按2-4字词）
    words = {}
    for length in [2, 3, 4]:
        for i in range(len(text) - length + 1):
            word = text[i:i+length]
            if re.match(r'^[\u4e00-\u9fa5]+$', word):
                words[word] = words.get(word, 0) + 1
    
    # 过滤常见词
    common_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    filtered = {k: v for k, v in words.items() if k not in common_words and v >= 3}
    
    # 排序
    sorted_words = sorted(filtered.items(), key=lambda x: -x[1])
    return [f"{word}({count})" for word, count in sorted_words[:top_n]]


def _analyze_paragraph_structure(text: str) -> str:
    """分析段落结构"""
    lines = []
    
    # 段落数
    paragraphs = [p for p in text.split('\n') if p.strip()]
    lines.append(f"段落数：{len(paragraphs)}")
    
    # 平均段长
    if paragraphs:
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
        lines.append(f"平均段长：{avg_para_len:.0f}字")
    
    # 短段比例
    short_paras = [p for p in paragraphs if len(p) < 50]
    if paragraphs:
        short_ratio = len(short_paras) / len(paragraphs)
        lines.append(f"短段比例：{short_ratio:.0%}")
    
    return '；'.join(lines) if lines else "（数据不足）"


def build_style_fingerprint(text: str) -> str:
    """构建文风指纹（用于prompt注入）"""
    analysis = analyze_style(text)
    
    lines = ["## 文风指纹（自动提取）"]
    lines.append("")
    
    for key, value in analysis.items():
        if isinstance(value, list):
            lines.append(f"**{key}：** {', '.join(value[:5])}")
        else:
            lines.append(f"**{key}：** {value}")
    
    return '\n'.join(lines)


def load_style_from_cache(config, ch_num: int) -> Optional[str]:
    """从缓存加载文风指纹"""
    source_dir = Path(config.get("source_dir", ""))
    if not source_dir:
        return None
    
    style_dir = source_dir / "_cache" / "styles"
    style_file = style_dir / f"style_{ch_num:03d}.md"
    
    if style_file.exists():
        return style_file.read_text(encoding="utf-8")
    
    return None


def generate_and_save_style(config, ch_num: int) -> Optional[str]:
    """生成并保存文风指纹"""
    source_dir = Path(config.get("source_dir", ""))
    if not source_dir:
        return None
    
    # 读取源文
    chapters_dir = source_dir / "_cache" / "chapters"
    candidates = [
        chapters_dir / f"第{ch_num:03d}章.txt",
        chapters_dir / f"第{ch_num}章.txt",
    ]
    
    source_text = None
    for path in candidates:
        if path.exists():
            source_text = path.read_text(encoding="utf-8")
            break
    
    if not source_text:
        return None
    
    # 生成文风指纹
    fingerprint = build_style_fingerprint(source_text)
    
    # 保存到缓存
    style_dir = source_dir / "_cache" / "styles"
    style_dir.mkdir(parents=True, exist_ok=True)
    style_file = style_dir / f"style_{ch_num:03d}.md"
    style_file.write_text(fingerprint, encoding="utf-8")
    
    return fingerprint
