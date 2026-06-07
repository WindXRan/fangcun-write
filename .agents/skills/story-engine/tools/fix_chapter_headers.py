"""修复章节文件的第一行（将# 第N章替换为正确的章节号）"""
import os
import re
import sys

def fix_chapter_files(input_dir):
    """修复章节文件的第一行。"""
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
        
        # 修复第一行
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            # 移除第一行
            lines = lines[1:]
            # 添加正确的章节标题
            lines.insert(0, f'第{chapter_num}章')
            fixed_content = '\n'.join(lines)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            fixed_count += 1
    
    print(f"修复完成: {fixed_count} 个文件")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python fix_chapter_headers.py <章节目录>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    fix_chapter_files(input_dir)