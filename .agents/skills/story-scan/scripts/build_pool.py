"""
每个榜单合成一个大池子：
- latest_female_new_ranks.json → pool_女频新书.json
- latest_female_read_ranks.json → pool_女频在读.json
- latest_male_new_ranks.json → pool_男频新书.json
每本书加上 category 字段标记来源分类。
"""

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POOL_DIR = DATA_DIR / "pools"
POOL_DIR.mkdir(exist_ok=True)

RANK_FILES = {
    "女频新书": "latest_female_new_ranks.json",
    "女频在读": "latest_female_read_ranks.json",
    "男频新书": "latest_male_new_ranks.json",
}

def merge_pool(name, filename):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  ❌ {filename} 不存在，跳过")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", [])
    pool = []
    cat_stats = {}

    for cat in categories:
        cat_name = cat.get("name", "未知")
        books = cat.get("books", [])
        cat_stats[cat_name] = len(books)
        for book in books:
            entry = dict(book)
            entry["category"] = cat_name
            pool.append(entry)

    total = len(pool)
    out = {
        "rank_type": data.get("rank_type", name),
        "date": data.get("date", ""),
        "prev_date": data.get("prev_date", ""),
        "total_books": total,
        "category_count": len(categories),
        "categories": cat_stats,
        "books": pool,
    }

    safe_name = name.replace(" ", "_").replace("/", "_")
    out_path = POOL_DIR / f"pool_{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {name}: {total} 本书（{len(categories)} 个分类）→ {out_path}")

def main():
    print("合并大池子...\n")
    for name, filename in RANK_FILES.items():
        merge_pool(name, filename)
    print(f"\n完成，文件在 {POOL_DIR}/")

if __name__ == "__main__":
    main()
