import re

path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\knowledge\超级大坦克科比\我在风花雪月里等你\我在风花雪月里等你.txt'
text = open(path, encoding='utf-8').read()

# Get first chapter only for testing
ch1_match = re.search(r'(第1章.*?)(?=第2章)', text, re.DOTALL)
ch1 = ch1_match.group(1)

# Remove duplicate title
ch1 = re.sub(r'第1章 我说孤独，她说梦想\s*', '', ch1, count=1)

print('=== 原始文本前200字 ===')
print(ch1[:200])
print()

# Test splitting
# Method: insert \n after 。！？ when followed by Chinese char or space+Chinese char
result = re.sub(r'([。！？])\s*([\u4e00-\u9fff\u201c"])', r'\1\n\2', ch1)
result = re.sub(r'([\u201d"])\s*([\u4e00-\u9fff])', r'\1\n\2', result)
result = result.replace('……', '\n……\n')

print('=== 分段后前10行 ===')
lines = [l.strip() for l in result.split('\n') if l.strip()]
for i, line in enumerate(lines[:10]):
    print(f'{i+1}: {line[:60]}...' if len(line) > 60 else f'{i+1}: {line}')
