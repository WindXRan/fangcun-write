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
from file_io import load_events, load_skeleton, load_adaptation, get_cache_dir, get_events_text

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


def phase_review(config, target="all"):
    """质量审核。target: skeleton / adaptation / all"""
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, "review")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return False

    # 从 drama-engine 加载审核 prompt
    drama_prompts = Path(__file__).parent.parent.parent / "drama-engine" / "prompts"
    supervision_file = drama_prompts / "supervision.md"
    if supervision_file.exists():
        system_prompt = supervision_file.read_text(encoding="utf-8")
    else:
        system_prompt = "你是短剧改编项目的监督层 Agent，负责审核产出物质量。"

    cache = get_cache_dir(config)
    reviews_dir = cache / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    events_text = get_events_text(config)

    results = []

    if target in ("skeleton", "all"):
        skeleton = load_skeleton(config)
        if skeleton:
            print(f"\n{'='*50}")
            print(f"审核：故事骨架")
            print(f"{'='*50}")
            user_prompt = f"""请审核【故事骨架】的产出物。
审核维度：结构完整性、分集与时长、章节全覆盖、付费点分布、股价级反转登记、矛盾强度、三大密度结构、心理级爽点/金手指、投放素材、前10%黄金结构、情绪布局、信息差标注、集末钩子、节奏框架

## 故事骨架
{skeleton}

## 事件表
{events_text}"""
            try:
                result = call_api(api_key, model, user_prompt, system_prompt=system_prompt,
                                  api_url=api_url, temperature=0.3, max_tokens=4096)
                review_file = reviews_dir / "skeleton_review.md"
                review_file.write_text(result, encoding="utf-8")
                results.append(("故事骨架", result))
                print(f"  ✓ 审核完成 → {review_file}")
            except Exception as e:
                print(f"  ✗ 审核失败: {e}")

    if target in ("adaptation", "all"):
        adaptation = load_adaptation(config)
        skeleton = load_skeleton(config)
        if adaptation:
            print(f"\n{'='*50}")
            print(f"审核：改编策略")
            print(f"{'='*50}")
            user_prompt = f"""请审核【改编策略】的产出物。
审核维度：用户意图一致、与骨架一致、原创性/反洗稿、股价级反转来源一致、8大要点覆盖、三大密度策略、心理级爽点锁定、AI形态适配、原则质量、情绪基调一致、人物弧光保留、删减合理性、世界观呈现、语言适配

## 故事骨架
{skeleton}

## 改编策略
{adaptation}"""
            try:
                result = call_api(api_key, model, user_prompt, system_prompt=system_prompt,
                                  api_url=api_url, temperature=0.3, max_tokens=4096)
                review_file = reviews_dir / "adaptation_review.md"
                review_file.write_text(result, encoding="utf-8")
                results.append(("改编策略", result))
                print(f"  ✓ 审核完成 → {review_file}")
            except Exception as e:
                print(f"  ✗ 审核失败: {e}")

    if results:
        print(f"\n{'='*50}")
        print(f"审核完成 | {len(results)}项")
        print(f"{'='*50}")
    return True


def main():
    parser = argparse.ArgumentParser(description="源书级分析 pipeline")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", default="all",
                        choices=["all", "event", "skeleton", "adaptation", "review", "status"],
                        help="执行阶段")
    parser.add_argument("--workers", type=int, default=5, help="事件提取并行数")
    parser.add_argument("--review-target", default="all", choices=["skeleton", "adaptation", "all"],
                        help="审核目标")
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
        if not phase_review(config, "skeleton"): return
        if not phase_adaptation(config, args.dry_run): return
        phase_review(config, "adaptation")
    elif args.phase == "event":
        phase_event(config, args.workers)
    elif args.phase == "skeleton":
        phase_skeleton(config, args.dry_run)
    elif args.phase == "adaptation":
        phase_adaptation(config, args.dry_run)
    elif args.phase == "review":
        phase_review(config, args.review_target)
    elif args.phase == "status":
        cache = get_cache_dir(config)
        for name in ["events.json", "story_skeleton.md", "adaptation_strategy.md"]:
            f = cache / name
            if f.exists():
                print(f"  ✓ {name} ({f.stat().st_size} 字节)")
            else:
                print(f"  ✗ {name} (不存在)")
        reviews = cache / "reviews"
        if reviews.exists():
            for f in sorted(reviews.glob("*.md")):
                print(f"  ✓ reviews/{f.name} ({f.stat().st_size} 字节)")


if __name__ == "__main__":
    main()
