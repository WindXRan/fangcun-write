"""快速 debug prompt：只调单章，查看生成的 prompt 和 API 返回。

用法：
  # 查看最终发给 API 的 prompt（不调 API，秒出）
  python debug_prompt.py --config configs/xxx.json --phase write --ch 1 --dry-run

  # 调单章并显示结果（不写文件）
  python debug_prompt.py --config configs/xxx.json --phase write --ch 1

  # 调单章并保存到文件
  python debug_prompt.py --config configs/xxx.json --phase write --ch 1 --save

  # 保存 prompt 到 _debug/（不调 API）
  python debug_prompt.py --config configs/xxx.json --phase write --ch 1 --dump-prompt
"""

import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _path_setup


PHASE_TO_PROMPT = {
    "guides": "plot-guide",
    "write": "write-chapter",
    "trim": "trim-chapter",
    "expand": "expand-chapter",
    "polish": "polish-chapter",
    "style": "style-analyze",
}


def dump_prompt_only(config, phase, ch):
    """复用 run_one 的完整注入逻辑，保存 prompt 到 _debug/，不调 API。"""
    from phases.guides import run_one

    prompt_type = PHASE_TO_PROMPT.get(phase, phase)

    # 临时开启 debug + prompts_only
    config["debug"] = True
    config["prompts_only"] = True

    try:
        result = run_one(config, prompt_type, ch)
        print(f"\n[OK] Prompt 已保存到 _debug/{prompt_type}/")
        print(f"  目录: {Path(config.get('rewrites_dir', '.')) / '_debug' / prompt_type}")
        return result
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def call_and_show(config, phase, ch, save=False):
    """调单章 API，显示结果。"""
    from phases.guides import run_one

    prompt_type = PHASE_TO_PROMPT.get(phase, phase)

    print(f"调用 API: {prompt_type} ch{ch} ...")
    try:
        result = run_one(config, prompt_type, ch)
        if result:
            print(f"\n{'=' * 60}")
            print(f"生成结果 ({len(result)}字)")
            print('=' * 60)
            print(result[:2000])
            if len(result) > 2000:
                print(f"\n... (共{len(result)}字)")

            if save:
                rewrites_dir = config.get("rewrites_dir", "")
                phase_map = {
                    "write": ("chapters", "ch_{:03d}.txt"),
                    "write-chapter": ("chapters", "ch_{:03d}.txt"),
                    "guides": ("guides", "plot_{}.md"),
                    "plot-guide": ("guides", "plot_{}.md"),
                }
                if phase in phase_map:
                    sub_dir, fmt = phase_map[phase]
                    out_path = Path(rewrites_dir) / sub_dir / fmt.format(ch)
                else:
                    out_path = Path(rewrites_dir) / "_debug" / f"{phase}_ch{ch:03d}.txt"

                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(result, encoding="utf-8")
                print(f"\n[SAVED] {out_path}")

            return result
        else:
            print("[FAIL] API 返回空结果")
            return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="快速 debug prompt")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", default="write", help="阶段: guides/write/trim/expand/polish")
    parser.add_argument("--ch", type=int, default=1, help="章节号")
    parser.add_argument("--dry-run", action="store_true", help="只保存 prompt 到 _debug/，不调 API")
    parser.add_argument("--save", action="store_true", help="保存结果到正式目录")
    parser.add_argument("--dump-prompt", action="store_true", help="等同 --dry-run")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("base_dir", str(config_path.resolve().parent))
    config.setdefault("prompts_dir", str(Path(__file__).parent.parent / "prompts"))

    rewrites_dir = config.get("rewrites_dir", "")
    if rewrites_dir and not Path(rewrites_dir).is_absolute():
        config["rewrites_dir"] = str(Path(config["base_dir"]) / rewrites_dir)

    if args.dry_run or args.dump_prompt:
        dump_prompt_only(config, args.phase, args.ch)
    else:
        call_and_show(config, args.phase, args.ch, save=args.save)


if __name__ == "__main__":
    main()
