"""
编辑反馈工具
先生成对比文件，再把内容发给AI分析
用法: python tools/ai_feedback.py <书名> <起始章> <结束章>
"""
import os, sys, subprocess, urllib.request, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(ROOT, 'projects')

API_KEY = os.environ.get('API_KEY', 'sk-db692f2841ee47c1b2afec0a0cb016f5')
API_BASE = os.environ.get('API_BASE_URL', 'https://api.deepseek.com')
API_MODEL = os.environ.get('API_MODEL', 'deepseek-chat')

def call_ai(prompt, max_tokens=2000):
    url = f"{API_BASE}/v1/chat/completions"
    data = json.dumps({"model":API_MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":max_tokens}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type','application/json')
    req.add_header('Authorization',f'Bearer {API_KEY}')
    with urllib.request.urlopen(req,timeout=90) as resp:
        return json.loads(resp.read().decode('utf-8'))['choices'][0]['message']['content']

def main():
    if len(sys.argv) < 4:
        print('用法: python tools/ai_feedback.py <书名> <起始章> <结束章>')
        return

    book_name, start, end = sys.argv[1], sys.argv[2], sys.argv[3]

    # 1. 找到compare目录
    compare_dir = None
    for author in os.listdir(PROJECTS_DIR):
        ad = os.path.join(PROJECTS_DIR, author)
        if not os.path.isdir(ad) or author.startswith('.'): continue
        for book in os.listdir(ad):
            if book_name not in book: continue
            bd = os.path.join(ad, book)
            for rn in os.listdir(os.path.join(bd, 'rewrites')):
                rpd = os.path.join(bd, 'rewrites', rn)
                cd = os.path.join(rpd, 'compare')
                if os.path.isdir(cd):
                    compare_dir = cd
                    break
            if compare_dir: break
        if compare_dir: break

    if not compare_dir:
        print(f'未找到compare目录，请先运行: python .agents/skills/story-compare/compare.py {book_name} {start} {end}')
        return

    # 2. 找到AI分析文件
    ai_file = os.path.join(compare_dir, f'对比_{start}-{end}_AI分析.md')
    if not os.path.exists(ai_file):
        print(f'未找到: {ai_file}')
        print(f'请先运行: python .agents/skills/story-compare/compare.py {book_name} {start} {end}')
        return

    # 3. 读取文件内容
    with open(ai_file, encoding='utf-8') as f:
        content = f.read()

    # 4. 直接发给AI
    print('发送给AI分析...')
    result = call_ai(content)

    # 5. 保存反馈
    feedback_file = os.path.join(compare_dir, f'反馈_{start}-{end}.md')
    with open(feedback_file, 'w', encoding='utf-8') as f:
        f.write(f'# 编辑反馈（第{start}-{end}章）\n\n')
        f.write(result)
    print(f'已保存: {feedback_file}')
    print()
    print(result.encode('gbk', errors='replace').decode('gbk'))

if __name__ == '__main__':
    main()
