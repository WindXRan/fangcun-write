"""本地书库：扫描projects目录，生成书籍索引，支持快速检索"""
import os
import re
import json
from pathlib import Path
from datetime import datetime


def count_chinese_chars(text):
    """统计中文字符数"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def extract_synopsis(content):
    """从内容中提取简介"""
    # 查找"简介："或"简介："后面的内容
    patterns = [
        r'简介[：:]\s*\n?(.*?)(?=\n\n|正文|第\d+章)',
        r'内容简介[：:]\s*\n?(.*?)(?=\n\n|正文|第\d+章)',
        r'作品简介[：:]\s*\n?(.*?)(?=\n\n|正文|第\d+章)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content[:5000], re.DOTALL)
        if match:
            synopsis = match.group(1).strip()
            # 清理简介
            synopsis = re.sub(r'\n+', ' ', synopsis)
            synopsis = synopsis[:200]  # 限制长度
            return synopsis
    
    return ""


def detect_genre(title, content=""):
    """从标题和内容推断题材"""
    title_lower = title.lower()
    
    # 甜宠类
    if any(w in title for w in ['网恋', '甜宠', '宠文', '撩', '撩人', '心动', '喜欢', '恋爱']):
        return "甜宠", ["甜宠", "恋爱"]
    
    # 虐文类
    if any(w in title for w in ['虐', '虐心', '悲', '误会', '分手', '离开', '失去']):
        return "虐文", ["虐文"]
    
    # 穿书/重生类
    if any(w in title for w in ['重生', '穿书', '穿越', '穿成', '回到', '重来']):
        return "穿书/重生", ["穿书", "重生"]
    
    # 总裁文
    if any(w in title for w in ['总裁', '豪门', '霸总', '契约', '婚', '闪婚']):
        return "总裁文", ["总裁", "豪门"]
    
    # 校园文
    if any(w in title for w in ['校园', '学长', '学弟', '同桌', '大学', '高中']):
        return "校园", ["校园"]
    
    # 娱乐圈
    if any(w in title for w in ['娱乐圈', '影帝', '顶流', '明星', '演员', '歌手']):
        return "娱乐圈", ["娱乐圈"]
    
    # 古言
    if any(w in title for w in ['古代', '古言', '王妃', '王爷', '太子', '皇帝']):
        return "古言", ["古言"]
    
    # 玄幻
    if any(w in title for w in ['修仙', '玄幻', '异能', '系统', '觉醒']):
        return "玄幻", ["玄幻"]
    
    # 从内容推断
    if content:
        if '甜宠' in content[:1000] or '宠文' in content[:1000]:
            return "甜宠", ["甜宠"]
        if '虐文' in content[:1000] or '虐心' in content[:1000]:
            return "虐文", ["虐文"]
    
    return "其他", []


def extract_metadata(filepath):
    """从txt文件提取元数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        metadata = {
            "file": str(filepath),
            "size_mb": round(filepath.stat().st_size / 1024 / 1024, 2),
            "title": filepath.stem,
            "author": "",
            "genre": "",
            "tags": [],
            "synopsis": "",
            "char_count": 0,
            "chapter_count": 0,
        }
        
        # 提取作者（从前20行）
        for line in content.split('\n')[:20]:
            if '作者' in line:
                match = re.search(r'作者[：:]\s*(.+)', line)
                if match:
                    metadata["author"] = match.group(1).strip()
                    break
        
        # 提取简介
        metadata["synopsis"] = extract_synopsis(content)
        
        # 推断题材
        metadata["genre"], metadata["tags"] = detect_genre(metadata["title"], content)
        
        # 统计字数和章节数
        metadata["char_count"] = count_chinese_chars(content)
        metadata["chapter_count"] = len(re.findall(r'第\d+章', content))
        
        return metadata
    except Exception as e:
        print(f"  错误: {filepath} - {e}")
        return None


def natural_sort_key(s):
    """自然排序：第1章 < 第2章 < 第10章"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(s))]


def scan_chapters(chapter_dir):
    """扫描章节目录，返回章节列表"""
    chapters = []
    for f in sorted(chapter_dir.iterdir(), key=lambda x: natural_sort_key(x.name)):
        if f.suffix == '.txt' and f.is_file():
            chapters.append({
                "name": f.stem,
                "file": str(f).replace("\\", "/"),
                "size": f.stat().st_size,
            })
    return chapters


def scan_book_versions(book_dir, author):
    """扫描一本书的所有版本（源文+仿写），同时检测封面"""
    versions = []
    cover_path = None

    # 1. 源文缓存（单文件）
    cache_dir = book_dir / "_cache"
    if cache_dir.is_dir():
        # 检测封面
        for ext in ('.jpg', '.jpeg', '.png', '.webp'):
            cover_file = cache_dir / f"cover{ext}"
            if cover_file.is_file():
                cover_path = str(cover_file).replace("\\", "/")
                break

        for f in cache_dir.glob("*.txt"):
            if f.is_file() and f.stat().st_size > 100 and not f.name.startswith('_'):
                versions.append({
                    "type": "source",
                    "name": "源文",
                    "file": str(f).replace("\\", "/"),
                })

    # 2. 源文目录
    source_dir = book_dir / "源文"
    if source_dir.is_dir():
        txt_files = list(source_dir.glob("*.txt"))
        if txt_files:
            chapters = scan_chapters(source_dir)
            if chapters:
                versions.append({
                    "type": "source",
                    "name": "源文",
                    "chapters": chapters,
                })

    # 3. 仿写（旧格式）: 仿写/新书名/正文/
    fw_dir = book_dir / "仿写"
    if fw_dir.is_dir():
        for sub in fw_dir.iterdir():
            if sub.is_dir():
                zhengwen = sub / "正文"
                if zhengwen.is_dir():
                    chapters = scan_chapters(zhengwen)
                    if chapters:
                        versions.append({
                            "type": "rewrite",
                            "name": sub.name,
                            "chapters": chapters,
                        })

    # 4. 仿写（新格式）: rewrites/新书名/chapters/
    rw_dir = book_dir / "rewrites"
    if rw_dir.is_dir():
        for sub in rw_dir.iterdir():
            if sub.is_dir():
                ch_dir = sub / "chapters"
                if ch_dir.is_dir():
                    chapters = scan_chapters(ch_dir)
                    if chapters:
                        versions.append({
                            "type": "rewrite",
                            "name": sub.name,
                            "chapters": chapters,
                        })

    # 5. combined
    combined_dir = book_dir / "combined"
    if combined_dir.is_dir():
        chapters = scan_chapters(combined_dir)
        if chapters:
            versions.append({
                "type": "combined",
                "name": "合并版",
                "chapters": chapters,
            })

    return versions, cover_path


def scan_library(projects_dir="projects"):
    """扫描projects目录，生成书库索引（含仿写版本）"""
    projects_path = Path(projects_dir)
    if not projects_path.exists():
        print(f"目录不存在: {projects_dir}")
        return []
    
    books = []
    
    # 扫描所有作者目录
    for author_dir in projects_path.iterdir():
        if not author_dir.is_dir():
            continue
        author = author_dir.name

        for book_dir in sorted(author_dir.iterdir()):
            if not book_dir.is_dir():
                continue

            # 跳过 combined 和非书目录
            if book_dir.name in ('combined', '_cache', 'ai-detect报告', '风格', '蒸馏'):
                continue

            # 收集该书的所有版本
            versions, cover_path = scan_book_versions(book_dir, author)
            if not versions:
                continue

            # 取源文元数据
            source_ver = next((v for v in versions if v["type"] == "source"), versions[0])
            source_file = source_ver.get("file")
            if source_file:
                meta = extract_metadata(Path(source_file))
            else:
                # 多章源文，拼接读取
                meta = {"title": book_dir.name, "author": author, "char_count": 0, "chapter_count": 0}
                if source_ver.get("chapters"):
                    meta["chapter_count"] = len(source_ver["chapters"])
                    total_size = sum(c["size"] for c in source_ver["chapters"])
                    meta["char_count"] = total_size // 3  # 粗估

            if not meta:
                continue

            if not meta.get("author"):
                meta["author"] = author

            # 添加版本信息和封面
            meta["versions"] = versions
            meta["version_count"] = len(versions)
            if cover_path:
                meta["cover"] = cover_path

            books.append(meta)
            print(f"  {author}/{book_dir.name} ({meta.get('char_count', 0)}字, {len(versions)}个版本)")
    
    # 按字数排序
    books.sort(key=lambda x: x.get("char_count", 0), reverse=True)
    
    return books


def save_library_index(books, output_file="book_library.json"):
    """保存书库索引"""
    index = {
        "updated": datetime.now().isoformat(),
        "total_books": len(books),
        "total_chars": sum(b["char_count"] for b in books),
        "genres": {},
        "books": books
    }
    
    # 统计题材分布
    for book in books:
        genre = book.get("genre", "其他")
        if genre not in index["genres"]:
            index["genres"][genre] = 0
        index["genres"][genre] += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n书库索引已生成: {output_file}")
    print(f"  总书籍: {len(books)}本")
    print(f"  总字数: {sum(b['char_count'] for b in books):,}字")
    print(f"  题材分布: {index['genres']}")
    
    return index


def search_books(query=None, genre=None, min_chars=None, max_chars=None, author=None):
    """检索书籍"""
    index_file = Path("book_library.json")
    if not index_file.exists():
        print("书库索引不存在，请先运行 scan_library()")
        return []
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    results = index["books"]
    
    # 关键词搜索（标题、作者、简介）
    if query:
        query = query.lower()
        results = [b for b in results if 
                   query in b["title"].lower() or 
                   query in b["author"].lower() or
                   query in b.get("synopsis", "").lower()]
    
    # 题材筛选
    if genre:
        results = [b for b in results if genre in b.get("genre", "") or genre in b.get("tags", [])]
    
    # 字数范围
    if min_chars:
        results = [b for b in results if b["char_count"] >= min_chars]
    if max_chars:
        results = [b for b in results if b["char_count"] <= max_chars]
    
    # 作者筛选
    if author:
        results = [b for b in results if author in b["author"]]
    
    return results


def format_book_list(books, verbose=False):
    """格式化书籍列表"""
    if not books:
        return "未找到匹配的书籍"
    
    lines = [f"共 {len(books)} 本书：\n"]
    
    for i, book in enumerate(books, 1):
        line = f"{i}. {book['author']}/{book['title']} - {book['char_count']:,}字"
        if book.get('genre'):
            line += f" [{book['genre']}]"
        if book.get('chapter_count'):
            line += f" ({book['chapter_count']}章)"
        lines.append(line)
        
        if verbose:
            if book.get('synopsis'):
                lines.append(f"   简介: {book['synopsis'][:100]}...")
            lines.append(f"   文件: {book['file']}")
            if book.get('tags'):
                lines.append(f"   标签: {', '.join(book['tags'])}")
    
    return '\n'.join(lines)


def generate_web_library(books, output_file="book_library_web.json"):
    """生成web端可用的书库格式"""
    web_books = []
    
    for book in books:
        web_book = {
            "id": book["title"],
            "title": book["title"],
            "author": book["author"],
            "genre": book.get("genre", ""),
            "tags": book.get("tags", []),
            "synopsis": book.get("synopsis", ""),
            "char_count": book["char_count"],
            "chapter_count": book.get("chapter_count", 0),
            "file": book["file"].replace("\\", "/"),
        }
        web_books.append(web_book)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(web_books, f, ensure_ascii=False, indent=2)
    
    print(f"Web端书库已生成: {output_file}")
    return web_books


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python book_library.py scan [目录]     # 扫描并生成索引")
        print("  python book_library.py search [关键词]  # 搜索书籍")
        print("  python book_library.py list            # 列出所有书籍")
        print("  python book_library.py genre [题材]    # 按题材筛选")
        print("  python book_library.py web            # 生成web端格式")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "scan":
        dir_path = sys.argv[2] if len(sys.argv) > 2 else "projects"
        print(f"扫描目录: {dir_path}")
        books = scan_library(dir_path)
        save_library_index(books)
    
    elif action == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else None
        books = search_books(query=query)
        print(format_book_list(books, verbose=True))
    
    elif action == "list":
        books = search_books()
        print(format_book_list(books))
    
    elif action == "genre":
        genre = sys.argv[2] if len(sys.argv) > 2 else None
        books = search_books(genre=genre)
        print(format_book_list(books))
    
    elif action == "web":
        books = search_books()
        generate_web_library(books)
    
    else:
        print(f"未知操作: {action}")
