"""
writer-engine pipeline: 通用写作能力引擎

支持独立使用或被其他引擎调用。
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 添加 shared-engine 到 path
_SHARED_ENGINE = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
_SHARED_ENGINE_LLM = _SHARED_ENGINE / "llm"
sys.path.insert(0, str(_SHARED_ENGINE))
sys.path.insert(0, str(_SHARED_ENGINE_LLM))

from writer import write_chapter, trim_chapter, polish_chapter, expand_chapter, rewrite_chapter


def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 自动检测 base_dir（如果未指定）
    if "base_dir" not in config:
        # 从 config_path 推断：.agents/skills/writer-engine/config/xxx.json -> 项目根目录
        config["base_dir"] = str(Path(config_path).parent.parent.parent.parent.parent)
    
    # 如果 rewrites_dir 是相对路径，基于 base_dir 解析
    if "rewrites_dir" in config and not Path(config["rewrites_dir"]).is_absolute():
        config["rewrites_dir"] = str(Path(config["base_dir"]) / config["rewrites_dir"])
    
    return config


def phase_write(config, start, end):
    """写章"""
    print("\n" + "=" * 50)
    print("Phase: 写章")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    for ch_num in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
        
        # 检查是否已存在
        if ch_file.exists():
            print(f"    [SKIP] 第{ch_num}章已存在")
            continue
        
        # 写章
        print(f"    [WRITE] 第{ch_num}章...")
        result = write_chapter(config, ch_num)
        
        if result:
            ch_file.write_text(result, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章 ({len(result)}字)")
        else:
            print(f"    [FAIL] 第{ch_num}章")


def phase_trim(config, start, end):
    """精简"""
    print("\n" + "=" * 50)
    print("Phase: 精简")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    
    for ch_num in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
        
        if not ch_file.exists():
            print(f"    [SKIP] 第{ch_num}章不存在")
            continue
        
        print(f"    [TRIM] 第{ch_num}章...")
        result = trim_chapter(config, ch_num)
        
        if result:
            ch_file.write_text(result, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章")
        else:
            print(f"    [FAIL] 第{ch_num}章")


def phase_polish(config, start, end):
    """润色"""
    print("\n" + "=" * 50)
    print("Phase: 润色")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    
    for ch_num in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
        
        if not ch_file.exists():
            print(f"    [SKIP] 第{ch_num}章不存在")
            continue
        
        print(f"    [POLISH] 第{ch_num}章...")
        result = polish_chapter(config, ch_num)
        
        if result:
            ch_file.write_text(result, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章")
        else:
            print(f"    [FAIL] 第{ch_num}章")


def phase_expand(config, start, end):
    """扩写"""
    print("\n" + "=" * 50)
    print("Phase: 扩写")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    
    for ch_num in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
        
        if not ch_file.exists():
            print(f"    [SKIP] 第{ch_num}章不存在")
            continue
        
        print(f"    [EXPAND] 第{ch_num}章...")
        result = expand_chapter(config, ch_num)
        
        if result:
            ch_file.write_text(result, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章")
        else:
            print(f"    [FAIL] 第{ch_num}章")


def phase_rewrite(config, start, end, reason=""):
    """重写"""
    print("\n" + "=" * 50)
    print("Phase: 重写")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    
    for ch_num in range(start, end + 1):
        print(f"    [REWRITE] 第{ch_num}章...")
        result = rewrite_chapter(config, ch_num, reason=reason)
        
        if result:
            ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
            ch_file.write_text(result, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章 ({len(result)}字)")
        else:
            print(f"    [FAIL] 第{ch_num}章")


def main():
    parser = argparse.ArgumentParser(description="writer-engine: 通用写作能力引擎")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", required=True, 
                       choices=["write", "trim", "polish", "expand", "rewrite"],
                       help="执行阶段")
    parser.add_argument("--start", type=int, required=True, help="开始章节")
    parser.add_argument("--end", type=int, required=True, help="结束章节")
    parser.add_argument("--reason", default="", help="重写原因")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.phase == "write":
        phase_write(config, args.start, args.end)
    elif args.phase == "trim":
        phase_trim(config, args.start, args.end)
    elif args.phase == "polish":
        phase_polish(config, args.start, args.end)
    elif args.phase == "expand":
        phase_expand(config, args.start, args.end)
    elif args.phase == "rewrite":
        phase_rewrite(config, args.start, args.end, reason=args.reason)


if __name__ == "__main__":
    main()
