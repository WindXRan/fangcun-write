"""
源文章节分割工具 — 从大文件中按"第X章"标记分割章节。
"""
import re
import sys
import os


def split_chapters(input_file: str, output_dir: str) -> list:
    """分割源文为独立章节文件。"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配章节标记
    pattern = r'(第\d+章[^\n]*)'
    parts = re.split(pattern, content)

    chapters = []
    current_title = None
    current_content = []

    for part in parts:
        if re.match(pattern, part):
            # 保存上一章
            if current_title and current_content:
                chapters.append((current_title, ''.join(current_content)))
            current_title = part.strip()
            current_content = []
        else:
            current_content.append(part)

    # 保存最后一章
    if current_title and current_content:
        chapters.append((current_title, ''.join(current_content)))

    # 写入文件
    os.makedirs(output_dir, exist_ok=True)
    for i, (title, content) in enumerate(chapters, 1):
        output_file = os.path.join(output_dir, f'第{i}章.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'{title}\n{content}')

    return chapters


def extract_chapters(input_file: str, start: int, end: int, output_file: str):
    """提取指定范围的章节到一个文件。"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配章节标记
    pattern = r'(第\d+章[^\n]*)'
    parts = re.split(pattern, content)

    chapters = []
    current_title = None
    current_content = []

    for part in parts:
        if re.match(pattern, part):
            if current_title and current_content:
                chapters.append((current_title, ''.join(current_content)))
            current_title = part.strip()
            current_content = []
        else:
            current_content.append(part)

    if current_title and current_content:
        chapters.append((current_title, ''.join(current_content)))

    # 提取指定范围
    selected = chapters[start-1:end]
    with open(output_file, 'w', encoding='utf-8') as f:
        for title, content in selected:
            f.write(f'{title}\n{content}\n\n')

    return len(selected)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法:')
        print('  分割全部：python source_chapter_splitter.py split <输入文件> <输出目录>')
        print('  提取范围：python source_chapter_splitter.py extract <输入文件> <开始> <结束> <输出文件>')
        sys.exit(1)

    action = sys.argv[1]

    if action == 'split':
        input_file = sys.argv[2]
        output_dir = sys.argv[3]
        chapters = split_chapters(input_file, output_dir)
        print(f'分割完成：{len(chapters)} 章')

    elif action == 'extract':
        input_file = sys.argv[2]
        start = int(sys.argv[3])
        end = int(sys.argv[4])
        output_file = sys.argv[5]
        count = extract_chapters(input_file, start, end, output_file)
        print(f'提取完成：{count} 章（第{start}-{end}章）')
