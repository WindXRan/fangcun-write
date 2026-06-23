#!/usr/bin/env python3
"""部署Skill到Coze平台"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

COZE_API_BASE = "https://api.coze.cn/v1"


def read_skill_config(skill_path: str) -> dict:
    """读取skill配置"""
    skill_dir = Path(skill_path)
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_path}")
    
    content = skill_md.read_text(encoding="utf-8")
    
    # 解析frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            # 简单解析YAML frontmatter
            frontmatter = parts[1].strip()
            description = ""
            for line in frontmatter.split("\n"):
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    break
            
            return {
                "name": skill_dir.name,
                "description": description,
                "prompt": parts[2].strip(),
                "path": str(skill_dir)
            }
    
    return {
        "name": skill_dir.name,
        "description": "",
        "prompt": content,
        "path": str(skill_dir)
    }


def create_coze_bot(config: dict, token: str, space_id: str) -> dict:
    """创建Coze Bot"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构建Bot配置
    bot_config = {
        "name": config["name"],
        "description": config["description"][:200],  # Coze限制200字
        "prompt": config["prompt"][:4000],  # Coze限制4000字
        "space_id": space_id,
        "visibility": "private"  # 先设为私有，审核后公开
    }
    
    # 调用Coze API
    resp = requests.post(
        f"{COZE_API_BASE}/bots",
        headers=headers,
        json=bot_config,
        timeout=30
    )
    
    if resp.status_code != 200:
        raise Exception(f"Coze API error: {resp.status_code} - {resp.text}")
    
    return resp.json()


def update_coze_bot(bot_id: str, config: dict, token: str) -> dict:
    """更新Coze Bot"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    bot_config = {
        "name": config["name"],
        "description": config["description"][:200],
        "prompt": config["prompt"][:4000]
    }
    
    resp = requests.put(
        f"{COZE_API_BASE}/bots/{bot_id}",
        headers=headers,
        json=bot_config,
        timeout=30
    )
    
    if resp.status_code != 200:
        raise Exception(f"Coze API error: {resp.status_code} - {resp.text}")
    
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Deploy skill to Coze")
    parser.add_argument("--skill", required=True, help="Skill directory path")
    parser.add_argument("--token", required=True, help="Coze API token")
    parser.add_argument("--space-id", required=True, help="Coze space ID")
    parser.add_argument("--bot-id", help="Existing bot ID to update")
    
    args = parser.parse_args()
    
    try:
        # 读取skill配置
        print(f"Reading skill config from {args.skill}...")
        config = read_skill_config(args.skill)
        print(f"  Name: {config['name']}")
        print(f"  Description: {config['description'][:50]}...")
        
        # 创建或更新Bot
        if args.bot_id:
            print(f"Updating existing bot {args.bot_id}...")
            result = update_coze_bot(args.bot_id, config, args.token)
        else:
            print("Creating new bot...")
            result = create_coze_bot(config, args.token, args.space_id)
        
        bot_id = result.get("data", {}).get("bot_id", "unknown")
        print(f"✅ Success! Bot ID: {bot_id}")
        print(f"   URL: https://www.coze.cn/bot/{bot_id}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
