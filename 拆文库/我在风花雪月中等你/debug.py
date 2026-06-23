import re

path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\拆文库\我在风花雪月里等你\原文\原文.txt'
text = open(path, encoding='utf-8').read()

# Get first chapter
ch1_match = re.search(r'(第1章.*?)(?=第2章)', text, re.DOTALL)
if ch1_match:
    ch1 = ch1_match.group(1)
    print(f'第1章长度: {len(ch1)} 字符')
    print()
    print('=== 前300字符 ===')
    print(ch1[:300])
    print()
    print('=== 检查引号类型 ===')
    quotes_found = set()
    for c in ch1:
        if c in '\u201c\u201d\u0022\u0027':
            quotes_found.add(repr(c))
    print(f'引号类型: {quotes_found}')
    print()
    print('=== 检查句号后字符 ===')
    for m in re.finditer(r'。(.{1,2})', ch1[:500]):
        print(f'位置{m.start()}: 。后是 {repr(m.group(1))}')
