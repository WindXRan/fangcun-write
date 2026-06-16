"""
下载番茄小说（通过 exe server API）。

用法:
  python download.py "书名"
  python download.py "书名" --range 1-50
  python download.py "书名" --author "作者名"
  python download.py "书名" --keep-server
"""
import os
import re
import sys
import json
import time
import shutil
import argparse
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DEFAULT_PORT = 18423


def ensure_server(port=None):
    """确保 server 运行，返回端口。"""
    # 检查是否已运行
    for p in [port, DEFAULT_PORT]:
        if p:
            try:
                resp = requests.get(f"http://127.0.0.1:{p}/api/status", timeout=3)
                if resp.status_code == 200:
                    print(f"  Server 已运行，端口: {p}")
                    return p
            except:
                pass

    # 启动 server
    print("  Server 未运行，正在启动...")
    exe = SKILL_DIR / "TomatoNovelDownloader-Win64-v2.4.11.exe"
    if not exe.exists():
        print(f"  [ERROR] 下载器不存在: {exe}")
        sys.exit(1)

    import subprocess
    subprocess.Popen(
        [str(exe), "--data-dir", str(SKILL_DIR), "--server"],
        cwd=str(SKILL_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(5)

    # 检测端口
    for p in [DEFAULT_PORT, 18424, 18425]:
        try:
            resp = requests.get(f"http://127.0.0.1:{p}/api/status", timeout=3)
            if resp.status_code == 200:
                print(f"  Server 已启动，端口: {p}")
                return p
        except:
            pass

    print("  [ERROR] 无法检测 server 端口")
    sys.exit(1)


def search_book(base_url, query):
    """搜索书籍。"""
    resp = requests.get(f"{base_url}/api/search", params={"q": query}, timeout=15)
    data = resp.json()
    items = data.get("items", [])
    if not items:
        print(f"  [ERROR] 未找到结果: {query}")
        sys.exit(1)

    # 精确匹配优先
    for item in items:
        if item.get("title") == query:
            return item
    for item in items:
        if query in item.get("title", ""):
            return item
    return items[0]


def create_job(base_url, book_id, range_start=None, range_end=None):
    """创建下载任务。"""
    payload = {"book_id": book_id}
    if range_start:
        payload["range_start"] = range_start
    if range_end:
        payload["range_end"] = range_end

    resp = requests.post(f"{base_url}/api/jobs", json=payload, timeout=15)
    return resp.json()


def wait_for_download(base_url, max_wait=300):
    """等待下载完成。"""
    print(f"  等待下载完成（最长 {max_wait} 秒）")
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            print("  [WARN] 等待超时")
            return None

        try:
            resp = requests.get(f"{base_url}/api/jobs", timeout=5)
            jobs = resp.json().get("items", [])

            running = [j for j in jobs if j.get("state") in ("running", "queued")]
            done = [j for j in jobs if j.get("state") == "done"]
            failed = [j for j in jobs if j.get("state") == "failed"]

            if not running:
                if failed:
                    for f in failed:
                        print(f"  [ERROR] {f.get('title')}: {f.get('message')}")
                if done:
                    d = done[0]
                    saved = d.get("progress", {}).get("saved_chapters", 0)
                    total = d.get("progress", {}).get("chapter_total", 0)
                    print(f"  下载完成: {d.get('title')} ({saved}/{total} 章)")
                    return d
                return None

            r = running[0]
            saved = r.get("progress", {}).get("saved_chapters", 0)
            total = r.get("progress", {}).get("chapter_total", 0)
            pct = round(saved / total * 100) if total > 0 else 0
            print(f"  {r.get('title')}: {saved}/{total} ({pct}%)")

        except Exception as e:
            pass

        time.sleep(3)


def find_txt_file(book_name):
    """查找下载的 txt 文件。"""
    # 检查 skill 根目录
    for f in SKILL_DIR.glob("*.txt"):
        if f.stat().st_mtime > time.time() - 300:  # 5 分钟内创建
            return f

    # 检查 downloads 目录
    downloads = SKILL_DIR / "downloads"
    if downloads.exists():
        for f in downloads.glob("*.txt"):
            if f.stat().st_mtime > time.time() - 300:
                return f

    return None


def fix_duplicate_titles(txt_path):
    """修复下载器 bug：去掉重复的章节标题。"""
    content = txt_path.read_text(encoding='utf-8')
    
    # 去掉重复的章节标题：第X章 标题 第X章 标题 → 第X章 标题
    content = re.sub(r'(第\d+章\s+.+?)\s+\1', r'\1', content)
    
    # 去掉重复的卷名
    content = re.sub(r'(第.+?卷.+?)\s+\1\s+\1', r'\1', content)
    
    txt_path.write_text(content, encoding='utf-8')
    print(f"  重复标题已修复")


def archive(txt_path, author, book_name):
    """归档到 projects 目录。"""
    safe_author = re.sub(r'[\\/:*?"<>|]', '_', author)
    safe_book_name = re.sub(r'[\\/:*?"<>|]', '_', book_name)
    
    book_dir = SKILL_DIR / "projects" / safe_author / safe_book_name
    cache_dir = book_dir / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    target = cache_dir / txt_path.name
    shutil.move(str(txt_path), str(target))
    print(f"  归档: {target}")
    return target


def main():
    parser = argparse.ArgumentParser(description="下载番茄小说")
    parser.add_argument("query", help="书名、book_id 或链接")
    parser.add_argument("--port", type=int, default=None, help="Server 端口")
    parser.add_argument("--range", help="章节范围，如 1-50")
    parser.add_argument("--author", help="作者名（可选）")
    parser.add_argument("--keep-server", action="store_true", help="下载后保持 server 运行")
    parser.add_argument("--no-archive", action="store_true", help="不归档")
    parser.add_argument("--max-wait", type=int, default=300, help="最大等待秒数")
    args = parser.parse_args()

    # 启动 server
    port = ensure_server(args.port)
    base_url = f"http://127.0.0.1:{port}"

    # 判断输入类型
    book_id = None
    if re.match(r'^\d+$', args.query):
        book_id = args.query
    elif 'book_id=' in args.query or '/page/' in args.query:
        m = re.search(r'(?:book_id=|/page/)(\d+)', args.query)
        if m:
            book_id = m.group(1)

    if book_id:
        print(f"  使用 book_id: {book_id}")
        # 获取书籍信息
        try:
            resp = requests.get(f"{base_url}/api/preview/{book_id}", timeout=15)
            preview = resp.json()
            book_name = preview.get("book_name", book_id)
            author = preview.get("author", args.author or "未知")
        except:
            book_name = book_id
            author = args.author or "未知"
    else:
        print(f"  搜索: {args.query}")
        match = search_book(base_url, args.query)
        book_id = match["book_id"]
        book_name = match.get("title", book_id)
        author = match.get("author", args.author or "未知")
        print(f"  匹配: {book_name} (作者: {author}, ID: {book_id})")

    # 创建下载任务
    print(f"  创建下载任务")
    range_start, range_end = None, None
    if args.range:
        parts = args.range.split('-')
        if len(parts) == 2:
            range_start, range_end = int(parts[0]), int(parts[1])
            print(f"  范围: {range_start}-{range_end}")

    create_job(base_url, book_id, range_start, range_end)

    # 等待完成
    result = wait_for_download(base_url, args.max_wait)
    if not result:
        print("  [ERROR] 下载失败")
        sys.exit(1)

    # 查找 txt 文件
    txt_file = find_txt_file(book_name)
    if not txt_file:
        print("  [ERROR] 未找到下载的 txt 文件")
        sys.exit(1)

    print(f"  找到文件: {txt_file.name}")

    # 修复重复标题
    fix_duplicate_titles(txt_file)

    # 归档
    if not args.no_archive:
        archive(txt_file, author, book_name)

    # 清理
    if not args.keep_server:
        print("  清理进程")
        import subprocess
        subprocess.run(["taskkill", "/f", "/im", "TomatoNovelDownloader-Win64-v2.4.11.exe"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"\n  下载完成！")


if __name__ == "__main__":
    main()
