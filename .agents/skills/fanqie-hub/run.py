#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说 Hub - 统一入口（Web 模式）
全部功能走下载器的 Web API（端口 18423），不启动 TUI。
"""
import os, sys, time, json, urllib.request, urllib.parse, subprocess, atexit
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HUB_DIR = Path(__file__).parent
DOWNLOADER_EXE = HUB_DIR / "downloader" / "TomatoNovelDownloader-Win64-v2.4.11.exe"
SCANNER_DIR = HUB_DIR / "scanner"
WEB_DIR = HUB_DIR / "web"
API_BASE = "http://127.0.0.1:18423"
_server_proc = None


def _api(path, data=None, timeout=30):
    """调用下载器 API。GET 或 POST。"""
    url = f"{API_BASE}{path}"
    if data:
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.read().decode()[:200]}"
    except urllib.error.URLError:
        return None  # 服务未启动


def _ensure_server():
    """确保下载器 Web 服务在运行。"""
    global _server_proc
    if _api("/api/status") is not None:
        return True  # 已在运行
    if not DOWNLOADER_EXE.exists():
        print(f"[错误] 下载器不存在: {DOWNLOADER_EXE}")
        return False
    _server_proc = subprocess.Popen(
        [str(DOWNLOADER_EXE), "--server", "--data-dir", str(DOWNLOADER_EXE.parent)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    atexit.register(lambda: _server_proc and _server_proc.kill())
    for i in range(15):
        time.sleep(1)
        if _api("/api/status") is not None:
            print(f"  下载器就绪 (pid={_server_proc.pid})")
            return True
    print("[错误] 下载器启动超时")
    return False


def cmd_search(query):
    """搜索小说。"""
    if not _ensure_server():
        return
    q = urllib.parse.quote(query)
    raw = _api(f"/api/search?q={q}", timeout=60)
    if raw is None:
        print("[错误] 搜索无响应")
        return
    try:
        data = json.loads(raw)
        books = data if isinstance(data, list) else data.get("books", data.get("data", []))
        print(f"\n搜索「{query}」结果 ({len(books)} 本):\n")
        for b in books[:10]:
            bid = b.get("book_id") or b.get("id", "?")
            name = b.get("book_name") or b.get("name", "?")
            author = b.get("author", "?")
            status = b.get("status", "?")
            print(f"  [{bid}] {name} — {author} ({status})")
    except json.JSONDecodeError:
        print(raw[:500])


def cmd_download(query):
    """搜索并下载小说，下载完自动转 txt。"""
    if not _ensure_server():
        return
    q = urllib.parse.quote(query)
    raw = _api(f"/api/search?q={q}", timeout=60)
    if raw is None:
        print("[错误] 搜索无响应")
        return
    try:
        data = json.loads(raw)
        books = data if isinstance(data, list) else data.get("books", data.get("data", []))
        if not books:
            print("未找到匹配的小说")
            return
        if len(books) == 1:
            bid = books[0].get("book_id") or books[0].get("id")
            name = books[0].get("book_name") or books[0].get("name", "?")
            print(f"下载《{name}》({bid})...")
            result = _api("/api/jobs", data={"book_id": bid}, timeout=600)
            print(result or "下载完成")

            # 自动转 txt
            fix_script = HUB_DIR / "downloader" / "fix_format.py"
            if fix_script.exists():
                print("  自动转 txt...")
                subprocess.run([sys.executable, str(fix_script)],
                             cwd=str(fix_script.parent), timeout=120)
                txt_files = list(fix_script.parent.glob("*.txt"))
                if txt_files:
                    print(f"  ✓ {txt_files[0].name} ({(txt_files[0].stat().st_size/1024):.0f} KB)")
            return
        print(f"\n搜索「{query}」找到 {len(books)} 本，选一个下载：")
        for i, b in enumerate(books[:10]):
            bid = b.get("book_id") or b.get("id", "?")
            name = b.get("book_name") or b.get("name", "?")
            author = b.get("author", "?")
            print(f"  {i+1}. [{bid}] {name} — {author}")
        print("\n输入序号或 book_id 下载，或直接告诉我")
    except json.JSONDecodeError:
        print(raw[:500])


def cmd_web():
    """启动 Flask 书库 Web 服务。"""
    _ensure_server()
    print("\n启动书库服务 http://localhost:5000")
    print("  - 书库首页: /")
    print("  - 番茄排行榜: /ranks/")
    print("  - 按 Ctrl+C 停止")
    subprocess.run([sys.executable, "app.py"], cwd=str(WEB_DIR))


def cmd_scan():
    subprocess.run(["python", "scrape_fanqie_ranks.py"], cwd=str(SCANNER_DIR), timeout=1200)


def cmd_build():
    subprocess.run(["python", "scripts/build_latest.py"], cwd=str(SCANNER_DIR), timeout=300)


def cmd_status():
    print("\n番茄小说 Hub 状态")
    print("=" * 60)
    ok = _api("/api/status")
    print(f"下载器 Web 服务: {'运行中' if ok else '未启动'}")
    data_dir = SCANNER_DIR / "data"
    if data_dir.exists():
        files = list(data_dir.glob("fanqie_*_ranks_*.json"))
        print(f"排行榜数据: {len(files)} 个文件")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "search":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("搜什么？")
        cmd_search(q)
    elif cmd == "download":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("下什么？")
        cmd_download(q)
    elif cmd == "web":
        cmd_web()
    elif cmd == "scan":
        cmd_scan()
    elif cmd == "build":
        cmd_build()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"未知命令: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
