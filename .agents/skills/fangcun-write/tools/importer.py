"""
fangcun 小说导入器 —— 把原始小说文件导入为标准项目结构。

输入格式支持：
  1. 散装 txt 目录（fanqie-hub 输出：0001_第1章 xxx.txt）
  2. 合并 txt（单文件，按「第N章」分割）
  3. EPUB（通过 zipfile 提取）

输出结构：
  projects/{author}/{book_name}/
  ├── 作品信息/project.xml
  ├── 正文/正文/第1章章名.xml
  ├── 正文/正文/第2章章名.xml
  └── ...
"""
import os, sys, re, zipfile, html
from pathlib import Path

# ─── 路径正则 ────────────────────────────────────────────

# 匹配 "第N章" 或 "第N章章名"
_CHAPTER_PATTERN = re.compile(r'第(\d+)章\s*([^\n]*)')

# 匹配 fanqie-hub 散装格式：0001_第1章 章名.txt
_FANQIE_FILE_PATTERN = re.compile(r'^\d+_第(\d+)章\s*(.+)\.txt$')

# 匹配已有标准格式：第N篇章名.txt
_STANDARD_FILE_PATTERN = re.compile(r'^第(\d+)章(.+)\.txt$')

# 匹配已有 XML 格式：<chapter number="N">
_XML_CHAPTER_PATTERN = re.compile(r'<chapter\s+number="(\d+)"')


def detect_source(source: str) -> str:
    """检测输入源类型：chapter_dir / merged_txt / epub / unknown"""
    p = Path(source)
    if not p.exists():
        return "not_found"
    if p.is_dir():
        # 检查是否包含章节文件
        txts = list(p.glob("*.txt"))
        xmls = list(p.glob("*.xml"))
        if txts or xmls:
            return "chapter_dir"
        return "empty_dir"
    suffix = p.suffix.lower()
    if suffix == ".epub":
        return "epub"
    if suffix == ".txt":
        return "merged_txt"
    return "unknown"


def parse_chapter_number(filename: str) -> tuple[int, str]:
    """从文件名解析章节号和标题。返回 (章号, 标题)。"""
    # fanqie 格式：0001_第1章 章名.txt
    m = _FANQIE_FILE_PATTERN.match(filename)
    if m:
        return int(m.group(1)), m.group(2).strip()

    # 标准格式：第1篇章名.txt
    m = _STANDARD_FILE_PATTERN.match(filename)
    if m:
        return int(m.group(1)), m.group(2).strip()

    # XML 格式：第1章.xml
    m = re.match(r'^第(\d+)章\.xml$', filename)
    if m:
        return int(m.group(1)), ""

    # 纯数字：1.txt
    m = re.match(r'^(\d+)\.txt$', filename)
    if m:
        return int(m.group(1)), ""

    # 数字开头：01 章名.txt
    m = re.match(r'^(\d+)[\s_.-]+(.+)\.txt$', filename)
    if m:
        return int(m.group(1)), m.group(2).strip()

    raise ValueError(f"无法解析章节号: {filename}")


def extract_chapters_from_merged(text: str) -> list[tuple[int, str, str]]:
    """从合并 txt 中按「第N章」分割。返回 [(章号, 标题, 正文)]。"""
    chapters = []
    # 用「第N章」作为分隔符
    parts = _CHAPTER_PATTERN.split(text)
    # parts 格式：["前缀", "1", "章名", "正文...", "2", "章名", "正文..."]
    i = 0
    while i < len(parts):
        # 跳过开头的前缀（第1章之前的内容）
        if not parts[i].strip() or i == 0:
            i += 1
            continue
        try:
            ch_num = int(parts[i])
            title = parts[i + 1].strip() if i + 1 < len(parts) else ""
            body = parts[i + 2].strip() if i + 2 < len(parts) else ""
            chapters.append((ch_num, title, body))
            i += 3
        except (ValueError, IndexError):
            i += 1
    return chapters


def extract_chapters_from_epub(epub_path: str) -> list[tuple[int, str, str]]:
    """从 epub 提取章节。返回 [(章号, 标题, 正文)]。"""
    chapters = []
    with zipfile.ZipFile(epub_path, 'r') as z:
        html_files = sorted([
            f for f in z.namelist()
            if f.endswith('.xhtml') or f.endswith('.html')
        ])
        # 排除封面/目录
        text_files = [
            f for f in html_files
            if not any(x in f.lower() for x in
                      ['cover', 'toc', 'nav', 'title_page', 'table_of_contents'])
        ]
        ch_num = 1
        for filename in text_files:
            content = z.read(filename).decode('utf-8', errors='replace')
            # 从 HTML 提取纯文本
            text = _html_to_text(content).strip()
            if not text:
                continue
            # 提取标题（首行）
            lines = text.split('\n', 1)
            title = lines[0].strip() if lines else ""
            body = lines[1].strip() if len(lines) > 1 else ""
            # 尝试从标题中解析章节号
            m = _CHAPTER_PATTERN.match(title)
            if m:
                ch_num = int(m.group(1))
            chapters.append((ch_num, title, body))
            ch_num += 1
    return chapters


def _html_to_text(html_content: str) -> str:
    """从 HTML 提取纯文本。"""
    text = re.sub(r'<head>.*?</head>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def import_from_dir(source_dir: str) -> list[tuple[int, str, str]]:
    """从散装 txt 目录导入。返回 [(章号, 标题, 正文)]。"""
    p = Path(source_dir)
    chapters = []

    for f in sorted(p.iterdir()):
        if f.suffix not in ('.txt', '.xml'):
            continue
        try:
            ch_num, title = parse_chapter_number(f.name)
        except ValueError:
            continue

        content = f.read_text(encoding='utf-8', errors='replace')

        # 如果是 XML 格式（<chapter><content>），提取 content
        if f.suffix == '.xml':
            m = re.search(r'<content>(.*?)</content>', content, re.DOTALL)
            if m:
                content = m.group(1).strip()

        chapters.append((ch_num, title, content))

    return sorted(chapters, key=lambda x: x[0])


def import_from_merged(filepath: str) -> list[tuple[int, str, str]]:
    """从合并 txt 导入。返回 [(章号, 标题, 正文)]。"""
    text = Path(filepath).read_text(encoding='utf-8', errors='replace')
    return extract_chapters_from_merged(text)


def import_from_epub(filepath: str) -> list[tuple[int, str, str]]:
    """从 epub 导入。返回 [(章号, 标题, 正文)]。"""
    return extract_chapters_from_epub(filepath)


def build_project_xml(book_name: str, author: str, channel: str,
                      total_chapters: int) -> str:
    """生成 作品信息/project.xml。"""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<project>
  <story_name>{_escape_xml(book_name)}</story_name>
  <channel>{_escape_xml(channel)}</channel>
  <perspective>第三人称</perspective>
  <author>{_escape_xml(author)}</author>
  <total_chapters>{total_chapters}</total_chapters>
  <source_book>{_escape_xml(book_name)}</source_book>
</project>'''


def _escape_xml(s: str) -> str:
    """XML 转义。"""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def write_chapter_xml(project_dir: str, ch_num: int, title: str, content: str):
    """写入单章 XML 文件。"""
    chap_dir = Path(project_dir) / "正文" / "正文"
    chap_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[<>:"/\\|?*]', '', title) if title else ""
    filename = f"第{ch_num}章{safe_title}.xml" if safe_title else f"第{ch_num}章.xml"
    filepath = chap_dir / filename

    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<chapter number="{ch_num}">
  <content>
{content}
  </content>
</chapter>'''
    filepath.write_text(xml_content, encoding='utf-8')
    return filepath


def run_import(book_name: str, author: str, source: str,
               channel: str = "男频",
               project_dir: str | None = None) -> dict:
    """
    执行导入，返回统计信息。

    Parameters
    ----------
    book_name : str
        书名
    author : str
        作者
    source : str
        源路径（txt 文件 / 章节目录 / epub）
    channel : str
        频道（男频/女频）
    project_dir : str | None
        输出目录，默认 projects/{author}/{book_name}/
    """
    source_type = detect_source(source)
    if source_type == "not_found":
        return {"success": False, "error": f"源路径不存在: {source}"}
    if source_type == "empty_dir":
        return {"success": False, "error": f"源目录为空: {source}"}
    if source_type == "unknown":
        return {"success": False, "error": f"不支持的源格式: {source}"}

    # 1. 提取章节
    if source_type == "chapter_dir":
        chapters = import_from_dir(source)
    elif source_type == "merged_txt":
        chapters = import_from_merged(source)
    elif source_type == "epub":
        chapters = import_from_epub(source)
    else:
        return {"success": False, "error": f"未处理的源类型: {source_type}"}

    if not chapters:
        return {"success": False, "error": "未提取到任何章节"}

    # 2. 确定输出目录
    base_dir = Path.cwd()
    if project_dir:
        out_dir = Path(project_dir)
    else:
        safe_book = re.sub(r'[<>:"/\\|?*]', '_', book_name)
        safe_author = re.sub(r'[<>:"/\\|?*]', '_', author) if author else "unknown"
        out_dir = base_dir / "projects" / safe_author / safe_book

    # 3. 创建目录结构
    dirs = [
        out_dir / "作品信息" / "主题",
        out_dir / "作品信息" / "设定" / "角色",
        out_dir / "作品信息" / "设定" / "背景",
        out_dir / "作品信息" / "设定" / "势力",
        out_dir / "作品信息" / "设定" / "地点",
        out_dir / "作品信息" / "设定" / "物品",
        out_dir / "正文" / "正文",
        out_dir / "正文" / "章纲",
        out_dir / "正文" / "卷纲",
        out_dir / "拆文库",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 4. 写入章节文件
    written = []
    for ch_num, title, content in chapters:
        fp = write_chapter_xml(str(out_dir), ch_num, title, content)
        written.append(str(fp.relative_to(base_dir) if fp.is_relative_to(base_dir) else fp))

    # 5. 生成 project.xml
    project_xml = build_project_xml(book_name, author, channel, len(chapters))
    proj_file = out_dir / "作品信息" / "project.xml"
    proj_file.write_text(project_xml, encoding='utf-8')

    # 6. 生成占位总纲（导入的书一定有总纲，后续可用 open-book 精修）
    outline_file = out_dir / "作品信息" / "主题" / "总纲.xml"
    if not outline_file.exists():
        outline_file.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<outline>\n'
            f'  <story_name>{_escape_xml(book_name)}</story_name>\n'
            f'  <total_chapters>{len(chapters)}</total_chapters>\n'
            f'  <summary>已导入 {len(chapters)} 章，待运行 open-book 生成完整总纲</summary>\n'
            f'</outline>\n',
            encoding='utf-8'
        )

    # 7. 生成占位卷纲（同上）
    volume_file = out_dir / "正文" / "卷纲" / "卷纲.xml"
    if not volume_file.exists():
        volume_file.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<volumes>\n'
            f'  <volume number="1" chapters="1-{len(chapters)}">\n'
            f'    <name>全书</name>\n'
            f'    <goal>待拆解</goal>\n'
            f'    <emotional_arc>待拆解</emotional_arc>\n'
            f'    <key_events>待拆解</key_events>\n'
            f'    <climax>待拆解</climax>\n'
            f'  </volume>\n'
            f'</volumes>\n',
            encoding='utf-8'
        )

    return {
        "success": True,
        "book_name": book_name,
        "author": author,
        "total_chapters": len(chapters),
        "project_dir": str(out_dir),
        "files_written": len(written),
        "chapter_files": written[:5],  # 前5章示例
        "project_xml": str(proj_file),
    }


# ─── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="fangcun 小说导入器")
    parser.add_argument("book_name", help="书名")
    parser.add_argument("source", help="源路径（txt/epub/目录）")
    parser.add_argument("--author", default="", help="作者")
    parser.add_argument("--channel", default="男频", choices=["男频", "女频"],
                        help="频道")
    parser.add_argument("--project-dir", default=None, help="输出目录")
    args = parser.parse_args()

    result = run_import(
        book_name=args.book_name,
        author=args.author,
        source=args.source,
        channel=args.channel,
        project_dir=args.project_dir,
    )

    if result["success"]:
        print(f"\n✓ 导入完成")
        print(f"  书名: {result['book_name']}")
        print(f"  作者: {result['author']}")
        print(f"  章节: {result['total_chapters']} 章")
        print(f"  输出: {result['project_dir']}")
        print(f"  文件: {result['files_written']} 个章节文件")
        print(f"  project.xml: {result['project_xml']}")
    else:
        print(f"\n✗ 导入失败: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
