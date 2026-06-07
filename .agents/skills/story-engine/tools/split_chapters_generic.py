"""通用拆章脚本：将番茄小说txt拆分为章节文件。"""
import re
import os
import sys

def detect_separator(content):
    """检测章节分隔符。"""
    # 常见分隔符模式
    patterns = [
        (r'\-{40,}', '---'),  # 40个以上短横线
        (r'={40,}', '==='),   # 40个以上等号
        (r'\*{40,}', '***'),  # 40个以上星号
    ]
    
    for pattern, name in patterns:
        matches = re.findall(pattern, content)
        if len(matches) > 5:  # 至少5个分隔符才算有效
            return pattern, name
    
    # 如果没有明显分隔符，尝试按"第X章"拆分
    return None, 'chapter_pattern'

def split_chapters(input_file, output_dir, encoding='utf-8'):
    """拆分章节。"""
    with open(input_file, 'r', encoding=encoding) as f:
        content = f.read()
    
    # 检测分隔符
    sep_pattern, sep_name = detect_separator(content)
    
    if sep_pattern:
        # 按分隔符拆分
        chapters = re.split(sep_pattern, content)
    else:
        # 按"第X章"拆分
        chapters = re.split(r'(?=第\d+章\s+)', content)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 章节标题模式
    chapter_pattern = re.compile(r'第(\d+)章\s+(.+)')
    
    chapter_count = 0
    for chapter in chapters:
        chapter = chapter.strip()
        if not chapter:
            continue
        
        match = chapter_pattern.search(chapter)
        if match:
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip()
            chapter_content = chapter[match.end():].strip()
            
            # 清理标题中的特殊字符
            safe_title = re.sub(r'[<>:"/\\|?*]', '', chapter_title)
            safe_title = safe_title[:50]  # 限制长度
            
            filename = f"第{chapter_num}章.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(f"第{chapter_num}章 {chapter_title}\n\n")
                f.write(chapter_content)
            
            chapter_count += 1
            print(f"已保存: {filename}")
    
    print(f"拆章完成，共 {chapter_count} 章")
    return chapter_count

def main():
    if len(sys.argv) < 3:
        print("用法: python split_chapters_generic.py <输入文件> <输出目录> [编码]")
        print("示例: python split_chapters_generic.py 源文.txt 源文章节/ utf-8")
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