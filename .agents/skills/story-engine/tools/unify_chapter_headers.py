"""统一章节标题格式（添加缺失的章节标题）"""
import os
import re
import sys

def unify_chapter_headers(input_dir):
    """统一章节标题格式。"""
    files = os.listdir(input_dir)
    chapter_files = [f for f in files if f.endswith('.txt') and re.match(r'第\d+章\.txt', f)]
    
    fixed_count = 0
    for filename in chapter_files:
        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取章节号
        match = re.match(r'第(\d+)章\.txt', filename)
        if not match:
            continue
        chapter_num = match.group(1)
        
        # 检查第一行是否是章节标题
        lines = content.split('\n')
        if lines and re.match(r'^第\d+章$', lines[0]):
            # 第一行是"第N章"（没有章节标题），添加一个空行
            lines.insert(1, '')
            fixed_content = '\n'.join(lines)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            fixed_count += 1
    
    print(f"统一完成: {fixed_count} 个文件")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python unify_chapter_headers.py <章节目录>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    unify_chapter_headers(input_dir)