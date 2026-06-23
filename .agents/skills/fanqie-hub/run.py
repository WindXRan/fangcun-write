#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说 Hub - 统一入口
用法：python run.py <command> [args]

命令：
  download <query>    下载小说（书名/book_id/链接）
  download-author <作者>  按作者批量下载
  scan               采集排行榜数据
  build              构建分析数据
  web                启动Web服务
  status             查看状态
  help               显示帮助
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Windows 控制台 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

HUB_DIR = Path(__file__).parent
DOWNLOADER_DIR = HUB_DIR / "downloader"
SCANNER_DIR = HUB_DIR / "scanner"
WEB_DIR = HUB_DIR / "web"
PROJECTS_DIR = HUB_DIR / "projects"


def run_cmd(cmd, cwd=None, timeout=None):
    """运行命令"""
    print(f"\n{'='*60}")
    print(f">>> {cmd}")
    print('='*60)
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, timeout=timeout)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"超时（{timeout}秒）")
        return False
    except Exception as e:
        print(f"执行失败: {e}")
        return False


def cmd_download(query, range_str=None):
    """下载单本小说"""
    ps_script = DOWNLOADER_DIR / "scripts" / "download_book.ps1"
    cmd = f'powershell -ExecutionPolicy Bypass -File "{ps_script}" -Query "{query}"'
    if range_str:
        cmd += f' -Range "{range_str}"'
    return run_cmd(cmd, cwd=str(DOWNLOADER_DIR))


def cmd_download_author(author, range_str=None):
    """按作者批量下载"""
    ps_script = DOWNLOADER_DIR / "scripts" / "download_by_author.ps1"
    cmd = f'powershell -ExecutionPolicy Bypass -File "{ps_script}" -Author "{author}"'
    if range_str:
        cmd += f' -Range "{range_str}"'
    return run_cmd(cmd, cwd=str(DOWNLOADER_DIR))


def cmd_scan():
    """采集排行榜数据"""
    return run_cmd("python scrape_fanqie_ranks.py", cwd=str(SCANNER_DIR), timeout=1200)


def cmd_build():
    """构建分析数据"""
    return run_cmd("python scripts/build_latest.py", cwd=str(SCANNER_DIR), timeout=300)


def cmd_web():
    """启动Web服务"""
    print("\n启动书库服务...")
    print("访问地址:")
    print("  - 书库首页: http://localhost:5000/")
    print("  - 番茄排行榜: http://localhost:5000/ranks/")
    print("  - 趋势风向: http://localhost:5000/ranks/trend.html")
    print("  - 创作灵感: http://localhost:5000/ranks/author.html")
    print("\n按 Ctrl+C 停止服务")
    return run_cmd("python app.py", cwd=str(WEB_DIR))


def cmd_status():
    """查看状态"""
    print("\n番茄小说 Hub 状态")
    print('='*60)
    
    # knowledge 目录
    knowledge_dir = HUB_DIR.parent.parent / "knowledge"
    if knowledge_dir.exists():
        authors = [d for d in knowledge_dir.iterdir() if d.is_dir()]
        print(f"\n知识库: {len(authors)} 个作者")
        for author_dir in authors[:5]:
            books = [d for d in author_dir.iterdir() if d.is_dir()]
            print(f"  - {author_dir.name}: {len(books)} 本书")
        if len(authors) > 5:
            print(f"  ... 还有 {len(authors)-5} 个作者")
    
    # projects 目录
    if PROJECTS_DIR.exists():
        authors = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
        print(f"\n项目库: {len(authors)} 个作者")
        for author_dir in authors[:5]:
            books = [d for d in author_dir.iterdir() if d.is_dir()]
            print(f"  - {author_dir.name}: {len(books)} 个项目")
        if len(authors) > 5:
            print(f"  ... 还有 {len(authors)-5} 个作者")
    
    # 排行榜数据
    data_dir = SCANNER_DIR / "data"
    if data_dir.exists():
        rank_files = list(data_dir.glob("fanqie_*_ranks_*.json"))
        print(f"\n排行榜数据: {len(rank_files)} 个文件")
        for f in sorted(rank_files)[-4:]:
            print(f"  - {f.name}")
    
    # Web服务状态
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:5000/api/books", timeout=2) as resp:
            print("\nWeb服务: 运行中 (http://localhost:5000)")
    except:
        print("\nWeb服务: 未运行")


def show_help():
    """显示帮助"""
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "download":
        if len(sys.argv) < 3:
            print("用法: python run.py download <书名>")
            return
        query = sys.argv[2]
        range_str = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_download(query, range_str)
    
    elif cmd == "download-author":
        if len(sys.argv) < 3:
            print("用法: python run.py download-author <作者名>")
            return
        author = sys.argv[2]
        range_str = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_download_author(author, range_str)
    
    elif cmd == "scan":
        cmd_scan()
    
    elif cmd == "build":
        cmd_build()
    
    elif cmd == "web":
        cmd_web()
    
    elif cmd == "status":
        cmd_status()
    
    elif cmd in ("help", "--help", "-h"):
        show_help()
    
    else:
        print(f"未知命令: {cmd}")
        show_help()


if __name__ == "__main__":
    main()
