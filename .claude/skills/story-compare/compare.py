import os, re, sys, glob

NOVEL_DB = 'novel-download-authors'

def read_chapter(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def count_words(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def count_sentences(text):
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
    words = [len(re.findall(r'[\u4e00-\u9fff]', s)) for s in sents]
    return round(sum(words) / len(words), 1)

def find_source_chapter(chapter_num):
    results = []
    pattern = os.path.join(NOVEL_DB, '*', '*', f'第{chapter_num}章*.txt')
    for f in sorted(glob.glob(pattern)):
        results.append(f)
    pattern2 = os.path.join(NOVEL_DB, '*', f'第{chapter_num}章*.txt')
    for f in sorted(glob.glob(pattern2)):
        if f not in results:
            results.append(f)
    return results

def parse_source_path(full_path):
    """Extract (author, book_name) from a source chapter path.
    Expected patterns:
      novel-download-authors/{author}/{book_name}/第{ch}章 *.txt
      novel-download-authors/{author}/第{ch}章 *.txt
    """
    rel = os.path.relpath(full_path, NOVEL_DB)
    parts = rel.split(os.sep)
    if len(parts) >= 2:
        return parts[0], os.path.splitext(parts[-1])[0]
    return None, None

def find_combined_file(author, chapter_num):
    """Search for a combined txt file in the author directory that contains the chapter."""
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
        lines = lines[1:]
    return '\n'.join(lines).strip()

def main():
    args = sys.argv[1:]
    if not args:
        print('用法: python compare.py <书名> [起始章] [结束章]')
        print('示例: python compare.py 假扮失忆大佬女友后我翻车了')
        print('示例: python compare.py 假扮失忆大佬女友后我翻车了 1 10')
        sys.exit(1)

    book_name = args[0]
    base_dir = book_name
    start = int(args[1]) if len(args) > 1 else 1
    end = int(args[2]) if len(args) > 2 else min(start + 2, start + 2)

    out_dir = os.path.join(base_dir, '对比')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'对比_{start}-{end}.md')

    output = []
    output.append(f'# 两份小说文本对比（第{start}-{end}章）')
    output.append('')
    output.append('---')
    output.append('')
    output.append('**以下内容可直接喂给 AI，无需额外说明。**')
    output.append('')
    output.append('请你以资深网文编辑的身份，对下面两份文本进行对比分析。')
    output.append('')
    output.append('## 分析要求')
    output.append('')
    output.append('1. **差异分析**：版本A和版本B在叙事风格、节奏控制、人设塑造、信息密度上有什么核心差异？')
    output.append('2. **优劣评估**：分别指出两版各自的优势和不足。哪个版本的阅读体验更好？好在哪里？')
    output.append('3. **数据特征**：结合每章的统计指标（字数、段落、对话占比、句长等），分析数据差异背后的叙事策略。')
    output.append('4. **市场判断**：从网文市场的角度，哪一版更容易留住读者？为什么？')
    output.append('5. **改进建议**：给较弱的那一版提出具体修改方向。')
    output.append('6. **抄袭风险评估**：逐章对比两版的具体情节、对话、场景设计，判断是否存在抄袭嫌疑。重点关注：(1) 情节走向是否高度雷同 (2) 关键场景/对话是否有大段相似 (3) 人设/关系框架是否照搬 (4) 两版的差异化程度是否足够——如果将版本B拿去查重，能否通过？给出具体的风险等级（低/中/高）和需要重点修改的段落。')
    output.append('')
    output.append('请逐章分析，最后给出总体评价。**不要猜测哪版是仿写**，仅基于文本本身做判断。')
    output.append('')
    output.append('---')
    output.append('')

    # 统计数据（所有章节汇总）
    all_stats = []

    for ch in range(start, end + 1):
        new_path = os.path.join(base_dir, '正文', f'第{ch}章.txt')
        if not os.path.exists(new_path):
            continue

        new_text = read_chapter(new_path)
        new_words = count_words(new_text)
        new_paras = count_paragraphs(new_text)
        new_sents = count_sentences(new_text)
        new_dialog = calc_dialog_ratio(new_text)
        new_avg_len = avg_sentence_len(new_text)

        source_files = find_source_chapter(ch)
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
            src_sents = count_sentences(src_text)
            src_dialog = calc_dialog_ratio(src_text)
            src_avg_len = avg_sentence_len(src_text)
            all_stats.append((ch, src_words, src_paras, src_sents, src_dialog, src_avg_len,
                              new_words, new_paras, new_sents, new_dialog, new_avg_len))

    # 统计汇总表
    if all_stats:
        output.append('## 统计对比')
        output.append('')
        output.append('| 章节 | A字数 | B字数 | A段落 | B段落 | A对话% | B对话% | A句长 | B句长 |')
        output.append('|------|-------|-------|-------|-------|--------|--------|-------|-------|')
        for s in all_stats:
            ch, sw, sp, ss, sd, sl, nw, np_, ns, nd, nl = s
            output.append(f'| 第{ch}章 | {sw} | {nw} | {sp} | {np_} | {sd:.0%} | {nd:.0%} | {sl} | {nl} |')
        output.append('')

    # 版本A（源文）全部连着放
    output.append('---')
    output.append('')
    output.append('# 版本A（源文）')
    output.append('')

    for ch in range(start, end + 1):
        source_files = find_source_chapter(ch)
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
            src_body = strip_title_line(src_text)
            output.append(f'## 第{ch}章')
            output.append('')
            output.append(src_body)
            output.append('')
        else:
            output.append(f'## 第{ch}章')
            output.append('')
            output.append('⚠️ 未找到源文')
            output.append('')

    # 版本B（新书）全部连着放
    output.append('---')
    output.append('')
    output.append('# 版本B（新书）')
    output.append('')

    for ch in range(start, end + 1):
        new_path = os.path.join(base_dir, '正文', f'第{ch}章.txt')
        if not os.path.exists(new_path):
            output.append(f'## 第{ch}章')
            output.append('')
            output.append('⚠️ 未写')
            output.append('')
            continue

        new_text = read_chapter(new_path)
        new_body = strip_title_line(new_text)
        output.append(f'## 第{ch}章')
        output.append('')
        output.append(new_body)
        output.append('')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f'对比报告已生成: {out_path}')

if __name__ == '__main__':
    main()
