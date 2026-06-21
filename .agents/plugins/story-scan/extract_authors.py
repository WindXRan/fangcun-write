import json

data = json.load(open('data/latest_female_new_ranks.json', encoding='utf-8'))

def parse_reads(s):
    if not s:
        return 0
    s = str(s)
    if '万' in s:
        return float(s.replace('万', '')) * 10000
    if '亿' in s:
        return float(s.replace('亿', '')) * 100000000
    try:
        return float(s)
    except:
        return 0

authors = {}
for cat in data.get('categories', []):
    for book in cat.get('books', []):
        author = book.get('author', '')
        if not author:
            continue
        if author not in authors:
            authors[author] = {'books': [], 'total_reads': 0}
        authors[author]['books'].append({
            'title': book.get('title', ''),
            'reads': parse_reads(book.get('reads', '')),
            'url': book.get('url', '')
        })
        authors[author]['total_reads'] += parse_reads(book.get('reads', ''))

# Sort by book count first, then by total reads
multi = [(n, i) for n, i in authors.items() if len(i['books']) >= 2]
multi.sort(key=lambda x: (-len(x[1]['books']), -x[1]['total_reads']))

lines = []
lines.append('=== 多本上榜作者（值得蒸馏） ===\n')
for name, info in multi:
    reads_str = '{:.1f}万'.format(info['total_reads'] / 10000)
    lines.append('{} | {}本 | {} 总阅读'.format(name, len(info['books']), reads_str))
    for b in info['books']:
        br = '{:.1f}万'.format(b['reads'] / 10000) if b['reads'] >= 10000 else str(int(b['reads']))
        lines.append('  - {} ({})'.format(b['title'], br))

# Also list top single-book authors worth distilling
lines.append('\n=== 单本高阅读量作者（阅读量>50万，可考虑蒸馏） ===\n')
single = [(n, i) for n, i in authors.items() if len(i['books']) == 1 and i['total_reads'] > 500000]
single.sort(key=lambda x: -x[1]['total_reads'])
for name, info in single:
    reads_str = '{:.1f}万'.format(info['total_reads'] / 10000)
    lines.append('{} | {} | {}'.format(name, reads_str, info['books'][0]['title']))

with open('worth_distill.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('done')
