# -*- coding: utf-8 -*-
"""网文质量扫描脚本 — 标出"删了更好"的句子"""

import re
import sys
from collections import Counter

# 导入统一字数统计模块
from word_count import count_chapter_words, MODE_STANDARD

def scan_quality(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    # 使用统一字数统计
    total_chars = count_chapter_words(content, MODE_STANDARD)
    
    findings = []
    
    # 1. 情绪告知
    emotion_tell = [
        '她很紧张', '他很紧张', '她很害怕', '他很害怕', '她很愤怒', '他很愤怒',
        '她很伤心', '他很伤心', '她很绝望', '他很绝望', '她很震惊', '他很震惊',
        '她很惊讶', '他很惊讶', '她很尴尬', '他很尴尬', '她很无奈', '他很无奈',
        '她松了口气', '他松了口气', '她心里一紧', '他心里一紧',
        '她心跳漏了一拍', '他心跳漏了一拍', '她心跳加速', '他心跳加速',
        '她脑子嗡的一声', '他脑子嗡的一声', '她脑子一片混乱', '他脑子一片混乱',
        '她脑子一片空白', '他脑子一片空白', '她整个人僵住', '他整个人僵住',
        '她后背一凉', '他后背一凉', '她后背发凉', '他后背发凉',
        '她腿有点软', '他腿有点软', '她手指发凉', '他手指发凉',
        '恐惧从脚底', '紧张得手心', '害怕得手心',
        '沈清歌的脑子转得飞快', '林念初的脑子转得飞快',
        '她心里松了口气', '他心里松了口气',
        '她心里很清楚', '他心里很清楚', '她心里明白', '他心里明白',
        '她觉得', '他觉得', '她感觉', '他感觉',
        '她心里咯噔', '他心里咯噔', '她心里一沉', '他心里一沉',
        '她心底泛起', '他心底泛起', '她心中涌起', '他心中涌起',
        '时间好像静止', '空气好像凝固', '气氛尴尬',
        '她整个人都不好了', '他整个人都不好了',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in emotion_tell:
            if pattern in stripped:
                findings.append({
                    'line': i + 1,
                    'type': 'EmotionTell',
                    'text': stripped[:60],
                    'suggestion': 'Delete - action already shows this emotion'
                })
                break
    
    # 2. 过渡句
    transition_patterns = [
        r'^\s*她站起来\b', r'^\s*他站起来\b', r'^\s*她转身\b', r'^\s*他转身\b',
        r'^\s*她走出\b', r'^\s*他走出\b', r'^\s*她走进\b', r'^\s*他走进\b',
        r'^\s*她回到\b', r'^\s*他回到\b', r'^\s*她来到\b', r'^\s*他来到\b',
        r'^\s*第二天\b', r'^\s*三天后\b', r'^\s*过了几天\b', r'^\s*过了很久\b',
        r'^\s*与此同时\b', r'^\s*另一边\b',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in transition_patterns:
            if re.match(pattern, line):
                prev_empty = (i == 0) or (not lines[i-1].strip())
                next_empty = (i == len(lines)-1) or (not lines[i+1].strip())
                if prev_empty and next_empty:
                    findings.append({
                        'line': i + 1,
                        'type': 'Transition',
                        'text': stripped[:60],
                        'suggestion': 'Delete - jump cut to next scene'
                    })
                break
    
    # 3. 解释
    explain_patterns = [
        r'因为.*所以', r'原因是', r'之所以.*是因为',
        r'她这么做是因为', r'他这么做是因为',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for pattern in explain_patterns:
            if re.search(pattern, stripped):
                findings.append({
                    'line': i + 1,
                    'type': 'Explanation',
                    'text': stripped[:60],
                    'suggestion': 'Delete explanation - let reader infer'
                })
                break
    
    # 4. 重复情绪（同一段内）
    emotion_kw = re.compile(r'紧张|害怕|愤怒|伤心|绝望|震惊|惊讶|尴尬|无奈|心跳|发抖|发凉|僵住|空白|嗡')
    
    paragraphs = []
    current = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append({'line': i + 1, 'text': stripped})
    if current:
        paragraphs.append(current)
    
    for para in paragraphs:
        emotion_lines = [item for item in para if emotion_kw.search(item['text'])]
        if len(emotion_lines) >= 2:
            for item in emotion_lines[1:]:
                findings.append({
                    'line': item['line'],
                    'type': 'RepeatEmotion',
                    'text': item['text'][:60],
                    'suggestion': 'Duplicate emotion in paragraph - keep only strongest'
                })
    
    # 5. 多余对话标签
    tag_pattern = re.compile(r'^["「].*["」]\s*[，,]?\s*(他|她)(说|问|答|道|喊|叫)')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if tag_pattern.match(stripped) and i > 0:
            prev = lines[i-1].strip()
            if prev and (prev.startswith('"') or prev.startswith('"') or prev.startswith('「')):
                findings.append({
                    'line': i + 1,
                    'type': 'RedundantTag',
                    'text': stripped[:60],
                    'suggestion': 'Remove tag - context makes speaker clear'
                })
    
    # Output
    findings.sort(key=lambda x: x['line'])
    by_type = Counter(f['type'] for f in findings)

    print('=' * 50)
    print('Quality Scan Report')
    print(f'File: {filepath}')
    print(f'Total chars: {total_chars} 字')
    print('=' * 50)
    print()
    print('--- Findings by type ---')
    for t, count in by_type.most_common():
        print(f'  {t}: {count} lines')
    print()
    print('--- Details ---')
    for f in findings:
        print(f'  Line {f["line"]} [{f["type"]}]: {f["text"]}')
        print(f'    -> {f["suggestion"]}')
    
    total = len(findings)
    print()
    print('=' * 50)
    print(f'Total findings: {total}')
    print('=' * 50)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scan-quality.py <filepath>')
        sys.exit(1)
    scan_quality(sys.argv[1])
