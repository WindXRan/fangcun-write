#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同步市场数据到story-rewrite
用法：python sync_market_data.py
"""

import shutil
from pathlib import Path

# 路径配置
SCAN_DIR = Path(__file__).parent
REWRITE_DIR = SCAN_DIR.parent / "story-rewrite"
SOURCE_FILE = SCAN_DIR / "market-data" / "番茄女频市场数据.json"
TARGET_FILE = REWRITE_DIR / "references" / "market-data.json"

def sync():
    """同步市场数据"""
    if not SOURCE_FILE.exists():
        print(f"❌ 源文件不存在: {SOURCE_FILE}")
        return False
    
    # 确保目标目录存在
    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 复制文件
    shutil.copy2(SOURCE_FILE, TARGET_FILE)
    
    print(f"✅ 同步成功!")
    print(f"   源: {SOURCE_FILE}")
    print(f"   目标: {TARGET_FILE}")
    print(f"   数据日期: {SOURCE_FILE.stat().st_mtime}")
    
    return True

if __name__ == "__main__":
    sync()
