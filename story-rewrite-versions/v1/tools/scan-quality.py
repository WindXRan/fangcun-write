# -*- coding: utf-8 -*-
"""缃戞枃璐ㄩ噺鎵弿鑴氭湰 鈥?鏍囧嚭"鍒犱簡鏇村ソ"鐨勫彞瀛?""

import re
import sys
from collections import Counter

# 瀵煎叆缁熶竴瀛楁暟缁熻妯″潡
from word_count import count_chapter_words, MODE_STANDARD

def scan_quality(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    # 浣跨敤缁熶竴瀛楁暟缁熻
    total_chars = count_chapter_words(content, MODE_STANDARD)
    
    findings = []
    
    # 1. 鎯呯华鍛婄煡
    emotion_tell = [
        '濂瑰緢绱у紶', '浠栧緢绱у紶', '濂瑰緢瀹虫€?, '浠栧緢瀹虫€?, '濂瑰緢鎰ゆ€?, '浠栧緢鎰ゆ€?,
        '濂瑰緢浼ゅ績', '浠栧緢浼ゅ績', '濂瑰緢缁濇湜', '浠栧緢缁濇湜', '濂瑰緢闇囨儕', '浠栧緢闇囨儕',
        '濂瑰緢鎯婅', '浠栧緢鎯婅', '濂瑰緢灏村艾', '浠栧緢灏村艾', '濂瑰緢鏃犲', '浠栧緢鏃犲',
        '濂规澗浜嗗彛姘?, '浠栨澗浜嗗彛姘?, '濂瑰績閲屼竴绱?, '浠栧績閲屼竴绱?,
        '濂瑰績璺虫紡浜嗕竴鎷?, '浠栧績璺虫紡浜嗕竴鎷?, '濂瑰績璺冲姞閫?, '浠栧績璺冲姞閫?,
        '濂硅剳瀛愬棥鐨勪竴澹?, '浠栬剳瀛愬棥鐨勪竴澹?, '濂硅剳瀛愪竴鐗囨贩涔?, '浠栬剳瀛愪竴鐗囨贩涔?,
        '濂硅剳瀛愪竴鐗囩┖鐧?, '浠栬剳瀛愪竴鐗囩┖鐧?, '濂规暣涓汉鍍典綇', '浠栨暣涓汉鍍典綇',
        '濂瑰悗鑳屼竴鍑?, '浠栧悗鑳屼竴鍑?, '濂瑰悗鑳屽彂鍑?, '浠栧悗鑳屽彂鍑?,
        '濂硅吙鏈夌偣杞?, '浠栬吙鏈夌偣杞?, '濂规墜鎸囧彂鍑?, '浠栨墜鎸囧彂鍑?,
        '鎭愭儳浠庤剼搴?, '绱у紶寰楁墜蹇?, '瀹虫€曞緱鎵嬪績',
        '娌堟竻姝岀殑鑴戝瓙杞緱椋炲揩', '鏋楀康鍒濈殑鑴戝瓙杞緱椋炲揩',
        '濂瑰績閲屾澗浜嗗彛姘?, '浠栧績閲屾澗浜嗗彛姘?,
        '濂瑰績閲屽緢娓呮', '浠栧績閲屽緢娓呮', '濂瑰績閲屾槑鐧?, '浠栧績閲屾槑鐧?,
        '濂硅寰?, '浠栬寰?, '濂规劅瑙?, '浠栨劅瑙?,
        '濂瑰績閲屽挴鍣?, '浠栧績閲屽挴鍣?, '濂瑰績閲屼竴娌?, '浠栧績閲屼竴娌?,
        '濂瑰績搴曟硾璧?, '浠栧績搴曟硾璧?, '濂瑰績涓秾璧?, '浠栧績涓秾璧?,
        '鏃堕棿濂藉儚闈欐', '绌烘皵濂藉儚鍑濆浐', '姘旀皼灏村艾',
        '濂规暣涓汉閮戒笉濂戒簡', '浠栨暣涓汉閮戒笉濂戒簡',
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
    
    # 2. 杩囨浮鍙?    transition_patterns = [
        r'^\s*濂圭珯璧锋潵\b', r'^\s*浠栫珯璧锋潵\b', r'^\s*濂硅浆韬玕b', r'^\s*浠栬浆韬玕b',
        r'^\s*濂硅蛋鍑篭b', r'^\s*浠栬蛋鍑篭b', r'^\s*濂硅蛋杩沑b', r'^\s*浠栬蛋杩沑b',
        r'^\s*濂瑰洖鍒癨b', r'^\s*浠栧洖鍒癨b', r'^\s*濂规潵鍒癨b', r'^\s*浠栨潵鍒癨b',
        r'^\s*绗簩澶‐b', r'^\s*涓夊ぉ鍚嶾b', r'^\s*杩囦簡鍑犲ぉ\b', r'^\s*杩囦簡寰堜箙\b',
        r'^\s*涓庢鍚屾椂\b', r'^\s*鍙︿竴杈筡b',
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
    
    # 3. 瑙ｉ噴
    explain_patterns = [
        r'鍥犱负.*鎵€浠?, r'鍘熷洜鏄?, r'涔嬫墍浠?*鏄洜涓?,
        r'濂硅繖涔堝仛鏄洜涓?, r'浠栬繖涔堝仛鏄洜涓?,
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
    
    # 4. 閲嶅鎯呯华锛堝悓涓€娈靛唴锛?    emotion_kw = re.compile(r'绱у紶|瀹虫€晐鎰ゆ€抾浼ゅ績|缁濇湜|闇囨儕|鎯婅|灏村艾|鏃犲|蹇冭烦|鍙戞姈|鍙戝噳|鍍典綇|绌虹櫧|鍡?)
    
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
    
    # 5. 澶氫綑瀵硅瘽鏍囩
    tag_pattern = re.compile(r'^["銆宂.*["銆峕\s*[锛?]?\s*(浠東濂?(璇磡闂畖绛攟閬搢鍠妡鍙?')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if tag_pattern.match(stripped) and i > 0:
            prev = lines[i-1].strip()
            if prev and (prev.startswith('"') or prev.startswith('"') or prev.startswith('銆?)):
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
    print(f'Total chars: {total_chars} 瀛?)
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
