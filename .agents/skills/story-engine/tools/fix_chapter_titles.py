"""修复章节标题：从源文提取标题，或统一格式。
模式：
  source  — 从源文提取标题覆盖章节文件（默认，需传源文路径）
  strip   — 移除第一行的 # 前缀
  unify   — 给只有"第N章"的行加空行
同时支持 ch_NNN.txt 和 第N章.txt 两种文件名。
"""
import os
import re
import sys


def extract_source_titles(source_path):
    """从源文提取所有章节标题。"""
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = re.compile(r'^\s*(第\d+章\s*.+?)$', re.MULTILINE)
    titles = {}
    for match in pattern.finditer(content):
        line = match.group(1).strip()
        num_match = re.match(r'第(\d+)章', line)
        if num_match:
            ch_num = int(num_match.group(1))
            if ch_num not in titles:
                titles[ch_num] = line
    return titles


def is_valid_title(line):
    """检查第一行是否是有效的章节标题。"""
    if '###' in line or '##' in line:
        return False
    if 'rewrites/' in line or 'chapters/' in line or '仿写/' in line or '正文/' in line:
        return False
    if '**' in line:
        return False
    if re.match(r'^第\d+章[：:]', line):
        return False
    if re.match(r'^第\d+章$', line):
        return False
    return True


def iter_chapter_files(chapter_dir):
    """迭代章节目录下的章节文件（支持新旧两种命名）。"""
    for f in os.listdir(chapter_dir):
        if f.endswith('.txt') and (
            re.match(r'第\d+章\.txt', f) or re.match(r'ch_\d+\.txt', f)
        ):
            yield f


def parse_chapter_num(filename):
    """从文件名提取章节号。"""
    m = re.match(r'(?:第(\d+)章|ch_(\d+))\.txt', filename)
    if m:
        return int(m.group(1) or m.group(2))
    return None


def mode_source(chapter_dir, source_path):
    """从源文提取标题，覆盖生成的章节文件第一行。"""
    source_titles = extract_source_titles(source_path)
    print(f"从源文提取了 {len(source_titles)} 个章节标题")

    fixed = 0
    for filename in iter_chapter_files(chapter_dir):
        filepath = os.path.join(chapter_dir, filename)
        ch_num = parse_chapter_num(filename)
        if ch_num is None:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        if not lines:
            continue

        correct_title = source_titles.get(ch_num, f"第{ch_num}章")
        first_line = lines[0].strip()
        need_fix = False

        if not re.match(r'^第\d+章', first_line):
            need_fix = True
        elif re.match(r'^第\d+章$', first_line):
            need_fix = True
        elif not is_valid_title(first_line):
            need_fix = True

        if need_fix:
            lines[0] = correct_title
            while len(lines) > 1 and lines[1] == '':
                lines.pop(1)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            fixed += 1

    print(f"[source] 修复了 {fixed} 个章节文件")


def mode_strip(chapter_dir):
    """移除第一行的 # 前缀。"""
    fixed = 0
    for filename in iter_chapter_files(chapter_dir):
        filepath = os.path.join(chapter_dir, filename)
        ch_num = parse_chapter_num(filename)
        if ch_num is None:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines = lines[1:]
            lines.insert(0, f'第{ch_num}章')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            fixed += 1

    print(f"[strip] 修复了 {fixed} 个文件")


def mode_unify(chapter_dir):
    """给只有"第N章"（无标题）的行后面加空行。"""
    fixed = 0
    for filename in iter_chapter_files(chapter_dir):
        filepath = os.path.join(chapter_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        if lines and re.match(r'^第\d+章$', lines[0]) and (len(lines) < 2 or lines[1] != ''):
            lines.insert(1, '')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            fixed += 1

    print(f"[unify] 修复了 {fixed} 个文件")


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_chapter_titles.py <章节目录> [源文路径] [--mode source|strip|unify]")
        print("  source — 从源文提取标题（默认）")
        print("  strip  — 移除 # 前缀")
        print("  unify  — 给无标题的'第N章'加空行")
        sys.exit(1)

    chapter_dir = sys.argv[1]
    if not os.path.exists(chapter_dir):
        print(f"错误: 章节目录不存在: {chapter_dir}")
        sys.exit(1)

    # 解析参数
    mode = "source"
    source_path = None
    for arg in sys.argv[2:]:
        if arg.startswith('--mode='):
            mode = arg.split('=', 1)[1]
        elif not arg.startswith('--'):
            source_path = arg

    if mode == "source":
        if not source_path:
            print("错误: source 模式需要源文路径")
            sys.exit(1)
        if not os.path.exists(source_path):
            print(f"错误: 源文不存在: {source_path}")
            sys.exit(1)
        mode_source(chapter_dir, source_path)
    elif mode == "strip":
        mode_strip(chapter_dir)
    elif mode == "unify":
        mode_unify(chapter_dir)
    else:
        print(f"未知模式: {mode}")
        sys.exit(1)


if __name__ == '__main__':
    main()
