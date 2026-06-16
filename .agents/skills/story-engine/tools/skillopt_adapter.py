"""SkillOpt adapter for novel rewrite pipeline.

The "skill" = write-chapter.md prompt.
The "environment" = write chapter + evaluate vs source.
Rollout = run pipeline, Reflect = analyze gaps.
"""

import sys, os, json, re, time
from pathlib import Path

# Add SkillOpt to path
sys.path.insert(0, "c:/Users/裴浩然/Desktop/AI网文项目/SkillOpt")

from skillopt.envs.base import EnvAdapter
from skillopt.datasets.base import BaseDataLoader, BatchSpec


class NovelChapterDataLoader(BaseDataLoader):
    """Load chapter pairs (source + config) as training items."""

    def __init__(self, config_path: str, start: int = 1, end: int = 3,
                 split_ratio: str = "2:1:7", seed: int = 42):
        super().__init__()
        self.config_path = config_path
        self.start = start
        self.end = end

        # Build all chapter items
        base = os.path.dirname(os.path.abspath(config_path))
        config = json.loads(open(config_path, encoding="utf-8").read())
        config.setdefault("base_dir", base)
        self.config = config

        all_items = []
        for ch in range(start, end + 1):
            all_items.append({
                "id": f"ch{ch:03d}",
                "chapter": ch,
                "config_path": config_path,
            })

        # Split
        import random
        rng = random.Random(seed)
        rng.shuffle(all_items)

        ratios = [int(x) for x in split_ratio.split(":")]
        total = sum(ratios)
        t = int(len(all_items) * ratios[0] / total)
        v = int(len(all_items) * ratios[1] / total)

        self.train_items = all_items[:t]
        self.val_items = all_items[t:t + v]
        self.test_items = all_items[t + v:]

        # If not enough items, use all for train
        if len(self.train_items) < 2:
            self.train_items = all_items
            self.val_items = all_items[:1]
            self.test_items = []

    def build_train_batch(self, batch_size: int, seed: int, **kwargs):
        items = self.train_items[:batch_size]
        return BatchSpec(payload=items, batch_id=f"train_{seed}", split="train")

    def build_eval_batch(self, env_num: int, split: str, seed: int, **kwargs):
        items = self.val_items[:env_num] if split == "val" else self.test_items[:env_num]
        return BatchSpec(payload=items, batch_id=f"{split}_{seed}", split=split)


class NovelRewriteAdapter(EnvAdapter):
    """Adapt novel rewrite pipeline to SkillOpt ReflACT loop."""

    def __init__(self, config_path: str, start: int = 1, end: int = 3,
                 api_key: str = "", base_dir: str = ""):
        self.dataloader = NovelChapterDataLoader(config_path, start, end)
        self.api_key = api_key or os.environ.get("API_KEY", "")
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(config_path))

    def setup(self, cfg: dict) -> None:
        super().setup(cfg)
        self.dataloader.setup(cfg)

    def get_dataloader(self):
        return self.dataloader

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        batch = self.dataloader.build_train_batch(batch_size=batch_size, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        batch = self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def rollout(self, env_manager, skill_content: str, out_dir: str, **kwargs) -> list[dict]:
        """Run write pipeline with current skill (prompt), evaluate vs source."""
        items: list[dict] = env_manager

        # Save current skill to write-chapter.md
        if skill_content:
            prompt_path = Path(".agents/skills/story-engine/prompts/write-chapter.md")
            prompt_path.write_text(skill_content, encoding="utf-8")

        # Import pipeline
        sys.path.insert(0, ".agents/skills/story-engine/tools")
        from phases.style_extract import phase_style_extract
        from phases.guides import phase_guides
        from phases.write import phase_write
        from utils import get_source_text
        from lib.text_metrics import count_style_fingerprint

        config = self.dataloader.config
        chapters_dir = Path(config["rewrites_dir"]) / "chapters"
        os.makedirs(str(chapters_dir), exist_ok=True)

        # Run pipeline
        chapters = sorted(set(item["chapter"] for item in items))
        start, end = min(chapters), max(chapters)
        phase_style_extract(config, start, end, workers=3)
        phase_guides(config, start, end, workers=3)
        phase_write(config, start, end, workers=3)

        results = []
        for item in items:
            ch = item["chapter"]
            result = {"id": item["id"], "hard": 0.0, "soft": 0.0, "meta": {}}

            # Compare rewrite vs source
            src = get_source_text(config, ch)
            rw_file = chapters_dir / f"ch_{ch:03d}.txt"
            if src and rw_file.exists():
                rw = rw_file.read_text(encoding="utf-8")
                fp_src = count_style_fingerprint(src)
                fp_rw = count_style_fingerprint(rw)

                # Distance score: how close is rewrite to source style?
                gaps = []
                for key in ["paragraph_avg_len", "sentence_avg_len", "dialogue_ratio"]:
                    sv = fp_src.get(key, 0)
                    rv = fp_rw.get(key, 0)
                    if sv > 0:
                        gaps.append(abs(rv - sv) / sv)

                avg_gap = sum(gaps) / max(len(gaps), 1) if gaps else 1.0
                soft_score = max(0, 1.0 - avg_gap)  # 0=bad, 1=perfect match
                hard_score = 1.0 if soft_score > 0.7 else 0.0

                result["soft"] = round(soft_score, 3)
                result["hard"] = hard_score
                result["meta"] = {
                    "chars": fp_rw.get("chars", 0),
                    "para_gap": abs(fp_rw.get("paragraph_avg_len", 0) - fp_src.get("paragraph_avg_len", 0)),
                    "sent_gap": abs(fp_rw.get("sentence_avg_len", 0) - fp_src.get("sentence_avg_len", 0)),
                }

            results.append(result)

        return results

    def get_task_types(self) -> list[str]:
        return ["novel_chapter"]
