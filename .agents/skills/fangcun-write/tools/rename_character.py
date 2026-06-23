"""一键改名工具：修改角色名并自动更新所有相关文件。

用法：
    python rename_character.py --config configs/xxx.json --old 旧名 --new 新名
    python rename_character.py --config configs/xxx.json --old 旧名 --new 新名 --dry-run
"""

import argparse
import json
import re
import shutil
from pathlib import Path


def rename_character(config, old_name, new_name, dry_run=False):
    """一键改名：更新 characters.md、角色卡、所有章节。"""
    base_dir = Path(config.get("base_dir", "."))
    rewrites_dir = base_dir / config.get("rewrites_dir", "")
    
    changes = []
    
    # 1. 更新 characters.md
    chars_path = rewrites_dir / "characters.md"
    if chars_path.exists():
        content = chars_path.read_text(encoding="utf-8")
        if old_name in content:
            new_content = content.replace(f"【{old_name}】", f"【{new_name}】")
            if not dry_run:
                chars_path.write_text(new_content, encoding="utf-8")
            changes.append(f"characters.md: 【{old_name}】 → 【{new_name}】")
    
    # 2. 重命名角色卡文件
    cards_dir = rewrites_dir / "characters"
    if cards_dir.exists():
        old_card = cards_dir / f"{old_name}.md"
        new_card = cards_dir / f"{new_name}.md"
        if old_card.exists():
            if not dry_run:
                old_card.rename(new_card)
            changes.append(f"characters/{old_name}.md → characters/{new_name}.md")
    
    # 3. 更新所有章节文件
    chapters_dir = rewrites_dir / "chapters"
    if chapters_dir.exists():
        for ch_file in sorted(chapters_dir.glob("ch_*.txt")):
            content = ch_file.read_text(encoding="utf-8")
            if old_name in content:
                new_content = content.replace(old_name, new_name)
                if not dry_run:
                    ch_file.write_text(new_content, encoding="utf-8")
                count = content.count(old_name)
                changes.append(f"{ch_file.name}: {count} 处替换")
    
    # 4. 更新 plot_guide 文件
    guides_dir = rewrites_dir / "guides"
    if guides_dir.exists():
        for guide_file in sorted(guides_dir.glob("plot_*.md")):
            content = guide_file.read_text(encoding="utf-8")
            if old_name in content:
                new_content = content.replace(old_name, new_name)
                if not dry_run:
                    guide_file.write_text(new_content, encoding="utf-8")
                count = content.count(old_name)
                changes.append(f"{guide_file.name}: {count} 处替换")
    
    # 5. 更新 source_analysis.md（如果存在）
    source_analysis = rewrites_dir / "source_analysis.md"
    if source_analysis.exists():
        content = source_analysis.read_text(encoding="utf-8")
        if old_name in content:
            new_content = content.replace(old_name, new_name)
            if not dry_run:
                source_analysis.write_text(new_content, encoding="utf-8")
            count = content.count(old_name)
            changes.append(f"source_analysis.md: {count} 处替换")
    
    return changes


def main():
    parser = argparse.ArgumentParser(description="一键改名工具")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--old", required=True, help="旧角色名")
    parser.add_argument("--new", required=True, help="新角色名")
    parser.add_argument("--dry-run", action="store_true", help="只显示变更，不实际修改")
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        return
    
    config = json.loads(config_path.read_text(encoding="utf-8"))
    
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}改名: {args.old} → {args.new}")
    print("=" * 50)
    
    changes = rename_character(config, args.old, args.new, args.dry_run)
    
    if changes:
        for change in changes:
            print(f"  ✓ {change}")
        print(f"\n共 {len(changes)} 处修改")
    else:
        print("  未找到需要修改的内容")


if __name__ == "__main__":
    main()
