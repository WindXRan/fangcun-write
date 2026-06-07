"""合并章节文件为完整小说。"""
import os
import re
import sys

def natural_sort_key(s):
    """自然排序键（支持数字排序）。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def merge_chapters(input_dir, output_file, encoding='utf-8'):
    """合并章节文件。"""
    # 获取所有章节文件（支持新旧两种命名）
    chapter_files = []
    for filename in os.listdir(input_dir):
        if filename.endswith('.txt') and (
            re.match(r'第\d+章\.txt', filename) or
            re.match(r'ch_\d+\.txt', filename)
        ):
            chapter_files.append(filename)
    
    # 自然排序
    chapter_files.sort(key=natural_sort_key)
    
    if not chapter_files:
        print(f"错误: 在 {input_dir} 中没有找到章节文件")
        return False
    
    # 合并内容
    merged_content = []
    total_chars = 0
    
    for filename in chapter_files:
        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r', encoding=encoding) as f:
            content = f.read().strip()
        
        if content:
            merged_content.append(content)
            total_chars += len(content)
            print(f"已合并: {filename} ({len(content)} 字)")
    
    # 写入输出文件
    with open(output_file, 'w', encoding=encoding) as f:
        f.write('\n\n'.join(merged_content))
    
    print(f"\n合并完成:")
    print(f"- 章节数: {len(chapter_files)}")
    print(f"- 总字数: {total_chars:,}")
    print(f"- 输出文件: {output_file}")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python merge_chapters.py <章节目录> <输出文件> [编码]")
        print("示例: python merge_chapters.py chapters/ export/新书.txt utf-8")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    encoding = sys.argv[3] if len(sys.argv) > 3 else 'utf-8'
    
    if not os.path.exists(input_dir):
        print(f"错误: 章节目录不存在: {input_dir}")
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        success = merge_chapters(input_dir, output_file, encoding)
        if success:
            print("合并成功!")
        else:
            print("合并失败!")
            sys.exit(1)
    except Exception as e:
        print(f"合并失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()