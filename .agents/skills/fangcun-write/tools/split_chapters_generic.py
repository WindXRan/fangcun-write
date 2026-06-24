"""通用拆章脚本：将番茄小说txt拆分为章节文件。"""
import re
import os
import sys

def split_chapters(input_file, output_dir, encoding='utf-8'):
    """拆分章节。"""
    with open(input_file, 'r', encoding=encoding) as f:
        content = f.read()
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 按"第X章"拆分（兼容有/无空格两种格式）
    chapters = re.split(r'(?=第\d+章\s*)', content)
    
    # 记录已保存的章节，避免重复
    saved_chapters = {}
    
    for chapter in chapters:
        chapter = chapter.strip()
        if not chapter:
            continue
        
        # 章节标题模式
        chapter_pattern = re.compile(r'第(\d+)章\s*(.*)')
        match = chapter_pattern.search(chapter)
        if match:
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip()
            
            # 如果只有标题没有正文，跳过
            if not chapter_title:
                continue
            
            # 如果已有同章节号，检查是否需要替换
            if chapter_num in saved_chapters:
                # 检查当前片段是否只有标题（标题+空格+标题）
                # 如果当前片段长度小于50字，可能是重复标题
                if len(chapter) < 50:
                    continue
                # 当前片段有正文，替换之前只有标题的版本
                saved_chapters[chapter_num] = chapter
                # 更新文件
                filename = f"第{chapter_num}章.txt"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding=encoding) as f:
                    f.write(chapter.strip())
                continue
            
            # 保存完整章节内容（标题+正文）
            filename = f"第{chapter_num}章.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(chapter.strip())
            
            saved_chapters[chapter_num] = chapter
            print(f"已保存: {filename}")
    
    chapter_count = len(saved_chapters)
    print(f"拆章完成，共 {chapter_count} 章")
    return chapter_count

def main():
    if len(sys.argv) < 3:
        print("用法: python split_chapters_generic.py <输入文件> <输出目录> [编码]")
        print("示例: python split_chapters_generic.py original.txt _cache/chapters/ utf-8")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    encoding = sys.argv[3] if len(sys.argv) > 3 else 'utf-8'
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    try:
        count = split_chapters(input_file, output_dir, encoding)
        print(f"成功拆分 {count} 章到 {output_dir}")
    except Exception as e:
        print(f"拆章失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
