"""
story-export: 标准化导出工具
合并章节为完整小说，格式与导入格式一致，支持互转。

用法：
  python story_export.py <项目目录>
  python story_export.py <项目目录> --output <输出文件>
"""

import os
import re
import sys
import argparse
from pathlib import Path


def natural_sort_key(s):
    """自然排序键。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def export_novel(project_dir, output_file=None):
    """导出小说。"""
    project_dir = Path(project_dir)
    
    if not project_dir.exists():
        print(f"错误：项目目录不存在 {project_dir}")
        return False
    
    # 查找章节目录
    chapters_dir = project_dir / "chapters"
    if not chapters_dir.exists():
        # 尝试 _cache/chapters
        chapters_dir = project_dir / "_cache" / "chapters"
    
    if not chapters_dir.exists():
        print(f"错误：章节目录不存在")
        return False
    
    # 获取所有章节文件
    chapter_files = sorted(
        [f for f in chapters_dir.glob("第*章*.txt")],
        key=lambda f: int(re.search(r'第(\d+)章', f.stem).group(1)) if re.search(r'第(\d+)章', f.stem) else 0
    )
    
    if not chapter_files:
        print(f"错误：没有找到章节文件")
        return False
    
    # 查找番外目录
    fanwai_dir = project_dir / "fanwai"
    if not fanwai_dir.exists():
        fanwai_dir = project_dir / "_cache" / "fanwai"
    
    fanwai_files = []
    if fanwai_dir.exists():
        fanwai_files = sorted(fanwai_dir.glob("*.txt"))
    
    # 读取 _header.txt 获取书名等信息
    header_file = project_dir / "_header.txt"
    if not header_file.exists():
        header_file = project_dir / "_cache" / "_header.txt"
    
    title = project_dir.name
    author = "未知"
    
    if header_file.exists():
        with open(header_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('书名：'):
                    title = line.split('：', 1)[-1].strip()
                elif line.startswith('作者：'):
                    author = line.split('：', 1)[-1].strip()
    
    # 确定输出文件
    if not output_file:
        export_dir = project_dir / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        output_file = export_dir / f"{title}.txt"
    
    # 合并内容
    merged_content = []
    total_chars = 0
    
    # 合并正文
    for f in chapter_files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        if content:
            merged_content.append(content)
            total_chars += len(content)
    
    # 合并番外
    for f in fanwai_files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        if content:
            merged_content.append(content)
            total_chars += len(content)
    
    # 写入输出文件
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入头部信息
        f.write(f"书名：{title}\n")
        f.write(f"作者：{author}\n")
        f.write(f"状态：完结\n")
        f.write(f"字数：{total_chars}\n")
        f.write(f"章节：{len(chapter_files)}\n")
        if fanwai_files:
            f.write(f"番外：{len(fanwai_files)}\n")
        f.write(f"分类：未知\n")
        f.write(f"标签：未知\n")
        f.write(f"\n简介：\n\n")
        f.write(f"========================================\n\n")
        f.write(f"【第一卷】\n\n")
        
        # 写入正文
        for content in merged_content:
            f.write(content + "\n\n")
        
        # 写入全文完标记
        f.write("—————全文完—————\n")
    
    print(f"导出完成！")
    print(f"  书名：{title}")
    print(f"  作者：{author}")
    print(f"  正文章节：{len(chapter_files)} 章")
    if fanwai_files:
        print(f"  番外章节：{len(fanwai_files)} 章")
    print(f"  总字数：{total_chars:,}")
    print(f"  输出文件：{output_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='story-export: 标准化导出工具')
    parser.add_argument('project_dir', help='项目目录')
    parser.add_argument('--output', '-o', help='输出文件')
    
    args = parser.parse_args()
    
    success = export_novel(args.project_dir, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
