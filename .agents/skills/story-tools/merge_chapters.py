"""合并章节文件为完整小说（番茄格式）。"""
import os
import re
import sys

def natural_sort_key(s):
    """自然排序键（支持数字排序）。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def parse_concept(concept_path):
    """从 concept.md 解析书名、简介、题材。"""
    if not os.path.exists(concept_path):
        return None, None, None
    
    with open(concept_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取书名（第一个 # 标题）
    title_match = re.search(r'^#\s*《(.+?)》', content, re.MULTILINE)
    title = title_match.group(1) if title_match else None
    
    # 提取简介（版本A优先）
    blurb = None
    blurb_match = re.search(r'###\s*版本A.*?\n\n(.+?)(?:\n\n###|\n##|\Z)', content, re.DOTALL)
    if blurb_match:
        blurb = blurb_match.group(1).strip()
    else:
        # 尝试第一个简介
        blurb_match = re.search(r'###\s*版本.*?\n\n(.+?)(?:\n\n###|\n##|\Z)', content, re.DOTALL)
        if blurb_match:
            blurb = blurb_match.group(1).strip()
    
    # 提取题材
    genre = None
    genre_match = re.search(r'\*\*题材\*\*[：:]\s*(.+)', content)
    if genre_match:
        genre = genre_match.group(1).strip()
    
    return title, blurb, genre


def find_source_tags(concept_path):
    """从源文提取标签。根据 concept.md 路径推断源文路径。"""
    if not concept_path:
        return None
    
    # concept 路径: projects/{作者}/{源书}/rewrites/{新书}/concept.md
    # 源文路径:   projects/{作者}/{源书}/_cache/{源书}.txt 或 projects/{作者}/{源书}/{源书}.txt
    concept_dir = os.path.dirname(os.path.abspath(concept_path))
    # 上溯到 rewrites 目录
    if os.path.basename(concept_dir) == 'rewrites':
        pass
    elif 'rewrites' in concept_dir:
        concept_dir = concept_dir[:concept_dir.rindex('rewrites')]
    
    # rewrites 的父目录就是源书目录
    source_book_dir = os.path.dirname(concept_dir)
    source_book_name = os.path.basename(source_book_dir)
    
    # 尝试多个可能的源文路径
    source_candidates = [
        os.path.join(source_book_dir, '_cache', f'{source_book_name}.txt'),
        os.path.join(source_book_dir, f'{source_book_name}.txt'),
    ]
    
    for src in source_candidates:
        if os.path.exists(src):
            with open(src, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('标签：') or line.startswith('标签:'):
                        return line.split('：', 1)[-1].strip()
    return None

def merge_chapters(input_dir, output_file, encoding='utf-8', concept_path=None):
    """合并章节文件（番茄格式）。"""
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
    
    # 解析 concept.md
    title, blurb, genre = None, None, None
    if concept_path:
        title, blurb, genre = parse_concept(concept_path)
    
    # 从源文提取标签
    tags = find_source_tags(concept_path)
    
    # 如果没有 concept，从目录名推断书名
    if not title:
        title = os.path.basename(os.path.dirname(os.path.dirname(output_file)))
    
    # 写入输出文件（番茄格式）
    with open(output_file, 'w', encoding=encoding) as f:
        # 头部信息
        f.write(f"书名：{title}\n")
        f.write(f"状态：完结\n")
        f.write(f"字数：{total_chars}\n")
        f.write(f"章节：{len(chapter_files)}\n")
        if genre:
            f.write(f"分类：{genre}\n")
        if tags:
            f.write(f"标签：{tags}\n")
        f.write("\n")
        
        # 简介
        if blurb:
            f.write("简介：\n")
            f.write(blurb + "\n")
            f.write("\n")
        
        # 分隔线
        f.write("=" * 40 + "\n")
        f.write("\n")
        
        # 章节内容
        f.write('\n\n'.join(merged_content))
    
    print(f"\n合并完成:")
    print(f"- 章节数: {len(chapter_files)}")
    print(f"- 总字数: {total_chars:,}")
    print(f"- 输出文件: {output_file}")
    
    return True

def main():
    if len(sys.argv) < 3:
        print("用法: python merge_chapters.py <章节目录> <输出文件> [编码] [concept.md路径]")
        print("示例: python merge_chapters.py chapters/ export/新书.txt utf-8 ../concept.md")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    encoding = sys.argv[3] if len(sys.argv) > 3 else 'utf-8'
    concept_path = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not os.path.exists(input_dir):
        print(f"错误: 章节目录不存在: {input_dir}")
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    try:
        success = merge_chapters(input_dir, output_file, encoding, concept_path)
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