"""
市场数据加载器 - 从 story-scan 数据中提取市场洞察
"""

import json
from pathlib import Path


def load_market_summary(config):
    """加载市场摘要数据，返回格式化的市场洞察。"""
    base_dir = Path(config.get("base_dir", "."))
    market_file = base_dir / ".agents" / "skills" / "story-scan" / "data" / "market_summary_male_new.json"
    
    if not market_file.exists():
        return "（市场数据未找到，请先运行 story-scan 采集数据）"
    
    try:
        with open(market_file, encoding='utf-8') as f:
            data = json.load(f)
        
        lines = []
        lines.append("## 市场洞察（番茄小说）")
        lines.append("")
        
        # 7日趋势
        if "periods" in data and "7" in data["periods"]:
            period = data["periods"]["7"]
            lines.append(f"### 近7日趋势")
            lines.append(f"- {period.get('summary', '无数据')}")
            lines.append("")
        
        # 热门题材
        if "periods" in data and "7" in data["periods"]:
            hot_genres = data["periods"]["7"].get("hot_genres", [])
            if hot_genres:
                lines.append("### 热门题材")
                for g in hot_genres[:5]:
                    lines.append(f"- {g['name']}（热度分：{g.get('score', 'N/A')}）")
                lines.append("")
        
        # 趋势题材
        if "periods" in data and "7" in data["periods"]:
            trending = data["periods"]["7"].get("trending_genres", [])
            if trending:
                lines.append("### 上升题材")
                for g in trending[:3]:
                    lines.append(f"- {g['name']}")
                lines.append("")
        
        return "\n".join(lines) if len(lines) > 3 else "（市场数据为空）"
    
    except Exception as e:
        return f"（市场数据读取失败：{e}）"


def get_genre_recommendation(config):
    """基于市场数据推荐题材。"""
    base_dir = Path(config.get("base_dir", "."))
    market_file = base_dir / ".agents" / "skills" / "story-scan" / "data" / "market_summary_male_new.json"
    
    if not market_file.exists():
        return None
    
    try:
        with open(market_file, encoding='utf-8') as f:
            data = json.load(f)
        
        if "periods" in data and "7" in data["periods"]:
            hot_genres = data["periods"]["7"].get("hot_genres", [])
            if hot_genres:
                return [g['name'] for g in hot_genres[:3]]
    
    except:
        pass
    
    return None
