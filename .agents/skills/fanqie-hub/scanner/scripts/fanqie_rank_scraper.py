#!/usr/bin/env python3
"""番茄小说排行榜爬虫

用法：
  python fanqie_rank_scraper.py --channel 1 --type 2 --outdir ./data
  python fanqie_rank_scraper.py --channel all --top 15 --outdir ./data

参数：
  --channel: 0=女频, 1=男频, all=全部
  --type: 1=新书榜, 2=阅读榜
  --top: 每个题材取前N本（默认20）
  --outdir: 输出目录
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from pathlib import Path

# 番茄API
FANQIE_API = "https://fanqienovel.com/api/rank"
FANQIE_PAGE = "https://fanqienovel.com/page"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fanqienovel.com/"
}

# 题材分类
CATEGORIES = {
    1: "都市",
    2: "玄幻",
    3: "仙侠",
    4: "历史",
    5: "游戏",
    6: "科幻",
    7: "悬疑",
    8: "灵异",
    9: "言情",
    10: "穿越",
    11: "重生",
    12: "宫斗",
    13: "种田",
    14: "年代",
    15: "现言",
    16: "古言",
    17: "快穿",
    18: "系统",
    19: "无敌",
    20: "赘婿"
}


def get_rank_list(channel, type_id, cat_id=0, page=0):
    """获取排行榜数据"""
    url = f"{FANQIE_API}/{channel}_{type_id}_{cat_id}"
    params = {"page": page}
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("rank_list", [])
    except Exception as e:
        print(f"  错误: {e}")
    
    return []


def get_book_info(book_id):
    """获取书籍详情"""
    url = f"{FANQIE_PAGE}/{book_id}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        # 从页面提取信息
        text = resp.text
        
        # 提取书名
        import re
        title_match = re.search(r'<title>(.*?)</title>', text)
        title = title_match.group(1) if title_match else ""
        title = title.replace("完整版在线免费阅读_番茄小说", "").strip()
        
        # 提取简介
        desc_match = re.search(r'<meta name="description" content="(.*?)"', text)
        desc = desc_match.group(1) if desc_match else ""
        
        return {
            "title": title,
            "description": desc[:200]
        }
    except:
        return {}


def scrape_rank(channel, type_id, top=20):
    """采集排行榜"""
    print(f"采集: channel={channel}, type={type_id}")
    
    books = []
    
    # 遍历题材分类
    for cat_id, cat_name in CATEGORIES.items():
        print(f"  {cat_name}...", end="", flush=True)
        
        rank_list = get_rank_list(channel, type_id, cat_id)
        
        for i, item in enumerate(rank_list[:top]):
            book = {
                "rank": i + 1,
                "book_id": item.get("book_id", ""),
                "title": item.get("book_name", ""),
                "author": item.get("author", ""),
                "category": cat_name,
                "word_count": item.get("word_count", 0),
                "read_count": item.get("read_count", 0),
                "score": item.get("score", 0),
                "tags": item.get("tags", []),
            }
            books.append(book)
        
        count = len(rank_list[:top])
        print(f" {count}本")
        time.sleep(0.5)
    
    return books


def save_report(books, outdir, channel_name, type_name):
    """保存扫榜报告"""
    os.makedirs(outdir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"番茄{channel_name}{type_name}_{timestamp}.md"
    filepath = os.path.join(outdir, filename)
    
    # 统计题材分布
    category_counts = {}
    for book in books:
        cat = book.get("category", "未知")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # 按数量排序
    sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    # 生成报告
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# 番茄小说扫榜报告\n\n")
        f.write(f"## 市场概况\n")
        f.write(f"- 扫榜时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"- 榜单类型：{channel_name}{type_name}\n")
        f.write(f"- 采集数量：{len(books)} 本\n\n")
        
        f.write(f"## 题材热度排行\n\n")
        f.write(f"| 排名 | 题材 | 榜上数量 | 占比 |\n")
        f.write(f"|------|------|----------|------|\n")
        for i, (cat, count) in enumerate(sorted_cats[:10], 1):
            pct = count / len(books) * 100
            f.write(f"| {i} | {cat} | {count}本 | {pct:.1f}% |\n")
        
        f.write(f"\n## 热门书籍\n\n")
        f.write(f"| 排名 | 书名 | 作者 | 题材 | 字数 |\n")
        f.write(f"|------|------|------|------|------|\n")
        for book in books[:50]:
            wc = book.get("word_count", 0)
            wc_str = f"{wc/10000:.1f}万" if wc > 10000 else str(wc)
            f.write(f"| {book['rank']} | {book['title']} | {book['author']} | {book['category']} | {wc_str} |\n")
        
        f.write(f"\n## 标签热词\n\n")
        # 统计标签
        tag_counts = {}
        for book in books:
            for tag in book.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        for tag, count in sorted_tags:
            f.write(f"- {tag}: {count}次\n")
    
    print(f"\n报告已保存: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description='番茄小说排行榜爬虫')
    parser.add_argument('--channel', type=str, default='1', help='0=女频, 1=男频, all=全部')
    parser.add_argument('--type', type=int, default=2, help='1=新书榜, 2=阅读榜')
    parser.add_argument('--top', type=int, default=20, help='每个题材取前N本')
    parser.add_argument('--outdir', type=str, default='./data', help='输出目录')
    
    args = parser.parse_args()
    
    # 确定采集范围
    channels = [0, 1] if args.channel == 'all' else [int(args.channel)]
    type_name = "新书榜" if args.type == 1 else "阅读榜"
    
    for channel in channels:
        channel_name = "女频" if channel == 0 else "男频"
        print(f"\n=== {channel_name}{type_name} ===\n")
        
        books = scrape_rank(channel, args.type, args.top)
        
        if books:
            save_report(books, args.outdir, channel_name, type_name)
        else:
            print("未采集到数据")


if __name__ == '__main__':
    main()
