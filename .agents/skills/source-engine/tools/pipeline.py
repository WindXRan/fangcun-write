"""
源书级分析 pipeline — 事件提取 → 故事骨架 → 改编策略。

产物存入 _cache/，供 story-engine 和 drama-engine 共用。

用法:
  python pipeline.py --config configs/xxx.json                     # 全流程
  python pipeline.py --config configs/xxx.json --phase event       # 仅事件提取
  python pipeline.py --config configs/xxx.json --phase skeleton    # 仅骨架
  python pipeline.py --config configs/xxx.json --phase adaptation  # 仅改编策略
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 确保 lib/ 在 path 中
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))

from lib.api_client import call_api, get_api_key, get_api_url
from source_analysis import extract_events, build_skeleton, build_adaptation
from file_io import load_events, load_skeleton, load_adaptation, get_cache_dir

# prompt 目录
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {p}")
    return p.read_text(encoding="utf-8")


def get_phase_model(config, phase: str) -> str:
    """按阶段解析模型。事件提取默认用非推理模型。"""
    overrides = config.get("model_overrides", {})
    if phase in overrides:
        return overrides[phase]
    if phase == "event" and "model_overrides" not in config:
        return "deepseek-chat"
    return config.get("model", "deepseek-chat")


def phase_event(config, workers=5):
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, "event")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    prompt_text = load_prompt("event_extraction.md")
    print(f"\n{'='*50}")
    print(f"事件提取 | 模型: {model} | 输出: {get_cache_dir(config)}/events.json")
    print(f"{'='*50}")
    events = extract_events(config, api_key, api_url, model, prompt_text, workers)
    return len(events) > 0


def phase_skeleton(config, dry_run=False):
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, "skeleton")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    system_prompt = load_prompt("skeleton.md")
    system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<storySkeleton>故事骨架内容</storySkeleton>"
    if dry_run:
        print(f"[DRY-RUN] 模型 {model}")
        return True
    print(f"\n{'='*50}")
    print(f"故事骨架 | 模型: {model} | 输出: {get_cache_dir(config)}/story_skeleton.md")
    print(f"{'='*50}")
    result = build_skeleton(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
    return result is not None


def phase_adaptation(config, dry_run=False):
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, "adaptation")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False
    system_prompt = load_prompt("adaptation.md")
    system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<adaptationStrategy>改编策略内容</adaptationStrategy>"
    if dry_run:
        print(f"[DRY-RUN] 模型 {model}")
        return True
    print(f"\n{'='*50}")
    print(f"改编策略 | 模型: {model} | 输出: {get_cache_dir(config)}/adaptation_strategy.md")
    print(f"{'='*50}")
    result = build_adaptation(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
    return result is not None


def main():
    parser = argparse.ArgumentParser(description="源书级分析 pipeline")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", default="all", choices=["all", "event", "skeleton", "adaptation"])
    parser.add_argument("--workers", type=int, default=5, help="事件提取并行数")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    get_cache_dir(config).mkdir(parents=True, exist_ok=True)

    print(f"\n{'#'*50}")
    print(f"源书级分析 | {config.get('source_book', '')}")
    print(f"{'#'*50}")

    if args.phase == "all":
        if not phase_event(config, args.workers): return
        if not phase_skeleton(config, args.dry_run): return
        phase_adaptation(config, args.dry_run)
    elif args.phase == "event":
        phase_event(config, args.workers)
    elif args.phase == "skeleton":
        phase_skeleton(config, args.dry_run)
    elif args.phase == "adaptation":
        phase_adaptation(config, args.dry_run)


if __name__ == "__main__":
    main()
