"""直接调番茄 API 下载小说"""
import json
import sys
import os
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://fanqienovel.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fanqienovel.com/"
}

def search_book(query):
    url = f"{BASE_URL}/api/author/search/search_book/v1"
    params = {"filter": "127,127,127,127", "page_count": 10, "page_index": 0, "query_type": 0, "query_word": query}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.text[:200]}")
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

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "将门有朵病娇花"
    
    print(f"搜索: {query}")
    results = search_book(query)
    if not results:
        print("未找到结果")
        return
    
    book = results[0]
    book_id = book.get("book_id", "")
    title = book.get("book_name", "")
    author = book.get("author", "")
    print(f"找到: {title} (作者: {author}, ID: {book_id})")
    
    # 获取章节目录
    print("获取章节目录...")
    chapters = get_chapter_list(book_id)
    if not chapters:
        print("获取章节目录失败")
        return
    
    # chapters 是一个列表，每个元素包含 chapter_items
    all_chapters = []
    for group in chapters:
        all_chapters.extend(group.get("chapter_items", []))
    
    print(f"共 {len(all_chapters)} 章")
    
    # 下载章节
    output_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.agents\skills\novel-download\downloads"
    os.makedirs(output_dir, exist_ok=True)
    
    full_text = f"书名：{title}\n作者：{author}\n\n"
    
    for i, ch in enumerate(all_chapters):
        ch_id = ch.get("chapter_id", "")
        ch_title = ch.get("title", f"第{i+1}章")
        
        content = get_chapter_content(ch_id)
        if content:
            full_text += f"\n\n{ch_title}\n\n{content}"
            print(f"  [{i+1}/{len(all_chapters)}] {ch_title}")
        else:
            print(f"  [{i+1}/{len(all_chapters)}] {ch_title} (空)")
        
        time.sleep(0.5)  # 防风控
    
    # 保存
    output_file = os.path.join(output_dir, f"{title}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print(f"\n下载完成: {output_file}")
    print(f"共 {len(all_chapters)} 章")

if __name__ == "__main__":
    main()
