"""
对比阅读器服务器
用法: python tools/compare_server.py [端口号]
默认端口: 8900
"""
import os, sys, json, re, http.server, socketserver, urllib.parse, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(ROOT, 'projects')
VIEWER_HTML = os.path.join(ROOT, 'tools', 'compare_viewer.html')

def scan_books():
    books = []
    if not os.path.isdir(PROJECTS_DIR):
        return books
    for author in os.listdir(PROJECTS_DIR):
        author_dir = os.path.join(PROJECTS_DIR, author)
        if not os.path.isdir(author_dir) or author.startswith('.'):
            continue
        for book in os.listdir(author_dir):
            book_dir = os.path.join(author_dir, book)
            if not os.path.isdir(book_dir):
                continue
            rewrites_dir = os.path.join(book_dir, 'rewrites')
            if not os.path.isdir(rewrites_dir):
                continue
            for rewrite_name in os.listdir(rewrites_dir):
                rewrite_dir = os.path.join(rewrites_dir, rewrite_name)
                if not os.path.isdir(rewrite_dir):
                    continue
                src_ch = find_chapter_dir(book_dir)
                new_ch = find_chapter_dir(rewrite_dir)
                if src_ch and new_ch:
                    books.append({
                        'author': author,
                        'source_book': book,
                        'rewrite_book': rewrite_name,
                        'source_dir': book_dir,
                        'rewrite_dir': rewrite_dir,
                        'source_chapters_dir': src_ch,
                        'new_chapters_dir': new_ch,
                    })
    return books

def find_chapter_dir(base):
    for name in ['chapters', '_cache/chapters']:
        d = os.path.join(base, name)
        if os.path.isdir(d):
            if any(f.endswith('.txt') for f in os.listdir(d)):
                return d
    return None

def list_chapters(chapters_dir):
    chapters = []
    for f in os.listdir(chapters_dir):
        if f.endswith('.txt'):
            m = re.search(r'(\d+)', f)
            if m:
                chapters.append(int(m.group(1)))
    chapters.sort()
    return chapters

def read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def find_file(chapters_dir, num):
    for f in os.listdir(chapters_dir):
        if f.endswith('.txt'):
            m = re.search(r'(\d+)', f)
            if m and int(m.group(1)) == num:
                return os.path.join(chapters_dir, f)
    return None

def count_cn(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def compute_diff(src_text, new_text):
    src_paras = [p.strip() for p in src_text.split('\n') if p.strip()]
    new_paras = [p.strip() for p in new_text.split('\n') if p.strip()]
    m, n = len(src_paras), len(new_paras)
    if m * n > 500000:
        return _simple_diff(src_paras, new_paras)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if src_paras[i-1] == new_paras[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    r_src, r_new = [], []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and src_paras[i-1] == new_paras[j-1]:
            r_src.append({'text': src_paras[i-1], 'type': 'same'})
            r_new.append({'text': new_paras[j-1], 'type': 'same'})
            i -= 1; j -= 1
        elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
            r_new.append({'text': new_paras[j-1], 'type': 'added'})
            j -= 1
        else:
            r_src.append({'text': src_paras[i-1], 'type': 'removed'})
            i -= 1
    r_src.reverse(); r_new.reverse()
    return r_src, r_new

def _simple_diff(src_paras, new_paras):
    import difflib
    sm = difflib.SequenceMatcher(None, src_paras, new_paras)
    r_src, r_new = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                r_src.append({'text': src_paras[k], 'type': 'same'})
                r_new.append({'text': new_paras[k], 'type': 'same'})
        elif tag == 'replace':
            for k in range(i1, i2): r_src.append({'text': src_paras[k], 'type': 'removed'})
            for k in range(j1, j2): r_new.append({'text': new_paras[k], 'type': 'added'})
        elif tag == 'delete':
            for k in range(i1, i2): r_src.append({'text': src_paras[k], 'type': 'removed'})
        elif tag == 'insert':
            for k in range(j1, j2): r_new.append({'text': new_paras[k], 'type': 'added'})
    return r_src, r_new

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = dict(urllib.parse.parse_qsl(parsed.query))

            if path in ('/', '/index.html'):
                self._serve_html()
            elif path == '/api/books':
                self._json(scan_books())
            elif path == '/api/chapters':
                self._json({
                    'source_chapters': list_chapters(qs.get('source_dir', '')),
                    'new_chapters': list_chapters(qs.get('new_dir', '')),
                })
            elif path == '/api/diff':
                sd, nd, num = qs.get('source_dir',''), qs.get('new_dir',''), qs.get('num','')
                if not sd or not nd or not num:
                    self._json({'error': 'missing params'}); return
                sf = find_file(sd, int(num))
                nf = find_file(nd, int(num))
                if not sf or not nf:
                    self._json({'src':[],'new':[],'src_chars':0,'new_chars':0,'error':'not found'}); return
                src_full = read_text(sf)
                new_full = read_text(nf)
                # 提取标题
                src_title = ''
                new_title = ''
                src_m = re.match(r'^(第\d+章.*)\n', src_full)
                if src_m: src_title = src_m.group(1)
                new_m = re.match(r'^(第\d+章.*)\n', new_full)
                if new_m: new_title = new_m.group(1)
                # 去掉标题后计算diff
                st = re.sub(r'^第\d+章.*\n', '', src_full, count=1).strip()
                nt = re.sub(r'^第\d+章.*\n', '', new_full, count=1).strip()
                ds, dn = compute_diff(st, nt)
                self._json({'src':ds,'new':dn,'src_chars':count_cn(st),'new_chars':count_cn(nt),'src_title':src_title,'new_title':new_title})
            else:
                self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            try: self.send_error(500)
            except: pass

    def _serve_html(self):
        with open(VIEWER_HTML, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8900
    server = ThreadedHTTPServer(('0.0.0.0', port), Handler)
    print(f'对比阅读器已启动: http://127.0.0.1:{port}')
    print('按 Ctrl+C 停止')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
        server.server_close()
