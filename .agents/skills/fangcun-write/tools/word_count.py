#!/usr/bin/env python3
"""字数统计工具 — 统计正文实际字数（去掉XML标签和空白）。"""

import re, sys
from pathlib import Path

def count_chars(text: str) -> int:
    """去掉XML标签和空白，统计纯中文字符数。"""
    clean = re.sub(r'<[^>]+>', '', text)         # 去XML标签
    clean = re.sub(r'\s+', '', clean)             # 去空白
    return len(clean)

def check_chapter(filepath: str, target_min=2000, target_max=3000) -> dict:
    p = Path(filepath)
    if not p.exists():
        return {"error": f"文件不存在: {filepath}", "path": filepath}

    raw = p.read_text(encoding='utf-8')
    total = count_chars(raw)

    # 只统计 <content> 标签内的正文
    content_m = re.search(r'<content>(.*?)</content>', raw, re.DOTALL)
    content_chars = count_chars(content_m.group(1)) if content_m else total

    status = "ok"
    notes = []
    if content_chars < target_min:
        status = "过短"
        notes.append(f"仅{content_chars}字，不足{target_min}字")
    elif content_chars > target_max:
        status = "过长"
        notes.append(f"{content_chars}字，超过{target_max}字")

    return {
        "path": str(p),
        "total_chars": total,
        "content_chars": content_chars,
        "target": f"{target_min}-{target_max}",
        "status": status,
        "notes": notes,
    }

if __name__ == "__main__":
    target_min = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    target_max = int(sys.argv[3]) if len(sys.argv) > 3 else 3000

    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            continue
        result = check_chapter(arg, target_min, target_max)
        status_sym = "✅" if result["status"] == "ok" else "🚨"
        print(f'{status_sym} {result["path"]}')
        print(f'   正文: {result["content_chars"]}字 / 目标: {result["target"]}')
        if result["notes"]:
            for n in result["notes"]:
                print(f'   ⚠️  {n}')
        if "error" in result:
            print(f'   ❌ {result["error"]}')
