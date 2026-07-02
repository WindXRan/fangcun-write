#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二轮深度清理：修复第一轮脚本没覆盖的深层AI腔
用法: python3 deep_clear_ai_tone.py <project_dir> [start_ch] [end_ch]
"""

import re, os, sys, glob

PROJECT = sys.argv[1] if len(sys.argv) > 1 else "."
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
END = int(sys.argv[3]) if len(sys.argv) > 3 else 99

REPORT = {"chapters": 0, "fixes": 0, "details": []}

def fix_chapter(text):
    """深层AI腔修复，返回(修复后文本, 修复次数)"""
    fixes = 0
    
    # === 修复1：解释性语句（AI喜欢直白解释，人类让读者自己体会）===
    # "显然，..." → 删掉"显然，"
    old = len(text)
    text = re.sub(r'显然[，,]\s*', '', text)
    fixes += (len(text) - old) // 2  # 粗略计数
    
    # "毫无疑问，..." → 删掉
    old = len(text)
    text = re.sub(r'毫无疑问[，,]\s*', '', text)
    fixes += (len(text) - old) // 2
    
    # "不难想象，..." / "可以想象，..." → 删掉
    old = len(text)
    text = re.sub(r'(?:不难)?想象[，,]\s*', '', text)
    fixes += (len(text) - old) // 2
    
    # "可见，..." → 删掉
    old = len(text)
    text = re.sub(r'可见[，,]\s*', '', text)
    fixes += (len(text) - old) // 2
    
    # === 修复2：情绪直白描述 → 改为动作/生理反应 ===
    # "他感到X" / "她感到X" → 改成动作
    emotions = [
        (r'([他她])感到一阵([\u4e00-\u9fff]+)', r'\1'),  # 简化，需要上下文
        (r'([他她])心中涌起一阵([\u4e00-\u9fff]+)', r'\1'),
        (r'([他她])心里一紧', None),  # 保留，这是好的写法
        (r'([他她])只觉得([\u4e00-\u9fff]+)', r'\1'),
    ]
    # 这个需要更精细的处理，先跳过
    
    # === 修复3："便"字过度使用（AI喜欢用"便"代替"就/于是"）===
    # 但"便"在古风/半古风里是合理的，只修明显AI腔的
    # "便不再" → "就不"
    old = len(text)
    text = re.sub(r'便不再', '就不再', text)
    fixes += (len(text) - old) // 2
    
    # "便也" → "也"
    old = len(text)
    text = re.sub(r'便也', '也', text)
    fixes += (len(text) - old) // 2
    
    # "便要" → "就要"
    old = len(text)
    text = re.sub(r'便要', '就要', text)
    fixes += (len(text) - old) // 2
    
    # === 修复4：AI cliché（更全的列表）===
    cliches = [
        ("嘴角微微勾起", "嘴角一勾"),
        ("嘴角微微上扬", "嘴角一挑"),
        ("眼中闪过一丝", "眼里掠过"),
        ("心中暗道", "心里想"),
        ("心中暗自", "心里"),
        ("不难看出", ""),  # 直接删
        ("可想而知", ""),
        ("换言之", "换句话说"),  # 太书面，改口语
        ("与此同时", "这时候"),
        ("尽管如此", "虽然这样"),
        ("总而言之", "总之"),
        ("某种程度上", ""),  # 删掉
        ("值得一提的是", ""),
        ("不可否认", ""),
        ("众所周知", ""),
        ("无一例外", ""),
        ("归根结底", ""),
        ("不言而喻", ""),
    ]
    for old_str, new_str in cliches:
        if old_str in text:
            if new_str:
                text = text.replace(old_str, new_str)
            else:
                # 删掉整个句子或短语
                text = re.sub(re.escape(old_str) + r'[，,。]?\s*', '', text)
            fixes += 1
    
    # === 修复5：过度使用破折号（AI喜欢用破折号解释）===
    # 连续超过2个破折号 → 随机替换成逗号或句号
    dashes = re.findall(r'——', text)
    if len(dashes) > 3:
        # 随机替换一部分（这里用确定性的：每隔一个替换）
        parts = text.split('——')
        if len(parts) > 2:
            new_text = parts[0]
            for i in range(1, len(parts)):
                if i % 2 == 0:
                    new_text += '，' + parts[i]
                else:
                    new_text += '——' + parts[i]
            text = new_text
            fixes += 1
    
    # === 修复6：括号解释（AI喜欢用括号补充信息）===
    # 删掉括号内的解释性文字（如果是重要信息就保留）
    def should_keep_bracket(match):
        content = match.group(1)
        # 保留：时间、数字、重要名词
        if re.search(r'\d+|年|月|日|时|分', content):
            return match.group(0)
        # 删掉：解释性文字
        return ''
    
    old = len(text)
    text = re.sub(r'（([^）]+)）', should_keep_bracket, text)
    fixes += max(0, (len(text) - old) // 10)  # 粗略计数
    
    # === 修复7：冗余的过渡句 ===
    transitions = [
        "话分两头",
        "却说",
        "且说",
        "再说",
        "回到",
        "镜头一转",
        "与此同时",
        "另一边",
    ]
    for t in transitions:
        if t in text:
            # 只删掉单独成段的过渡句
            text = re.sub(r'\n\s*' + re.escape(t) + r'[，,。]?\s*\n', '\n', text)
            fixes += 1
    
    # === 修复8：AI喜欢的"X，而非Y"句式 ===
    old = len(text)
    text = re.sub(r'([\u4e00-\u9fff，,。！？]+)，而非([\u4e00-\u9fff，,。！？]+)', r'\1，不是\2', text)
    fixes += max(0, (len(text) - old) // 10)
    
    # === 修复9：段落过长/过短 ===
    # 这个需要理解上下文，暂时跳过
    
    # === 修复10：标点符号AI腔 ===
    # 连续3个以上逗号 → 拆分句子
    text = re.sub(r'([，,]{3,})', '。', text)  # 过于碎的句子合并
    
    return text, fixes

def process_file(fpath):
    content = open(fpath, encoding="utf-8").read()
    m = re.search(r'<content>(.*?)</content>', content, re.DOTALL)
    if not m:
        return False
    
    original = m.group(1)
    fixed, n_fixes = fix_chapter(original)
    
    if fixed != original:
        content = content.replace(original, fixed, 1)
        open(fpath, "w", encoding="utf-8").write(content)
        return n_fixes
    return 0

def main():
    pattern = os.path.join(PROJECT, "正文", "正文", "第*.xml")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"未找到正文文件: {pattern}")
        return
    
    total_fixes = 0
    chs = 0
    
    for fpath in files:
        fname = os.path.basename(fpath)
        m = re.search(r'第(\d+)章', fname)
        if not m:
            continue
        ch = int(m.group(1))
        if ch < START or ch > END:
            continue
        
        n = process_file(fpath)
        if n:
            print(f"  第{ch}章: {n}处深层AI腔")
            total_fixes += n
            chs += 1
    
    print(f"\n完成！共修复 {chs} 章，{total_fixes} 处深层AI腔")

if __name__ == "__main__":
    main()
