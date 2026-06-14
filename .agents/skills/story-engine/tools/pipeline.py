"""Pipeline：Orchestrator 驱动，全局串行 + 章级流水线并行。"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

from state_manager import StateManager
from config_validator import validate_config
from utils import get_chapters_list
from phases import (
    phase_prep, phase_open_book,
    phase_guides,
    phase_write, phase_write_agent,
    phase_validate,
    phase_postfix, phase_trim, phase_rewrite, phase_polish, phase_expand,
    phase_compare,
    phase_unified_check, phase_unified_fix, phase_unified_review_fix,
)
from mcp.orchestrator import Orchestrator
from mcp.phase_meta import PHASES


GOAL_MAP = {
    "all": {"prep", "open_book", "extract", "guides", "write", "trim", "validate", "compare"},
    "open-book": {"prep", "open_book", "extract"},
    "write": {"guides", "write", "trim"},
    "unified": {"write", "unified_review_fix"},
}


def _expand(phase_str: str) -> set[str]:
    parts = set(phase_str.split(","))
    combined = set()
    for p in parts:
        combined |= GOAL_MAP.get(p, {p})
    return combined


def _post_process(config, goal):
    if "write" not in goal:
        return
    print(f"\n{'=' * 50}\n导出 TXT...\n{'=' * 50}")
    try:
        from merge_chapters import merge_chapters
        d = config["rewrites_dir"]
        os.makedirs(f"{d}/export", exist_ok=True)
        if merge_chapters(f"{d}/chapters", f"{d}/export/{config['book_name']}.txt",
                          "utf-8", f"{d}/concept.md"):
            print(f"[OK] 已导出: {d}/export/{config['book_name']}.txt")
    except Exception as e:
        print(f"[WARN] 导出失败: {e}")


def _print_report(t0, config):
    total = time.time() - t0
    p = Path(config.get("rewrites_dir", ""))
    print(f"\n{'=' * 50}\n仿写完成！\n{'=' * 50}")
    if p.exists():
        chs = sorted((p / "chapters").glob("ch_*.txt")) if (p / "chapters").exists() else []
        print(f"  chapters/: {len(chs)} 章")
        if chs:
            chars = sum(len(f.read_text("utf-8").replace("\n", "").replace(" ", "")) for f in chs)
            print(f"  总字数: {chars:,}")
    print(f"  耗时: {total:.0f}s")


def _get_execution_mode(config, phase_name: str = "") -> str:
    """获取执行模式：api | agent。

    优先级：phase 级 > global > 默认 "api"
    """
    mode = config.get("execution_mode", "api")
    if isinstance(mode, dict):
        return mode.get(phase_name, mode.get("default", "api"))
    return mode


def _build_orch(config, state_mgr, config_path=None) -> Orchestrator:
    orch = Orchestrator(config, state_mgr)

    def _extract(cfg, s, e):
        import importlib
        bd = importlib.import_module("extract_book_data").extract(cfg)
        if not bd:
            print("  [FAIL] extract_book_data 失败")
            sys.exit(1)
        cv = bd.get("meta", {}).get("character_variables", {})
        print(f"  [OK] book_data.json: {len(cv)} 变量")

    def _write_handler(cfg, s, e):
        phase_write(cfg, s, e, cfg.get("workers", 30))
        phase_postfix(cfg, s, e)

    def _write_handler_agent(cfg, s, e):
        ok, fail = phase_write_agent(cfg, s, e, workers=cfg.get("workers", 10), state_mgr=state_mgr)
        if ok:
            rewrites_dir = cfg.get("rewrites_dir", "")
            manifest_path = Path(rewrites_dir) / "_agent_tasks" / "write_manifest.json"
            cfg_path = config_path or "configs/xxx.json"
            print(f"\n  ⚠ Agent 写章任务已生成: {manifest_path}")
            print(f"  请用 opencode agent 消费任务后，再运行 postfix:")
            print(f"  python pipeline.py --config {cfg_path} --phase postfix")

    def _guide_handler(cfg, s, e):
        phase_guides(cfg, s, e, workers=1, state_mgr=state_mgr)

    orch.register_handler("prep", lambda cfg, s, e: phase_prep(cfg))
    orch.register_handler("open_book", lambda cfg, s, e: phase_open_book(cfg, state_mgr=state_mgr))
    orch.register_handler("extract", _extract)
    orch.register_handler("guides", _guide_handler)
    # 根据 execution_mode 选择 write handler
    if _get_execution_mode(config, "write") == "agent":
        orch.register_handler("write", _write_handler_agent)
        print(f"  [MODE] write → agent")
    else:
        orch.register_handler("write", _write_handler)
    orch.register_handler("validate", phase_validate)
    orch.register_handler("compare", phase_compare)
    orch.register_handler("trim", phase_trim)
    orch.register_handler("rewrite", phase_rewrite)
    orch.register_handler("polish", phase_polish)
    orch.register_handler("expand", phase_expand)
    orch.register_handler("unified_check", phase_unified_check)
    orch.register_handler("unified_fix", phase_unified_fix)
    orch.register_handler("unified_review_fix", phase_unified_review_fix)

    return orch


def main():
    parser = argparse.ArgumentParser(description="改写流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=200)
    parser.add_argument("--phase", default="all")
    parser.add_argument("--include-fanwai", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--health-output")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--auto-rollback", action="store_true")
    parser.add_argument("--debug", action="store_true", help="输出最终发给 API 的完整 prompt 到 _debug/ 目录")

    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}"); sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())
    config["workers"] = args.workers
    config["debug"] = args.debug

    # 相对路径对齐 base_dir，防 CWD 变化导致文件散落
    base_dir = config.get("base_dir", os.getcwd())
    for key in ("rewrites_dir", "prompts_dir"):
        val = config.get(key, "")
        if val and not Path(val).is_absolute():
            config[key] = str(Path(base_dir) / val)

    errors = validate_config(config)
    if errors:
        for e in errors: print(f"  - {e}")
        sys.exit(1)

    rewrites_dir = config.get("rewrites_dir", "")
    state_mgr = StateManager(rewrites_dir) if rewrites_dir else None
    if state_mgr:
        state_mgr.load()
        print(f"[STATE] {state_mgr.summary()}")

    if args.status:
        state_mgr and state_mgr.print_status() or print("未初始化状态管理")
        return

    if args.health_check or "health-check" in args.phase.split(","):
        from health_check import run_health_check
        run_health_check(config, args.health_output)
        return

    if args.diff:
        from metrics_history import print_diff, auto_rollback_if_degraded
        rewrites_dir = config.get("rewrites_dir", "")
        print_diff(rewrites_dir)
        if args.auto_rollback:
            auto_rollback_if_degraded(rewrites_dir)
        return

    if not any("--end" in a for a in sys.argv):
        chs = get_chapters_list(config, include_fanwai=args.include_fanwai)
        if chs: args.end = max(chs)

    goal = _expand(args.phase)

    # 显示执行模式
    exec_mode = _get_execution_mode(config)
    mode_str = f"mode: {exec_mode}"
    if isinstance(exec_mode, str):
        phase_modes = [f"{p}={_get_execution_mode(config, p)}" for p in goal if _get_execution_mode(config, p) != exec_mode]
        if phase_modes:
            mode_str += f" ({', '.join(phase_modes)})"

    print(f"{'=' * 50}")
    print(f"{config['book_name']} | ch{args.start}-{args.end} | workers={args.workers}")
    print(f"目的: {', '.join(sorted(goal))} | {mode_str}")
    print(f"{'=' * 50}")

    t0 = time.time()
    orch = _build_orch(config, state_mgr, config_path=args.config)
    results = orch.run(goal, args.start, args.end, args.workers)

    _post_process(config, goal)
    _print_report(t0, config)
    print(orch.summary)

    errors = [r for r in results if r.status == "error"]
    if errors:
        print(f"\n⚠ {len(errors)} 个失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
