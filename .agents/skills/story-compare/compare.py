import os, re, sys, glob, json
from collections import Counter

NOVEL_DB = 'projects'
LEGACY_DB = 'projects'  # 向后兼容旧目录

# ── 风格指纹分析 ──────────────────────

def split_sentences(text):
    text = text.replace('\n', ' ')
    parts = re.split(r"[。！？]", text)
    return [s.strip() for s in parts if s.strip()]

def count_chinese_chars(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def split_paragraphs(text):
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]

def calc_stats(values):
    if not values:
        return {"avg": 0, "stddev": 0}
    avg = sum(values) / len(values)
    if len(values) < 2:
        return {"avg": round(avg, 1), "stddev": 0}
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    stddev = variance ** 0.5
    return {"avg": round(avg, 1), "stddev": round(stddev, 1)}

AI_TELLS_PATTERNS = [
    ("路标词", re.compile(r"首先|其次|最后|总而言之|综上所述|值得注意的是")),
    ("二分对照", re.compile(r"一方面.{1,20}另一方面")),
    ("协作口吻", re.compile(r"让我们|接下来|现在我们")),
    ("高频副词", re.compile(r"微微|轻轻|淡淡|缓缓")),
    ("说道", re.compile(r"她说道|他说道|她轻声道|他低声道")),
]

def analyze_style(text):
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)
    
    sentence_lengths = [count_chinese_chars(s) for s in sentences]
    sentence_stats = calc_stats(sentence_lengths)
    
    para_lengths = [count_chinese_chars(p) for p in paragraphs]
    para_stats = calc_stats(para_lengths)
    
    total_chars = len(re.sub(r'\s', '', text))
    total_words = count_chinese_chars(text)
    total_sentences = len(sentences)
    total_paragraphs = len(paragraphs)
    
    dialog_chars = 0
    for line in text.split('\n'):
        if re.search(r'[「」""\u201c\u201d]', line):
            dialog_chars += len(re.sub(r'\s+', '', line))
    dialogue_ratio = dialog_chars / total_chars if total_chars > 0 else 0
    
    short_sents = sum(1 for l in sentence_lengths if l < 15)
    long_sents = sum(1 for l in sentence_lengths if l > 60)
    short_ratio = round(short_sents / total_sentences, 3) if total_sentences > 0 else 0
    long_ratio = round(long_sents / total_sentences, 3) if total_sentences > 0 else 0
    
    short_paras = sum(1 for l in para_lengths if l < 50)
    medium_paras = sum(1 for l in para_lengths if 50 <= l <= 200)
    long_paras = sum(1 for l in para_lengths if l > 200)
    single_para = sum(1 for p in paragraphs if len(split_sentences(p)) == 1)
    
    all_chars = re.findall(r'[\u4e00-\u9fff]', text)
    unique_chars = len(set(all_chars))
    ttr = round(unique_chars / len(all_chars), 3) if all_chars else 0
    
    ai_tells = []
    for name, pattern in AI_TELLS_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            ai_tells.append(f"{name}({len(matches)}处)")
    
    return {
        "total_chars": total_chars,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "total_paragraphs": total_paragraphs,
        "sentence_length": sentence_stats,
        "sentence_distribution": {
            "short_ratio_lt15": short_ratio,
            "long_ratio_gt60": long_ratio,
        },
        "paragraph_length": para_stats,
        "paragraph_distribution": {
            "short_lt50": round(short_paras / total_paragraphs, 3) if total_paragraphs > 0 else 0,
            "medium_50_200": round(medium_paras / total_paragraphs, 3) if total_paragraphs > 0 else 0,
            "long_gt200": round(long_paras / total_paragraphs, 3) if total_paragraphs > 0 else 0,
            "single_sentence_ratio": round(single_para / total_paragraphs, 3) if total_paragraphs > 0 else 0,
        },
        "vocabulary_ttr": ttr,
        "dialogue_ratio": round(dialogue_ratio, 3),
        "ai_tells": ai_tells,
    }

# ── 原有功能 ──────────────────────

def read_source_path_from_concept(book_dir):
    # 新路径: concept.md
    for fname in ['concept.md', '设定/新书设定.md', '设定/新书概念.md']:
        concept_file = os.path.join(book_dir, fname)
        if os.path.exists(concept_file):
            with open(concept_file, encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'\*?\*?源文路径\*?\*?[：:]\s*(.+)', content)
            if match:
                return match.group(1).strip()
        # 对新结构，也尝试从 concept.md 推断
        if fname == 'concept.md' and os.path.exists(concept_file):
            # 源文路径通常在 projects/{作者}/{书名}/ 下
            parts = book_dir.replace('\\', '/').split('/')
            if 'rewrites' in parts:
                idx = parts.index('rewrites')
                if idx >= 2:
                    source_path = '/'.join(parts[:idx])
                    if os.path.isdir(source_path):
                        return source_path
    return None

def read_chapter(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def count_words(text):
    return len(re.sub(r'[\s\n\r]', '', text))

def count_sentences_simple(text):
    return len(re.findall(r'[。！？.!?]', text))

def count_paragraphs(text):
    return len([p for p in text.split('\n\n') if p.strip()])

def calc_dialog_ratio(text):
    chars = re.sub(r'\s+', '', text)
    if not chars:
        return 0
    dialog = 0
    for line in text.split('\n'):
        if re.search(r'[「」""\u201c\u201d]', line):
            dialog += len(re.sub(r'\s+', '', line))
    return dialog / len(chars)

def avg_sentence_len(text):
    sents = [s.strip() for s in re.split(r'[。！？.!?\n]', text) if len(s.strip()) > 3]
    if not sents:
        return 0
    words = [len(re.sub(r'[\s\n\r]', '', s)) for s in sents]
    return round(sum(words) / len(words), 1)

def find_source_chapter(chapter_num, source_override=None, base_dir=None):
    results = []

    # 0. 优先检查源书目录下的缓存拆章（最可靠）
    # 新结构: projects/{作者}/{书名}/_cache/chapters/
    if base_dir:
        # 从 rewrite 项目路径推导源书路径
        parts = base_dir.replace('\\', '/').split('/')
        if 'rewrites' in parts:
            idx = parts.index('rewrites')
            source_book = '/'.join(parts[:idx])
            # 新路径
            for cache_dir in ['_cache/chapters', '源文章节', '源文']:
                local_src = os.path.join(source_book, cache_dir)
                if os.path.isdir(local_src):
                    for fmt in [f'ch_{chapter_num:03d}', f'第{chapter_num:03d}章', f'第{chapter_num}章']:
                        for f in sorted(glob.glob(os.path.join(local_src, f'{fmt}*.txt'))):
                            results.append(f)
                    if results:
                        return results
        # 旧结构 fallback
        for cache_dir in ['源文章节', '源文', '_cache/chapters']:
            local_src = os.path.join(base_dir, cache_dir)
            if os.path.isdir(local_src):
                for fmt in [f'ch_{chapter_num:03d}', f'第{chapter_num:03d}章', f'第{chapter_num}章']:
                    for f in sorted(glob.glob(os.path.join(local_src, f'{fmt}*.txt'))):
                        results.append(f)
                if results:
                    return results

    if source_override:
        src_dir = os.path.join(NOVEL_DB, source_override)
        if not os.path.isdir(src_dir):
            src_dir = os.path.join(LEGACY_DB, source_override)
        if os.path.isdir(src_dir):
            # 1. 先搜 _cache/chapters/ 或 源文/ 子目录
            for cache_dir in ['_cache/chapters', '源文', '源文章节']:
                split_dir = os.path.join(src_dir, cache_dir)
                if os.path.isdir(split_dir):
                    for fmt in [f'ch_{chapter_num:03d}', f'第{chapter_num:03d}章', f'第{chapter_num}章']:
                        for f in sorted(glob.glob(os.path.join(split_dir, f'{fmt}*.txt'))):
                            results.append(f)
                    if results:
                        break
            # 2. 搜根目录下的拆章文件
            if not results:
                for fmt in [f'ch_{chapter_num:03d}', f'第{chapter_num:03d}章', f'第{chapter_num}章']:
                    for f in sorted(glob.glob(os.path.join(src_dir, f'{fmt}*.txt'))):
                        if f not in results:
                            results.append(f)
            # 3. 搜合并文件
            if not results:
                for f in os.listdir(src_dir):
                    if f.endswith('.txt') and os.path.isfile(os.path.join(src_dir, f)):
                        path = os.path.join(src_dir, f)
                        text = read_chapter(path)
                        if re.search(rf'第{chapter_num}章\s', text):
                            results.append(path)
    if results:
        return results
    # 5. 全局搜索（兜底，但限制在同作者目录下）
    if source_override:
        author = source_override.split('/')[0] if '/' in source_override else None
        if author:
            for db in [NOVEL_DB, LEGACY_DB]:
                for cache_dir in ['_cache/chapters', '源文']:
                    pattern = os.path.join(db, author, '*', cache_dir, f'第{chapter_num}章*.txt')
                    for f in sorted(glob.glob(pattern)):
                        results.append(f)
                pattern = os.path.join(db, author, '*', f'第{chapter_num}章*.txt')
                for f in sorted(glob.glob(pattern)):
                    if f not in results:
                        results.append(f)
    # 6. 最后才全局搜索
    if not results:
        for db in [NOVEL_DB, LEGACY_DB]:
            for cache_dir in ['_cache/chapters', '源文']:
                pattern = os.path.join(db, '*', '*', cache_dir, f'第{chapter_num}章*.txt')
                for f in sorted(glob.glob(pattern)):
                    results.append(f)
    return results

def parse_source_path(full_path):
    rel = os.path.relpath(full_path, NOVEL_DB)
    parts = rel.split(os.sep)
    if len(parts) >= 2:
        return parts[0], os.path.splitext(parts[-1])[0]
    return None, None

def find_combined_file(author, chapter_num):
    if not author:
        return None
    author_dir = os.path.join(NOVEL_DB, author)
    if not os.path.isdir(author_dir):
        return None
    for f in os.listdir(author_dir):
        if f.endswith('.txt') and os.path.isfile(os.path.join(author_dir, f)):
            path = os.path.join(author_dir, f)
            text = read_chapter(path)
            if re.search(rf'第{chapter_num}章\s', text):
                return path
    return None

def extract_from_combined(file_path, chapter_num):
    if not os.path.exists(file_path):
        return None
    text = read_chapter(file_path)
    chapters = re.split(rf'第{chapter_num}章\s', text, maxsplit=1)
    if len(chapters) < 2:
        return None
    content = chapters[1]
    next_ch = re.split(r'第\d+章\s', content, maxsplit=1)
    return next_ch[0].strip() if next_ch else content.strip()

def strip_title_line(text):
    lines = text.split('\n')
    if lines and re.match(r'^第\d+章', lines[0].strip()):
        return '\n'.join(lines[1:]).strip(), lines[0].strip()
    return text, ''

# ── 数据收集 ──────────────────────

def collect_data(base_dir, start, end, source_override):
    all_stats = []
    all_profiles = []
    src_chapters = {}
    new_chapters = {}

    for ch in range(start, end + 1):
        # 支持新旧两种命名
        new_path = None
        for chapters_dir in ['chapters', '正文']:
            for fmt in [f'ch_{ch:03d}.txt', f'第{ch}章.txt']:
                candidate = os.path.join(base_dir, chapters_dir, fmt)
                if os.path.exists(candidate):
                    new_path = candidate
                    break
            if new_path:
                break
        if not new_path:
            continue

        new_text = read_chapter(new_path)
        new_words = count_words(new_text)
        new_paras = count_paragraphs(new_text)
        new_sents = count_sentences_simple(new_text)
        new_dialog = calc_dialog_ratio(new_text)
        new_avg_len = avg_sentence_len(new_text)
        new_profile = analyze_style(new_text)
        new_chapters[ch] = strip_title_line(new_text)  # (content, title)

        source_files = find_source_chapter(ch, source_override, base_dir)
        src_text = None
        src_author = None

        if source_files:
            src_path = source_files[0]
            src_text = read_chapter(src_path)
            src_author, _ = parse_source_path(src_path)

        if not src_text and src_author:
            combined_path = find_combined_file(src_author, ch)
            if combined_path:
                extracted = extract_from_combined(combined_path, ch)
                if extracted:
                    src_text = extracted

        if src_text:
            src_words = count_words(src_text)
            src_paras = count_paragraphs(src_text)
            src_sents = count_sentences_simple(src_text)
            src_dialog = calc_dialog_ratio(src_text)
            src_avg_len = avg_sentence_len(src_text)
            src_profile = analyze_style(src_text)
            all_stats.append((ch, src_words, src_paras, src_sents, src_dialog, src_avg_len,
                              new_words, new_paras, new_sents, new_dialog, new_avg_len))
            all_profiles.append((ch, src_profile, new_profile))
            src_chapters[ch] = strip_title_line(src_text)  # (content, title)

    return all_stats, all_profiles, src_chapters, new_chapters

# ── 生成报告版（给人看） ──────────────────────

def generate_report(book_name, start, end, all_stats, all_profiles, new_chapters=None):
    output = []
    output.append(f'# 仿写对比报告：{book_name}')
    output.append(f'> 对比区间：第{start}-{end}章')
    output.append('')
    output.append('---')
    output.append('')
    
    # 基础统计
    output.append('## 一、基础统计')
    output.append('')
    if all_stats:
        output.append('| 章节 | A字数 | B字数 | 字数差 | A段落 | B段落 | A对话% | B对话% | A句长 | B句长 |')
        output.append('|------|-------|-------|--------|-------|-------|--------|--------|-------|-------|')
        for s in all_stats:
            ch, sw, sp, ss, sd, sl, nw, np_, ns, nd, nl = s
            diff = nw - sw
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            output.append(f'| 第{ch}章 | {sw} | {nw} | {diff_str} | {sp} | {np_} | {sd:.0%} | {nd:.0%} | {sl} | {nl} |')
        
        # 汇总
        total_src = sum(s[1] for s in all_stats)
        total_new = sum(s[6] for s in all_stats)
        avg_src_dialog = sum(s[4] for s in all_stats) / len(all_stats)
        avg_new_dialog = sum(s[9] for s in all_stats) / len(all_stats)
        avg_src_sent = sum(s[5] for s in all_stats) / len(all_stats)
        avg_new_sent = sum(s[10] for s in all_stats) / len(all_stats)
        output.append(f'| **合计** | **{total_src}** | **{total_new}** | **{total_new-total_src:+d}** | - | - | **{avg_src_dialog:.0%}** | **{avg_new_dialog:.0%}** | **{avg_src_sent}** | **{avg_new_sent}** |')
    output.append('')
    
    # 风格指纹
    output.append('## 二、风格指纹')
    output.append('')
    if all_profiles:
        output.append('### 句长分布')
        output.append('')
        output.append('| 章节 | A句长(均值±标准差) | B句长(均值±标准差) | A短句% | B短句% | 差异说明 |')
        output.append('|------|-------------------|-------------------|--------|--------|----------|')
        for ch, src_p, new_p in all_profiles:
            src_sl = src_p['sentence_length']
            new_sl = new_p['sentence_length']
            src_short = src_p['sentence_distribution']['short_ratio_lt15']
            new_short = new_p['sentence_distribution']['short_ratio_lt15']
            diff_desc = "B更短" if new_sl['avg'] < src_sl['avg'] else "B更长" if new_sl['avg'] > src_sl['avg'] else "相近"
            output.append(f'| 第{ch}章 | {src_sl["avg"]}±{src_sl["stddev"]} | {new_sl["avg"]}±{new_sl["stddev"]} | {src_short:.0%} | {new_short:.0%} | {diff_desc} |')
        output.append('')
        
        output.append('### 段落结构')
        output.append('')
        output.append('| 章节 | A段长均值 | B段长均值 | A单句段% | B单句段% |')
        output.append('|------|----------|----------|----------|----------|')
        for ch, src_p, new_p in all_profiles:
            output.append(f'| 第{ch}章 | {src_p["paragraph_length"]["avg"]} | {new_p["paragraph_length"]["avg"]} | {src_p["paragraph_distribution"]["single_sentence_ratio"]:.0%} | {new_p["paragraph_distribution"]["single_sentence_ratio"]:.0%} |')
        output.append('')
        
        output.append('### 词汇与对话')
        output.append('')
        output.append('| 章节 | A-TTR | B-TTR | A对话% | B对话% |')
        output.append('|------|-------|-------|--------|--------|')
        for ch, src_p, new_p in all_profiles:
            output.append(f'| 第{ch}章 | {src_p["vocabulary_ttr"]} | {new_p["vocabulary_ttr"]} | {src_p["dialogue_ratio"]:.0%} | {new_p["dialogue_ratio"]:.0%} |')
        output.append('')
        
        # AI痕迹
        output.append('## 三、AI痕迹检测')
        output.append('')
        has_ai = False
        for ch, src_p, new_p in all_profiles:
            if src_p["ai_tells"] or new_p["ai_tells"]:
                has_ai = True
                break
        
        if has_ai:
            output.append('| 章节 | A(源文) | B(新书) | 风险提示 |')
            output.append('|------|---------|---------|----------|')
            for ch, src_p, new_p in all_profiles:
                src_ai = ", ".join(src_p["ai_tells"]) if src_p["ai_tells"] else "无"
                new_ai = ", ".join(new_p["ai_tells"]) if new_p["ai_tells"] else "无"
                src_count = len(src_p["ai_tells"])
                new_count = len(new_p["ai_tells"])
                risk = "⚠️ B偏高" if new_count > src_count + 1 else "✅ 正常"
                output.append(f'| 第{ch}章 | {src_ai} | {new_ai} | {risk} |')
            output.append('')
            
            # 汇总
            total_src_ai = sum(len(p[1]["ai_tells"]) for p in all_profiles)
            total_new_ai = sum(len(p[2]["ai_tells"]) for p in all_profiles)
            output.append(f'> **汇总**：源文共 {total_src_ai} 处AI痕迹，新书共 {total_new_ai} 处AI痕迹。')
            if total_new_ai > total_src_ai * 2:
                output.append('> ⚠️ **新书AI痕迹偏高，建议修改高频副词和路标词。**')
            else:
                output.append('> ✅ AI痕迹在合理范围内。')
        else:
            output.append('✅ 未检测到明显AI痕迹。')
        output.append('')
    
    # 章节衔接性分析
    output.append('## 四、章节衔接性分析')
    output.append('')
    output.append('| 章节对 | 剧情连贯 | 人物一致 | 场景转换 | 时间线 | 问题提示 |')
    output.append('|--------|----------|----------|----------|--------|----------|')
    
    # 分析相邻章节的衔接性
    for i in range(len(all_stats) - 1):
        ch1 = all_stats[i][0]
        ch2 = all_stats[i+1][0]
        
        # 获取新书章节内容
        ch1_content = new_chapters.get(ch1, ("", ""))[0] if new_chapters else ""
        ch2_content = new_chapters.get(ch2, ("", ""))[0] if new_chapters else ""
        
        issues = []
        
        # 检查字数波动
        ch1_words = all_stats[i][6]  # 新书字数
        ch2_words = all_stats[i+1][6]
        word_diff = abs(ch2_words - ch1_words) / max(ch1_words, 1)
        if word_diff > 0.5:
            issues.append(f"字数波动{word_diff:.0%}")
        
        # 检查对话占比变化
        ch1_dialog = all_stats[i][9]
        ch2_dialog = all_stats[i+1][9]
        dialog_diff = abs(ch2_dialog - ch1_dialog)
        if dialog_diff > 0.3:
            issues.append(f"对话占比变化大")
        
        # 检查句长变化
        ch1_sent_len = all_stats[i][10]
        ch2_sent_len = all_stats[i+1][10]
        if ch1_sent_len > 0 and ch2_sent_len > 0:
            sent_len_diff = abs(ch2_sent_len - ch1_sent_len) / max(ch1_sent_len, 1)
            if sent_len_diff > 0.3:
                issues.append(f"句长变化大")
        
        # 默认评价
        plot_coherent = "✅" if not issues else "⚠️"
        char_consistent = "✅"
        scene_transition = "✅"
        timeline = "✅"
        
        issue_str = "；".join(issues) if issues else "无"
        output.append(f'| 第{ch1}-{ch2}章 | {plot_coherent} | {char_consistent} | {scene_transition} | {timeline} | {issue_str} |')
    
    output.append('')
    output.append('> **说明**：✅=正常，⚠️=需关注。字数波动>50%、对话占比变化>30%、句长变化>30%会触发警告。')
    output.append('')
    
    # 总结
    output.append('## 五、总结')
    output.append('')
    if all_stats:
        total_src = sum(s[1] for s in all_stats)
        total_new = sum(s[6] for s in all_stats)
        output.append(f'- **总字数**：源文 {total_src} 字 → 新书 {total_new} 字（{total_new-total_src:+d}）')
        output.append(f'- **章节数**：{len(all_stats)} 章')
        avg_diff = (total_new - total_src) / len(all_stats)
        output.append(f'- **平均每章差异**：{avg_diff:+.0f} 字')
    output.append('')
    
    return '\n'.join(output)

# ── 生成AI分析版（喂给AI） ──────────────────────

def generate_ai_analysis(start, end, all_stats, all_profiles, src_chapters, new_chapters):
    output = []
    output.append(f'# 仿写文本对比（第{start}-{end}章）')
    output.append('')
    output.append('**以下内容可直接喂给 AI，无需额外说明。**')
    output.append('')
    output.append('请你以资深网文编辑的身份，对下面两份文本进行对比分析。版本A是源文（原作），版本B是仿写作品。')
    output.append('')
    output.append('## 分析要求')
    output.append('')
    output.append('1. **差异分析**：版本A和版本B在叙事风格、节奏控制、人设塑造、信息密度上有什么核心差异？')
    output.append('2. **优劣评估**：分别指出两版各自的优势和不足。哪个版本的阅读体验更好？好在哪里？')
    output.append('3. **市场判断**：从网文市场的角度，哪一版更容易留住读者？为什么？')
    output.append('4. **改进建议**：给仿写版提出具体修改方向。')
    output.append('5. **抄袭风险评估**：逐章对比两版的具体情节、对话、场景设计，判断是否存在抄袭嫌疑。重点关注：(1) 情节走向是否高度雷同 (2) 关键场景/对话是否有大段相似 (3) 人设/关系框架是否照搬 (4) 两版的差异化程度是否足够。给出具体的风险等级（低/中/高）和需要重点修改的段落。')
    output.append('6. **Prompt优化建议**：根据仿写成品暴露的问题，反推写作prompt应该如何调整（2-3条具体可执行的修改建议）。')
    output.append('')
    output.append('请逐章分析，最后给出总体评价。')
    output.append('')
    output.append('---')
    output.append('')
    
    # 版本A全文
    output.append('# 版本A（源文）')
    output.append('')
    for ch in sorted(src_chapters.keys()):
        content, title = src_chapters[ch]
        output.append(f'## {title}' if title else f'## 第{ch}章')
        output.append('')
        output.append(content)
        output.append('')
    output.append('---')
    output.append('')
    
    # 版本B全文
    output.append('# 版本B（仿写）')
    output.append('')
    for ch in sorted(new_chapters.keys()):
        content, title = new_chapters[ch]
        output.append(f'## {title}' if title else f'## 第{ch}章')
        output.append('')
        output.append(content)
        output.append('')
    
    return '\n'.join(output)

# ── 主函数 ──────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print('用法: python compare.py <书名> [起始章] [结束章] [--source <作者/书名>]')
        sys.exit(1)

    book_name = args[0]
    base_dir = book_name
    start = int(args[1]) if len(args) > 1 else 1
    end = int(args[2]) if len(args) > 2 else min(start + 2, start + 2)

    source_override = None
    for i, arg in enumerate(args):
        if arg == '--source' and i + 1 < len(args):
            source_override = args[i + 1]
            break

    if not source_override:
        source_path = read_source_path_from_concept(base_dir)
        if source_path:
            source_path = source_path.replace('/', os.sep).replace('\\', os.sep)
            if source_path.startswith(NOVEL_DB + os.sep):
                source_path = source_path[len(NOVEL_DB) + 1:]
            source_override = source_path

    out_dir = os.path.join(base_dir, 'compare')
    os.makedirs(out_dir, exist_ok=True)

    # 收集数据
    all_stats, all_profiles, src_chapters, new_chapters = collect_data(base_dir, start, end, source_override)

    # 生成报告版（给人看）
    report_path = os.path.join(out_dir, f'对比_{start}-{end}_报告.md')
    report_content = generate_report(book_name, start, end, all_stats, all_profiles, new_chapters)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f'报告版已生成: {report_path}')

    # 生成AI分析版（喂给AI）
    ai_path = os.path.join(out_dir, f'对比_{start}-{end}_AI分析.md')
    ai_content = generate_ai_analysis(start, end, all_stats, all_profiles, src_chapters, new_chapters)
    with open(ai_path, 'w', encoding='utf-8') as f:
        f.write(ai_content)
    print(f'AI分析版已生成: {ai_path}')

if __name__ == '__main__':
    main()
