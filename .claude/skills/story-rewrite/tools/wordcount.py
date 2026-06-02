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

    # 按章节分割
    chapters = re.split(r'第[123]章\s+\S+\n[-=]{20,}\n', content)

    # 找到各章内容
    ch_markers = re.findall(r'(第[123]章\s+\S+)\n[-=]{20,}\n', content)

    results = []
    for i, marker in enumerate(ch_markers):
        ch_num = marker[1]  # 1, 2, 3
        if i + 1 < len(chapters):
            # 找到下一章或后续方向之前的文本
            ch_text = chapters[i + 1]
            # 去掉末尾的分隔符和后续方向
            ch_text = re.split(r'\n[-=]{20,}\n|\n={40,}\n', ch_text)[0]
            # 使用统一字数统计
            chars = count_chapter_words(ch_text, MODE_STANDARD)
            results.append(f"Ch{ch_num}={chars}")

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
