"""AI网文小说项目 - 书库+阅读+对比网站"""
import os
import json
import re
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"
BOOK_LIBRARY_FILE = ROOT_DIR / "book_library.json"


def load_book_library():
    """加载书库索引"""
    if BOOK_LIBRARY_FILE.exists():
        with open(BOOK_LIBRARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"books": []}


def get_book_content(file_path, chapter=None):
    """读取书籍内容"""
    try:
        full_path = ROOT_DIR / file_path
        if not full_path.exists():
            return None
        
        content = full_path.read_text(encoding='utf-8')
        
        if chapter:
            # 提取指定章节
            pattern = rf'第{chapter}章.*?(?=第{chapter+1}章|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(0)
        
        return content
    except Exception as e:
        return None


def split_chapters(content):
    """将内容拆分为章节"""
    chapters = []
    pattern = r'(第\d+章[^\n]*)'
    parts = re.split(pattern, content)
    
    i = 1
    while i < len(parts):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        chapters.append({
            "title": title,
            "content": body,
            "char_count": len(re.sub(r'\s', '', body))
        })
        i += 2
    
    return chapters


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页 - 书库"""
    library = load_book_library()
    return render_template('index.html', books=library.get('books', []))


@app.route('/book/<path:file_path>')
def book_reader(file_path):
    """书籍阅读器"""
    content = get_book_content(file_path)
    if content is None:
        return "书籍不存在", 404
    
    chapters = split_chapters(content)
    return render_template('reader.html', 
                         file_path=file_path,
                         chapters=chapters)


@app.route('/compare')
def compare():
    """对比阅读器"""
    library = load_book_library()
    return render_template('compare.html', books=library.get('books', []))


@app.route('/api/books')
def api_books():
    """API: 获取书库列表"""
    library = load_book_library()
    return jsonify(library.get('books', []))


@app.route('/api/search')
def api_search():
    """API: 搜索书籍"""
    query = request.args.get('q', '')
    genre = request.args.get('genre', '')
    
    library = load_book_library()
    books = library.get('books', [])
    
    if query:
        books = [b for b in books if query.lower() in b['title'].lower() 
                 or query.lower() in b.get('author', '').lower()
                 or query.lower() in b.get('synopsis', '').lower()]
    
    if genre:
        books = [b for b in books if genre in b.get('genre', '')]
    
    return jsonify(books)


@app.route('/api/chapters')
def api_chapters():
    """API: 获取章节列表"""
    file_path = request.args.get('file', '')
    content = get_book_content(file_path)
    
    if content is None:
        return jsonify([])
    
    chapters = split_chapters(content)
    return jsonify([{"title": c["title"], "char_count": c["char_count"]} 
                    for c in chapters])


@app.route('/api/content')
def api_content():
    """API: 获取章节内容"""
    file_path = request.args.get('file', '')
    chapter = request.args.get('chapter', type=int)
    
    content = get_book_content(file_path, chapter)
    if content is None:
        return jsonify({"error": "内容不存在"}), 404
    
    return jsonify({"content": content})


@app.route('/scan')
def scan_page():
    """扫描页面"""
    return render_template('scan.html')


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API: 扫描书库"""
    from book_library import scan_library, save_library_index
    
    projects_dir = request.json.get('dir', 'projects')
    books = scan_library(str(ROOT_DIR / projects_dir))
    index = save_library_index(books, str(BOOK_LIBRARY_FILE))
    
    return jsonify({
        "total_books": index["total_books"],
        "total_chars": index["total_chars"],
        "genres": index.get("genres", {})
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
