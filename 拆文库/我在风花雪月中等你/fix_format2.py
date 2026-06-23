import re

path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\knowledge\超级大坦克科比\我在风花雪月里等你\我在风花雪月里等你.txt'
text = open(path, encoding='utf-8').read()

# Remove duplicate chapter titles (e.g., "第1章 标题 第1章 标题" -> "第1章 标题")
text = re.sub(r'(第\d+章\s+.+?)\s+\1', r'\1', text)

# Remove metadata at the beginning
text = re.sub(r'^简介 简介\s+书名：.*?简介：.*?(?=第1章)', '', text, flags=re.DOTALL)
text = re.sub(r'书名：我在风花雪月里等你作者：超级大坦克科比标签：都市\|第一人称\|已完结', '', text)

# Find chapter positions
ch_pattern = re.compile(r'(第\d+章\s+[^\n]+)')
chapters = list(ch_pattern.finditer(text))

print(f'找到 {len(chapters)} 个章节')

# Process each chapter
output_parts = []
for idx, match in enumerate(chapters):
    ch_title = match.group(1).strip()
    start = match.end()
    end = chapters[idx+1].start() if idx+1 < len(chapters) else len(text)
    content = text[start:end].strip()
    
    # Remove the duplicate title if it appears at the start of content
    content = re.sub(r'^' + re.escape(ch_title) + r'\s*', '', content)
    
    # Split content into paragraphs
    # Strategy: split at sentence boundaries and dialogue markers
    
    # First, normalize whitespace
    content = content.strip()
    
    # Split at: 。！？ followed by content (not just spaces)
    # Split at: …… (scene break)
    # Split at: " (dialogue start after non-quote text)
    
    # Add newlines at logical breaks
    # 1. After 。！？ when followed by Chinese character or quote
    content = re.sub(r'([。！？])(\s*)([\u4e00-\u9fff\u201c"])', r'\1\n\3', content)
    
    # 2. At scene breaks
    content = content.replace('……', '\n……\n')
    content = content.replace('....', '\n....\n')
    
    # 3. Before dialogue quotes (when preceded by non-quote)
    content = re.sub(r'([\u4e00-\u9fff。！？])\s*([\u201c"])', r'\1\n\2', content)
    
    # 4. After closing quotes when followed by narration
    content = re.sub(r'([\u201d"])\s*([\u4e00-\u9fff])', r'\1\n\2', content)
    
    # Clean up: remove empty lines, strip whitespace
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    # Remove pure "……" lines that are just scene breaks
    cleaned_lines = []
    for line in lines:
        if line == '……' or line == '....':
            cleaned_lines.append('')  # Empty line for scene break
        else:
            cleaned_lines.append(line)
    
    # Build chapter output
    chapter_text = '\n'.join(cleaned_lines)
    # Remove excessive blank lines
    chapter_text = re.sub(r'\n{3,}', '\n\n', chapter_text)
    
    output_parts.append(f'\n{ch_title}\n{chapter_text}')

# Join all chapters
result = '\n'.join(output_parts)
result = re.sub(r'\n{3,}', '\n\n', result)
result = result.strip()

# Save
out_path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\拆文库\我在风花雪月里等你\原文\原文.txt'
open(out_path, 'w', encoding='utf-8').write(result)

# Verify
ch_count = len(re.findall(r'^第\d+章\s+.+$', result, re.MULTILINE))
line_count = len(result.split('\n'))
chinese = sum(1 for c in result if '\u4e00' <= c <= '\u9fff')

print(f'章节数: {ch_count}')
print(f'总行数: {line_count}')
print(f'中文字数: {chinese}')

# Show first chapter
print('\n=== 第1章（前30行）===')
in_ch1 = False
line_num = 0
for line in result.split('\n'):
    if re.match(r'^第1章\s+', line):
        in_ch1 = True
    if in_ch1:
        if line.strip():
            print(line)
            line_num += 1
        if line_num >= 30:
            break
    if in_ch1 and re.match(r'^第2章\s+', line):
        break
