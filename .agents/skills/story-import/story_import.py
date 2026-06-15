"""
story-import: 标准化导入工具
替代手动拆章，自动完成：
1. 解析原始txt（书名、作者、简介、章节）
2. 拆章到 chapters/ 目录
3. 生成 _header.txt 和 _toc.txt
"""

import os
import re
import sys
import argparse
from pathlib import Path


def parse_header(text: str) -> dict:
    """解析书籍头部信息"""
    info = {}
    
    # 书名
    m = re.search(r'书名[：:]\s*(.+)', text)
    if m:
        info['title'] = m.group(1).strip()
    
    # 作者
    m = re.search(r'作者[：:]\s*(.+)', text)
    if m:
        info['author'] = m.group(1).strip()
    
    # book_id
    m = re.search(r'book_id[=:]\s*(\d+)', text)
    if m:
        info['book_id'] = m.group(1).strip()
    
    # 状态
    m = re.search(r'状态[：:]\s*(.+)', text)
    if m:
        info['status'] = m.group(1).strip()
    
    # 评分
    m = re.search(r'评分[：:]\s*(.+)', text)
    if m:
        info['score'] = m.group(1).strip()
    
    # 字数
    m = re.search(r'字数[：:]\s*(\d+)', text)
    if m:
        info['word_count'] = m.group(1).strip()
    
    # 分类
    m = re.search(r'分类[：:]\s*(.+)', text)
    if m:
        info['category'] = m.group(1).strip()
    
    # 标签
    m = re.search(r'标签[：:]\s*(.+)', text)
    if m:
        info['tags'] = m.group(1).strip()
    
    return info


def parse_synopsis(text: str) -> str:
    """解析简介"""
    # 找到"简介："后面的内容，直到第一个"==="或"【第"
    m = re.search(r'简介[：:]\s*\n(.*?)(?=\n={10}|\n【第|\Z)', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def split_chapters(text: str) -> list:
    """拆分章节"""
    # 匹配"第X章"的模式
    pattern = r'\n(?=第\d+章)'
    parts = re.split(pattern, text)
    
    chapters = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # 检查是否是章节内容（以"第X章"开头）
        m = re.match(r'(第\d+章\s*.*)\n', part)
        if m:
            chapter_header = m.group(1).strip()
            chapter_num_match = re.match(r'第(\d+)章', chapter_header)
            if chapter_num_match:
                chapter_num = int(chapter_num_match.group(1))
                # 保留章节标题行在正文中
                content = part.strip()
                chapters.append({
                    'num': chapter_num,
                    'content': content
                })
    
    return chapters


def generate_header(info: dict, synopsis: str, chapter_count: int) -> str:
    """生成 _header.txt"""
    lines = []
    lines.append(f"书名：{info.get('title', '未知')}")
    lines.append(f"作者：{info.get('author', '未知')}")
    if 'book_id' in info:
        lines.append(f"book_id={info['book_id']}")
    lines.append(f"状态：{info.get('status', '未知')}")
    lines.append(f"评分：{info.get('score', '未知')}")
    lines.append(f"字数：{info.get('word_count', '未知')}")
    lines.append(f"章节：{chapter_count}")
    lines.append(f"分类：{info.get('category', '未知')}")
    lines.append(f"标签：{info.get('tags', '未知')}")
    lines.append("")
    lines.append("简介：")
    lines.append(synopsis)
    lines.append("")
    lines.append("=" * 40)
    lines.append("")
    lines.append("【第一卷】")
    
    return "\n".join(lines)


def generate_toc(chapters: list) -> str:
    """生成 _toc.txt"""
    lines = []
    lines.append(f"总章数: {len(chapters)}")
    lines.append("")
    lines.append("")
    for ch in chapters:
        first_line = ch['content'].split('\n')[0].strip()
        lines.append(first_line)
    
    return "\n".join(lines)


def import_novel(txt_path: str, output_dir: str = None):
    """导入小说"""
    txt_path = Path(txt_path)
    
    if not txt_path.exists():
        print(f"错误：文件不存在 {txt_path}")
        return False
    
    # 读取文件
    print(f"读取文件：{txt_path}")
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(txt_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            print("错误：无法读取文件（编码问题）")
            return False
    
    # 解析头部信息
    print("解析书籍信息...")
    info = parse_header(content)
    synopsis = parse_synopsis(content)
    
    if not info.get('title'):
        print("警告：无法解析书名，使用文件名")
        info['title'] = txt_path.stem
    
    print(f"  书名：{info.get('title', '未知')}")
    print(f"  作者：{info.get('author', '未知')}")
    
    # 拆分章节
    print("拆分章节...")
    chapters = split_chapters(content)
    
    if not chapters:
        print("错误：无法拆分章节")
        return False
    
    print(f"  章节数：{len(chapters)}")
    
    # 确定输出目录
    if output_dir:
        output_path = Path(output_dir)
    else:
        # 默认目录：projects/{作者}/{书名}/_cache/
        # 从文件内容中获取作者和书名，而不是文件名
        author = info.get('author', '未知')
        title = info.get('title', txt_path.stem)
        output_path = Path(f"projects/{author}/{title}/_cache")
    
    # 创建目录
    chapters_dir = output_path / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入章节文件
    print(f"写入章节到：{chapters_dir}")
    for ch in chapters:
        chapter_file = chapters_dir / f"第{ch['num']}章.txt"
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(ch['content'])
    
    # 生成 _header.txt
    header_file = output_path / "_header.txt"
    print(f"生成：{header_file}")
    with open(header_file, 'w', encoding='utf-8') as f:
        f.write(generate_header(info, synopsis, len(chapters)))
    
    # 生成 _toc.txt
    toc_file = output_path / "_toc.txt"
    print(f"生成：{toc_file}")
    with open(toc_file, 'w', encoding='utf-8') as f:
        f.write(generate_toc(chapters))
    
    print(f"\n导入完成！")
    print(f"  输出目录：{output_path}")
    print(f"  章节数：{len(chapters)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='story-import: 标准化导入工具')
    parser.add_argument('txt_path', help='原始txt文件路径')
    parser.add_argument('--output', '-o', help='输出目录（默认：projects/{作者}/{书名}/_cache/）')
    
    args = parser.parse_args()
    
    success = import_novel(args.txt_path, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
