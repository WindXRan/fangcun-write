#!/usr/bin/env python3
"""
story-export · 小说导出工具
将仿写章节合并导出为番茄小说格式的txt文件
"""

import os
import re
import argparse
from pathlib import Path


def extract_from_concept(concept_path: str) -> dict:
    """从concept.md提取书名、分类、简介"""
    result = {
        'book_name': '',
        'category': '',
        'intro': ''
    }
    
    with open(concept_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取书名：从"# 《书名》设定"或"## 书名"
    book_name_match = re.search(r'#\s*《(.+?)》', content)
    if not book_name_match:
        book_name_match = re.search(r'##\s*书名\s*\n(.+)', content)
    if book_name_match:
        result['book_name'] = book_name_match.group(1).strip()
    
    # 提取分类：从"**题材**"字段
    category_match = re.search(r'\*\*题材\*\*[：:]\s*(.+)', content)
    if category_match:
        result['category'] = category_match.group(1).strip()
    
    # 提取简介：从"### 版本A"或"## 简介"
    intro_match = re.search(r'###\s*版本A.*?\n([\s\S]*?)(?=\n###|\n##|\Z)', content)
    if not intro_match:
        intro_match = re.search(r'##\s*简介\s*\n([\s\S]*?)(?=\n##|\Z)', content)
    if intro_match:
        result['intro'] = intro_match.group(1).strip()
    
    return result


def extract_tags_from_source(cache_dir: str, source_book: str) -> str:
    """从源文txt文件提取标签"""
    source_path = os.path.join(cache_dir, f'{source_book}.txt')
    if not os.path.exists(source_path):
        return '现代言情'
    
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取标签
    tag_match = re.search(r'标签[：:]\s*(.+)', content)
    if tag_match:
        return tag_match.group(1).strip()
    
    return '现代言情'


def merge_chapters(chapters_dir: str) -> tuple:
    """合并所有章节，返回(内容, 字数, 章节数)"""
    chapters = []
    total_chars = 0
    
    # 按文件名排序
    chapter_files = sorted([
        f for f in os.listdir(chapters_dir)
        if f.startswith('ch_') and f.endswith('.txt')
    ])
    
    for filename in chapter_files:
        filepath = os.path.join(chapters_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 统计字数（去除空白和标点）
        chars = len(re.sub(r'\s+', '', content))
        total_chars += chars
        chapters.append(content)
    
    return '\n\n'.join(chapters), total_chars, len(chapters)


def export(project_dir: str, output_path: str = None, encoding: str = 'utf-8'):
    """导出小说"""
    project_dir = Path(project_dir)
    
    # 查找concept.md
    concept_path = project_dir / 'concept.md'
    if not concept_path.exists():
        print(f"错误：找不到 concept.md: {concept_path}")
        return
    
    # 查找chapters目录
    chapters_dir = project_dir / 'chapters'
    if not chapters_dir.exists():
        print(f"错误：找不到 chapters 目录: {chapters_dir}")
        return
    
    # 提取信息
    concept_info = extract_from_concept(str(concept_path))
    
    # 查找源文目录（用于提取标签）
    # 项目路径格式：projects/{作者}/{源书}/rewrites/{新书}/
    rewrites_dir = project_dir.parent
    source_book = project_dir.name.replace('仿写', '')
    cache_dir = str(rewrites_dir.parent / '_cache')
    
    tags = extract_tags_from_source(cache_dir, source_book)
    
    # 合并章节
    chapters_content, total_chars, chapter_count = merge_chapters(str(chapters_dir))
    
    # 生成输出内容
    book_name = concept_info['book_name'] or project_dir.name
    category = concept_info['category'] or '现代言情'
    intro = concept_info['intro'] or '暂无简介'
    
    output = f"""书名：{book_name}
状态：连载中
字数：{total_chars}
章节：{chapter_count}
分类：{category}
标签：{tags}

简介：
{intro}

========================================

{chapters_content}"""
    
    # 确定输出路径
    if not output_path:
        export_dir = project_dir / 'export'
        export_dir.mkdir(exist_ok=True)
        output_path = export_dir / f'{book_name}.txt'
    
    # 写入文件
    with open(output_path, 'w', encoding=encoding) as f:
        f.write(output)
    
    print(f"导出完成:")
    print(f"  书名：{book_name}")
    print(f"  章节：{chapter_count}")
    print(f"  字数：{total_chars}")
    print(f"  输出：{output_path}")


def main():
    parser = argparse.ArgumentParser(description='小说导出工具')
    parser.add_argument('project_dir', help='项目目录路径')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--encoding', '-e', default='utf-8', help='输出编码')
    
    args = parser.parse_args()
    export(args.project_dir, args.output, args.encoding)


if __name__ == '__main__':
    main()
