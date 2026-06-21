#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄指数数据分析工具
用法：python analyze.py [命令] [参数]
命令：
  top [N]           - 显示 Top N 书籍（默认 10）
  trend [days]      - 显示最近 N 天趋势（默认 7）
  category [name]   - 显示指定分类数据
  hot               - 显示热门题材
  new               - 显示新上榜书籍
  summary           - 显示市场总结
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Windows 控制台默认 GBK 编码，无法输出 emoji，强制使用 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

def load_json(file_path):
    """加载 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载失败 {file_path}: {e}")
        return None

def get_latest_file(prefix):
    """获取最新的数据文件"""
    files = list(DATA_DIR.glob(f"latest_{prefix}_ranks.json"))
    if files:
        return files[0]
    return None

def show_top(n=10, prefix="male_new"):
    """显示 Top N 书籍"""
    file_path = get_latest_file(prefix)
    if not file_path:
        print(f"❌ 未找到 {prefix} 数据")
        return
    
    data = load_json(file_path)
    if not data:
        return
    
    print(f"\n📚 {prefix} Top {n} 书籍:")
    print("=" * 80)
    
    # 收集所有书籍
    all_books = []
    for category in data.get('categories', []):
        cat_name = category.get('name', '未知')
        for book in category.get('books', []):
            book['category'] = cat_name
            all_books.append(book)
    
    # 按排名排序
    all_books.sort(key=lambda x: x.get('rank', 999))
    
    # 显示 Top N
    for i, book in enumerate(all_books[:n], 1):
        rank = book.get('rank', '?')
        title = book.get('title', '未知')
        author = book.get('author', '未知')
        reads = book.get('reads', 0)
        category = book.get('category', '未知')
        rank_change = book.get('rank_change', 0)
        
        # 格式化阅读量
        try:
            reads = int(reads)
            if reads >= 10000:
                reads_str = f"{reads/10000:.1f}万"
            else:
                reads_str = str(reads)
        except (ValueError, TypeError):
            reads_str = str(reads)
        
        # 排名变化符号
        try:
            rank_change = int(rank_change)
            if rank_change > 0:
                change_str = f"↑{rank_change}"
            elif rank_change < 0:
                change_str = f"↓{abs(rank_change)}"
            else:
                change_str = "→"
        except (ValueError, TypeError):
            change_str = "→"
        
        # 格式化排名
        try:
            rank = int(rank)
            rank_str = f"{rank:3d}"
        except (ValueError, TypeError):
            rank_str = str(rank)
        
        print(f"{i:2d}. [{rank_str}] {title}")
        print(f"    作者: {author} | 分类: {category} | 阅读: {reads_str} | 变化: {change_str}")

def show_hot(prefix="male_new"):
    """显示热门题材"""
    file_path = get_latest_file(prefix)
    if not file_path:
        print(f"❌ 未找到 {prefix} 数据")
        return
    
    data = load_json(file_path)
    if not data:
        return
    
    print(f"\n🔥 {prefix} 热门题材:")
    print("=" * 60)
    
    # 统计各分类书籍数量和平均排名
    category_stats = []
    for category in data.get('categories', []):
        cat_name = category.get('name', '未知')
        books = category.get('books', [])
        if books:
            # 计算平均排名
            ranks = []
            reads_list = []
            for b in books:
                try:
                    ranks.append(int(b.get('rank', 0)))
                except (ValueError, TypeError):
                    ranks.append(0)
                try:
                    reads_list.append(int(b.get('reads', 0)))
                except (ValueError, TypeError):
                    reads_list.append(0)
            
            avg_rank = sum(ranks) / len(ranks)
            total_reads = sum(reads_list)
            category_stats.append({
                'name': cat_name,
                'count': len(books),
                'avg_rank': avg_rank,
                'total_reads': total_reads
            })
    
    # 按平均排名排序
    category_stats.sort(key=lambda x: x['avg_rank'])
    
    for i, cat in enumerate(category_stats[:15], 1):
        total_reads = cat['total_reads']
        if total_reads >= 10000:
            reads_str = f"{total_reads/10000:.1f}万"
        else:
            reads_str = str(total_reads)
        
        print(f"{i:2d}. {cat['name']}")
        print(f"    书籍: {cat['count']}本 | 平均排名: {cat['avg_rank']:.1f} | 总阅读: {reads_str}")

def show_new(prefix="male_new"):
    """显示新上榜书籍"""
    file_path = get_latest_file(prefix)
    if not file_path:
        print(f"❌ 未找到 {prefix} 数据")
        return
    
    data = load_json(file_path)
    if not data:
        return
    
    print(f"\n🆕 {prefix} 新上榜书籍:")
    print("=" * 60)
    
    new_books = []
    for category in data.get('categories', []):
        cat_name = category.get('name', '未知')
        for book in category.get('books', []):
            if book.get('is_new', False):
                book['category'] = cat_name
                new_books.append(book)
    
    if not new_books:
        print("暂无新上榜书籍")
        return
    
    for i, book in enumerate(new_books[:20], 1):
        title = book.get('title', '未知')
        author = book.get('author', '未知')
        category = book.get('category', '未知')
        rank = book.get('rank', '?')
        
        print(f"{i:2d}. [{rank:3d}] {title}")
        print(f"    作者: {author} | 分类: {category}")

def show_summary(prefix="male_new"):
    """显示市场总结"""
    file_path = DATA_DIR / f"market_summary_{prefix}.json"
    if not file_path.exists():
        print(f"❌ 未找到 {prefix} 市场总结")
        return
    
    data = load_json(file_path)
    if not data:
        return
    
    print(f"\n📰 {prefix} 市场总结:")
    print("=" * 60)
    
    # 显示各周期总结
    for period in ['7d', '14d', '30d', 'all']:
        period_data = data.get(period, {})
        if period_data:
            print(f"\n📅 {period} 周期:")
            summary = period_data.get('summary', '暂无数据')
            print(f"  {summary[:200]}...")

def show_help():
    """显示帮助信息"""
    print(__doc__)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    # 获取可选参数
    prefix = "male_new"
    if len(sys.argv) > 2:
        if sys.argv[2] in ['male_new', 'male_read', 'female_new', 'female_read']:
            prefix = sys.argv[2]
    
    if command == "top":
        n = 10
        if len(sys.argv) > 2:
            try:
                n = int(sys.argv[2])
            except ValueError:
                pass
        show_top(n, prefix)
    
    elif command == "hot":
        show_hot(prefix)
    
    elif command == "new":
        show_new(prefix)
    
    elif command == "summary":
        show_summary(prefix)
    
    elif command == "help":
        show_help()
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == "__main__":
    main()