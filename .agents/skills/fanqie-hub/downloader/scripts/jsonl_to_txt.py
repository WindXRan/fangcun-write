"""将番茄下载器的jsonl输出转换为txt，并导入到projects目录"""
import json
import sys
import os
import re

def clean_html(text):
    """清理HTML标签"""
    text = re.sub(r'<article>', '', text)
    text = re.sub(r'</article>', '', text)
    text = re.sub(r'<h1[^>]*>', '\n', text)
    text = re.sub(r'</h1>', '\n', text)
    text = re.sub(r'<blk[^>]*>', '', text)
    text = re.sub(r'</blk>', '', text)
    text = re.sub(r'<p[^>]*>', '', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'(\r?\n){3,}', '\n\n', text)
    return text.strip()

def remove_duplicate_title(content, title):
    """去除重复的章节标题"""
    # 清理标题中的空格和特殊字符
    clean_title = re.sub(r'\s+', '', title)
    
    # 检查内容是否以标题开头
    content_lines = content.strip().split('\n')
    if not content_lines:
        return content
    
    first_line = content_lines[0].strip()
    clean_first_line = re.sub(r'\s+', '', first_line)
    
    # 如果第一行就是标题，或者第一行包含标题，去除它
    if clean_first_line == clean_title or clean_first_line.startswith(clean_title):
        # 去掉第一行，保留剩余内容
        remaining = '\n'.join(content_lines[1:]).strip()
        return remaining
    
    # 如果内容中包含重复的标题行，去除重复的
    # 例如："第1章 标题\n第1章 标题\n内容" -> "第1章 标题\n内容"
    pattern = re.escape(title) + r'\s*\n\s*' + re.escape(title)
    content = re.sub(pattern, title, content)
    
    return content

def extract_metadata(status_path):
    """从status.json提取元信息"""
    if not os.path.exists(status_path):
        return {}
    
    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return {}
    
    metadata = {
        'book_name': data.get('book_name', ''),
        'author': data.get('author', ''),
        'book_id': data.get('book_id', ''),
        'category': data.get('category', ''),
        'description': data.get('description', ''),
        'chapter_count': data.get('chapter_count', 0),
        'word_count': data.get('word_count', 0),
        'score': data.get('score', ''),
        'tags': data.get('tags', ''),
        'read_count': data.get('read_count', 0),
        'like_count': data.get('like_count', 0),
        'status': data.get('status', ''),
    }
    return metadata

def convert_jsonl_to_txt(jsonl_path, output_path, book_name, author, status_path=None):
    """将jsonl转换为txt"""
    print(f"读取: {jsonl_path}")
    
    # 读取文件（UTF-8编码）
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取元信息
    metadata = {}
    if status_path:
        metadata = extract_metadata(status_path)
        if metadata:
            print(f"  元信息: {metadata.get('category', '')} | {len(metadata.get('tags', []))}个标签")
    
    # 构建头部
    header = f"书名：{book_name}\n作者：{author}\n"
    if metadata.get('category'):
        header += f"分类：{metadata['category']}\n"
    if metadata.get('tags'):
        tags = metadata['tags']
        if isinstance(tags, str):
            tags = tags.replace('|', '、')
        elif isinstance(tags, list):
            tags = '、'.join(tags)
        header += f"标签：{tags}\n"
    if metadata.get('score'):
        header += f"评分：{metadata['score']}\n"
    if metadata.get('word_count'):
        wc = metadata['word_count']
        if wc > 10000:
            header += f"字数：{wc/10000:.1f}万\n"
        else:
            header += f"字数：{wc}\n"
    if metadata.get('chapter_count'):
        header += f"章节：{metadata['chapter_count']}\n"
    if metadata.get('status'):
        header += f"状态：{metadata['status']}\n"
    if metadata.get('description'):
        header += f"\n简介：\n{metadata['description']}\n"
    header += "\n" + "="*50 + "\n\n"
    
    # 解析jsonl
    lines = content.strip().split('\n')
    txt_content = header
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            chapter = json.loads(line)
            title = chapter.get('title', f'第{i+1}章')
            ch_content = chapter.get('content', '')
            ch_content = clean_html(ch_content)
            
            # 去除重复的章节标题
            ch_content = remove_duplicate_title(ch_content, title)
            
            # 添加章节内容
            txt_content += f"\n\n{title}\n\n{ch_content}"
        except json.JSONDecodeError as e:
            print(f"  警告: 第{i+1}行解析失败: {e}")
            continue
    
    # 保存txt
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    print(f"保存: {output_path}")
    
    # 保存精简的metadata.json
    if metadata:
        metadata_path = os.path.join(os.path.dirname(output_path), 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"保存: {metadata_path}")
    
    return True

def main():
    if len(sys.argv) < 5:
        print("用法: python jsonl_to_txt.py <jsonl_path> <output_path> <book_name> <author> [status_path]")
        sys.exit(1)
    
    jsonl_path = sys.argv[1]
    output_path = sys.argv[2]
    book_name = sys.argv[3]
    author = sys.argv[4]
    status_path = sys.argv[5] if len(sys.argv) > 5 else None
    
    success = convert_jsonl_to_txt(jsonl_path, output_path, book_name, author, status_path)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
