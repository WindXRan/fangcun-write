import os
import re

def split_novel(input_file, output_dir):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chapters = re.split(r'\-{40,}', content)
    
    os.makedirs(output_dir, exist_ok=True)
    
    chapter_pattern = re.compile(r'第(\d+)章\s+(.+)')
    
    for chapter in chapters:
        chapter = chapter.strip()
        if not chapter:
            continue
        
        match = chapter_pattern.search(chapter)
        if match:
            chapter_num = match.group(1)
            chapter_title = match.group(2)
            chapter_content = chapter[match.end():].strip()
            
            filename = f"第{chapter_num}章.txt"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"第{chapter_num}章 {chapter_title}\n\n")
                f.write(chapter_content)
            
            print(f"已保存: {filename}")

if __name__ == "__main__":
    input_file = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\novel-download-authors\奶糖酥\酸涩湿吻.txt"
    output_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\novel-download-authors\奶糖酥\酸涩湿吻\源文"
    
    split_novel(input_file, output_dir)
    print("拆章完成！")