#!/usr/bin/env python3
"""网文写作知识库导入工具

用法：
  python import_knowledge.py <文件或目录> [--category 分类]
  
支持格式：.md .txt .json .pdf
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path

# 知识库根目录（项目根目录/knowledge/_writing）
SKILL_DIR = Path(__file__).parent.parent
KNOWLEDGE_ROOT = SKILL_DIR.parent.parent.parent / "knowledge" / "_writing"

# 分类映射
CATEGORY_MAP = {
    "theory": ["理论", "总论", "体系", "核心", "基础"],
    "techniques": ["技巧", "技法", "笔力", "描写", "人物", "场景", "爽点", "节奏", "情绪"],
    "templates": ["模板", "框架", "大纲", "拆书"],
    "categories": ["品类", "都市", "玄幻", "仙侠", "历史", "科幻", "同人"],
    "market": ["市场", "运营", "签约", "更新", "宣传", "桥段", "题材"],
}


def detect_category(content: str, filename: str) -> str:
    """根据内容和文件名自动检测分类"""
    text = (content[:2000] + filename).lower()
    
    scores = {}
    for cat, keywords in CATEGORY_MAP.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    
    if scores:
        return max(scores, key=scores.get)
    return "theory"  # 默认分类


def split_chapters(content: str) -> list:
    """按章节标题拆分内容"""
    # 匹配 # 开头的标题
    pattern = r'^(#{1,3}\s+.+)$'
    parts = re.split(pattern, content, flags=re.MULTILINE)
    
    chapters = []
    current_title = ""
    current_content = ""
    
    for part in parts:
        if re.match(r'^#{1,3}\s+', part):
            # 保存上一章
            if current_title:
                chapters.append({
                    "title": current_title.strip(),
                    "content": current_content.strip()
                })
            current_title = part
            current_content = ""
        else:
            current_content += part
    
    # 保存最后一章
    if current_title:
        chapters.append({
            "title": current_title.strip(),
            "content": current_content.strip()
        })
    
    return chapters


def import_markdown(filepath: Path, category: str = None) -> dict:
    """导入markdown文件"""
    print(f"读取: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 自动检测分类
    if not category:
        category = detect_category(content, filepath.name)
    
    # 拆分章节
    chapters = split_chapters(content)
    
    # 生成索引
    index = {
        "source": filepath.name,
        "category": category,
        "chapter_count": len(chapters),
        "chapters": []
    }
    
    # 写入目标目录
    target_dir = KNOWLEDGE_ROOT / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存完整文件
    target_file = target_dir / filepath.name
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  保存: {target_file}")
    
    # 保存拆分章节
    if len(chapters) > 1:
        chapters_dir = target_dir / filepath.stem
        chapters_dir.mkdir(exist_ok=True)
        
        for i, ch in enumerate(chapters, 1):
            # 生成安全文件名
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', ch['title'])
            ch_file = chapters_dir / f"{i:02d}_{safe_title[:50]}.md"
            
            with open(ch_file, 'w', encoding='utf-8') as f:
                f.write(f"{ch['title']}\n\n{ch['content']}")
            
            index["chapters"].append({
                "num": i,
                "title": ch['title'],
                "file": str(ch_file.relative_to(KNOWLEDGE_ROOT))
            })
    
    return index


def import_text(filepath: Path, category: str = None) -> dict:
    """导入txt文件"""
    # 尝试不同编码
    content = None
    for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if not content:
        print(f"  错误: 无法读取文件")
        return None
    
    # 自动检测分类
    if not category:
        category = detect_category(content, filepath.name)
    
    # 拆分章节
    chapters = split_chapters(content)
    
    # 生成索引
    index = {
        "source": filepath.name,
        "category": category,
        "chapter_count": len(chapters),
        "chapters": []
    }
    
    # 写入目标目录
    target_dir = KNOWLEDGE_ROOT / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存为md格式
    target_file = target_dir / f"{filepath.stem}.md"
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  保存: {target_file}")
    
    return index


def import_json(filepath: Path, category: str = None) -> dict:
    """导入json文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not category:
        category = "market"  # json默认归为市场数据
    
    target_dir = KNOWLEDGE_ROOT / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = target_dir / filepath.name
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  保存: {target_file}")
    
    return {
        "source": filepath.name,
        "category": category,
        "type": "json"
    }


def import_file(filepath: Path, category: str = None) -> dict:
    """导入单个文件"""
    suffix = filepath.suffix.lower()
    
    if suffix in ['.md', '.markdown']:
        return import_markdown(filepath, category)
    elif suffix == '.txt':
        return import_text(filepath, category)
    elif suffix == '.json':
        return import_json(filepath, category)
    else:
        print(f"  跳过: 不支持的格式 {suffix}")
        return None


def import_directory(dirpath: Path, category: str = None) -> list:
    """导入目录下所有文件"""
    results = []
    
    for f in sorted(dirpath.iterdir()):
        if f.is_file() and f.suffix.lower() in ['.md', '.txt', '.json']:
            result = import_file(f, category)
            if result:
                results.append(result)
    
    return results


def update_index(results: list):
    """更新索引文件"""
    index_file = KNOWLEDGE_ROOT / "index.json"
    
    # 读取现有索引
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {"files": []}
    
    # 添加新条目
    for r in results:
        if r:
            index["files"].append(r)
    
    # 保存索引
    index_file.parent.mkdir(parents=True, exist_ok=True)
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n索引已更新: {index_file}")


def main():
    parser = argparse.ArgumentParser(description='网文写作知识库导入工具')
    parser.add_argument('path', help='文件或目录路径')
    parser.add_argument('--category', '-c', help='指定分类 (theory/techniques/templates/categories/market)')
    
    args = parser.parse_args()
    path = Path(args.path)
    
    if not path.exists():
        print(f"错误: 路径不存在 {path}")
        sys.exit(1)
    
    print(f"导入到: {KNOWLEDGE_ROOT}\n")
    
    if path.is_file():
        result = import_file(path, args.category)
        results = [result] if result else []
    elif path.is_dir():
        results = import_directory(path, args.category)
    else:
        print(f"错误: 无效路径 {path}")
        sys.exit(1)
    
    # 更新索引
    if results:
        update_index(results)
    
    print(f"\n完成: 导入 {len(results)} 个文件")


if __name__ == '__main__':
    main()
