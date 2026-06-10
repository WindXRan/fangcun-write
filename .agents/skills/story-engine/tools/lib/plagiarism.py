"""8-gram 台词雷同检测。"""

import re


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
