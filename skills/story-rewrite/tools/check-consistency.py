# -*- coding: utf-8 -*-
"""
人设一致性检查脚本
检查对话是否符合角色当前身份/处境

用法：python check-consistency.py <正文路径> <角色设定JSON路径>
输出：不一致的对话列表
"""

import re
import sys
import json

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def extract_dialogues(text):
    """提取所有对话"""
    dialogues = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Match Chinese quotes
        matches = re.finditer(r'["「]([^"」]*)["」]', line)
        for m in matches:
            dialogues.append({
                'line': i + 1,
                'text': m.group(1),
                'full_line': line.strip()[:80]
            })
    return dialogues

def check_persona_violations(dialogues, persona_rules):
    """检查对话是否违反人设"""
    violations = []
    
    for d in dialogues:
        text = d['text']
        
        # 检测霸总腔（如果角色是伪装的底层人物）
        boss_phrases = ['除非我死', '你敢', '找死', '放肆', '跪下', '本少爷', '本王']
        for phrase in boss_phrases:
            if phrase in text:
                violations.append({
                    'line': d['line'],
                    'type': 'BossTone',
                    'dialogue': text[:60],
                    'issue': f'角色说了霸总台词"{phrase}"，但当前身份可能不允许',
                    'suggestion': '改用符合当前身份的说法'
                })
        
        # 检测现代词汇在古代场景
        modern_words = ['OK', 'ok', '没问题', '好的', '收到', '了解']
        ancient_markers = ['小姐', '公子', '大人', '奴婢', '老爷']
        has_ancient = any(m in d['full_line'] for m in ancient_markers)
        for word in modern_words:
            if word in text and has_ancient:
                violations.append({
                    'line': d['line'],
                    'type': 'ModernInAncient',
                    'dialogue': text[:60],
                    'issue': f'古代场景中出现现代词"{word}"',
                    'suggestion': '换成古代口语表达'
                })
        
        # 检测失忆角色说出不该知道的信息
        # (这个需要更复杂的上下文分析，这里做简单检测)
    
    return violations

def check_emotion_duplicates(text):
    """检查重复情绪表达"""
    violations = []
    lines = text.split('\n')
    
    emotion_kw = re.compile(r'紧张|害怕|愤怒|伤心|绝望|震惊|惊讶|尴尬|无奈|心跳|发抖|发凉|僵住|空白|嗡')
    
    # 按段落分组
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
                violations.append({
                    'line': item['line'],
                    'type': 'RepeatEmotion',
                    'dialogue': item['text'][:60],
                    'issue': '同一段内重复情绪表达',
                    'suggestion': '只保留最强的一个'
                })
    
    return violations

def check_clichés(text):
    """检查古早梗"""
    violations = []
    lines = text.split('\n')
    
    clichés = [
        ('平地摔', '脚下一滑|脚底一滑|脚下一绊'),
        ('恰好撞见', '正好.*看见|刚好.*撞见|恰好.*看到'),
        ('霸总宣言', '除非我死|你是我的|不许离开'),
        ('记忆涌入', '记忆涌上来|记忆像.*洪水|记忆的闸门'),
        ('倏地睁眼', '倏地.*睁开眼'),
    ]
    
    for i, line in enumerate(lines):
        for name, pattern in clichés:
            if re.search(pattern, line):
                violations.append({
                    'line': i + 1,
                    'type': 'Cliché',
                    'dialogue': line.strip()[:60],
                    'issue': f'古早梗：{name}',
                    'suggestion': '换成更有新意的表达'
                })
    
    return violations

def main():
    if len(sys.argv) < 2:
        print('Usage: python check-consistency.py <正文路径> [角色设定JSON路径]')
        sys.exit(1)
    
    filepath = sys.argv[1]
    text = read_file(filepath)
    
    all_violations = []
    
    # 1. 人设一致性检查
    dialogues = extract_dialogues(text)
    persona_violations = check_persona_violations(dialogues, {})
    all_violations.extend(persona_violations)
    
    # 2. 重复情绪检查
    emotion_violations = check_emotion_duplicates(text)
    all_violations.extend(emotion_violations)
    
    # 3. 古早梗检查
    cliché_violations = check_clichés(text)
    all_violations.extend(cliché_violations)
    
    # 输出
    print('=' * 50)
    print('Consistency Check Report')
    print(f'File: {filepath}')
    print('=' * 50)
    
    by_type = {}
    for v in all_violations:
        t = v['type']
        by_type[t] = by_type.get(t, 0) + 1
    
    print()
    print('--- Findings by type ---')
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f'  {t}: {count}')
    
    print()
    print('--- Details ---')
    for v in all_violations:
        print(f'  Line {v["line"]} [{v["type"]}]: {v["dialogue"]}')
        print(f'    Issue: {v["issue"]}')
        print(f'    -> {v["suggestion"]}')
    
    print()
    print('=' * 50)
    print(f'Total violations: {len(all_violations)}')
    print('=' * 50)

if __name__ == '__main__':
    main()
