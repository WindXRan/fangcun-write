import os
base = r'c:\Users\裴浩然\Desktop\AI网文项目\oh-novel-writer\projects'
for author in os.listdir(base):
    a_path = os.path.join(base, author)
    if not os.path.isdir(a_path): continue
    for book in os.listdir(a_path):
        ch_dir = os.path.join(a_path, book, '_cache', 'chapters')
        if not os.path.isdir(ch_dir): continue
        ch1 = os.path.join(ch_dir, '第1章.txt')
        if not os.path.exists(ch1): continue
        try:
            with open(ch1, encoding='utf-8') as f:
                first = f.readline().strip()
        except:
            first = '(read error)'
        n_ch = len([f for f in os.listdir(ch_dir) if f.endswith('.txt')])
        print(f'{author}/{book} ({n_ch}章): {first[:80]}')
