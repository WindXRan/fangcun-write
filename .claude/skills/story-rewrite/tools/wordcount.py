# -*- coding: utf-8 -*-
"""字数统计工具：统计仿写试水库 TXT 每章字数"""

import re
import sys
import os

# 导入统一字数统计模块
from word_count import count_chapter_words, MODE_STANDARD


def find_chapters_by_separator(content):
    """按分隔符分割章节（仿写试水库格式）"""
    # 章节名模式
    chapter_pattern = r'(第\d+章|番外[一二三四五六七八九十百千\d]*|新春番外|蛇年新春番外|现代番外|番外[·\-].+?)(\s+\S+)?'

    # 按章节分割（分隔符为20个以上短横线或等号）
    chapters = re.split(r'\n[-=]{20,}\n', content)

    # 找到各章内容（匹配章节标题行）
    ch_markers = []
    for line in content.split('\n'):
        line = line.strip()
        if re.match(chapter_pattern, line):
            ch_markers.append(line)

    return chapters, ch_markers


def find_chapters_by_title(content):
    """按章节标题分割章节（原始小说格式）"""
    lines = content.split('\n')

    # 匹配章节标题：第X章、番外一、番外1、新春番外等
    # 支持：第1章、第123章、番外一、番外1、番外·xxx、新春番外 等
    chapter_re = re.compile(
        r'^(第[一二三四五六七八九十百千零\d]+章'
        r'|番外[一二三四五六七八九十百千\d]*'
        r'|新春番外|蛇年新春番外|现代番外'
        r'|番外[·\-].*?)(\s+.*)?$'
    )

    chapters = []
    current_title = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        match = chapter_re.match(stripped)

        if match:
            # 保存前一章
            if current_title is not None:
                chapters.append((current_title, '\n'.join(current_lines)))

            # 开始新章
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # 保存最后一章
    if current_title is not None:
        chapters.append((current_title, '\n'.join(current_lines)))

    return chapters


def count_file(filepath, mode='auto'):
    """统计文件字数

    Args:
        filepath: 文件路径
        mode: 统计模式
            - 'auto': 自动检测格式
            - 'separator': 按分隔符分割
            - 'title': 按章节标题分割

    Returns:
        [(章节名, 字数), ...]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 自动检测格式
    if mode == 'auto':
        if re.search(r'\n[-=]{20,}\n', content):
            mode = 'separator'
        else:
            mode = 'title'

    if mode == 'separator':
        chapters, ch_markers = find_chapters_by_separator(content)
        results = []
        for i, marker in enumerate(ch_markers):
            if i < len(chapters) - 1:
                ch_text = chapters[i + 1]
                ch_text = re.split(r'\n[-=]{20,}\n|\n={40,}\n', ch_text)[0]
                chars = count_chapter_words(ch_text, MODE_STANDARD)
                results.append((marker, chars))
        return results
    else:
        chapter_list = find_chapters_by_title(content)
        results = []
        for title, ch_text in chapter_list:
            chars = count_chapter_words(ch_text, MODE_STANDARD)
            results.append((title, chars))
        return results


def main():
    if len(sys.argv) < 2:
        # 默认路径
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(base, '仿写试水库')
        files = [f for f in os.listdir(path) if f.startswith('试水_') and f.endswith('.txt')]
        if not files:
            print("未找到试水文件")
            return
        filepath = os.path.join(path, files[-1])
    else:
        filepath = sys.argv[1]

    # 检测模式
    mode = 'auto'
    if '--separator' in sys.argv:
        mode = 'separator'
    elif '--title' in sys.argv:
        mode = 'title'

    results = count_file(filepath, mode)

    # 输出每章字数
    parts = []
    total = 0
    for title, chars in results:
        parts.append(f"{title}={chars}")
        total += chars

    print(" | ".join(parts))
    print(f"Total={total} ({len(results)} chapters)")


if __name__ == '__main__':
    main()
