"""Check for duplicate chapter titles across all chapter files"""
import os, re

ch_dir = 'C:/Users/裴浩然/Desktop/AI网文项目/oh-novel-writer/projects/散打饼干/漂亮美人在年代文被偏执疯狗缠上/rewrites/穿书七零偏执疯狗的娇气包/chapters'

title_map = {}
files = sorted(os.listdir(ch_dir), key=lambda x: int(re.search(r'\d+', x).group()))

for f in files:
    ch_num = int(re.search(r'\d+', f).group())
    with open(os.path.join(ch_dir, f), 'r', encoding='utf-8') as fh:
        first_line = fh.readline().strip()
    m = re.match(r'第\d+章\s*(.*)', first_line)
    if m:
        title = m.group(1).strip()
        if title in title_map:
            title_map[title].append(ch_num)
        else:
            title_map[title] = [ch_num]
    else:
        print(f'Warning: {f} no header: {first_line!r}')

dupes = {k: v for k, v in title_map.items() if len(v) > 1}
if dupes:
    print('重复章节标题:')
    for title, chapters in sorted(dupes.items(), key=lambda x: x[1]):
        print(f'  "{title}" -> ' + '、'.join(f'第{c}章' for c in chapters))
else:
    print('没有重复章节标题')

# Also show titles of the mentioned chapters
print('\n平台报错的章节:')
for cn in [9, 64, 94, 99, 102, 119]:
    fname = f'ch_{cn:03d}.txt'
    with open(os.path.join(ch_dir, fname), 'r', encoding='utf-8') as fh:
        first = fh.readline().strip()
    print(f'  第{cn}章: {first}')
