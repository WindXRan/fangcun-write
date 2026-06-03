import os, re, sys, glob

NOVEL_DB = '.claude/skills/novel-download/novel-download-authors'

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
        if re.search(r'[「」""]', line):
            dialog += len(re.sub(r'\s+', '', line))
    return dialog / len(chars)

def avg_sentence_len(text):
    sents = [s.strip() for s in re.split(r'[。！？.!?\n]', text) if len(s.strip()) > 3]
    if not sents:
        return 0
    words = [len(re.findall(r'[\u4e00-\u9fff]', s)) for s in sents]
    return round(sum(words) / len(words), 1)

def find_source_chapter(chapter_num):
    """Search all author/book directories for the matching source chapter file."""
    results = []
    pattern = os.path.join(NOVEL_DB, '*', '*', f'第{chapter_num}章*.txt')
    for f in sorted(glob.glob(pattern)):
        results.append(f)
    # also search direct child (author without subdirectory)
    pattern2 = os.path.join(NOVEL_DB, '*', f'第{chapter_num}章*.txt')
    for f in sorted(glob.glob(pattern2)):
        if f not in results:
            results.append(f)
    return results

def extract_from_combined(source_path, chapter_num):
    """Extract a chapter from a combined txt file if individual files don't exist."""
    if not os.path.exists(source_path):
        return None
    text = read_chapter(source_path)
    # Split by chapter markers
    chapters = re.split(rf'第{chapter_num}章\s', text, maxsplit=1)
    if len(chapters) < 2:
        return None
    content = chapters[1]
    # Cut at next chapter marker
    next_ch = re.split(r'第\d+章\s', content, maxsplit=1)
    return next_ch[0].strip() if next_ch else content.strip()

def get_first_line(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # skip the title line (starts with 第)
    for l in lines:
        if not re.match(r'^第\d+章', l):
            return l
    return lines[0] if lines else ''

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
    output.append(f'# 《{book_name}》vs 源文 对比报告（第{start}-{end}章）')
    output.append('')

    for ch in range(start, end + 1):
        new_path = os.path.join(base_dir, '正文', f'第{ch}章.txt')
        if not os.path.exists(new_path):
            output.append(f'## 第{ch}章 新书未写，跳过')
            output.append('')
            continue

        new_text = read_chapter(new_path)
        new_words = count_words(new_text)
        new_paras = count_paragraphs(new_text)
        new_sents = count_sentences(new_text)
        new_dialog = calc_dialog_ratio(new_text)
        new_avg_len = avg_sentence_len(new_text)

        # Find source
        source_files = find_source_chapter(ch)
        src_text = None
        src_path_used = None

        if source_files:
            src_path_used = source_files[0]
            if len(source_files) > 1:
                src_path_used = source_files[0]
                output.append(f'> ℹ️ 找到 {len(source_files)} 个源文版本，使用: {os.path.relpath(src_path_used)}')
            src_text = read_chapter(src_path_used)

        # Fallback: try combined file in author dir
        if not src_text:
            combined_candidates = glob.glob(os.path.join(NOVEL_DB, '*', '女配一睁眼*'))
            combined_candidates += glob.glob(os.path.join(NOVEL_DB, '*', '*', '女配一睁眼*'))
            for cf in combined_candidates:
                if os.path.isfile(cf) and cf.endswith('.txt'):
                    extracted = extract_from_combined(cf, ch)
                    if extracted:
                        src_text = extracted
                        src_path_used = cf
                        break

        output.append(f'## 第{ch}章')
        output.append('')

        if src_text and src_path_used:
            src_words = count_words(src_text)
            src_paras = count_paragraphs(src_text)
            src_sents = count_sentences(src_text)
            src_dialog = calc_dialog_ratio(src_text)
            src_avg_len = avg_sentence_len(src_text)

            output.append('| 维度 | 源文 | 新书 |')
            output.append('|------|------|------|')
            output.append(f'| 正文字数 | {src_words} | {new_words} |')
            output.append(f'| 段落数 | {src_paras} | {new_paras} |')
            output.append(f'| 句数 | {src_sents} | {new_sents} |')
            output.append(f'| 对话占比 | {src_dialog:.0%} | {new_dialog:.0%} |')
            output.append(f'| 平均句长(字) | {src_avg_len} | {new_avg_len} |')
            output.append('')

            output.append('**开篇句**')
            output.append(f'- 源文：{get_first_line(src_text)}')
            output.append(f'- 新书：{get_first_line(new_text)}')
            output.append('')

            # Find title from source filename for reference
            src_basename = os.path.basename(src_path_used)
            title_match = re.search(r'第\d+章\s+(.+)\.txt', src_basename)
            if title_match:
                output.append(f'> 源文章名：{title_match.group(1)}')
                output.append('')
        else:
            output.append(f'⚠️ 源文第{ch}章未找到')
            output.append('')
            output.append('| 维度 | 值 |')
            output.append('|------|------|')
            output.append(f'| 正文字数 | {new_words} |')
            output.append(f'| 段落数 | {new_paras} |')
            output.append(f'| 句数 | {new_sents} |')
            output.append(f'| 对话占比 | {new_dialog:.0%} |')
            output.append(f'| 平均句长(字) | {new_avg_len} |')
            output.append('')

        output.append('---')
        output.append('')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f'对比报告已生成: {out_path}')

if __name__ == '__main__':
    main()
