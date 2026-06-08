"""拆分源文章节到缓存目录"""
import os
import re
import sys
from pathlib import Path


def split_chapters(source_file, output_dir, start_chapter=1, end_chapter=None):
    """从源文件拆分章节到缓存目录"""
    # 读取源文件
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找章节标题位置（支持"第X章"和"番外"）
    chapter_pattern = re.compile(r'^第(\d+)章')
    fanwai_pattern = re.compile(r'^番外[_\s]*(.*)')
    chapter_positions = []
    
    for i, line in enumerate(lines):
        line_s = line.strip()
        match = chapter_pattern.match(line_s)
        if match:
            chapter_num = int(match.group(1))
            chapter_positions.append((chapter_num, i, 'chapter'))
            continue
        match = fanwai_pattern.match(line_s)
        if match:
            title = match.group(1).strip() or f"番外{len([p for p in chapter_positions if p[2]=='fanwai'])+1}"
            chapter_positions.append((title, i, 'fanwai'))
    
    if not chapter_positions:
        print("未找到章节标题")
        return
    
    # 确定结束章节
    if end_chapter is None:
        end_chapter = max(p[0] for p in chapter_positions if p[2]=='chapter')
    
    print(f"找到 {len(chapter_positions)} 个章节")
    print(f"拆分范围：第{start_chapter}章 - 第{end_chapter}章 + 番外")
    
    # 拆分章节
    for i, (chapter_id, start_line, ch_type) in enumerate(chapter_positions):
        # 确定结束行
        if i + 1 < len(chapter_positions):
            end_line = chapter_positions[i + 1][1]
        else:
            end_line = len(lines)
        
        # 提取章节内容
        chapter_content = ''.join(lines[start_line:end_line])
        
        # 保存章节
        if ch_type == 'chapter':
            if chapter_id < start_chapter or chapter_id > end_chapter:
                continue
            chapter_file = os.path.join(output_dir, f"第{chapter_id}章.txt")
        else:
            chapter_file = os.path.join(output_dir, f"番外_{chapter_id}.txt")
        
        with open(chapter_file, 'w', encoding='utf-8') as f:
            f.write(chapter_content)
        
        # 统计字数
        content_without_title = '\n'.join(lines[start_line + 1:end_line])
        char_count = len(re.sub(r'\s', '', content_without_title))
        print(f"  {chapter_id}：{char_count}字 → {chapter_file}")
    
    print(f"完成！")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python split_chapters.py <源文件> <输出目录> [起始章] [结束章]")
        print("示例: python split_chapters.py projects/午夜凶球/认亲后，大家的画风一起跑偏了.txt projects/午夜凶球/认亲后，大家的画风一起跑偏了/_cache/chapters 4 8")
        sys.exit(1)
    
    source_file = sys.argv[1]
    output_dir = sys.argv[2]
    start_chapter = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    end_chapter = int(sys.argv[4]) if len(sys.argv) > 4 else None
    
    if not os.path.exists(source_file):
        print(f"源文件不存在: {source_file}")
        sys.exit(1)
    
    split_chapters(source_file, output_dir, start_chapter, end_chapter)
