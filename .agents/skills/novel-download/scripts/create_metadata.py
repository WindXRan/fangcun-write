import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')

cache_dir = r'C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\projects\闻栖\将门有朵病娇花\_cache'
source_file = os.path.join(cache_dir, '春深锁惊鸿.txt')

with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 创建 _header.txt
header_lines = [
    '书名：春深锁惊鸿',
    '作者：暴躁123',
    'book_id=7621419029625834521',
    '状态：完结',
    '评分：7.4',
    '字数：234701',
    '章节：116',
    '分类：古风世情',
    '标签：古代言情|将军|大小姐|双洁',
    '',
    '简介：',
    '(少年纨绔子弟vs命短娇弱美人)',
    '京城人人皆知，镇北将军府嫡子沈惊鸿是个混不吝的纨绔。',
]
with open(os.path.join(cache_dir, '_header.txt'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(header_lines))
print('Created _header.txt')

# 2. 创建 _toc.txt
matches = list(re.finditer(r'(第\d+章[^\n]*)', content))
toc = '\n'.join(m.group() for m in matches)
with open(os.path.join(cache_dir, '_toc.txt'), 'w', encoding='utf-8') as f:
    f.write(toc)
print(f'Created _toc.txt ({len(matches)} chapters)')
