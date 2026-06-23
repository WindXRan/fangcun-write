import re

path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\knowledge\静山\我在风花雪月中等你\我在风花雪月中等你.txt'
text = open(path, encoding='utf-8').read()

print(f'源文件大小: {len(text)} 字符')

# Remove duplicate chapter titles
text = re.sub(r'(第\d+章\s+.+?)\s+\1', r'\1', text)

# Find chapters
ch_pattern = re.compile(r'(第\d+章\s+[^\n]+)')
ch_matches = list(ch_pattern.finditer(text))
print(f'找到 {len(ch_matches)} 个章节')

def split_paragraphs(content):
    """Split continuous text into paragraphs, preserving dialogue."""
    result = []
    i = 0
    in_quote = False
    
    while i < len(content):
        c = content[i]
        result.append(c)
        
        # Track quote state
        if c == '\u201c':  # "
            in_quote = True
        elif c == '\u201d':  # "
            in_quote = False
            # After closing quote, add newline if followed by Chinese char
            if i + 1 < len(content) and '\u4e00' <= content[i+1] <= '\u9fff':
                result.append('\n')
        elif c == '"':
            in_quote = not in_quote
            if not in_quote:
                # After closing quote, add newline if followed by Chinese char
                if i + 1 < len(content) and '\u4e00' <= content[i+1] <= '\u9fff':
                    result.append('\n')
        
        # Split at sentence endings ONLY when not in quotes
        if not in_quote:
            if c in '。！？':
                # Check if next char is Chinese char (possibly with space)
                if i + 1 < len(content):
                    next_char = content[i+1]
                    if next_char == ' ' and i + 2 < len(content) and '\u4e00' <= content[i+2] <= '\u9fff':
                        result.append('\n')
                    elif '\u4e00' <= next_char <= '\u9fff' and next_char not in '，、；：':
                        result.append('\n')
        
        # Scene breaks
        if c == '…' and i + 1 < len(content) and content[i+1] == '…':
            # This is part of ……
            pass
        elif c == '…' and (i == 0 or content[i-1] != '…'):
            # Single …, check if it's part of ……
            pass
        
        i += 1
    
    content = ''.join(result)
    
    # Handle …… scene breaks
    content = content.replace('……', '\n……\n')
    content = content.replace('....', '\n……\n')
    
    # Clean up
    lines = content.split('\n')
    cleaned = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned.append(line)
    
    return '\n'.join(cleaned)

# Process each chapter
output_parts = []
for idx, match in enumerate(ch_matches):
    ch_title = match.group(1).strip()
    start = match.end()
    end = ch_matches[idx+1].start() if idx+1 < len(ch_matches) else len(text)
    content = text[start:end].strip()
    
    # Remove duplicate title at start
    content = re.sub(r'^' + re.escape(ch_title) + r'\s*', '', content)
    
    # Split into paragraphs
    content = split_paragraphs(content)
    
    # Remove excessive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    output_parts.append(f'\n{ch_title}\n{content}')

# Join
result = '\n'.join(output_parts)
result = re.sub(r'\n{3,}', '\n\n', result)
result = result.strip()

# Save
out_path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\拆文库\我在风花雪月中等你\原文\原文.txt'
open(out_path, 'w', encoding='utf-8').write(result)

# Verify
ch_count = len(re.findall(r'^第\d+章\s+.+$', result, re.MULTILINE))
line_count = len(result.split('\n'))
chinese = sum(1 for c in result if '\u4e00' <= c <= '\u9fff')

print(f'章节数: {ch_count}')
print(f'总行数: {line_count}')
print(f'中文字数: {chinese}')

# Show first chapter
print('\n=== 第1章（前25行）===')
lines = result.split('\n')
in_ch1 = False
line_num = 0
for line in lines:
    if re.match(r'^第1章\s+', line):
        in_ch1 = True
    if in_ch1:
        if line.strip():
            print(line[:80] + ('...' if len(line) > 80 else ''))
            line_num += 1
        if line_num >= 25:
            break
    if in_ch1 and re.match(r'^第2章\s+', line):
        break
