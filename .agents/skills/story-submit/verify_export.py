"""Verify export has no duplicate chapters/titles"""
import re
from collections import Counter

path = 'C:/Users/裴浩然/Desktop/AI网文项目/oh-novel-writer/projects/散打饼干/漂亮美人在年代文被偏执疯狗缠上/rewrites/穿书七零偏执疯狗的娇气包/export/穿书七零被偏执狂盯上了.txt'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

titles = re.findall(r'^第(\d+)章\s*(.*)', content, re.MULTILINE)
print(f'总章节数: {len(titles)}')

ch_counts = Counter(t[0] for t in titles)
dupes = {k:v for k,v in ch_counts.items() if v > 1}
if dupes:
    print(f'\n重复章号:')
    for k,v in sorted(dupes.items()):
        print(f'  第{k}章 -> {v}次')
else:
    print('\n无重复章号')

title_counts = Counter(t[1].strip() for t in titles)
title_dupes = {k:v for k,v in title_counts.items() if v > 1}
if title_dupes:
    print(f'\n重复标题:')
    for k,v in sorted(title_dupes.items()):
        print(f'  "{k}" -> {v}次')
else:
    print('\n无重复标题')
