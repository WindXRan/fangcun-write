"""换皮检测：连续匹配 + 结构相似度 + n-gram 重叠率。"""

import re
from collections import Counter


def find_plagiarism(new_text, source_text, min_gram=8):
    """检测 new_text 与 source_text 的台词雷同（连续 N 字以上匹配）。

    返回:
        [{"text": "匹配文本片段", "length": 匹配长度, "position": 位置}, ...]
    """
    new_clean = re.sub(r'[。！？…\n\s]+', '', new_text)
    src_clean = re.sub(r'[。！？…\n\s]+', '', source_text)

    if len(src_clean) < min_gram or len(new_clean) < min_gram:
        return []

    # 构建源文 n-gram 集合
    src_grams = set()
    for i in range(len(src_clean) - min_gram + 1):
        src_grams.add(src_clean[i:i + min_gram])

    # 检测匹配
    matches = []
    matched_ranges = []
    i = 0
    while i < len(new_clean) - min_gram + 1:
        gram = new_clean[i:i + min_gram]
        if gram in src_grams:
            # 扩展找最长匹配
            j = i + min_gram
            while j < len(new_clean) and new_clean[i:j + 1] in src_grams:
                j += 1
            # 避免重叠计数
            if not matched_ranges or i >= matched_ranges[-1][1]:
                matches.append({
                    "text": new_clean[max(0, i - 5):i + 20],
                    "length": j - i,
                    "position": i,
                })
                matched_ranges.append((i, j))
            i = j
        else:
            i += 1

    return matches


def has_plagiarism(new_text, source_text, min_gram=8):
    """快速检查是否存在台词雷同。"""
    return len(find_plagiarism(new_text, source_text, min_gram)) > 0


def calc_ngram_overlap(new_text, source_text, n=4):
    """计算 n-gram 重叠率（检测结构性抄袭）。

    返回:
        float: 0.0-1.0，越高表示结构越相似
    """
    def get_ngrams(text, n):
        clean = re.sub(r'[。！？…\n\s]+', '', text)
        return [clean[i:i+n] for i in range(len(clean) - n + 1)]
    
    src_ngrams = get_ngrams(source_text, n)
    new_ngrams = get_ngrams(new_text, n)
    
    if not src_ngrams or not new_ngrams:
        return 0.0
    
    src_counter = Counter(src_ngrams)
    new_counter = Counter(new_ngrams)
    
    # 计算交集
    intersection = sum((src_counter & new_counter).values())
    total = sum(new_counter.values())
    
    return intersection / total if total > 0 else 0.0


def calc_sentence_structure_similarity(new_text, source_text):
    """计算句子结构相似度（检测换皮）。

    将句子抽象为"模式"（如：对话句→D，动作句→A，心理句→P），
    然后比较模式序列的相似度。

    返回:
        float: 0.0-1.0，越高表示结构越相似
    """
    def extract_patterns(text):
        """提取句子模式序列。"""
        sentences = re.split(r'[。！？\n]+', text)
        patterns = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            # 判断句子类型
            if re.search(r'[""「].*?[""」]', sent):
                patterns.append('D')  # 对话
            elif re.search(r'(想|觉得|感到|心里|暗想|琢磨)', sent):
                patterns.append('P')  # 心理
            elif re.search(r'(走|跑|拿|放|站|坐|转|看|听)', sent):
                patterns.append('A')  # 动作
            elif re.search(r'(阳光|月光|风|雨|花|树)', sent):
                patterns.append('E')  # 环境
            else:
                patterns.append('N')  # 叙述
        return patterns
    
    src_patterns = extract_patterns(source_text)
    new_patterns = extract_patterns(new_text)
    
    if not src_patterns or not new_patterns:
        return 0.0
    
    # 计算模式分布相似度（余弦相似度）
    src_counter = Counter(src_patterns)
    new_counter = Counter(new_patterns)
    
    all_types = set(src_counter.keys()) | set(new_counter.keys())
    
    dot_product = sum(src_counter.get(t, 0) * new_counter.get(t, 0) for t in all_types)
    src_norm = sum(v**2 for v in src_counter.values()) ** 0.5
    new_norm = sum(v**2 for v in new_counter.values()) ** 0.5
    
    if src_norm == 0 or new_norm == 0:
        return 0.0
    
    return dot_product / (src_norm * new_norm)


def check_structural_plagiarism(new_text, source_text, threshold=0.7):
    """综合检查结构性抄袭。

    返回:
        dict: {
            "is_plagiarism": bool,
            "ngram_overlap": float,
            "structure_similarity": float,
            "reason": str
        }
    """
    ngram_4 = calc_ngram_overlap(new_text, source_text, n=4)
    ngram_6 = calc_ngram_overlap(new_text, source_text, n=6)
    structure = calc_sentence_structure_similarity(new_text, source_text)
    
    # 综合评分（加权平均）
    score = ngram_4 * 0.3 + ngram_6 * 0.4 + structure * 0.3
    
    reasons = []
    if ngram_4 > 0.5:
        reasons.append(f"4-gram重叠率{ngram_4:.0%}")
    if ngram_6 > 0.4:
        reasons.append(f"6-gram重叠率{ngram_6:.0%}")
    if structure > 0.8:
        reasons.append(f"句子结构相似度{structure:.0%}")
    
    return {
        "is_plagiarism": score >= threshold,
        "score": score,
        "ngram_4_overlap": ngram_4,
        "ngram_6_overlap": ngram_6,
        "structure_similarity": structure,
        "reason": "、".join(reasons) if reasons else ""
    }
