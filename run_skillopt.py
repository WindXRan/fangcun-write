"""SkillOpt training for novel rewrite prompts."""

import sys, os, json, re, time

sys.path.insert(0, "SkillOpt")
sys.path.insert(0, ".agents/skills/story-engine/tools")

os.environ["OPENAI_API_KEY"] = os.environ.get("API_KEY", "sk-ad9450b1670b485c8a456a52520dc5a8")

from pathlib import Path
from skillopt.envs.base import EnvAdapter
from skillopt.datasets.base import BaseDataLoader, BatchSpec


class NovelDataLoader(BaseDataLoader):
    def __init__(self, config_path, start=1, end=2):
        super().__init__()
        self.config = json.loads(open(config_path, encoding="utf-8").read())
        all_items = [{"id": f"ch{ch:03d}", "chapter": ch} for ch in range(start, end + 1)]
        n = len(all_items)
        self.train_items = all_items[:max(1, n - 1)]
        self.val_items = all_items[n - 1:] if n > 1 else all_items[:1]
        self.test_items = []

    def build_train_batch(self, batch_size, seed, **kw):
        return BatchSpec(payload=self.train_items[:batch_size], seed=seed, batch_size=batch_size, phase="train", split="train")

    def build_eval_batch(self, env_num, split, seed, **kw):
        items = self.val_items[:env_num] if split == "val" else self.test_items[:env_num]
        return BatchSpec(payload=items, seed=seed, batch_size=env_num, phase="eval", split=split)


class NovelAdapter(EnvAdapter):
    def __init__(self, config_path="", start=1, end=2, api_key="", base_dir="", **kw):
        super().__init__()
        self.dl = NovelDataLoader(config_path, start, end)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.analyst_workers = 2
        self.edit_budget = 3
        self.minibatch_size = 2
        self.failure_only = False
        config = self.dl.config
        config.setdefault("base_dir", base_dir or os.path.dirname(os.path.abspath(config_path)))
        rw = config.get("rewrites_dir", "")
        if rw and not Path(rw).is_absolute():
            config["rewrites_dir"] = str(Path(config["base_dir"]) / rw)
        self.config = config

    def setup(self, cfg):
        super().setup(cfg)
        self.dl.setup(cfg)

    def get_dataloader(self):
        return self.dl

    def build_env_from_batch(self, batch, **kw):
        return list(batch.payload or [])

    def build_train_env(self, batch_size, seed, **kw):
        b = self.dl.build_train_batch(batch_size, seed, **kw)
        return self.build_env_from_batch(b)

    def build_eval_env(self, env_num, split, seed, **kw):
        b = self.dl.build_eval_batch(env_num, split, seed, **kw)
        return self.build_env_from_batch(b)

    def rollout(self, env_manager, skill_content, out_dir, **kw):
        items = env_manager
        if not items:
            return []

        # Write skill to prompt
        pp = Path(".agents/skills/story-engine/prompts/write-chapter.md")
        old = pp.read_text(encoding="utf-8")
        if skill_content and skill_content.strip().startswith("---"):
            pp.write_text(skill_content, encoding="utf-8")

        # Run pipeline
        from phases.style_extract import phase_style_extract
        from phases.guides import phase_guides
        from phases.write import phase_write
        from utils import get_source_text
        from lib.text_metrics import count_style_fingerprint

        config = self.config
        chs = sorted(set(i["chapter"] for i in items))
        os.makedirs(Path(config["rewrites_dir"]) / "chapters", exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        phase_style_extract(config, min(chs), max(chs), workers=3)
        phase_guides(config, min(chs), max(chs), workers=3)
        phase_write(config, min(chs), max(chs), workers=3)

        results = []
        for item in items:
            ch = item["chapter"]
            src = get_source_text(config, ch)
            rwf = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
            r = {"id": item["id"], "hard": 0.0, "soft": 0.0, "meta": {}}

            if src and rwf.exists():
                rw = rwf.read_text(encoding="utf-8")
                fs = count_style_fingerprint(src)
                fr = count_style_fingerprint(rw)

                # Score: lower gap = better
                gaps = []
                for k in ["paragraph_avg_len", "sentence_avg_len", "dialogue_ratio"]:
                    sv = fs.get(k, 0); rv = fr.get(k, 0)
                    if sv > 0: gaps.append(abs(rv - sv) / sv)

                avg_gap = sum(gaps) / max(len(gaps), 1) if gaps else 1.0
                soft = round(max(0, 1.0 - avg_gap), 3)
                hard = 1.0 if soft > 0.7 else 0.0
                r = {"id": item["id"], "hard": hard, "soft": soft,
                     "meta": {"gap": round(avg_gap, 3), "chars": fr.get("chars", 0)}}

            results.append(r)

        # Save as rollouts.json
        with open(Path(out_dir) / "rollouts.json", "w") as f:
            json.dump({"items": results}, f, indent=2)

        # Restore original prompt (SkillOpt will edit its own copy)
        pp.write_text(old, encoding="utf-8")
        return results

    def get_task_types(self):
        return ["novel_chapter"]

    def _load_env_prompt(self, name):
        from skillopt.prompts import load_prompt
        return load_prompt(name, env="novel_rewrite") or ""

    def get_error_minibatch_prompt(self):
        return "Analyze the failed rollouts and propose specific edits to the skill."

    def get_success_minibatch_prompt(self):
        return "Analyze the successful rollouts and propose improvements to the skill."


# ── Register ──
from skillopt.engine.trainer import ReflACTTrainer

# 复制 skill 到 SkillOpt 输出目录，用英文路径防 GBK
import shutil
os.makedirs("_skillopt_train", exist_ok=True)
shutil.copy(".agents/skills/story-engine/prompts/write-chapter.md",
            "_skillopt_train/initial_skill.md")

cfg = {
    "optimizer_model": "deepseek-chat",
    "target_model": "deepseek-chat",
    "optimizer_backend": "openai_chat",
    "target_backend": "openai_chat",
    "reasoning_effort": "medium",
    "num_epochs": 2,
    "batch_size": 2,
    "seed": 42,
    "train_size": 2,
    "accumulation": 1,
    "minibatch_size": 2,
    "merge_batch_size": 2,
    "edit_budget": 3,
    "learning_rate": 3,
    "skill_update_mode": "patch",
    "use_slow_update": False,
    "use_meta_skill": False,
    "eval_test": False,
    "use_gate": True,
    "sel_env_num": 1,
    "test_env_num": 0,
    "env": "novel_rewrite",
    "skill_init": "_skillopt_train/initial_skill.md",
    "out_root": "_skillopt_train",
}

adapter = NovelAdapter(
    config_path="configs/test_female.json", start=1, end=2,
    api_key=os.environ["OPENAI_API_KEY"],
    base_dir=os.path.dirname(os.path.abspath(__file__)),
)
adapter.setup(cfg)

print(f"\n{'='*60}")
print(f"  SkillOpt — Novel Rewrite")
print(f"  chapters: 1-2, epochs: 2, batch: 2")
print(f"  target: deepseek-chat @ api.deepseek.com")
print(f"  output: {cfg['out_root']}")
print(f"{'='*60}\n")

trainer = ReflACTTrainer(cfg, adapter)
summary = trainer.train()

print(f"\nDone: {cfg['out_root']}")
