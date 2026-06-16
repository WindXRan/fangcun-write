"""Train novel rewrite skill using SkillOpt ReflACT loop.

Usage:
  python train_skill.py --config configs/test_female.json --epochs 5
"""

import sys, os, yaml, json, argparse

# Add paths
sys.path.insert(0, "c:/Users/裴浩然/Desktop/AI网文项目/SkillOpt")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skillopt.engine.trainer import Trainer
from skillopt.model import set_target_backend, set_optimizer_backend
from skillopt_adapter import NovelRewriteAdapter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Pipeline config JSON")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("API_KEY", "")
    base_dir = os.path.dirname(os.path.abspath(args.config))

    # Build adapter
    adapter = NovelRewriteAdapter(
        config_path=args.config,
        start=args.start,
        end=args.end,
        api_key=api_key,
        base_dir=base_dir,
    )

    # Initial skill = current write-chapter.md
    initial_skill = open(
        ".agents/skills/story-engine/prompts/write-chapter.md",
        encoding="utf-8"
    ).read()

    # Build config dict
    cfg = {
        "model": {
            "target_backend": "deepseek",
            "target_model": "deepseek-v4-pro",
            "optimizer_backend": "deepseek",
            "optimizer_model": "deepseek-v4-flash",
        },
        "train": {
            "num_epochs": args.epochs,
            "batch_size": args.batch_size,
        },
        "gradient": {
            "minibatch_size": 2,
            "edit_budget": 3,
        },
        "optimizer": {
            "learning_rate": 2,
        },
        "evaluation": {
            "sel_env_num": 1,
        },
        "env": {
            "name": "novel_rewrite",
            "skill_init_content": initial_skill,
        },
        "output_dir": "projects/闻栖/女配一睁眼，失忆男主冷脸洗床单/rewrites/女配觉醒后，失忆男主他慌了/_skillopt_train",
        "checkpoint_dir": "projects/闻栖/女配一睁眼，失忆男主冷脸洗床单/rewrites/女配觉醒后，失忆男主他慌了/_skillopt_ckpt",
        "seed": 42,
    }

    # Set API key via env
    os.environ["DEEPSEEK_API_KEY"] = api_key

    # Run trainer
    print(f"\nSkillOpt Training: {args.epochs} epochs x {args.batch_size} batch")
    print(f"Initial skill: {len(initial_skill)} chars")
    print(f"Output: {cfg['output_dir']}\n")

    trainer = Trainer(adapter=adapter, cfg=cfg)
    trainer.train()

    # Save best skill
    best_path = os.path.join(cfg["output_dir"], "best_skill.md")
    print(f"\nBest skill saved to: {best_path}")


if __name__ == "__main__":
    main()
