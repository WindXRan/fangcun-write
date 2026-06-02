# -*- coding: utf-8 -*-
"""字数统计工具：统计仿写试水库 TXT 每章字数"""

import re
import sys
import os

# 导入统一字数统计模块
from word_count import count_chapter_words, MODE_STANDARD


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

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 章节名模式：支持"第X章"和"番外"等格式
    # 匹配：第1章、第123章、番外、番外一、番外1、新春番外、番外·xxx 等
    chapter_pattern = r'(第\d+章|番外[一二三四五六七八九十百千\d]*|新春番外|蛇年新春番外|现代番外|番外[·\-].+?)(\s+\S+)?'

    # 按章节分割（分隔符为20个以上短横线或等号）
    chapters = re.split(r'\n[-=]{20,}\n', content)

    # 找到各章内容（匹配章节标题行）
    ch_markers = []
    for line in content.split('\n'):
        line = line.strip()
        if re.match(chapter_pattern, line):
            ch_markers.append(line)

    results = []
    for i, marker in enumerate(ch_markers):
        if i < len(chapters) - 1:
            # 章节内容在分隔符之后
            ch_text = chapters[i + 1]
            # 去掉末尾的分隔符和后续方向
            ch_text = re.split(r'\n[-=]{20,}\n|\n={40,}\n', ch_text)[0]
            # 使用统一字数统计
            chars = count_chapter_words(ch_text, MODE_STANDARD)
            results.append(f"{marker}={chars}")

    print(" | ".join(results))

    # 总字数
    all_ch_text = ""
    for i in range(1, len(chapters)):
        ch_text = re.split(r'\n[-=]{20,}\n|\n={40,}\n', chapters[i])[0]
        all_ch_text += ch_text
    # 使用统一字数统计
    total = count_chapter_words(all_ch_text, MODE_STANDARD)
    print(f"Total={total}")


if __name__ == '__main__':
    main()
