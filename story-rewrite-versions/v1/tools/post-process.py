# -*- coding: utf-8 -*-
"""
鍚庡鐞嗛殢鏈哄寲鑴氭湰 鈥?鎵撶牬LLM鐨?瀹岀編缁撴瀯"
鍐欏畬姝ｆ枃鍚庤窇涓€閬嶏紝杈撳嚭鏇村儚浜哄啓鐨勭増鏈€?
鐢ㄦ硶锛歱ython post-process.py <姝ｆ枃璺緞> [--aggressive]
"""

import re
import sys
import random

# 瀵煎叆缁熶竴瀛楁暟缁熻妯″潡
from word_count import count_chapter_words, format_word_count, MODE_STANDARD

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def split_paragraphs(text):
    """鎸夌┖琛屽垎娈?""
    return text.split('\n\n')

def join_paragraphs(paragraphs):
    return '\n\n'.join(paragraphs)

def is_dialogue(line):
    """鍒ゆ柇鏄惁鏄璇濊"""
    stripped = line.strip()
    return stripped.startswith('"') or stripped.startswith('"') or stripped.startswith('銆?)

def is_chapter_header(line):
    """鍒ゆ柇鏄惁鏄珷鑺傛爣棰?""
    stripped = line.strip()
    return bool(re.match(r'^绗琝d+绔?, stripped)) or bool(re.match(r'^#', stripped))

def random_delete_sentences(paragraph, p=0.15):
    """闅忔満鍒犲彞瀛愶紙姒傜巼p锛?""
    lines = paragraph.split('\n')
    if len(lines) <= 1:
        return paragraph
    
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        # 涓嶅垹瀵硅瘽锛堝璇濆垹浜嗕細褰卞搷鍓ф儏锛?        if is_dialogue(stripped):
            kept.append(line)
            continue
        # 涓嶅垹绔犺妭鏍囬
        if is_chapter_header(stripped):
            kept.append(line)
            continue
        # 闅忔満淇濈暀
        if random.random() > p:
            kept.append(line)
    
    result = '\n'.join(kept).strip()
    return result if result else paragraph

def merge_short_paragraphs(paragraphs, threshold=30):
    """鍚堝苟杩囩煭鐨勬钀?""
    result = []
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i].strip()
        if len(p) < threshold and i + 1 < len(paragraphs):
            # 鍚堝苟鍒颁笅涓€涓钀?            next_p = paragraphs[i + 1].strip()
            merged = p + '\n' + next_p
            result.append(merged)
            i += 2
        else:
            result.append(p)
            i += 1
    return result

def split_long_paragraph(paragraph, max_sentences=5):
    """鎷嗗垎杩囬暱鐨勬钀?""
    lines = [l for l in paragraph.split('\n') if l.strip()]
    if len(lines) <= max_sentences:
        return [paragraph]
    
    # 鍦ㄩ殢鏈轰綅缃媶鍒?    split_point = random.randint(2, len(lines) - 2)
    part1 = '\n'.join(lines[:split_point])
    part2 = '\n'.join(lines[split_point:])
    return [part1, part2]

def add_solo_paragraph(paragraphs, text):
    """鍦ㄩ殢鏈轰綅缃彃鍏ョ嫭璇嶆"""
    # 浠庢枃鏈腑鎻愬彇鍊欓€夌殑鐭彞
    sentences = re.split(r'[銆傦紒锛焆', text)
    short_sentences = [s.strip() for s in sentences if 3 < len(s.strip()) < 15]
    
    if not short_sentences:
        return paragraphs
    
    # 闅忔満閫変竴涓煭鍙?    solo = random.choice(short_sentences)
    
    # 鍦ㄩ殢鏈轰綅缃彃鍏?    pos = random.randint(1, len(paragraphs) - 1)
    paragraphs.insert(pos, solo + '銆?)
    
    return paragraphs

def randomize_paragraph_lengths(paragraphs):
    """闅忔満鍖栨钀介暱搴?""
    result = []
    for p in paragraphs:
        lines = [l for l in p.split('\n') if l.strip()]
        
        if len(lines) >= 6:
            # 闀挎钀斤細闅忔満鎷?            parts = split_long_paragraph(p)
            result.extend(parts)
        elif len(lines) == 1 and len(p.strip()) < 20 and random.random() < 0.3:
            # 鐙瘝娈碉細30%姒傜巼鍚堝苟鍒颁笅涓€涓?            if result:
                result[-1] = result[-1].strip() + '\n' + p.strip()
            else:
                result.append(p)
        else:
            result.append(p)
    
    return result

def break_scene_transitions(paragraphs):
    """鎵撶鍦烘櫙杩囨浮"""
    transition_patterns = [
        r'^鈥斺€?',
        r'^---+$',
        r'^\*\*\*+$',
    ]
    
    result = []
    for p in paragraphs:
        stripped = p.strip()
        # 濡傛灉鏄函鍒嗛殧绾匡紝50%姒傜巼鍒犻櫎
        for pattern in transition_patterns:
            if re.match(pattern, stripped):
                if random.random() < 0.5:
                    continue
        result.append(p)
    
    return result

def post_process(text, aggressive=False):
    """涓诲鐞嗘祦绋?""
    paragraphs = split_paragraphs(text)
    
    # Step 1: 闅忔満鍒犲彞瀛愶紙姣忔15%姒傜巼鍒犱竴涓潪瀵硅瘽鍙ワ級
    processed = []
    for p in paragraphs:
        if random.random() < 0.3:  # 30%鐨勬钀戒細琚鐞?            p = random_delete_sentences(p, p=0.15)
        processed.append(p)
    
    # Step 2: 鍚堝苟杩囩煭娈佃惤
    processed = merge_short_paragraphs(processed, threshold=30)
    
    # Step 3: 闅忔満鍖栨钀介暱搴?    processed = randomize_paragraph_lengths(processed)
    
    # Step 4: 鎻掑叆鐙瘝娈碉紙姣忕珷鑷冲皯2涓級
    solo_count = sum(1 for p in processed if len(p.strip()) < 15)
    if solo_count < 2:
        processed = add_solo_paragraph(processed, text)
        processed = add_solo_paragraph(processed, text)
    
    # Step 5: 鎵撶鍦烘櫙杩囨浮
    processed = break_scene_transitions(processed)
    
    # Step 6: aggressive妯″紡 - 鏇存縺杩涚殑鎵撲贡
    if aggressive:
        # 闅忔満鍚堝苟鐩搁偦娈佃惤锛?0%姒傜巼锛?        merged = []
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
    # 浣跨敤缁熶竴瀛楁暟缁熻
    original_chars = count_chapter_words(text, MODE_STANDARD)

    result = post_process(text, aggressive)
    # 浣跨敤缁熶竴瀛楁暟缁熻
    processed_chars = count_chapter_words(result, MODE_STANDARD)

    # 杈撳嚭鍒版柊鏂囦欢
    output_path = filepath.replace('.txt', '_processed.txt')
    write_file(output_path, result)

    print(f'Original: {original_chars} 瀛?)
    print(f'Processed: {processed_chars} 瀛?)
    print(f'Change: {processed_chars - original_chars} 瀛?({(processed_chars - original_chars) / original_chars * 100:.1f}%)')
    print(f'Output: {output_path}')

if __name__ == '__main__':
    main()
