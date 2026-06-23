"""直接调番茄 API 下载小说，输出到 projects 目录"""
import json
import sys
import os
import re
import time
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://fanqienovel.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fanqienovel.com/"
}

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROJECTS_DIR = PROJECT_ROOT / "projects"


def search_book(query):
    url = f"{BASE_URL}/api/author/search/search_book/v1"
    params = {"filter": "127,127,127,127", "page_count": 10, "page_index": 0, "query_type": 0, "query_word": query}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        return []
    return data.get("data", {}).get("search_book_data_list", [])


def get_book_info(book_id):
    url = f"{BASE_URL}/api/reader/full/v1"
    params = {"item_id": book_id}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        return None
    return data.get("data", {})


def get_chapter_list(book_id):
    url = f"{BASE_URL}/api/reader/directory/v1"
    params = {"item_id": book_id}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        return []
    return data.get("data", {}).get("all_group_items", [])


def get_chapter_content(chapter_id):
    url = f"{BASE_URL}/api/reader/full/v1"
    params = {"item_id": chapter_id}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = resp.json()
    if data.get("code") != 0:
        return ""
    return data.get("data", {}).get("chapter_data", {}).get("content", "")


def clean_html(text):
    """清理HTML标签"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'(\r?\n){3,}', '\n\n', text)
    return text.strip()


def download_book(query, output_dir=None):
    """下载书籍，返回输出路径"""
    print(f"搜索: {query}")
    results = search_book(query)
    if not results:
        print("未找到结果")
        return None

    # 精确匹配优先
    match = None
    for r in results:
        if r.get("book_name") == query:
            match = r
            break
    if not match:
        for r in results:
            if query in r.get("book_name", ""):
                match = r
                break
    if not match:
        match = results[0]

    book_id = match.get("book_id", "")
    title = match.get("book_name", book_id)
    author = match.get("author", "未知作者")
    print(f"找到: {title} (作者: {author}, ID: {book_id})")

    # 获取章节目录
    print("获取章节目录...")
    chapter_groups = get_chapter_list(book_id)
    if not chapter_groups:
        print("获取章节目录失败")
        return None

    all_chapters = []
    for group in chapter_groups:
        all_chapters.extend(group.get("chapter_items", []))
    print(f"共 {len(all_chapters)} 章")

    # 确定输出目录
    if output_dir:
        cache_dir = Path(output_dir)
    else:
        safe_author = re.sub(r'[\\/:*?"<>|]', '_', author)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        cache_dir = PROJECTS_DIR / safe_author / safe_title / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 下载章节
    full_text = f"书名：{title}\n作者：{author}\n\n"
    for i, ch in enumerate(all_chapters):
        ch_id = ch.get("chapter_id", "")
        ch_title = ch.get("title", f"第{i+1}章")
        content = get_chapter_content(ch_id)
        if content:
            content = clean_html(content)
            full_text += f"\n\n{ch_title}\n\n{content}"
            print(f"  [{i+1}/{len(all_chapters)}] {ch_title}")
        else:
            print(f"  [{i+1}/{len(all_chapters)}] {ch_title} (空)")
        time.sleep(0.3)

    # 保存txt
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
    txt_path = cache_dir / f"{safe_title}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"保存: {txt_path}")

    # 保存元信息
    meta = {
        "book_name": title,
        "author": author,
        "book_id": book_id,
        "chapter_count": len(all_chapters)
    }
    meta_path = cache_dir / "status.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"保存: {meta_path}")

    # 下载封面
    try:
        preview_url = f"{BASE_URL}/page/{book_id}"
        resp = requests.get(preview_url, headers=HEADERS, timeout=15)
        cover_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', resp.text)
        if cover_match:
            cover_url = cover_match.group(1)
            cover_path = cache_dir / "cover.png"
            resp = requests.get(cover_url, headers=HEADERS, timeout=15)
            with open(cover_path, 'wb') as f:
                f.write(resp.content)
            print(f"保存: {cover_path}")
    except Exception as e:
        print(f"封面下载失败: {e}")

    print(f"\n下载完成: {cache_dir}")
    return cache_dir


def main():
    if len(sys.argv) < 2:
        print("用法: python direct_download.py <书名或book_id> [输出目录]")
        sys.exit(1)
    
    query = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    result = download_book(query, output_dir)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
