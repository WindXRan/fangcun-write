"""
story-import: 标准化导入工具
用 LLM 识别书名、作者、章节、番外，输出到标准目录结构。

用法：
  python story_import.py <txt文件路径>
  python story_import.py <txt文件路径> --output <输出目录>
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path


def read_file(txt_path):
    """读取文件，自动检测编码。"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(txt_path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            print("错误：无法读取文件（编码问题）")
            return None


def split_chapters(text):
    """拆分章节和番外。"""
    # 找到"全文完"标记
    end_match = re.search(r'—————全文完—————|全文完', text)
    if end_match:
        main_text = text[:end_match.start()]
        fanwai_after_text = text[end_match.end():]
    else:
        main_text = text
        fanwai_after_text = ""
    
    # 按章节和番外分割
    split_pattern = r'\n(?=第\s*\d+\s*章|番外)'
    parts = re.split(split_pattern, main_text)
    
    chapters = []
    fanwai_before_text = ""
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # 检查是否是番外
        fanwai_match = re.match(r'(番外\s*.*)\n', part)
        if fanwai_match:
            fanwai_before_text += "\n\n" + part
            continue
        
        # 检查是否是章节
        m = re.match(r'(第\s*\d+\s*章\s*.*)\n', part)
        if not m:
            m = re.match(r'(第\s*\d+\s*章\s+.+?)(?:\s+第\s*\d+\s*章|\s+)', part)
        
        if m:
            chapter_header = m.group(1).strip()
            chapter_num_match = re.match(r'第\s*(\d+)\s*章', chapter_header)
            if chapter_num_match:
                chapter_num = int(chapter_num_match.group(1))
                content = part.strip()
                chapters.append({
                    'num': chapter_num,
                    'content': content,
                    'is_fanwai': False
                })
    
    # 处理番外
    all_fanwai_text = fanwai_before_text + "\n\n" + fanwai_after_text if fanwai_before_text else fanwai_after_text
    if all_fanwai_text.strip():
        fanwai_pattern = r'\n(?=番外)'
        fanwai_parts = re.split(fanwai_pattern, all_fanwai_text)
        
        for part in fanwai_parts:
            part = part.strip()
            if not part:
                continue
            
            m = re.match(r'(番外\s*.*)\n', part)
            if m:
                fanwai_header = m.group(1).strip()
                chapters.append({
                    'num': -1,
                    'content': part.strip(),
                    'is_fanwai': True,
                    'fanwai_title': fanwai_header
                })
    
    # 按章节号排序
    chapters.sort(key=lambda x: (x['is_fanwai'], x['num']))
    
    return chapters


def clean_html(text):
    """清理HTML标签。"""
    text = re.sub(r'<p>', '', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)
    return text.strip()


def import_novel(txt_path, output_dir=None):
    """导入小说。"""
    txt_path = Path(txt_path)
    
    if not txt_path.exists():
        print(f"错误：文件不存在 {txt_path}")
        return False
    
    # 读取文件
    print(f"读取文件：{txt_path}")
    content = read_file(txt_path)
    if not content:
        return False
    
    # 从目录结构推断作者和书名
    parts = txt_path.parts
    author = "未知"
    title = txt_path.stem
    
    for i, part in enumerate(parts):
        if part == 'projects' and i + 2 < len(parts):
            author = parts[i + 1]
            title = parts[i + 2]
            break
    
    print(f"  书名：{title}")
    print(f"  作者：{author}")
    
    # 拆分章节
    print("拆分章节...")
    chapters = split_chapters(content)
    
    if not chapters:
        print("错误：无法拆分章节")
        return False
    
    # 分离正文和番外
    main_chapters = [ch for ch in chapters if not ch.get('is_fanwai', False)]
    fanwai_chapters = [ch for ch in chapters if ch.get('is_fanwai', False)]
    
    print(f"  正文章节：{len(main_chapters)} 章")
    print(f"  番外章节：{len(fanwai_chapters)} 章")
    
    # 确定输出目录
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = Path(f"projects/{author}/{title}/_cache")
    
    # 检查是否有重要文件需要保护
    _check_and_backup_important_files(output_path)
    
    # 创建目录
    chapters_dir = output_path / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入正文章节
    print(f"写入正文章节到：{chapters_dir}")
    for ch in main_chapters:
        chapter_file = chapters_dir / f"第{ch['num']:03d}章.txt"
        with open(chapter_file, 'w', encoding='utf-8') as f:
            content = clean_html(ch['content'])
            lines = content.split('\n')
            ch_title = lines[0].strip() if lines else f"第{ch['num']}章"
            if not ch_title.startswith('第'):
                ch_title = f"第{ch['num']}章 {ch_title}"
            f.write(ch_title + '\n\n' + '\n'.join(lines[1:]))
    
    # 写入番外章节
    if fanwai_chapters:
        fanwai_dir = output_path / "fanwai"
        fanwai_dir.mkdir(parents=True, exist_ok=True)
        print(f"写入番外章节到：{fanwai_dir}")
        for i, ch in enumerate(fanwai_chapters, 1):
            fanwai_title = ch.get('fanwai_title', f'番外{i}')
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', fanwai_title)
            fanwai_file = fanwai_dir / f"{safe_title}.txt"
            with open(fanwai_file, 'w', encoding='utf-8') as f:
                f.write(clean_html(ch['content']))
    
    # 尝试从status.json获取元信息（番茄下载器输出）
    status_info = _load_status_json(txt_path, output_path)
    
    # 生成 _header.txt
    header_file = output_path / "_header.txt"
    print(f"生成：{header_file}")
    with open(header_file, 'w', encoding='utf-8') as f:
        if status_info:
            # 使用status.json中的信息
            f.write(f"书名：{status_info.get('book_name', title)}\n")
            f.write(f"作者：{status_info.get('author', author)}\n")
            f.write(f"状态：连载中\n")
            f.write(f"评分：{status_info.get('score', '未知')}\n")
            f.write(f"字数：{status_info.get('word_count', '未知')}\n")
            f.write(f"章节：{len(main_chapters)}\n")
            if fanwai_chapters:
                f.write(f"番外：{len(fanwai_chapters)}\n")
            f.write(f"分类：{status_info.get('category', '未知')}\n")
            f.write(f"标签：{status_info.get('tags', '未知')}\n")
            f.write(f"\n简介：\n{status_info.get('description', '未知')}\n")
        else:
            # 使用解析的信息
            f.write(f"书名：{title}\n")
            f.write(f"作者：{author}\n")
            f.write(f"状态：未知\n")
            f.write(f"字数：未知\n")
            f.write(f"章节：{len(main_chapters)}\n")
            if fanwai_chapters:
                f.write(f"番外：{len(fanwai_chapters)}\n")
            f.write(f"分类：未知\n")
            f.write(f"标签：未知\n")
            f.write(f"\n简介：未知\n")
        f.write(f"\n========================================\n\n")
        f.write(f"【第一卷】\n")
    
    # 生成 _toc.txt
    toc_file = output_path / "_toc.txt"
    print(f"生成：{toc_file}")
    with open(toc_file, 'w', encoding='utf-8') as f:
        f.write(f"总章数: {len(main_chapters)}\n")
        if fanwai_chapters:
            f.write(f"番外数: {len(fanwai_chapters)}\n")
        f.write(f"\n\n")
        f.write(f"【正文】\n")
        for ch in main_chapters:
            first_line = ch['content'].split('\n')[0].strip()
            f.write(f"{first_line}\n")
        if fanwai_chapters:
            f.write(f"\n【番外】\n")
            for ch in fanwai_chapters:
                first_line = ch['content'].split('\n')[0].strip()
                f.write(f"{first_line}\n")
    
    print(f"\n导入完成！")
    print(f"  输出目录：{output_path}")
    print(f"  正文章节：{len(main_chapters)} 章")
    if fanwai_chapters:
        print(f"  番外章节：{len(fanwai_chapters)} 章")
    
    return True


def _load_status_json(txt_path, output_path):
    """尝试加载status.json（番茄下载器输出）。"""
    # 可能的位置：同目录下、父目录下、output_path下
    candidates = [
        txt_path.parent / "status.json",
        txt_path.parent.parent / "status.json",
        output_path.parent / "status.json",
    ]
    
    for path in candidates:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('book_name') or data.get('author'):
                    print(f"  从 status.json 读取元信息: {path}")
                    return data
            except Exception:
                pass
    
    return None


def _check_and_backup_important_files(output_path):
    """检查并备份重要文件，防止导入时丢失。"""
    import shutil
    
    important_files = [
        "events.json",
        "story_skeleton.md",
        "adaptation_strategy.md",
        "book_data.json",
    ]
    
    backup_dir = output_path / "_backup"
    has_important = False
    
    for fname in important_files:
        file_path = output_path / fname
        if file_path.exists():
            if not has_important:
                backup_dir.mkdir(parents=True, exist_ok=True)
                has_important = True
                print(f"  [备份] 检测到重要文件，备份到 {backup_dir}/")
            
            backup_path = backup_dir / fname
            shutil.copy2(file_path, backup_path)
            print(f"    - {fname}")


def main():
    parser = argparse.ArgumentParser(description='story-import: 标准化导入工具')
    parser.add_argument('txt_path', help='原始txt文件路径')
    parser.add_argument('--output', '-o', help='输出目录')
    
    args = parser.parse_args()
    
    success = import_novel(args.txt_path, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
