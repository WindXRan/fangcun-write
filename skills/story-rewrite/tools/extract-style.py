# -*- coding: utf-8 -*-
"""
源文本叙述者风格提取脚本
从源文本前3章自动提取：叙述者人格类型、语感样本、节奏特征

用法：python extract-style.py <源文本路径>
输出：JSON格式的风格分析结果
"""

import re
import sys
import json
from collections import Counter

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_chapters(content, max_chapters=3):
    """提取前N章内容"""
    chapters = []
    # Split by chapter markers
    parts = re.split(r'第\d+章[^\n]*\n', content)
    headers = re.findall(r'(第\d+章[^\n]*)', content)
    
    for i, part in enumerate(parts[1:], 0):
        if i >= max_chapters:
            break
        title = headers[i] if i < len(headers) else f"第{i+1}章"
        chapters.append({'title': title, 'content': part.strip()})
    
    return chapters

def detect_persona_type(text):
    """检测叙述者人格类型"""
    scores = {
        'A_吐槽型': 0,
        'B_冷幽默': 0,
        'C_沉浸型': 0,
        'D_故事人': 0,
        'E_冷峻型': 0
    }
    
    # 检测网感口语
    slang_patterns = ['好家伙', '两眼一黑', '悬着的心', '薛定谔', 'PUA', '人机', '查岗', '他妈', '操', '行吧']
    slang_count = sum(1 for p in slang_patterns if p in text)
    scores['A_吐槽型'] += slang_count * 3
    
    # 检测第四面墙碎裂
    fourth_wall = ['别问', '问就是', '剧情需要', '说实话', '不得不说']
    fw_count = sum(1 for p in fourth_wall if p in text)
    scores['A_吐槽型'] += fw_count * 4
    
    # 检测现代人视角
    modern = ['原主', '穿越', '穿书', '系统', '金手指']
    modern_count = sum(1 for p in modern if p in text)
    scores['A_吐槽型'] += modern_count * 2
    scores['C_沉浸型'] += modern_count * 1
    
    # 检测冷幽默
    cold_humor = ['要不是', '居然', '竟然', '不得不']
    humor_count = sum(1 for p in cold_humor if p in text)
    scores['B_冷幽默'] += humor_count * 2
    
    # 检测口语连接词
    oral = ['你别说', '话说回来', '这不', '你猜怎么着', '这事儿啊']
    oral_count = sum(1 for p in oral if p in text)
    scores['D_故事人'] += oral_count * 3
    
    # 检测极简陈述（短句密度）
    sentences = re.split(r'[。！？]', text)
    short_sentences = [s for s in sentences if 0 < len(s.strip()) <= 8]
    short_ratio = len(short_sentences) / max(len(sentences), 1)
    if short_ratio > 0.4:
        scores['E_冷峻型'] += 5
    
    # 检测主观判断
    subjective = ['挺漂亮的', '长得还行', '真俊', '不错', '挺好的']
    subj_count = sum(1 for p in subjective if p in text)
    scores['C_沉浸型'] += subj_count * 2
    
    # 返回最高分的人格类型
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_scores[0]
    secondary = sorted_scores[1] if sorted_scores[1][1] > 0 else None
    
    result = {
        'primary_type': primary[0],
        'primary_score': primary[1],
    }
    if secondary and secondary[1] > primary[1] * 0.5:
        result['secondary_type'] = secondary[0]
        result['secondary_score'] = secondary[1]
    
    return result, scores

def extract_rhythm_features(text):
    """提取节奏特征"""
    features = []
    
    # 检测信息直给
    direct_starts = len(re.findall(r'^[^，。！？\n]{5,15}[。！？]', text, re.MULTILINE))
    if direct_starts > 5:
        features.append('信息直给：不铺垫，第一句直接扔事实')
    
    # 检测段落极短
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    short_paras = [p for p in paragraphs if len(p) < 50]
    if len(short_paras) > len(paragraphs) * 0.3:
        features.append('段落极短：1-3句一段，没有4句以上的段落')
    
    # 检测对话省略标签
    dialogues = re.findall(r'["「][^"」]*["」]', text)
    tagged = len(re.findall(r'["」]\s*[，,]?\s*(他|她)(说|问|答|道)', text))
    if len(dialogues) > 0 and tagged / len(dialogues) < 0.3:
        features.append('对话省略标签：超过70%的对话不写"他说""她说"')
    
    # 检测跳过过渡
    transitions = len(re.findall(r'(她站起来|他站起来|她转身|他转身|她走出|他走出)', text))
    if transitions < 3:
        features.append('跳过过渡：场景切换不铺垫，直接跳切')
    
    # 检测吐槽打断叙事
    interruptions = len(re.findall(r'(?<=[。！？])[^。！？]{2,20}(说实话|不得不说|你别说|行吧|好家伙)', text))
    if interruptions > 0:
        features.append('吐槽打断叙事：吐槽出现在段落中间打断叙事')
    
    return features

def extract_samples(text, max_samples=5):
    """提取语感样本"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    samples = []
    for para in paragraphs:
        # 跳过太短或太长的段落
        if len(para) < 20 or len(para) > 150:
            continue
        
        # 识别风格标签
        tag = '叙述型'
        if re.search(r'["「]', para):
            tag = '对话型'
        elif re.search(r'(觉得|想|心里|脑子)', para):
            tag = '内心独白型'
        elif re.search(r'(说实话|不得不说|你别说|行吧)', para):
            tag = '吐槽打断型'
        elif len(para) < 40:
            tag = '短句型'
        
        samples.append({
            'text': para[:100],
            'tag': tag,
            'length': len(para)
        })
    
    # 优先选有辨识度的样本（吐槽型、对话型优先）
    priority_order = ['吐槽打断型', '对话型', '内心独白型', '短句型', '叙述型']
    sorted_samples = sorted(samples, key=lambda s: priority_order.index(s['tag']) if s['tag'] in priority_order else 99)
    
    return sorted_samples[:max_samples]

def main():
    if len(sys.argv) < 2:
        print('Usage: python extract-style.py <源文本路径>')
        sys.exit(1)
    
    filepath = sys.argv[1]
    content = read_file(filepath)
    chapters = extract_chapters(content, 3)
    
    if not chapters:
        print('Error: No chapters found')
        sys.exit(1)
    
    # 合并前3章文本
    full_text = '\n\n'.join(ch['content'] for ch in chapters)
    
    # 检测人格类型
    persona, scores = detect_persona_type(full_text)
    
    # 提取节奏特征
    rhythm = extract_rhythm_features(full_text)
    
    # 提取语感样本
    samples = extract_samples(full_text)
    
    # 输出结果
    result = {
        'source_file': filepath,
        'chapters_analyzed': len(chapters),
        'persona': persona,
        'persona_scores': scores,
        'rhythm_features': rhythm,
        'samples': samples
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
