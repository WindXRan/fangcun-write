import re

path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\knowledge\超级大坦克科比\我在风花雪月里等你\我在风花雪月里等你.txt'
text = open(path, encoding='utf-8').read()

# Remove duplicate chapter titles
text = re.sub(r'(第\d+章\s+.+?)\s+\1', r'\1', text)

# Remove metadata
text = re.sub(r'简介 简介\s+书名：.*?作者：.*?标签：.*?简介：.*?(?=第1章)', '', text, flags=re.DOTALL)

# Split by chapters
ch_pattern = re.compile(r'(第\d+章\s+[^\n]+)')
parts = ch_pattern.split(text)

output_lines = []
for i, part in enumerate(parts):
    if ch_pattern.match(part.strip()):
        output_lines.append('')
        output_lines.append(part.strip())
        output_lines.append('')
    else:
        # This is chapter content - split into paragraphs
        part = part.replace('……', '\n……\n')
        part = part.replace('....', '\n....\n')
        
        # Split at Chinese sentence endings followed by space
        part = re.sub(r'([。！？])\s+', r'\1\n', part)
        
        # Split at dialogue markers
        part = re.sub(r'([。！？])([\u201c"])', r'\1\n\2', part)
        part = re.sub(r'\s+([\u201c\u201d"])', r'\n\1', part)
        
        # Split at '……' markers
        lines = part.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                output_lines.append(line)

result = '\n'.join(output_lines)
result = re.sub(r'\n{3,}', '\n\n', result)
result = result.strip()

out_path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\拆文库\我在风花雪月里等你\原文\原文.txt'
open(out_path, 'w', encoding='utf-8').write(result)

chapters = re.findall(r'^第\d+章\s+.+$', result, re.MULTILINE)
print(f'章节数: {len(chapters)}')
print(f'总行数: {len(result.split(chr(10)))}')

# Show first chapter
print('\n=== 第1章 ===')
in_ch1 = False
line_count = 0
for line in result.split('\n'):
    if '第1章' in line:
        in_ch1 = True
    if in_ch1:
        if line.strip():
            print(line)
            line_count += 1
        if line_count >= 15:
            break
    if in_ch1 and '第2章' in line:
        break
