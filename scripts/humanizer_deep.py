#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三轮深度清理：基于 humanizer skill 的24种AI腔模式
用法: python3 humanizer_deep.py <project_dir> [start_ch] [end_ch]
"""

import re, os, sys, glob

PROJECT = sys.argv[1] if len(sys.argv) > 1 else "."
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
END = int(sys.argv[3]) if len(sys.argv) > 3 else 99

REPORT = {"chapters": 0, "fixes": 0, "patterns": {}}

def fix_text(text):
    """应用 humanizer skill 的24种模式，返回(修复后文本, 修复次数, 模式统计)"""
    fixes = 0
    patterns = {}
    
    def log(pattern, n=1):
        patterns[pattern] = patterns.get(pattern, 0) + n
    
    # === 模式1: 过度强调重要性（stands as/testament/pivotal等）===
    for w in ["标志着一个 pivotal", "标志着一个关键", "作为一个重要的", "作为一个关键的"]:
        if w in text:
            text = text.replace(w, "")
            fixes += 1
            log("过度强调重要性")
    
    # === 模式2: 表面分析（-ing结尾短语）===
    # "，反映了..." / "，象征着..." / "，突出了..."
    old = len(text)
    text = re.sub(r'，\s*(?:反映|象征|突出|强调|展示|体现|代表|标记)[了着了]?\s*\w+', '', text)
    n = (len(text) - old) // 10
    if n > 0:
        fixes += n
        log("表面分析-ing短语", n)
    
    # === 模式3: 宣传性语言（boasts/丰富的/深刻的/令人惊叹的）===
    promotional = [
        ("令人惊叹的", ""),
        ("令人震撼的", ""),
        ("丰富的", ""),  # 如果是"丰富的经验"这种，删掉"丰富的"
        ("深刻的", ""),
        ("充满活力的", ""),
        ("必访的", ""),
        ("令人叹为观止的", ""),
        ("享有盛誉的", ""),
    ]
    for old_w, new_w in promotional:
        if old_w in text:
            if new_w:
                text = text.replace(old_w, new_w)
            else:
                text = re.sub(re.escape(old_w), '', text)
            fixes += 1
            log("宣传性语言")
    
    # === 模式4: 模糊归因（"专家指出"/"业内人士认为"）===
    vague_attrs = [
        "专家指出", "专家认为", "业内人士认为", "观察者指出",
        "有分析认为", "相关报告显示", "研究表明",
    ]
    for w in vague_attrs:
        if w in text and not re.search(r'\d{4}年|20\d{2}', text[max(0, text.find(w)-50):text.find(w)+50]):
            # 只有在没有具体年份/来源的情况下才删
            text = text.replace(w, "")
            fixes += 1
            log("模糊归因")
    
    # === 模式5: AI高频词汇 ===
    ai_words = [
        ("此外", "而且"),  # Additionally → 而且/另外
        ("此外，", "而且，"),
        ("凸显了", "显示了"),
        ("突显了", "显示了"),
        ("展现了", "展示了"),
        ("体现了", "显示了"),
        ("标志着", "说明"),
        ("象征着", "说明"),
        ("作为印证", ""),
        ("无疑", ""),  # 删掉
        ("毋庸置疑", ""),
        ("至关重要", "很重要"),
        ("重大意义", "意义"),
        ("深远影响", "影响"),
        ("广泛关注", "关注"),
    ]
    for old_w, new_w in ai_words:
        if old_w in text:
            if new_w:
                text = text.replace(old_w, new_w)
            else:
                text = re.sub(re.escape(old_w) + r'[，,。]?\s*', '', text)
            fixes += 1
            log("AI高频词汇")
    
    # === 模式6: 避免用"是/are"（serves as/stands as）===
    # "X serves as Y" → "X是Y"
    old = len(text)
    text = re.sub(r'([\u4e00-\u9fff]+)(?:作为|担任了|扮演了)\s*([\u4e00-\u9fff]+[的的])', r'\1是\2', text)
    if len(text) != old:
        fixes += 1
        log("避免用'是'")
    
    # === 模式7: 否定对比句（"不是A，而是B"）===
    # 这个在小说里有时是对的，暂时跳过
    
    # === 模式8: 排比句（三个一组）===
    # 检测连续三个相似结构的句子
    sentences = re.split(r'([。！？])', text)
    # 这个需要语义理解，暂时跳过
    
    # === 模式9: 破折号过度使用 ===
    dashes = text.count('——')
    if dashes > 2:
        # 随机替换一半的破折号为逗号
        parts = text.split('——')
        if len(parts) > 1:
            new_text = parts[0]
            for i in range(1, len(parts)):
                if i % 2 == 0 and len(parts[i]) < 30:  # 短的后半句用逗号
                    new_text += '，' + parts[i]
                else:
                    new_text += '——' + parts[i]
            text = new_text
            fixes += 1
            log("破折号过度")
    
    # === 模式10: 括号解释 ===
    def is_trivial_bracket(match):
        content = match.group(1)
        # 保留：时间、数字
        if re.search(r'\d+', content):
            return match.group(0)
        # 删掉：解释性文字
        return ''
    
    old = len(text)
    text = re.sub(r'（([^）]+)）', is_trivial_bracket, text)
    if len(text) < old:
        fixes += 1
        log("括号解释")
    
    # === 模式11: 冗余过渡句 ===
    transitions = [
        "总的来说", "总而言之", "综上所述",
        "不难看出", "可想而知", "换言之",
        "换句话说", "也就是说",
        "值得一提的是", "值得注意的是",
        "不可否认", "毋庸置疑",
        "众所周知", "如前所述",
        "与此同时", "在这种情况下",
    ]
    for t in transitions:
        if t in text:
            text = re.sub(re.escape(t) + r'[，,。]?\s*', '', text)
            fixes += 1
            log("冗余过渡句")
    
    # === 模式12: 情绪直白描述 → 改为动作 ===
    # "他感到X" → 改
    emotion_patterns = [
        (r'([他她])感到([\u4e00-\u9fff]{2,4})', None),  # 需要上下文，暂时跳过
        (r'([他她])心中涌起([\u4e00-\u9fff]+)', None),
        (r'([他她])心里一紧', None),  # 这个是好的
    ]
    
    # === 模式13: "得"字结构过度 ===
    # 把一些"X得Y"改成更自然的表达
    de_patterns = [
        (r'高兴得跳了起来', '高兴得蹦起来'),
        (r'吓得后退一步', '吓退一步'),
        (r'痛得闷哼一声', '痛得闷哼'),
    ]
    for old_p, new_p in de_patterns:
        if old_p in text:
            text = text.replace(old_p, new_p)
            fixes += 1
            log("得字结构")
    
    # === 模式14: 书面语副词 ===
    written_adv = [
        ("缓缓地", "慢慢"),
        ("轻轻地", "轻轻"),
        ("静静地", "静静"),
        ("默默地", "默默"),
        ("深深地", "深深"),
        ("重重地", "重重"),
        ("悄悄地", "悄悄"),
    ]
    for old_w, new_w in written_adv:
        if old_w in text:
            text = text.replace(old_w, new_w)
            fixes += 1
            log("书面语副词")
    
    # === 模式15: "便"字（古风小说里合理，但过度使用不好）===
    # 只修明显的
    old = len(text)
    text = re.sub(r'便([\u4e00-\u9fff]{1,2})了', r'就\1了', text)
    if len(text) != old:
        fixes += 1
        log("便字")
    
    # === 模式16: 解释性语句 ===
    explain_words = ["显然", "毫无疑问", "不难想象", "可以想象", "可见"]
    for w in explain_words:
        if w in text:
            text = re.sub(re.escape(w) + r'[，,。]?\s*', '', text)
            fixes += 1
            log("解释性语句")
    
    # === 模式17: 句子过长（超过40字）===
    # 这个需要理解语义，暂时跳过
    
    # === 模式18: 重复词汇 ===
    # 检测同一段落里重复出现的词
    # 这个需要语义理解，暂时跳过
    
    return text, fixes, patterns

def process_file(fpath):
    content = open(fpath, encoding="utf-8").read()
    m = re.search(r'<content>(.*?)</content>', content, re.DOTALL)
    if not m:
        return 0, {}
    
    original = m.group(1)
    fixed, n_fixes, patterns = fix_text(original)
    
    if fixed != original:
        content = content.replace(original, fixed, 1)
        open(fpath, "w", encoding="utf-8").write(content)
        return n_fixes, patterns
    return 0, {}

def main():
    pattern = os.path.join(PROJECT, "正文", "正文", "第*.xml")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"未找到正文文件: {pattern}")
        return
    
    total_fixes = 0
    chs = 0
    all_patterns = {}
    
    for fpath in files:
        fname = os.path.basename(fpath)
        m = re.search(r'第(\d+)章', fname)
        if not m:
            continue
        ch = int(m.group(1))
        if ch < START or ch > END:
            continue
        
        n, patterns = process_file(fpath)
        if n:
            print(f"  第{ch}章: {n}处")
            total_fixes += n
            chs += 1
            for p, cnt in patterns.items():
                all_patterns[p] = all_patterns.get(p, 0) + cnt
    
    print(f"\n完成！共修复 {chs} 章，{total_fixes} 处")
    if all_patterns:
        print("\n修复模式统计:")
        for p, cnt in sorted(all_patterns.items(), key=lambda x: -x[1]):
            print(f"  {p}: {cnt}处")

if __name__ == "__main__":
    main()
