"""用番茄官方 API 下载小说"""
import json, sys, os, time, re
import requests

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fanqienovel.com/"
}

def get_chapters(book_id):
    """获取章节目录"""
    url = f"https://fanqienovel.com/api/reader/directory/v1?item_id={book_id}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  Directory status: {r.status_code}")
    print(f"  Directory response: {r.text[:200]}")
    data = r.json()
    if data.get("code") != 0:
        print(f"Error: {data}")
        return []
    groups = data.get("data", {}).get("all_group_items", [])
    chapters = []
    for g in groups:
        chapters.extend(g.get("chapter_items", []))
    return chapters

def get_content(chapter_id):
    """获取章节内容"""
    url = f"https://fanqienovel.com/api/reader/full/v1?item_id={chapter_id}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    data = r.json()
    if data.get("code") != 0:
        return ""
    chapter_data = data.get("data", {}).get("chapter_data", {})
    return chapter_data.get("content", "")

def main():
    book_id = sys.argv[1] if len(sys.argv) > 1 else "7621419029625834521"
    
    # 从页面获取书名
    page_url = f"https://fanqienovel.com/page/{book_id}"
    r = requests.get(page_url, headers=HEADERS, timeout=15)
    m = re.search(r'<title>(.*?)完整版', r.text)
    title = m.group(1) if m else "unknown"
    print(f"书名: {title}")
    print(f"book_id: {book_id}")
    
    # 获取章节目录
    print("获取章节目录...")
    chapters = get_chapters(book_id)
    print(f"共 {len(chapters)} 章")
    
    if not chapters:
        print("获取章节目录失败")
        return
    
    # 下载内容
    full_text = f"书名：{title}\n\n"
    for i, ch in enumerate(chapters):
        ch_id = ch.get("chapter_id", "")
        ch_title = ch.get("title", f"第{i+1}章")
        content = get_content(ch_id)
        if content:
            full_text += f"\n\n{ch_title}\n\n{content}"
            print(f"  [{i+1}/{len(chapters)}] {ch_title}")
        else:
            print(f"  [{i+1}/{len(chapters)}] {ch_title} (空)")
        time.sleep(0.3)
    
    # 保存
    output_dir = Path(__file__).parent.parent.parent.parent / "projects" / "_downloads"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{title}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"\n下载完成: {output_file}")

if __name__ == "__main__":
    main()
