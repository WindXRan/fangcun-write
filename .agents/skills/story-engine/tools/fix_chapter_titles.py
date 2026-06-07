"""修复章节标题：从源文提取标题，覆盖生成的章节文件第一行"""
import os
import re
import sys

def extract_source_titles(source_path):
    """从源文提取所有章节标题。"""
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配 "第N章" 开头的行（允许前面有空格）
    pattern = re.compile(r'^\s*(第\d+章\s*.+?)$', re.MULTILINE)
    titles = {}
    for match in pattern.finditer(content):
        line = match.group(1).strip()
        num_match = re.match(r'第(\d+)章', line)
        if num_match:
            ch_num = int(num_match.group(1))
            if ch_num not in titles:
                titles[ch_num] = line
    
    return titles

def is_valid_title(line):
    """检查第一行是否是有效的章节标题（排除干扰内容）。"""
    # 排除markdown标题标记
    if '###' in line or '##' in line:
        return False
    # 排除包含路径的行
    if '仿写/' in line or '正文/' in line:
        return False
    # 排除包含**包围的行
    if '**' in line:
        return False
    # 排除包含书名后缀的行（如"第5章：女配一睁眼..."）
    if re.match(r'^第\d+章[：:]', line):
        return False
    # 排除包含"第N章"但后面跟的是正文内容（没有标题）
    if re.match(r'^第\d+章$', line):
        return False
    return True

def fix_chapter_files(chapter_dir, source_path):
    """修复章节文件的标题。"""
    source_titles = extract_source_titles(source_path)
    print(f"从源文提取了 {len(source_titles)} 个章节标题")
    
    files = os.listdir(chapter_dir)
    chapter_files = [f for f in files if f.endswith('.txt') and re.match(r'第\d+章\.txt', f)]
    
    fixed_count = 0
    for filename in chapter_files:
        filepath = os.path.join(chapter_dir, filename)
        
        match = re.match(r'第(\d+)章\.txt', filename)
        if not match:
            continue
        ch_num = int(match.group(1))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        if not lines:
            continue
        
        # 获取正确的标题
        correct_title = source_titles.get(ch_num, f"第{ch_num}章")
        
        # 检查第一行是否需要修复
        need_fix = False
        first_line = lines[0].strip()
        
        # 情况1：第一行不是以"第N章"开头
        if not re.match(r'^第\d+章', first_line):
            need_fix = True
        # 情况2：第一行是"第N章"（没有标题）
        elif re.match(r'^第\d+章$', first_line):
            need_fix = True
        # 情况3：第一行包含干扰内容
        elif not is_valid_title(first_line):
            need_fix = True
        
        if need_fix:
            lines[0] = correct_title
            # 移除标题后的多余空行
            while len(lines) > 1 and lines[1] == '':
                lines.pop(1)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            fixed_count += 1
    
    print(f"修复了 {fixed_count} 个章节文件")
    return fixed_count

def main():
    if len(sys.argv) < 3:
        print("用法: python fix_chapter_titles.py <章节目录> <源文路径>")
        sys.exit(1)
    
    chapter_dir = sys.argv[1]
    source_path = sys.argv[2]
    
    if not os.path.exists(chapter_dir):
        print(f"错误: 章节目录不存在: {chapter_dir}")
        sys.exit(1)
    
    if not os.path.exists(source_path):
        print(f"错误: 源文不存在: {source_path}")
        sys.exit(1)
    
    fix_chapter_files(chapter_dir, source_path)

if __name__ == '__main__':
    main()