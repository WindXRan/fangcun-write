#!/usr/bin/env python3
"""按章节分割原文文件。"""

import re
import os
from pathlib import Path

def split_chapters(input_file, output_dir):
    """按章节分割原文。"""
    
    # 读取原文
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 创建输出目录
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 章节分割正则
    # 匹配 "第X章" 或 "第 X章" 或 "第X 章"
    chapter_pattern = r'^(第\s*\d+\.?\d*\s*章.*)$'
    
    # 按章节分割
    lines = content.split('\n')
    chapters = []
    current_chapter = []
    current_title = ""
    
    for line in lines:
        if re.match(chapter_pattern, line.strip()):
            # 保存当前章节
            if current_chapter and current_title:
                chapters.append({
                    'title': current_title,
                    'content': '\n'.join(current_chapter)
                })
            # 开始新章节
            current_title = line.strip()
            current_chapter = []
        else:
            current_chapter.append(line)
    
    # 保存最后一个章节
    if current_chapter and current_title:
        chapters.append({
            'title': current_title,
            'content': '\n'.join(current_chapter)
        })
    
    # 保存章节文件
    for i, chapter in enumerate(chapters, 1):
        # 提取章节号
        match = re.search(r'第\s*(\d+\.?\d*)\s*章', chapter['title'])
        if match:
            chapter_num = match.group(1)
            # 处理小数章节号（如85.5）
            if '.' in chapter_num:
                filename = f"ch{chapter_num.replace('.', '_')}.txt"
            else:
                filename = f"ch{int(chapter_num):03d}.txt"
        else:
            filename = f"ch{i:03d}.txt"
        
        output_file = output_dir / filename
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chapter['title'] + '\n\n')
            f.write(chapter['content'])
        
        print(f"保存: {filename} - {chapter['title'][:20]}...")
    
    print(f"\n总共分割出 {len(chapters)} 个章节")
    return len(chapters)

if __name__ == "__main__":
    input_file = "projects/午夜凶球/认亲后，画风跑偏/original.txt"
    output_dir = "projects/午夜凶球/认亲后，画风跑偏/cyber_author/knowledge_base/raw_chapters"
    
    split_chapters(input_file, output_dir)