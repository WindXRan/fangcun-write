#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说 Hub - 统一入口（Web 模式）
全部功能走下载器的 Web API（端口 18423），不启动 TUI。

流程：搜索 → 选书 → 提交下载 → 轮询进度 → 自动合并为单文件 txt
"""
import os, sys, time, json, re, urllib.request, urllib.parse, subprocess, atexit
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


# ── 下载器 API ──────────────────────────────

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
        print(f"[HTTP Error {e.code}] {e.read().decode()[:200]}")
        return None
    except urllib.error.URLError:
        return None


def _api_json(path, data=None, timeout=30):
    """调用 API 并直接解析 JSON。"""
    raw = _api(path, data, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _get_save_dir():
    """从状态 API 获取下载器的保存根目录。"""
    st = _api_json("/api/status")
    if st and "save_dir" in st:
        return Path(st["save_dir"])
    return HUB_DIR  # fallback


def _ensure_server():
    """确保下载器 Web 服务在运行。"""
    global _server_proc
    if _api("/api/status") is not None:
        return True
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


# ── 搜索 ────────────────────────────────────

def _parse_books(data):
    """从 API 返回值提取书籍列表，兼容多种字段名。"""
    if isinstance(data, list):
        return data
    for key in ("items", "books", "data", "results"):
        val = data.get(key)
        if isinstance(val, list):
            return val
    return []


def _pick_book(books, query=""):
    """让用户从书籍列表中选择一本，返回选中项或 None。"""
    if not books:
        return None
    if len(books) == 1:
        return books[0]

    print(f"\n搜索「{query}」找到 {len(books)} 本，选一个下载：")
    for i, b in enumerate(books[:10]):
        bid = b.get("book_id") or b.get("id", "?")
        name = b.get("title") or b.get("book_name") or b.get("name", "?")
        author = b.get("author", "?")
        print(f"  {i+1}. [{bid}] {name} — {author}")
    if len(books) > 10:
        print(f"  ...以及 {len(books) - 10} 本更多")

    choice = input("\n输入序号或 book_id 下载 (回车取消): ").strip()
    if not choice:
        print("已取消")
        return None

    # 序号匹配
    try:
        idx = int(choice) - 1
        if 0 <= idx < min(len(books), 10):
            return books[idx]
    except ValueError:
        pass

    # book_id 匹配
    for b in books:
        if str(b.get("book_id") or b.get("id")) == choice:
            return b

    print(f"未找到匹配: {choice}")
    return None


def cmd_search(query):
    """搜索小说。"""
    if not _ensure_server():
        return
    q = urllib.parse.quote(query)
    data = _api_json(f"/api/search?q={q}", timeout=60)
    if data is None:
        print("[错误] 搜索无响应")
        return
    books = _parse_books(data)
    if not books:
        print("未找到匹配的小说")
        return
    print(f"\n搜索「{query}」结果 ({len(books)} 本):\n")
    for b in books[:10]:
        bid = b.get("book_id") or b.get("id", "?")
        name = b.get("title") or b.get("book_name") or b.get("name", "?")
        author = b.get("author", "?")
        print(f"  [{bid}] {name} — {author}")
    if len(books) > 10:
        print(f"  ...以及 {len(books) - 10} 本更多")


# ── 下载 & 合并 ─────────────────────────────

def _submit_job(book_id):
    """提交下载任务，返回 job_id。"""
    result = _api_json("/api/jobs", data={"book_id": book_id}, timeout=30)
    if result is None:
        return None
    return result.get("id")


def _poll_job(job_id, book_name):
    """轮询下载进度直到完成，返回最终状态。"""
    last_pct = -1
    print("  ⏳ 排队中...", end="", flush=True)
    started = False
    while True:
        jobs = _api_json("/api/jobs")
        if not jobs:
            time.sleep(3)
            continue
        for item in jobs.get("items", []):
            if item.get("id") == job_id:
                state = item.get("state", "?")
                prog = item.get("progress", {})
                saved = prog.get("saved_chapters", 0)
                total = prog.get("chapter_total", 0)
                pct = int(saved / total * 100) if total else 0

                if pct != last_pct:
                    if not started and pct > 0:
                        started = True
                    bar_len = 20
                    filled = int(bar_len * pct / 100)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    print(f"\r  [{bar}] {pct}%  {saved}/{total}章", end="", flush=True)
                    last_pct = pct

                if state == "done":
                    print(f"\n  ✓ 下载完成 ({total}章)")
                    return "done"
                if state == "failed":
                    msg = item.get("message", "未知错误")
                    print(f"\n  ✗ 下载失败: {msg}")
                    return "failed"
                break
        time.sleep(2)


def _merge_book_txt(book_name):
    """
    查找下载器输出的散装 txt 目录，合并为单文件。
    返回 (输出路径, 章节数) 或 (None, 0)。
    """
    save_dir = _get_save_dir()
    book_dir = save_dir / book_name
    if not book_dir.is_dir():
        # 尝试模糊匹配
        candidates = sorted(save_dir.glob(f"*{book_name[:8]}*"))
        book_dir = candidates[0] if candidates else None
    if not book_dir or not book_dir.is_dir():
        return None, 0

    txt_files = sorted(book_dir.glob("[0-9]*_*.txt"))
    if not txt_files:
        return None, 0

    # 跳过 0000_ 书籍信息文件
    chap_files = [f for f in txt_files if not f.name.startswith("0000_")]
    if not chap_files:
        return None, 0

    # 合并
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
    out_path = save_dir / f"{safe_name}.txt"
    with open(out_path, "w", encoding="utf-8") as out:
        for i, fp in enumerate(chap_files):
            if i > 0:
                out.write("\n")
            out.write(fp.read_text(encoding="utf-8", errors="replace").strip())
            out.write("\n")

    return out_path, len(chap_files)


def cmd_download(query):
    """搜索 → 下载 → 合并为单文件 txt，一步到位。"""
    if not _ensure_server():
        return

    # 1. 搜索
    q = urllib.parse.quote(query)
    data = _api_json(f"/api/search?q={q}", timeout=60)
    if data is None:
        print("[错误] 搜索无响应")
        return
    books = _parse_books(data)
    if not books:
        print("未找到匹配的小说")
        return

    # 2. 选书
    book = _pick_book(books, query)
    if not book:
        return

    bid = book.get("book_id") or book.get("id")
    name = book.get("title") or book.get("book_name") or book.get("name", "?")
    if not bid:
        print(f"[错误] 无法获取《{name}》的 book_id，API 返回字段可能不匹配")
        return

    # 3. 提交下载
    print(f"\n提交下载《{name}》...")
    job_id = _submit_job(bid)
    if job_id is None:
        print("[错误] 下载请求失败")
        return
    print(f"  任务 #{job_id} 已排队")

    # 4. 等完成
    status = _poll_job(job_id, name)

    # 5. 合并
    if status == "done":
        print(f"  合并散装 txt...", end=" ")
        out_path, chap_count = _merge_book_txt(name)
        if out_path:
            kb = out_path.stat().st_size / 1024
            print(f"✓ {chap_count}章 → {out_path.name} ({kb:.0f} KB)")
        else:
            print("⚠ 未找到章节文件（下载器可能已直接存为 epub）")
            # fallback: 搜 epub
            epubs = list((HUB_DIR / "downloader").glob("*.epub"))
            if epubs:
                print(f"  尝试运行 fix_format.py 转换...")
                subprocess.run([sys.executable, str(HUB_DIR / "downloader" / "fix_format.py")],
                             cwd=str(HUB_DIR / "downloader"), timeout=120)
    else:
        print("  跳过合并")


def cmd_web():
    """启动 Flask 书库 Web 服务。"""
    _ensure_server()
    print("\n启动书库服务 http://localhost:5000")
    print("  - 书库首页: /")
    print("  - 番茄排行榜: /ranks/")
    print("  - 按 Ctrl+C 停止")
    subprocess.run([sys.executable, "app.py"], cwd=str(WEB_DIR))


def cmd_scan():
    try:
        subprocess.run(["python", "scrape_fanqie_ranks.py"], cwd=str(SCANNER_DIR), timeout=1200)
        print("  扫描完成")
    except subprocess.TimeoutExpired:
        print("[警告] 排行榜扫描超时（超过 1200 秒），可能未完成")


def cmd_build():
    try:
        subprocess.run(["python", "scripts/build_latest.py"], cwd=str(SCANNER_DIR), timeout=300)
        print("  数据构建完成")
    except subprocess.TimeoutExpired:
        print("[警告] 数据构建超时（超过 300 秒）")


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
