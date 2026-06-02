# -*- coding: utf-8 -*-
"""
后处理随机化脚本 — 打破LLM的"完美结构"
写完正文后跑一遍，输出更像人写的版本。

用法：python post-process.py <正文路径> [--aggressive]
"""

import re
import sys
import random

# 导入统一字数统计模块
from word_count import count_chapter_words, format_word_count, MODE_STANDARD

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def split_paragraphs(text):
    """按空行分段"""
    return text.split('\n\n')

def join_paragraphs(paragraphs):
    return '\n\n'.join(paragraphs)

def is_dialogue(line):
    """判断是否是对话行"""
    stripped = line.strip()
    return stripped.startswith('"') or stripped.startswith('"') or stripped.startswith('「')

def is_chapter_header(line):
    """判断是否是章节标题"""
    stripped = line.strip()
    return bool(re.match(r'^第\d+章', stripped)) or bool(re.match(r'^#', stripped))

def random_delete_sentences(paragraph, p=0.15):
    """随机删句子（概率p）"""
    lines = paragraph.split('\n')
    if len(lines) <= 1:
        return paragraph
    
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        # 不删对话（对话删了会影响剧情）
        if is_dialogue(stripped):
            kept.append(line)
            continue
        # 不删章节标题
        if is_chapter_header(stripped):
            kept.append(line)
            continue
        # 随机保留
        if random.random() > p:
            kept.append(line)
    
    result = '\n'.join(kept).strip()
    return result if result else paragraph

def merge_short_paragraphs(paragraphs, threshold=30):
    """合并过短的段落"""
    result = []
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i].strip()
        if len(p) < threshold and i + 1 < len(paragraphs):
            # 合并到下一个段落
            next_p = paragraphs[i + 1].strip()
            merged = p + '\n' + next_p
            result.append(merged)
            i += 2
        else:
            result.append(p)
            i += 1
    return result

def split_long_paragraph(paragraph, max_sentences=5):
    """拆分过长的段落"""
    lines = [l for l in paragraph.split('\n') if l.strip()]
    if len(lines) <= max_sentences:
        return [paragraph]
    
    # 在随机位置拆分
    split_point = random.randint(2, len(lines) - 2)
    part1 = '\n'.join(lines[:split_point])
    part2 = '\n'.join(lines[split_point:])
    return [part1, part2]

def add_solo_paragraph(paragraphs, text):
    """在随机位置插入独词段"""
    # 从文本中提取候选的短句
    sentences = re.split(r'[。！？]', text)
    short_sentences = [s.strip() for s in sentences if 3 < len(s.strip()) < 15]
    
    if not short_sentences:
        return paragraphs
    
    # 随机选一个短句
    solo = random.choice(short_sentences)
    
    # 在随机位置插入
    pos = random.randint(1, len(paragraphs) - 1)
    paragraphs.insert(pos, solo + '。')
    
    return paragraphs

def randomize_paragraph_lengths(paragraphs):
    """随机化段落长度"""
    result = []
    for p in paragraphs:
        lines = [l for l in p.split('\n') if l.strip()]
        
        if len(lines) >= 6:
            # 长段落：随机拆
            parts = split_long_paragraph(p)
            result.extend(parts)
        elif len(lines) == 1 and len(p.strip()) < 20 and random.random() < 0.3:
            # 独词段：30%概率合并到下一个
            if result:
                result[-1] = result[-1].strip() + '\n' + p.strip()
            else:
                result.append(p)
        else:
            result.append(p)
    
    return result

def break_scene_transitions(paragraphs):
    """打碎场景过渡"""
    transition_patterns = [
        r'^——$',
        r'^---+$',
        r'^\*\*\*+$',
    ]
    
    result = []
    for p in paragraphs:
        stripped = p.strip()
        # 如果是纯分隔线，50%概率删除
        for pattern in transition_patterns:
            if re.match(pattern, stripped):
                if random.random() < 0.5:
                    continue
        result.append(p)
    
    return result

def post_process(text, aggressive=False):
    """主处理流程"""
    paragraphs = split_paragraphs(text)
    
    # Step 1: 随机删句子（每段15%概率删一个非对话句）
    processed = []
    for p in paragraphs:
        if random.random() < 0.3:  # 30%的段落会被处理
            p = random_delete_sentences(p, p=0.15)
        processed.append(p)
    
    # Step 2: 合并过短段落
    processed = merge_short_paragraphs(processed, threshold=30)
    
    # Step 3: 随机化段落长度
    processed = randomize_paragraph_lengths(processed)
    
    # Step 4: 插入独词段（每章至少2个）
    solo_count = sum(1 for p in processed if len(p.strip()) < 15)
    if solo_count < 2:
        processed = add_solo_paragraph(processed, text)
        processed = add_solo_paragraph(processed, text)
    
    # Step 5: 打碎场景过渡
    processed = break_scene_transitions(processed)
    
    # Step 6: aggressive模式 - 更激进的打乱
    if aggressive:
        # 随机合并相邻段落（20%概率）
        merged = []
        i = 0
        while i < len(processed):
            if i + 1 < len(processed) and random.random() < 0.2:
                merged.append(processed[i].strip() + '\n' + processed[i+1].strip())
                i += 2
            else:
                merged.append(processed[i])
                i += 1
        processed = merged
    
    return join_paragraphs(processed)

def main():
    if len(sys.argv) < 2:
        print('Usage: python post-process.py <filepath> [--aggressive]')
        sys.exit(1)
    
    filepath = sys.argv[1]
    aggressive = '--aggressive' in sys.argv
    
    text = read_file(filepath)
    # 使用统一字数统计
    original_chars = count_chapter_words(text, MODE_STANDARD)

    result = post_process(text, aggressive)
    # 使用统一字数统计
    processed_chars = count_chapter_words(result, MODE_STANDARD)

    # 输出到新文件
    output_path = filepath.replace('.txt', '_processed.txt')
    write_file(output_path, result)

    print(f'Original: {original_chars} 字')
    print(f'Processed: {processed_chars} 字')
    print(f'Change: {processed_chars - original_chars} 字 ({(processed_chars - original_chars) / original_chars * 100:.1f}%)')
    print(f'Output: {output_path}')

if __name__ == '__main__':
    main()
