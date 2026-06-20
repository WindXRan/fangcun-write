"""AI网文小说项目 - 书库+阅读+对比+排行榜网站"""
import os
import json
import re
import sys
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect

SKILL_DIR = Path(__file__).parent
ROOT_DIR = SKILL_DIR.parent.parent.parent  # 项目根目录
PROJECTS_DIR = ROOT_DIR / "projects"
BOOK_LIBRARY_FILE = SKILL_DIR / "data" / "book_library.json"
SCAN_DATA_DIR = SKILL_DIR.parent / "story-scan"
NOVEL_DOWNLOAD_DIR = SKILL_DIR.parent / "novel-download"  # 下载器目录

# 添加 tools 目录到 sys.path
sys.path.insert(0, str(SKILL_DIR / "tools"))

app = Flask(__name__,
            template_folder=str(SKILL_DIR / "templates"),
            static_folder=str(SKILL_DIR / "static"))


def load_book_library():
    if BOOK_LIBRARY_FILE.exists():
        with open(BOOK_LIBRARY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"books": []}


def read_file(path):
    try:
        p = Path(path) if os.path.isabs(path) else ROOT_DIR / path
        if not p.exists():
            return None
        return p.read_text(encoding='utf-8')
    except:
        return None


def split_chapters(content):
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


def get_version_chapters(book, version_idx=0):
    """获取指定版本的章节列表"""
    versions = book.get("versions", [])
    if not versions:
        # 兼容旧格式：单文件
        content = read_file(book.get("file", ""))
        if content:
            return split_chapters(content)
        return []

    ver = versions[version_idx] if version_idx < len(versions) else versions[0]

    # 单文件版本
    if ver.get("file"):
        content = read_file(ver["file"])
        if content:
            return split_chapters(content)
        return []

    # 多章版本
    if ver.get("chapters"):
        result = []
        for ch in ver["chapters"]:
            content = read_file(ch["file"])
            if content:
                result.append({
                    "title": ch["name"],
                    "content": content,
                    "char_count": len(re.sub(r'\s', '', content)),
                })
        return result

    return []


# ==================== 路由 ====================

@app.route('/')
def index():
    library = load_book_library()
    return render_template('index.html', books=library.get('books', []))


@app.route('/book/<int:book_idx>')
def book_reader(book_idx):
    """阅读器 - 按索引访问书"""
    library = load_book_library()
    books = library.get('books', [])
    if book_idx < 0 or book_idx >= len(books):
        return "书籍不存在", 404

    book = books[book_idx]
    versions = book.get("versions", [])

    # 版本信息
    ver_list = []
    for i, v in enumerate(versions):
        label = v.get("name", f"版本{i+1}")
        vtype = v.get("type", "unknown")
        ver_list.append({"idx": i, "name": label, "type": vtype})

    # 默认加载第一个版本的章节
    chapters = get_version_chapters(book, 0)

    return render_template('reader.html',
                         book_idx=book_idx,
                         book=book,
                         versions=ver_list,
                         chapters=chapters)


@app.route('/api/version_chapters')
def api_version_chapters():
    """API: 获取指定版本的章节"""
    book_idx = request.args.get('book_idx', type=int, default=0)
    ver_idx = request.args.get('ver_idx', type=int, default=0)

    library = load_book_library()
    books = library.get('books', [])
    if book_idx < 0 or book_idx >= len(books):
        return jsonify({"error": "书不存在"}), 404

    chapters = get_version_chapters(books[book_idx], ver_idx)
    return jsonify(chapters)


@app.route('/cover/<path:filepath>')
def serve_cover(filepath):
    return send_from_directory(ROOT_DIR, filepath)


# 排行榜数据路由（排行榜页面用相对路径 data/ 和 api/ 读数据）
@app.route('/data/<path:filepath>')
def serve_scan_data(filepath):
    return send_from_directory(str(SCAN_DATA_DIR / "data"), filepath)


@app.route('/api/latest/<path:filepath>')
def serve_scan_api(filepath):
    return send_from_directory(str(SCAN_DATA_DIR / "api" / "latest"), filepath)


# ── 排行榜 ──

@app.route('/ranks/')
def ranks_index():
    return redirect('/ranks/index.html')

@app.route('/ranks/<path:filepath>')
def serve_ranks(filepath):
    return send_from_directory(str(SKILL_DIR / "static" / "ranks"), filepath)


@app.route('/ranks/data/<path:filepath>')
def serve_ranks_data(filepath):
    return send_from_directory(str(SCAN_DATA_DIR / "data"), filepath)


@app.route('/ranks/api/<path:filepath>')
def serve_ranks_api(filepath):
    return send_from_directory(str(SCAN_DATA_DIR / "api"), filepath)


@app.route('/compare')
def compare():
    library = load_book_library()
    return render_template('compare.html', books=library.get('books', []))


@app.route('/api/books')
def api_books():
    library = load_book_library()
    return jsonify(library.get('books', []))


@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    genre = request.args.get('genre', '')
    library = load_book_library()
    books = library.get('books', [])
    if query:
        q = query.lower()
        books = [b for b in books if q in b['title'].lower()
                 or q in b.get('author', '').lower()
                 or q in b.get('synopsis', '').lower()]
    if genre:
        books = [b for b in books if genre in b.get('genre', '')]
    return jsonify(books)


@app.route('/api/chapters')
def api_chapters():
    """API: 获取书籍的章节列表"""
    file = request.args.get('file', '')
    if not file:
        return jsonify([])
    
    content = read_file(file)
    if not content:
        return jsonify([])
    
    chapters = split_chapters(content)
    return jsonify(chapters)


@app.route('/api/content')
def api_content():
    """API: 获取指定章节内容"""
    file = request.args.get('file', '')
    chapter = request.args.get('chapter', type=int, default=0)
    
    if not file:
        return jsonify({"content": ""})
    
    content = read_file(file)
    if not content:
        return jsonify({"content": ""})
    
    chapters = split_chapters(content)
    if chapter < 1 or chapter > len(chapters):
        return jsonify({"content": ""})
    
    return jsonify({"content": chapters[chapter - 1]["content"]})


@app.route('/scan')
def scan_page():
    return render_template('scan.html')


@app.route('/api/scan', methods=['POST'])
def api_scan():
    from book_library import scan_library, save_library_index

    projects_dir = request.json.get('dir', 'projects')
    books = scan_library(str(ROOT_DIR / projects_dir))
    index = save_library_index(books, str(BOOK_LIBRARY_FILE))

    return jsonify({
        "total_books": index["total_books"],
        "total_chars": index["total_chars"],
        "genres": index.get("genres", {})
    })


# ── 排行榜（大池子） ──

@app.route('/api/pools')
def api_pools_list():
    """返回可用的排行榜列表"""
    import glob
    data_dir = SCAN_DATA_DIR / "data"
    
    pools = []
    seen_types = set()
    
    # 全榜混排（所有题材混在一起）
    pools.append({
        "type": "all",
        "name": "全榜混排",
        "file": "",
    })
    
    for f in sorted(data_dir.glob("fanqie_*_ranks_*.json"), reverse=True):
        parts = f.stem.split('_')
        if len(parts) >= 4:
            gender = parts[1]
            rank_kind = parts[2]
            rank_type = f"{gender}_{rank_kind}"
            
            if rank_type not in seen_types:
                seen_types.add(rank_type)
                name_map = {
                    "male_new": "男频新书",
                    "male_read": "男频在读",
                    "female_new": "女频新书",
                    "female_read": "女频在读",
                }
                pools.append({
                    "type": rank_type,
                    "name": name_map.get(rank_type, rank_type),
                    "file": f.name,
                })
    
    return jsonify(pools)


@app.route('/api/pools/all')
def api_pools_all():
    """全榜混排：所有题材混在一起，统一排序"""
    data_dir = SCAN_DATA_DIR / "data"
    
    all_books = []
    seen = set()
    
    # 读取所有排行榜文件，合并去重
    for f in sorted(data_dir.glob("fanqie_*_ranks_*.json"), reverse=True):
        parts = f.stem.split('_')
        if len(parts) >= 4:
            gender = parts[1]  # male/female
            rank_kind = parts[2]  # new/read
            
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                
                # 数据格式：{categories: {类别名: [书籍列表]}}
                categories = data.get("categories", {})
                for cat_name, books in categories.items():
                    if not isinstance(books, list):
                        continue
                    for book in books:
                        title = book.get("title", book.get("bookName", ""))
                        if not title or title in seen:
                            continue
                        seen.add(title)
                        
                        all_books.append({
                            "title": title,
                            "author": book.get("author", book.get("authorName", "")),
                            "category": cat_name,
                            "gender": "男频" if gender == "male" else "女频",
                            "rank_type": "新书榜" if rank_kind == "new" else "在读榜",
                            "rank": book.get("rank", 0),
                            "readCount": book.get("readCount", book.get("readCountStr", "")),
                            "wordCount": book.get("wordCount", book.get("wordCountStr", "")),
                            "description": book.get("description", book.get("bookDesc", ""))[:200],
                        })
            except Exception:
                continue
    
    # 按阅读量统一排序（跨题材混排）
    def parse_read_count(x):
        val = x.get("readCount", "0")
        if isinstance(val, str):
            val = val.replace("万", "0000").replace(",", "").strip()
            try:
                return float(val)
            except:
                return 0
        return float(val) if val else 0

    all_books.sort(key=lambda x: parse_read_count(x), reverse=True)

    # 生成统一排名
    for i, book in enumerate(all_books):
        book["unified_rank"] = i + 1

    return jsonify({
        "total": len(all_books),
        "books": all_books,
    })


@app.route('/api/pools/<rank_type>')
def api_pools_data(rank_type):
    """返回指定排行榜的数据"""
    if rank_type == "all":
        return api_pools_all()
    
    import glob
    data_dir = SCAN_DATA_DIR / "data"
    
    pattern = f"fanqie_{rank_type}_ranks_*.json"
    files = sorted(data_dir.glob(pattern), reverse=True)
    
    if not files:
        return jsonify({"error": f"未找到 {rank_type} 排行榜数据"}), 404
    
    # 返回最新的数据文件
    return send_from_directory(str(data_dir), files[0].name)


DOWNLOADER_URL = "http://127.0.0.1:18423"

@app.route('/api/download', methods=['POST'])
def api_download():
    """调用番茄下载器下载小说，下载完成后自动归档"""
    import requests as req

    data = request.json
    book_id = data.get('book_id', '')
    title = data.get('title', '')
    author = data.get('author', '')

    if not book_id:
        return jsonify({"error": "missing book_id"}), 400

    # 1. 创建下载任务
    try:
        r = req.post(f"{DOWNLOADER_URL}/api/jobs",
                     json={"book_id": book_id},
                     timeout=10)
        job = r.json()
    except Exception as e:
        return jsonify({"error": f"downloader error: {e}"}), 502

    return jsonify({
        "job_id": job.get("id"),
        "state": job.get("state"),
        "book_id": book_id,
        "title": title,
        "author": author
    })


@app.route('/api/download/status')
def api_download_status():
    """查询下载器任务状态"""
    import requests as req

    try:
        r = req.get(f"{DOWNLOADER_URL}/api/jobs", timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route('/api/download/archive', methods=['POST'])
def api_download_archive():
    """将下载完成的小说归档到 projects/（以 book_id 为准）"""
    import requests as req

    data = request.json
    book_id = data.get('book_id', '')
    title = data.get('title', '')
    author = data.get('author', '未知作者')

    downloads_dir = NOVEL_DOWNLOAD_DIR / "downloads"
    # 以 book_id 子目录为准（下载器按 book_id 创建子目录）
    book_id_dir = downloads_dir / book_id
    projects_dir = PROJECTS_DIR / author / title / "_cache"
    projects_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    # 优先从 book_id 子目录找 txt
    if book_id_dir.is_dir():
        for f in book_id_dir.glob("*.txt"):
            target = projects_dir / f.name
            if target.exists():
                target.unlink()  # 覆盖已存在的文件
            f.rename(target)
            moved.append(str(target))
    else:
        # fallback: 递归查找
        for f in downloads_dir.rglob("*.txt"):
            if f.parent == downloads_dir or f.parent.name == book_id:
                target = projects_dir / f.name
                if target.exists():
                    target.unlink()
                f.rename(target)
                moved.append(str(target))

    # 清理空子目录
    for d in downloads_dir.iterdir():
        if d.is_dir():
            try:
                d.rmdir()
            except:
                pass

    # 下载封面
    cover_url = data.get('cover', '')
    if cover_url:
        try:
            cover_path = projects_dir / "cover.jpg"
            r = req.get(cover_url, timeout=15)
            cover_path.write_bytes(r.content)
        except:
            pass

    return jsonify({"moved": moved, "target": str(projects_dir), "book_id": book_id})


if __name__ == '__main__':
    # production 模式：关 reloader 防子进程冲突，关 debugger 防信息泄露
    app.run(debug=False, use_reloader=False, port=5000)
