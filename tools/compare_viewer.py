"""
对比阅读器 - 调色盘版
用法: python tools/compare_viewer.py [端口号]
默认端口: 8900
"""
import os, sys, re, json, http.server, urllib.parse, difflib, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(ROOT, 'projects')

def scan_books():
    books = []
    if not os.path.isdir(PROJECTS_DIR): return books
    for author in os.listdir(PROJECTS_DIR):
        ad = os.path.join(PROJECTS_DIR, author)
        if not os.path.isdir(ad) or author.startswith('.'): continue
        for book in os.listdir(ad):
            bd = os.path.join(ad, book)
            if not os.path.isdir(bd): continue
            rd = os.path.join(bd, 'rewrites')
            if not os.path.isdir(rd): continue
            for rn in os.listdir(rd):
                rpd = os.path.join(rd, rn)
                if not os.path.isdir(rpd): continue
                sc = find_ch_dir(bd); nc = find_ch_dir(rpd)
                if sc and nc:
                    books.append({'author':author,'source_book':book,'rewrite_book':rn,'src_ch_dir':sc,'new_ch_dir':nc})
    return books

def find_ch_dir(base):
    for name in ['chapters', '_cache/chapters']:
        d = os.path.join(base, name)
        if os.path.isdir(d) and any(f.endswith('.txt') for f in os.listdir(d)): return d
    return None

def list_chs(d):
    chs = []
    for f in os.listdir(d):
        if f.endswith('.txt'):
            m = re.search(r'(\d+)', f)
            if m: chs.append(int(m.group(1)))
    chs.sort(); return chs

def find_file(d, num):
    for f in os.listdir(d):
        if f.endswith('.txt'):
            m = re.search(r'(\d+)', f)
            if m and int(m.group(1)) == num: return os.path.join(d, f)
    return None

def read_text(path):
    with open(path, encoding='utf-8') as f: return f.read()

def count_cn(t): return len(re.findall(r'[\u4e00-\u9fff]', t))

def strip_title(t):
    return re.sub(r'^第\d+章.*\n', '', t, count=1).strip()

def esc(t): return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def highlight_diff(src_line, new_line):
    """逐字对比，返回带高亮HTML的两行（限制长度避免卡顿）"""
    if len(src_line) > 300 or len(new_line) > 300:
        return esc(src_line), esc(new_line)
    sm = difflib.SequenceMatcher(None, src_line, new_line)
    src_parts, new_parts = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        src_seg = src_line[i1:i2]
        new_seg = new_line[j1:j2]
        if tag == 'equal':
            src_parts.append(f'<m>{esc(src_seg)}</m>')
            new_parts.append(f'<m>{esc(new_seg)}</m>')
        elif tag == 'replace':
            src_parts.append(f'<del>{esc(src_seg)}</del>')
            new_parts.append(f'<ins>{esc(new_seg)}</ins>')
        elif tag == 'delete':
            src_parts.append(f'<del>{esc(src_seg)}</del>')
        elif tag == 'insert':
            new_parts.append(f'<ins>{esc(new_seg)}</ins>')
    return ''.join(src_parts), ''.join(new_parts)

def compute_rows(src_text, new_text):
    """逐段对比，返回表格行数据"""
    sp = [p.strip() for p in src_text.split('\n') if p.strip()]
    np = [p.strip() for p in new_text.split('\n') if p.strip()]
    # 限制段落数避免卡顿
    if len(sp) > 500 or len(np) > 500:
        sp = sp[:500]; np = np[:500]
    sm = difflib.SequenceMatcher(None, sp, np)
    rows = []
    src_idx, new_idx = 0, 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2):
                src_idx += 1; new_idx += 1
                rows.append({'idx': len(rows)+1, 'src': sp[k], 'new': np[j1+(k-i1)], 'type': 'same', 'src_n': src_idx, 'new_n': new_idx})
        elif tag == 'replace':
            max_len = max(i2-i1, j2-j1)
            for k in range(max_len):
                s = sp[i1+k] if i1+k < i2 else ''
                n = np[j1+k] if j1+k < j2 else ''
                if s: src_idx += 1
                if n: new_idx += 1
                sh, nh = highlight_diff(s, n) if s and n else (esc(s), esc(n))
                rows.append({'idx': len(rows)+1, 'src_html': sh, 'new_html': nh, 'type': 'diff', 'src_n': src_idx if s else '', 'new_n': new_idx if n else ''})
        elif tag == 'delete':
            for k in range(i1, i2):
                src_idx += 1
                rows.append({'idx': len(rows)+1, 'src': sp[k], 'new': '', 'type': 'del', 'src_n': src_idx, 'new_n': ''})
        elif tag == 'insert':
            for k in range(j1, j2):
                new_idx += 1
                rows.append({'idx': len(rows)+1, 'src': '', 'new': np[k], 'type': 'add', 'src_n': '', 'new_n': new_idx})
    return rows

def calc_similarity(src_text, new_text):
    """计算相似度"""
    src_cn = re.findall(r'[\u4e00-\u9fff]', src_text)
    new_cn = re.findall(r'[\u4e00-\u9fff]', new_text)
    if not src_cn or not new_cn: return 0
    sm = difflib.SequenceMatcher(None, src_cn, new_cn)
    return round(sm.ratio() * 100, 1)

def ai_analyze(src_text, new_text, book_name, chapter):
    """调用AI分析仿写质量"""
    api_key = os.environ.get('API_KEY', '')
    api_base = os.environ.get('API_BASE_URL', 'https://api.deepseek.com')
    api_model = os.environ.get('API_MODEL', 'deepseek-chat')
    
    if not api_key:
        return {'error': '未配置API_KEY环境变量，无法调用AI分析'}
    
    # 截取文本避免过长
    src_sample = src_text[:3000] if len(src_text) > 3000 else src_text
    new_sample = new_text[:3000] if len(new_text) > 3000 else new_text
    
    prompt = f"""请以资深网文编辑的身份，对下面两份文本进行对比分析。总字数控制在800字以内，不要逐章罗列，抓核心差异。

【版本A·源文】
{src_sample}

【版本B·仿写】
{new_sample}

请从以下维度分析：

1. **核心差异**（2-3句话）：版本B和版本A最大的不同是什么？一句话说清楚。
2. **质量判断**：哪个版本阅读体验更好？好在哪？各自的硬伤是什么？
3. **抄袭风险**：两版是否存在情节骨架/关键台词/人设框架的雷同？给出风险等级（低/中/高），若有雷同指出具体哪里像。
4. **改进建议**：如果要降低抄袭风险，最需要改的1-2处是什么？

直接给出分析，不要废话。"""

    try:
        url = f"{api_base}/v1/chat/completions"
        data = json.dumps({
            "model": api_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1500
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            return {'content': content}
    except Exception as e:
        return {'error': f'AI分析失败: {str(e)}'}

def build_html(books, book_idx, chapter):
    b = books[book_idx]
    src_chs = list_chs(b['src_ch_dir'])
    new_chs = list_chs(b['new_ch_dir'])
    all_chs = sorted(set(src_chs) | set(new_chs))

    sf = find_file(b['src_ch_dir'], chapter)
    nf = find_file(b['new_ch_dir'], chapter)
    rows = []
    src_chars, new_chars, similarity = 0, 0, 0
    same_count, diff_count, add_count, del_count = 0, 0, 0, 0
    if sf and nf:
        st = strip_title(read_text(sf))
        nt = strip_title(read_text(nf))
        src_chars = count_cn(st); new_chars = count_cn(nt)
        similarity = calc_similarity(st, nt)
        rows = compute_rows(st, nt)
        for r in rows:
            if r['type'] == 'same': same_count += 1
            elif r['type'] == 'diff': diff_count += 1
            elif r['type'] == 'add': add_count += 1
            elif r['type'] == 'del': del_count += 1

    ch_options = ''.join(
        f'<option value="{c}" {"selected" if c==chapter else ""}>第{c}章</option>'
        for c in all_chs
    )

    dc = new_chars - src_chars
    dc_s = f'+{dc}' if dc >= 0 else str(dc)

    # 表格行
    table_rows = ''
    for r in rows:
        tp = r['type']
        cls = {'same':'row-same','diff':'row-diff','add':'row-add','del':'row-del'}[tp]
        src_html = r.get('src_html', esc(r.get('src','')))
        new_html = r.get('new_html', esc(r.get('new','')))
        table_rows += f'''<tr class="{cls}">
          <td class="n">{r['idx']}</td>
          <td class="sn">{r['src_n']}</td>
          <td class="src">{src_html}</td>
          <td class="sn">{r['new_n']}</td>
          <td class="new">{new_html}</td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{esc(b["source_book"])} 第{chapter}章 - 调色盘</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#fafaf5;--fg:#fff;--border:#d4d0c8;--text:#222;--dim:#888;
  --same-bg:#fff;--diff-bg:#fff8e1;--add-bg:#e8f5e9;--del-bg:#ffebee;
  --match:#1565c0;--ins:#2e7d32;--del:#c62828;
  --font:13px;--lh:1.8;
}}
body{{background:var(--bg);color:var(--text);font-family:"PingFang SC","Microsoft YaHei",sans-serif}}

/* 顶栏 */
.top{{background:var(--fg);border-bottom:2px solid var(--border);padding:8px 16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10;flex-wrap:wrap}}
.top select{{border:1px solid var(--border);border-radius:3px;padding:4px 6px;font-size:12px;background:var(--fg)}}
.top b{{font-size:14px;white-space:nowrap}}
.spacer{{flex:1}}
.btn{{border:1px solid var(--border);border-radius:3px;padding:4px 12px;cursor:pointer;background:var(--fg);font-size:12px;color:var(--text)}}
.btn:hover{{background:var(--bg)}}
.btn.p{{background:#1565c0;color:#fff;border-color:#1565c0}}
.btn.p:hover{{filter:brightness(1.1)}}
.btn:disabled{{opacity:.3;cursor:default}}
.mbtn{{border:1px solid var(--border);border-radius:3px;padding:3px 8px;cursor:pointer;background:var(--fg);font-size:11px;color:var(--dim)}}
.mbtn.on{{background:#1565c0;color:#fff;border-color:#1565c0}}

/* 统计条 */
.stats-bar{{background:var(--fg);border-bottom:1px solid var(--border);padding:6px 16px;display:flex;gap:20px;flex-wrap:wrap;font-size:12px}}
.stats-bar .item{{display:flex;align-items:center;gap:4px}}
.stats-bar .item b{{font-weight:600}}
.stats-bar .sim{{font-size:16px;font-weight:700}}
.stats-bar .sim.high{{color:#2e7d32}}
.stats-bar .sim.mid{{color:#f57f17}}
.stats-bar .sim.low{{color:#c62828}}

/* 图例 */
.legend{{background:var(--fg);border-bottom:1px solid var(--border);padding:4px 16px;display:flex;gap:16px;font-size:11px;color:var(--dim)}}
.legend span{{display:flex;align-items:center;gap:4px}}
.legend i{{display:inline-block;width:14px;height:14px;border-radius:2px;vertical-align:middle}}

/* 表格 */
.table-wrap{{overflow-x:auto;padding:0}}
table{{width:100%;border-collapse:collapse;font-size:var(--font);line-height:var(--lh)}}
thead{{position:sticky;top:80px;z-index:5}}
thead th{{background:#e8e4dc;border:1px solid var(--border);padding:6px 8px;font-size:11px;font-weight:600;text-align:center;color:#555;white-space:nowrap}}
tbody td{{border:1px solid var(--border);padding:6px 10px;vertical-align:top;word-break:break-all}}
td.n{{width:36px;text-align:center;color:var(--dim);font-size:11px;background:var(--fg);position:sticky;left:0;z-index:2}}
td.sn{{width:30px;text-align:center;color:#aaa;font-size:10px;background:var(--fg)}}
td.src{{width:calc(50% - 66px)}}
td.new{{width:calc(50% - 66px)}}
tr.row-same td{{background:var(--same-bg)}}
tr.row-diff td.src{{background:var(--diff-bg)}}
tr.row-diff td.new{{background:var(--diff-bg)}}
tr.row-add td{{background:var(--add-bg)}}
tr.row-add td.src{{background:var(--fg);color:#ccc}}
tr.row-del td{{background:var(--del-bg)}}
tr.row-del td.new{{background:var(--fg);color:#ccc}}
tr:hover td{{filter:brightness(0.97)}}

/* 高亮标记 */
m{{color:var(--match);font-style:normal;border-bottom:1px dashed var(--match)}}
del{{color:var(--del);text-decoration:line-through;background:rgba(198,40,40,.08);font-style:normal}}
ins{{color:var(--ins);text-decoration:none;background:rgba(46,125,50,.08);font-style:normal;font-weight:600}}

/* 空状态 */
.empty{{text-align:center;padding:60px;color:var(--dim);font-size:14px}}

/* 调色盘面板 */
.palette{{position:fixed;top:0;right:-320px;width:320px;height:100vh;background:var(--fg);border-left:1px solid var(--border);box-shadow:-4px 0 12px rgba(0,0,0,.08);z-index:30;transition:right .2s;overflow-y:auto}}
.palette.show{{right:0}}
.p-hd{{padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center}}
.p-hd h3{{font-size:13px;flex:1}}
.p-hd button{{background:none;border:none;cursor:pointer;font-size:18px;color:var(--dim)}}
.p-body{{padding:12px 14px}}
.p-body label{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--dim);margin-bottom:8px}}
.p-body input[type=range]{{flex:1;accent-color:#1565c0}}
.p-body .val{{width:28px;text-align:right;font-size:11px}}
.p-body h4{{font-size:12px;color:var(--dim);margin:10px 0 6px}}
.themes{{display:flex;gap:5px;flex-wrap:wrap}}
.themes span{{width:26px;height:26px;border-radius:3px;cursor:pointer;border:2px solid transparent}}
.themes span:hover,.themes span.on{{border-color:var(--text)}}

.fab{{position:fixed;bottom:20px;right:20px;width:40px;height:40px;border-radius:50%;background:#1565c0;color:#fff;border:none;cursor:pointer;font-size:16px;box-shadow:0 2px 8px rgba(0,0,0,.15);z-index:30}}
.fab:hover{{filter:brightness(1.1)}}
.fab2{{position:fixed;bottom:70px;right:20px;width:40px;height:40px;border-radius:50%;background:#9c27b0;color:#fff;border:none;cursor:pointer;font-size:16px;box-shadow:0 2px 8px rgba(0,0,0,.15);z-index:30}}
.fab2:hover{{filter:brightness(1.1)}}
.fab2:disabled{{opacity:.5;cursor:default}}

/* AI分析面板 */
.ai-panel{{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:40;display:none;align-items:center;justify-content:center}}
.ai-panel.show{{display:flex}}
.ai-box{{background:var(--fg);border-radius:8px;width:90%;max-width:700px;max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.2)}}
.ai-hd{{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center}}
.ai-hd h3{{font-size:15px;flex:1;color:#9c27b0}}
.ai-hd button{{background:none;border:none;cursor:pointer;font-size:20px;color:var(--dim)}}
.ai-body{{padding:18px;line-height:1.8;font-size:14px;white-space:pre-wrap}}
.ai-body h4{{color:#9c27b0;margin:12px 0 4px;font-size:14px}}
.ai-loading{{text-align:center;padding:40px;color:var(--dim)}}
.ai-error{{color:#c62828;padding:10px;background:#ffebee;border-radius:4px}}

/* 键盘提示 */
.kbd{{position:fixed;bottom:20px;left:20px;font-size:11px;color:var(--dim);background:var(--fg);border:1px solid var(--border);border-radius:4px;padding:4px 8px}}
</style>
</head>
<body>
<div class="top">
  <select onchange="location.href='/?book='+this.value+'&ch={chapter}'">{ch_options}</select>
  <b>{esc(b["source_book"])} → {esc(b["rewrite_book"])} · 第{chapter}章</b>
  <div class="spacer"></div>
  <button class="mbtn on" id="m-both" onclick="setV('both')">双栏</button>
  <button class="mbtn" id="m-a" onclick="setV('a')">只看A</button>
  <button class="mbtn" id="m-b" onclick="setV('b')">只看B</button>
  <button class="btn p" onclick="go(current-1)">← 上一章</button>
  <select id="ch-sel" onchange="go(parseInt(this.value))">{ch_options}</select>
  <button class="btn p" onclick="go(current+1)">下一章 →</button>
</div>
<div class="stats-bar">
  <div class="item">相似度: <b class="sim {"high" if similarity>=70 else "mid" if similarity>=40 else "low"}">{similarity}%</b></div>
  <div class="item">A字数: <b>{src_chars}</b></div>
  <div class="item">B字数: <b>{new_chars}</b></div>
  <div class="item">差: <b>{dc_s}</b></div>
  <div class="item">相同段: <b>{same_count}</b></div>
  <div class="item">改写段: <b>{diff_count}</b></div>
  <div class="item">新增段: <b>{add_count}</b></div>
  <div class="item">删除段: <b>{del_count}</b></div>
</div>
<div class="legend">
  <span><i style="background:#1565c0"></i> 相同文字</span>
  <span><i style="background:#c62828"></i> A独有/改前</span>
  <span><i style="background:#2e7d32"></i> B独有/改后</span>
  <span><i style="background:var(--diff-bg)"></i> 改写段落</span>
  <span><i style="background:var(--add-bg)"></i> 新增段落</span>
  <span><i style="background:var(--del-bg)"></i> 删除段落</span>
</div>
<div class="table-wrap">
  <table id="tbl">
    <thead><tr>
      <th>#</th><th>A</th><th>源文 (A)</th><th>B</th><th>新文 (B)</th>
    </tr></thead>
    <tbody>{table_rows if table_rows else '<tr><td colspan="5" class="empty">无数据</td></tr>'}</tbody>
  </table>
</div>
<button class="fab" onclick="toggleP()" title="设置">⚙</button>
<button class="fab2" onclick="runAI()" id="ai-btn" title="AI分析">🤖</button>
<div class="ai-panel" id="ai-panel">
  <div class="ai-box">
    <div class="ai-hd"><h3>AI 分析报告</h3><button onclick="closeAI()">×</button></div>
    <div class="ai-body" id="ai-body">点击分析按钮开始...</div>
  </div>
</div>
<div class="palette" id="palette">
  <div class="p-hd"><h3>阅读设置</h3><button onclick="toggleP()">×</button></div>
  <div class="p-body">
    <label>字号 <input type="range" min="11" max="20" value="13" oninput="setF(this.value)"><span class="val" id="v-fs">13</span></label>
    <label>行高 <input type="range" min="1.4" max="2.5" step="0.1" value="1.8" oninput="setL(this.value)"><span class="val" id="v-lh">1.8</span></label>
    <h4>主题</h4>
    <div class="themes" id="themes"></div>
  </div>
</div>
<div class="kbd">← → 翻章</div>
<script>
var current={chapter};
var allChs={json.dumps(all_chs)};
var bookIdx={book_idx};

function go(n){{
  if(n<allChs[0])n=allChs[0];
  if(n>allChs[allChs.length-1])n=allChs[allChs.length-1];
  location.href='/?book='+bookIdx+'&ch='+n;
}}

function setV(m){{
  var tbl=document.getElementById('tbl');
  var srcCol=document.querySelectorAll('.src,.sn:nth-child(2),th:nth-child(2),th:nth-child(3)');
  var newCol=document.querySelectorAll('.new,.sn:nth-child(4),th:nth-child(4),th:nth-child(5)');
  document.getElementById('m-both').className='mbtn'+(m==='both'?' on':'');
  document.getElementById('m-a').className='mbtn'+(m==='a'?' on':'');
  document.getElementById('m-b').className='mbtn'+(m==='b'?' on':'');
  srcCol.forEach(function(el){{el.style.display=''}});
  newCol.forEach(function(el){{el.style.display=''}});
  if(m==='a')newCol.forEach(function(el){{el.style.display='none'}});
  if(m==='b')srcCol.forEach(function(el){{el.style.display='none'}});
}}

document.addEventListener('keydown',function(e){{
  if(e.target.tagName==='SELECT'||e.target.tagName==='INPUT')return;
  if(e.key==='ArrowLeft')go(current-1);
  if(e.key==='ArrowRight')go(current+1);
}});

var themes=[
  {{n:'默认',bg:'#fafaf5',fg:'#fff',bd:'#d4d0c8',tx:'#222'}},
  {{n:'纯白',bg:'#f8f8f8',fg:'#fff',bd:'#ddd',tx:'#111'}},
  {{n:'暗黑',bg:'#1a1a2e',fg:'#16213e',bd:'#0f3460',tx:'#e0e0e0'}},
  {{n:'护眼',bg:'#fdf6e3',fg:'#fffdf5',bd:'#e8dcc8',tx:'#333'}},
  {{n:'淡蓝',bg:'#eef5fb',fg:'#fff',bd:'#c8dae8',tx:'#2c3e50'}},
  {{n:'豆绿',bg:'#e8f0e4',fg:'#fcfef8',bd:'#c4d4b8',tx:'#2d3a28'}},
];
var thDiv=document.getElementById('themes');
themes.forEach(function(t,i){{
  var s=document.createElement('span');
  s.style.background=t.bg;s.title=t.n;
  if(i===0)s.className='on';
  s.onclick=function(){{
    var r=document.documentElement.style;
    r.setProperty('--bg',t.bg);r.setProperty('--fg',t.fg);
    r.setProperty('--border',t.bd);r.setProperty('--text',t.tx);
    thDiv.querySelectorAll('span').forEach(function(x){{x.className=''}});
    s.className='on';
  }};
  thDiv.appendChild(s);
}});

function setF(v){{document.documentElement.style.setProperty('--font',v+'px');document.getElementById('v-fs').textContent=v}}
function setL(v){{document.documentElement.style.setProperty('--lh',v);document.getElementById('v-lh').textContent=v}}
function toggleP(){{document.getElementById('palette').classList.toggle('show')}}

function runAI(){{
  var btn=document.getElementById('ai-btn');
  var panel=document.getElementById('ai-panel');
  var body=document.getElementById('ai-body');
  btn.disabled=true;
  panel.classList.add('show');
  body.innerHTML='<div class="ai-loading">AI 分析中，请稍候...</div>';
  fetch('/api/analyze?book='+bookIdx+'&ch='+current)
    .then(function(r){{return r.json()}})
    .then(function(d){{
      if(d.error){{
        body.innerHTML='<div class="ai-error">'+d.error+'</div>';
      }} else {{
        var html=d.content.replace(/\*\*(.*?)\*\*/g,'<b>$1</b>');
        html=html.replace(/\n/g,'<br>');
        body.innerHTML=html;
      }}
      btn.disabled=false;
    }})
    .catch(function(e){{
      body.innerHTML='<div class="ai-error">请求失败: '+e.message+'</div>';
      btn.disabled=false;
    }});
}}

function closeAI(){{
  document.getElementById('ai-panel').classList.remove('show');
}}
</script>
</body>
</html>'''

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = dict(urllib.parse.parse_qsl(parsed.query))
        
        if path == '/api/analyze':
            self.handle_analyze(qs)
            return
        
        if path == '/api/batch-analyze':
            self.handle_batch(qs)
            return
        
        book_idx = int(qs.get('book', 0))
        chapter = int(qs.get('ch', 1))
        if book_idx >= len(self.books): book_idx = 0
        if book_idx < 0: book_idx = 0
        html = build_html(self.books, book_idx, chapter).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html)))
        self.end_headers()
        self.wfile.write(html)
    
    def handle_analyze(self, qs):
        book_idx = int(qs.get('book', 0))
        chapter = int(qs.get('ch', 1))
        if book_idx >= len(self.books): book_idx = 0
        if book_idx < 0: book_idx = 0
        
        b = self.books[book_idx]
        sf = find_file(b['src_ch_dir'], chapter)
        nf = find_file(b['new_ch_dir'], chapter)
        
        if not sf or not nf:
            result = {'error': '未找到章节文件'}
        else:
            st = strip_title(read_text(sf))
            nt = strip_title(read_text(nf))
            result = ai_analyze(st, nt, b['source_book'], chapter)
        
        data = json.dumps(result, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)
    
    def handle_batch(self, qs):
        """批量分析多章并生成prompt优化建议"""
        book_idx = int(qs.get('book', 0))
        start = int(qs.get('start', 1))
        end = int(qs.get('end', 3))
        if book_idx >= len(self.books): book_idx = 0
        if book_idx < 0: book_idx = 0
        
        b = self.books[book_idx]
        src_chs = list_chs(b['src_ch_dir'])
        new_chs = list_chs(b['new_ch_dir'])
        common = sorted(set(src_chs) & set(new_chs))
        chapters = [c for c in common if start <= c <= end][:10]
        
        results = []
        for ch in chapters:
            sf = find_file(b['src_ch_dir'], ch)
            nf = find_file(b['new_ch_dir'], ch)
            if sf and nf:
                st = strip_title(read_text(sf))
                nt = strip_title(read_text(nf))
                # 简单统计
                src_cn = count_cn(st)
                new_cn = count_cn(nt)
                sim = calc_similarity(st, nt)
                results.append({
                    'chapter': ch,
                    'src_chars': src_cn,
                    'new_chars': new_cn,
                    'similarity': sim
                })
        
        data = json.dumps({'chapters': results}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8900
    books = scan_books()
    if not books: print('未找到可对比的书籍'); sys.exit(1)
    Handler.books = books
    server = http.server.HTTPServer(('0.0.0.0', port), Handler)
    print(f'调色盘: http://127.0.0.1:{port}')
    try: server.serve_forever()
    except KeyboardInterrupt: print('\n已停止')
