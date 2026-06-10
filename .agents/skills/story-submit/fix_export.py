"""Fix duplicate chapter titles in export file by adding distinguishing suffix"""
import re, os

export_path = 'C:/Users/裴浩然/Desktop/AI网文项目/oh-novel-writer/projects/散打饼干/漂亮美人在年代文被偏执疯狗缠上/rewrites/穿书七零偏执疯狗的娇气包/export/穿书七零被偏执狂盯上了.txt'

with open(export_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
title_count = {}
new_lines = []
modifications = []

for line in lines:
    m = re.match(r'^(第\d+章\s*)(.*)', line)
    if m:
        prefix = m.group(1)
        title = m.group(2).strip()
        if title in title_count:
            title_count[title] += 1
            new_title = f'{title}（{title_count[title]}）'
            new_line = prefix + new_title
            modifications.append((line, new_line))
            new_lines.append(new_line)
        else:
            title_count[title] = 1
            new_lines.append(line)
    else:
        new_lines.append(line)

if modifications:
    new_content = '\n'.join(new_lines)
    with open(export_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'修复了 {len(modifications)} 个重复章节标题:')
    for old, new in modifications:
        print(f'  {old}  →  {new}')
else:
    print('没有需要修复的重复标题')
