#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书在线表格同步脚本
将story-scan采集的数据同步到飞书在线表格
"""

import os
import sys
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# 飞书API配置
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_SPREADSHEET_TOKEN = os.getenv('FEISHU_SPREADSHEET_TOKEN')
FEISHU_SHEET_ID = os.getenv('FEISHU_SHEET_ID')

class FeishuSync:
    def __init__(self):
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.token_expires_at = 0
        
    def get_tenant_access_token(self) -> str:
        """获取tenant_access_token"""
        if self.access_token and datetime.now().timestamp() < self.token_expires_at:
            return self.access_token
            
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        }
        
        response = requests.post(url, json=data)
        if response.status_code != 200:
            raise Exception(f"获取token失败: {response.text}")
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"获取token失败: {result.get('msg')}")
            
        self.access_token = result["tenant_access_token"]
        # token有效期2小时，提前5分钟刷新
        self.token_expires_at = datetime.now().timestamp() + 7200 - 300
        return self.access_token
        
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
    def read_sheet_data(self, range_str: str = None) -> List[List[Any]]:
        """读取表格数据"""
        if not range_str:
            range_str = f"{FEISHU_SHEET_ID}"
            
        url = f"{self.base_url}/sheets/v2/spreadsheets/{FEISHU_SPREADSHEET_TOKEN}/values/{range_str}"
        headers = self.get_headers()
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"读取表格失败: {response.text}")
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"读取表格失败: {result.get('msg')}")
            
        return result.get("data", {}).get("valueRange", {}).get("values", [])
        
    def write_sheet_data(self, range_str: str, values: List[List[Any]]) -> bool:
        """写入表格数据"""
        url = f"{self.base_url}/sheets/v2/spreadsheets/{FEISHU_SPREADSHEET_TOKEN}/values"
        headers = self.get_headers()
        
        data = {
            "valueRange": {
                "range": range_str,
                "values": values
            }
        }
        
        response = requests.put(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"写入表格失败: {response.text}")
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"写入表格失败: {result.get('msg')}")
            
        return True
        
    def append_sheet_data(self, range_str: str, values: List[List[Any]]) -> bool:
        """追加表格数据"""
        url = f"{self.base_url}/sheets/v2/spreadsheets/{FEISHU_SPREADSHEET_TOKEN}/values_append"
        headers = self.get_headers()
        
        data = {
            "valueRange": {
                "range": range_str,
                "values": values
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"追加表格失败: {response.text}")
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"追加表格失败: {result.get('msg')}")
            
        return True
        
    def clear_sheet_data(self, range_str: str) -> bool:
        """清空表格数据"""
        url = f"{self.base_url}/sheets/v2/spreadsheets/{FEISHU_SPREADSHEET_TOKEN}/values"
        headers = self.get_headers()
        
        data = {
            "valueRange": {
                "range": range_str,
                "values": []
            }
        }
        
        response = requests.delete(url, headers=headers, json=data)
        if response.status_code != 200:
            raise Exception(f"清空表格失败: {response.text}")
            
        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"清空表格失败: {result.get('msg')}")
            
        return True

def load_latest_data(data_dir: Path) -> Dict[str, Any]:
    """加载最新的数据文件"""
    data = {}
    
    # 加载排行榜数据
    for prefix in ['male_new', 'male_read', 'female_new', 'female_read']:
        latest_file = data_dir / f"latest_{prefix}_ranks.json"
        if latest_file.exists():
            with open(latest_file, 'r', encoding='utf-8') as f:
                data[f"ranks_{prefix}"] = json.load(f)
                
    # 加载市场总结
    for prefix in ['male_new', 'male_read', 'female_new', 'female_read']:
        summary_file = data_dir / f"market_summary_{prefix}.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                data[f"summary_{prefix}"] = json.load(f)
                
    # 加载市场数据
    market_data_file = Path(__file__).parent / "market-data" / "番茄女频市场数据.json"
    if market_data_file.exists():
        with open(market_data_file, 'r', encoding='utf-8') as f:
            data["market_data"] = json.load(f)
            
    return data

def prepare_rank_data(rank_data: Dict[str, Any]) -> List[List[Any]]:
    """准备排行榜数据用于写入表格"""
    rows = []
    
    # 写入表头
    headers = ["排名", "书名", "作者", "阅读量", "状态", "字数", "最后更新", "简介"]
    rows.append(headers)
    
    # 写入数据
    for category in rank_data.get("categories", []):
        for i, book in enumerate(category.get("books", []), 1):
            row = [
                i,
                book.get("title", ""),
                book.get("author", ""),
                book.get("reads", ""),
                book.get("status", ""),
                book.get("word_count", ""),
                book.get("last_chapter", ""),
                book.get("intro", "")[:100] + "..." if len(book.get("intro", "")) > 100 else book.get("intro", "")
            ]
            rows.append(row)
            
    return rows

def prepare_summary_data(summary_data: Dict[str, Any]) -> List[List[Any]]:
    """准备市场总结数据用于写入表格"""
    rows = []
    
    # 写入标题
    rows.append(["市场总结", summary_data.get("date", ""), summary_data.get("periods", {}).get("7", {}).get("period", "")])
    rows.append([])  # 空行
    
    # 写入高频题材
    rows.append(["高频题材", "出现次数", "覆盖分类数"])
    for theme in summary_data.get("periods", {}).get("7", {}).get("hot_themes", []):
        rows.append([
            theme.get("name", ""),
            theme.get("count", 0),
            theme.get("category_count", 0)
        ])
        
    return rows

def prepare_market_data(market_data: Dict[str, Any]) -> List[List[Any]]:
    """准备市场数据用于写入表格"""
    rows = []
    
    # 写入热门题材
    rows.append(["热门题材", "热度", "趋势", "竞争程度", "描述", "代表作品"])
    for genre in market_data.get("hot_genres", []):
        rows.append([
            genre.get("name", ""),
            genre.get("heat", 0),
            genre.get("trend", ""),
            genre.get("competition", ""),
            genre.get("description", ""),
            ", ".join(genre.get("examples", []))
        ])
        
    rows.append([])  # 空行
    
    # 写入书名模式
    rows.append(["书名模式", "占比", "结构", "示例"])
    title_patterns = market_data.get("title_patterns", {})
    rows.append([
        title_patterns.get("dominant_style", ""),
        title_patterns.get("ratio_in_top", ""),
        title_patterns.get("structure", ""),
        ", ".join(title_patterns.get("examples", []))
    ])
        
    return rows

def sync_to_feishu(data_dir: Path = None):
    """同步数据到飞书"""
    if not data_dir:
        data_dir = Path(__file__).parent / "data"
        
    # 检查飞书配置
    if not all([FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_SPREADSHEET_TOKEN, FEISHU_SHEET_ID]):
        print("❌ 错误：请设置飞书环境变量")
        print("需要设置：FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_SPREADSHEET_TOKEN, FEISHU_SHEET_ID")
        return False
        
    print("📊 开始同步数据到飞书...")
    
    try:
        # 加载数据
        data = load_latest_data(data_dir)
        if not data:
            print("❌ 错误：没有找到数据文件")
            return False
            
        # 创建飞书同步实例
        feishu = FeishuSync()
        
        # 同步女频新书榜
        if "ranks_female_new" in data:
            print("📝 同步女频新书榜...")
            rank_data = data["ranks_female_new"]
            rows = prepare_rank_data(rank_data)
            range_str = f"{FEISHU_SHEET_ID}!A1:H{len(rows)}"
            feishu.write_sheet_data(range_str, rows)
            print(f"✅ 女频新书榜同步完成，共 {len(rows)-1} 条数据")
            
        # 同步市场总结
        if "summary_female_new" in data:
            print("📝 同步市场总结...")
            summary_data = data["summary_female_new"]
            rows = prepare_summary_data(summary_data)
            range_str = f"{FEISHU_SHEET_ID}!J1:L{len(rows)}"
            feishu.write_sheet_data(range_str, rows)
            print(f"✅ 市场总结同步完成")
            
        # 同步市场数据
        if "market_data" in data:
            print("📝 同步市场数据...")
            market_data = data["market_data"]
            rows = prepare_market_data(market_data)
            range_str = f"{FEISHU_SHEET_ID}!N1:S{len(rows)}"
            feishu.write_sheet_data(range_str, rows)
            print(f"✅ 市场数据同步完成")
            
        print("🎉 所有数据同步完成！")
        return True
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='同步数据到飞书在线表格')
    parser.add_argument('--data-dir', type=str, help='数据目录路径')
    parser.add_argument('--test', action='store_true', help='测试模式，只读取数据不写入')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    
    if args.test:
        print("🧪 测试模式：只读取数据")
        data = load_latest_data(data_dir or Path(__file__).parent / "data")
        print(f"📊 找到 {len(data)} 个数据文件")
        for key, value in data.items():
            print(f"  - {key}: {type(value)}")
    else:
        sync_to_feishu(data_dir)

if __name__ == "__main__":
    main()