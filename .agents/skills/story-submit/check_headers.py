"""Check file number vs header number mismatches"""
import os, re

ch_dir = 'C:/Users/裴浩然/Desktop/AI网文项目/oh-novel-writer/projects/散打饼干/漂亮美人在年代文被偏执疯狗缠上/rewrites/穿书七零偏执疯狗的娇气包/chapters'
files = sorted(os.listdir(ch_dir), key=lambda x: int(re.search(r'\d+', x).group()))
issues = []

for f in files:
    ch_num = int(re.search(r'\d+', f).group())
    with open(os.path.join(ch_dir, f), 'r', encoding='utf-8') as fh:
        first_line = fh.readline().strip()
    m = re.search(r'第(\d+)章', first_line)
    if m:
        header_num = int(m.group(1))
        if header_num != ch_num:
            issues.append((ch_num, header_num, first_line[:80]))
    else:
        # Check for markdown-style header
        m2 = re.search(r'#\s*第(\d+)章', first_line)
        if m2:
            header_num = int(m2.group(1))
            if header_num != ch_num:
                issues.append((ch_num, f'#{header_num}', first_line[:80]))
            else:
                # Has # prefix but correct number - style issue only
                pass
        else:
            issues.append((ch_num, 'NO_MATCH', first_line[:80]))

print(f'共 {len(issues)} 个问题文件:')
for ch_num, hdr, preview in issues:
    print(f'  ch_{ch_num:03d}.txt -> header={hdr} | {preview}')
