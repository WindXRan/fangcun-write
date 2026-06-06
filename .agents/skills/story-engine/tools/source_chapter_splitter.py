"""
源文章节分割工具 — 从大文件中按"第X章"标记分割章节。
"""
import re
import sys
import os


def split_chapters(input_file: str, output_dir: str, use_title_name: bool = False) -> list:
    """分割源文为独立章节文件。
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        use_title_name: 是否使用章节标题作为文件名（如"第1章 李好好其人.txt"）
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配章节标记（支持空格：第x章、第 x章、第x 章、第 x 章）
    pattern = r'(第\s*\d+\s*章[^\n]*)'
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
        if use_title_name:
            # 使用章节标题作为文件名，清理非法字符
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title.strip())
            output_file = os.path.join(output_dir, f'{safe_title}.txt')
        else:
            output_file = os.path.join(output_dir, f'第{i}章.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'{title}\n{content}')

    return chapters


def verify_chapters(output_dir: str) -> list:
    """验证分割后的章节文件是否连续且正确。
    
    Returns:
        问题列表，每项为 (章节号, 问题描述)
    """
    issues = []
    
    # 获取所有章节文件
    files = [f for f in os.listdir(output_dir) if f.startswith('第') and f.endswith('章.txt')]
    if not files:
        return [('0', '没有找到章节文件')]
    
    # 提取章节号
    chapter_nums = []
    for f in files:
        m = re.search(r'第(\d+)章', f)
        if m:
            chapter_nums.append(int(m.group(1)))
    
    chapter_nums.sort()
    
    # 检查是否从1开始
    if chapter_nums and chapter_nums[0] != 1:
        issues.append(('1', f'第一章缺失，实际从第{chapter_nums[0]}章开始'))
    
    # 检查是否连续
    for i in range(len(chapter_nums) - 1):
        if chapter_nums[i + 1] - chapter_nums[i] != 1:
            missing = list(range(chapter_nums[i] + 1, chapter_nums[i + 1]))
            issues.append((str(chapter_nums[i]), f'第{missing}章缺失'))
    
    return issues


def extract_chapters(input_file: str, start: int, end: int, output_file: str):
    """提取指定范围的章节到一个文件。"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配章节标记（支持空格：第x章、第 x章、第x 章、第 x 章）
    pattern = r'(第\s*\d+\s*章[^\n]*)'
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
        print('  分割全部：python source_chapter_splitter.py split <输入文件> <输出目录> [--use-title-name]')
        print('  提取范围：python source_chapter_splitter.py extract <输入文件> <开始> <结束> <输出文件>')
        print('  验证章节：python source_chapter_splitter.py verify <输出目录>')
        sys.exit(1)

    action = sys.argv[1]

    if action == 'split':
        input_file = sys.argv[2]
        output_dir = sys.argv[3]
        use_title_name = '--use-title-name' in sys.argv
        chapters = split_chapters(input_file, output_dir, use_title_name)
        print(f'分割完成：{len(chapters)} 章')
        
        # 自动验证
        issues = verify_chapters(output_dir)
        if issues:
            print(f'发现 {len(issues)} 个问题:')
            for ch, msg in issues[:10]:
                print(f'  第{ch}章: {msg}')
        else:
            print('章节验证通过')

    elif action == 'extract':
        input_file = sys.argv[2]
        start = int(sys.argv[3])
        end = int(sys.argv[4])
        output_file = sys.argv[5]
        count = extract_chapters(input_file, start, end, output_file)
        print(f'提取完成：{count} 章（第{start}-{end}章）')

    elif action == 'verify':
        output_dir = sys.argv[2]
        issues = verify_chapters(output_dir)
        if issues:
            print(f'发现 {len(issues)} 个问题:')
            for ch, msg in issues:
                print(f'  第{ch}章: {msg}')
        else:
            print('章节验证通过')
