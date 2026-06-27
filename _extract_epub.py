"""从 epub 提取章节到项目目录"""
import sys, re, html
from pathlib import Path
from ebooklib import epub

epub_path = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fanqie-hub\downloader\我冒充富二代？身份都是自己给的.epub'

author = "提笔忘章节"
book_name = "我冒充富二代？身份都是自己给的"
base_dir = Path(r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\projects')
proj_dir = base_dir / author / book_name
chapters_dir = proj_dir / "正文" / "正文"
chapters_dir.mkdir(parents=True, exist_ok=True)

book = epub.read_epub(str(epub_path))

docs = []
for item in book.get_items():
    if item.get_type() == 9:
        content = item.get_content().decode('utf-8', errors='replace')
        text = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        text = html.unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        if text:
            docs.append((item.get_name(), text))

chapter_files = []
for name, text in docs:
    m = re.match(r'chapter_(\d+)', name)
    if m:
        ch_num = int(m.group(1))
        # 取出第一行作为可能的标题
        lines = text.split('\n', 1)
        first_line = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ''
        filename = f"第{ch_num}章 {first_line}.txt" if first_line else f"第{ch_num}章.txt"
        fp = chapters_dir / filename
        fp.write_text(text.strip(), encoding='utf-8')
        chapter_files.append((ch_num, filename))

chapter_files.sort()
print(f"提取完成：{len(chapter_files)} 章 → {chapters_dir}")
for n, f in chapter_files[:5]:
    print(f"  {f}")
print(f"  ...")
for n, f in chapter_files[-3:]:
    print(f"  {f}")

# 创建 project.xml
project_xml = proj_dir / "作品信息"
project_xml.mkdir(parents=True, exist_ok=True)
xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project>
  <story_name>{book_name}</story_name>
  <channel>男频</channel>
  <perspective>第一人称</perspective>
  <author>{author}</author>
  <total_chapters>{len(chapter_files)}</total_chapters>
  <source_book>{book_name}</source_book>
</project>
"""
(project_xml / "project.xml").write_text(xml_content.strip(), encoding='utf-8')
print(f"\nproject.xml 已创建")
print(f"\n导入完成！项目路径：{proj_dir}")
