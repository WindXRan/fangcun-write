#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄下载器格式修复脚本。

问题：
1. TomatoNovelDownloader v2.4.11 无视 novel_format: txt 配置，强制输出 epub
2. 章节文件名和首行标题重复（Bug）

修复步骤：
1. 从已下载的 epub 提取正文，合并为单文件 txt
2. 如果 epub 不存在，从散装 txt 文件修复并合并
3. 对散装缓存文件也做重命名修复
"""
import os, sys, re, zipfile, html
from pathlib import Path

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False
    print("[信息] ebooklib 未安装，将使用 zipfile 模式提取 epub")

DOWNLOADER_DIR = Path(__file__).parent


def find_epub_files():
    """查找下载器目录下所有 epub 文件"""
    return sorted(DOWNLOADER_DIR.glob("**/*.epub"))


def extract_text_from_epub(epub_path):
    """
    从 epub 提取纯文本正文（需要 ebooklib）。
    回退到 extract_text_from_epub_zip（基于 zipfile）。"""
    if not HAS_EBOOKLIB:
        print("  ebooklib 未安装，改用 zipfile 模式...")
        return extract_text_from_epub_zip(epub_path)

    book = epub.read_epub(str(epub_path))
    chapters = []

    for item in book.get_items():
        if item.get_type() == 9:  # ITEM_DOCUMENT
            content = item.get_content().decode('utf-8', errors='replace')
            text = html_text(content)
            text = text.strip()
            if text:
                chapters.append(text)

    return chapters


def html_text(html_content):
    """从 HTML 提取纯文本"""
    text = re.sub(r'<head>.*?</head>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_text_from_epub_zip(epub_path):
    """
    备用方法：直接用 zipfile 提取 epub 中的 xhtml 文本。
    ebooklib 可能解析失败时使用。
    """
    chapters = []
    with zipfile.ZipFile(epub_path, 'r') as z:
        # 找出所有 xhtml/html 文件
        html_files = sorted([f for f in z.namelist()
                            if f.endswith('.xhtml') or f.endswith('.html')])
        # 排除封面、目录等
        text_files = [f for f in html_files
                     if not any(x in f.lower() for x in
                               ['cover', 'toc', 'nav', 'title_page', 'table_of_contents'])]

        for filename in text_files:
            content = z.read(filename).decode('utf-8', errors='replace')
            text = html_text(content).strip()
            if text:
                chapters.append(text)

    return chapters


def fix_cache_chapters(author, book_name):
    """
    修复散装缓存文件的标题重复问题。
    文件名: 第N章 第N章<标题>第N章<标题>.txt → 第N章 <标题>.txt
    首行:   第N章<标题>第N章<标题> → 第N章<标题>
    """
    cache_dir = DOWNLOADER_DIR / "projects" / author / book_name / "_cache" / "chapters"
    if not cache_dir.exists():
        print(f"  [跳过] 缓存目录不存在: {cache_dir}")
        return []

    files = sorted(cache_dir.glob("*.txt"))
    print(f"  找到 {len(files)} 个缓存章节文件")

    fixed_files = []
    for fpath in files:
        filename = fpath.name
        # 修复模式: 第N章 第N章<标题>第N章<标题>.txt
        # → 第N章 <标题>.txt
        m = re.match(r'(第\d+章)\s*\1(.+?)\1(.+?)\.txt', filename)
        if m:
            new_name = f"{m.group(1)} {m.group(2)}.txt"
            new_path = fpath.parent / new_name
            # 去重检查
            counter = 1
            while new_path.exists():
                stem = new_path.stem
                new_path = fpath.parent / f"{stem}_{counter}.txt"
                counter += 1
            os.rename(str(fpath), str(new_path))
            fpath = new_path
            fixed_files.append(fpath)

        # 修复首行标题重复
        content = fpath.read_text(encoding='utf-8', errors='replace')
        first_newline = content.find('\n')
        first_line = content[:first_newline] if first_newline > 0 else content

        # 模式: 第N章<标题>第N章<标题>
        m2 = re.match(r'(第\d+章)(.+)\1(.+)', first_line.strip())
        if m2:
            correct_title = f"{m2.group(1)}{m2.group(2)}"
            rest = content[first_newline:] if first_newline > 0 else ''
            fpath.write_text(correct_title + rest, encoding='utf-8')
            fixed_files.append(fpath)

    if fixed_files:
        print(f"  修复了 {len(fixed_files)} 个文件的标题重复")

    return sorted(cache_dir.glob("*.txt"))


def merge_to_txt(chapters_or_files, output_path):
    """
    合并章节到单文件 txt。
    chapters_or_files: 文本列表 或 文件路径列表
    """
    print(f"  合并中...")
    with open(output_path, 'w', encoding='utf-8') as out:
        if chapters_or_files and hasattr(chapters_or_files[0], 'read_text'):
            # 文件路径列表
            for i, fpath in enumerate(chapters_or_files):
                content = fpath.read_text(encoding='utf-8', errors='replace')
                if i > 0:
                    out.write('\n')
                out.write(content.strip())
                out.write('\n')
        else:
            # 文本列表
            for i, text in enumerate(chapters_or_files):
                if i > 0:
                    out.write('\n')
                out.write(text.strip())
                out.write('\n')

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✓ 已生成: {output_path.name} ({size_kb:.0f} KB)")


def main():
    print("=" * 60)
    print("番茄小说下载器 - 格式修复工具")
    print("=" * 60)

    epubs = find_epub_files()

    if epubs:
        print(f"\n找到 {len(epubs)} 个 epub 文件:")
        for ep in epubs:
            rel = ep.relative_to(DOWNLOADER_DIR)
            size_kb = ep.stat().st_size / 1024
            print(f"  {rel} ({size_kb:.0f} KB)")

        epub_path = epubs[0]
        print(f"\n从 epub 提取正文: {epub_path.name}")

        try:
            chapters = extract_text_from_epub(epub_path)
        except Exception as e:
            print(f"  ebooklib 解析失败: {e}")
            print(f"  改用 zip 直接提取...")
            chapters = extract_text_from_epub_zip(epub_path)

        if chapters:
            print(f"  提取到 {len(chapters)} 章")
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', epub_path.stem)
            output_name = safe_name + ".txt"
            output_path = epub_path.parent / output_name
            merge_to_txt(chapters, output_path)

            print(f"\n✓ 完成！合并文件: {output_path}")
        else:
            print("  [错误] 未能从 epub 提取到任何章节")
    else:
        print("\n未找到 epub 文件，尝试从散装缓存修复...")

    # 尝试修复散装缓存文件
    projects_dir = DOWNLOADER_DIR / "projects"
    if projects_dir.exists():
        for author_dir in projects_dir.iterdir():
            if author_dir.is_dir():
                for book_dir in author_dir.iterdir():
                    if book_dir.is_dir():
                        print(f"\n处理: {author_dir.name}/{book_dir.name}")
                        chap_files = fix_cache_chapters(author_dir.name, book_dir.name)
                        if chap_files:
                            output_name = f"{book_dir.name}.txt"
                            output_path = DOWNLOADER_DIR / output_name
                            merge_to_txt(chap_files, output_path)

    print("\n" + "=" * 60)
    print("提示: 如需彻底解决 config.yml 不生效问题，")
    print("请在 run.py 启动下载器时加上 --data-dir 参数：")
    print("  --data-dir .agents/skills/fanqie-hub/downloader")
    print("=" * 60)


if __name__ == "__main__":
    main()
