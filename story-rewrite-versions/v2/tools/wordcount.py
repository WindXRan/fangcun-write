# -*- coding: utf-8 -*-
"""瀛楁暟缁熻宸ュ叿锛氱粺璁′豢鍐欒瘯姘村簱 TXT 姣忕珷瀛楁暟"""

import re
import sys
import os

# 瀵煎叆缁熶竴瀛楁暟缁熻妯″潡
from word_count import count_chapter_words, MODE_STANDARD


def find_chapters_by_separator(content):
    """鎸夊垎闅旂鍒嗗壊绔犺妭锛堜豢鍐欒瘯姘村簱鏍煎紡锛?""
    # 绔犺妭鍚嶆ā寮?    chapter_pattern = r'(绗琝d+绔爘鐣[涓€浜屼笁鍥涗簲鍏竷鍏節鍗佺櫨鍗僜d]*|鏂版槬鐣|铔囧勾鏂版槬鐣|鐜颁唬鐣|鐣[路\-].+?)(\s+\S+)?'

    # 鎸夌珷鑺傚垎鍓诧紙鍒嗛殧绗︿负20涓互涓婄煭妯嚎鎴栫瓑鍙凤級
    chapters = re.split(r'\n[-=]{20,}\n', content)

    # 鎵惧埌鍚勭珷鍐呭锛堝尮閰嶇珷鑺傛爣棰樿锛?    ch_markers = []
    for line in content.split('\n'):
        line = line.strip()
        if re.match(chapter_pattern, line):
            ch_markers.append(line)

    return chapters, ch_markers


def find_chapters_by_title(content):
    """鎸夌珷鑺傛爣棰樺垎鍓茬珷鑺傦紙鍘熷灏忚鏍煎紡锛?""
    lines = content.split('\n')

    # 鍖归厤绔犺妭鏍囬锛氱X绔犮€佺暘澶栦竴銆佺暘澶?銆佹柊鏄ョ暘澶栫瓑
    # 鏀寔锛氱1绔犮€佺123绔犮€佺暘澶栦竴銆佺暘澶?銆佺暘澶柭穢xx銆佹柊鏄ョ暘澶?绛?    chapter_re = re.compile(
        r'^(绗琜涓€浜屼笁鍥涗簲鍏竷鍏節鍗佺櫨鍗冮浂\d]+绔?
        r'|鐣[涓€浜屼笁鍥涗簲鍏竷鍏節鍗佺櫨鍗僜d]*'
        r'|鏂版槬鐣|铔囧勾鏂版槬鐣|鐜颁唬鐣'
        r'|鐣[路\-].*?)(\s+.*)?$'
    )

    chapters = []
    current_title = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        match = chapter_re.match(stripped)

        if match:
            # 淇濆瓨鍓嶄竴绔?            if current_title is not None:
                chapters.append((current_title, '\n'.join(current_lines)))

            # 寮€濮嬫柊绔?            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # 淇濆瓨鏈€鍚庝竴绔?    if current_title is not None:
        chapters.append((current_title, '\n'.join(current_lines)))

    return chapters


def count_file(filepath, mode='auto'):
    """缁熻鏂囦欢瀛楁暟

    Args:
        filepath: 鏂囦欢璺緞
        mode: 缁熻妯″紡
            - 'auto': 鑷姩妫€娴嬫牸寮?            - 'separator': 鎸夊垎闅旂鍒嗗壊
            - 'title': 鎸夌珷鑺傛爣棰樺垎鍓?
    Returns:
        [(绔犺妭鍚? 瀛楁暟), ...]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 鑷姩妫€娴嬫牸寮?    if mode == 'auto':
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
        # 榛樿璺緞
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(base, '浠垮啓璇曟按搴?)
        files = [f for f in os.listdir(path) if f.startswith('璇曟按_') and f.endswith('.txt')]
        if not files:
            print("鏈壘鍒拌瘯姘存枃浠?)
            return
        filepath = os.path.join(path, files[-1])
    else:
        filepath = sys.argv[1]

    # 妫€娴嬫ā寮?    mode = 'auto'
    if '--separator' in sys.argv:
        mode = 'separator'
    elif '--title' in sys.argv:
        mode = 'title'

    results = count_file(filepath, mode)

    # 杈撳嚭姣忕珷瀛楁暟
    parts = []
    total = 0
    for title, chars in results:
        parts.append(f"{title}={chars}")
        total += chars

    print(" | ".join(parts))
    print(f"Total={total} ({len(results)} chapters)")


if __name__ == '__main__':
    main()
