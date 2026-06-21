"""Pipeline：写章流程编排。

开书流程已转为skill控制（open-book skill）。
本文件只负责写章流程：guides → write → postfix → compare → review
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

import _path_setup  # noqa: F401
import io
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from state_manager import StateManager
from config_validator import validate_config
from utils import get_chapters_list
from logger import setup_pipeline_log, close_pipeline_log
from phases import (
    phase_guides,
    phase_write, phase_write_agent,
    phase_postfix,
    phase_unified_review_fix,
)
from phases.compare import phase_compare


# ─── 模型解析 ──────────────────────────────────────────────────────

def get_phase_model(config: dict, phase: str) -> str:
    """按阶段解析模型。优先级：model_overrides.{phase} > model。"""
    overrides = config.get("model_overrides", {})
    if phase in overrides:
        return overrides[phase]
    return config.get("model", "mimo-v2.5-pro")


def get_phase_api(config: dict, phase: str) -> tuple:
    """返回 (api_key, api_url, model)。"""
    from lib.api_client import get_api_key, get_api_url
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = get_phase_model(config, phase)
    return api_key, api_url, model


# ─── Phase 映射 ──────────────────────────────────────────────────────

GOAL_MAP = {
    "guides": {"guides"},
    "write": {"guides", "write", "postfix"},
    "review": {"unified_review_fix"},
    "postfix": {"postfix"},
}

# 章级 phase 按此顺序执行
_CHAPTER_PHASE_ORDER = [
    "guides", "write", "compare",
    "unified_check", "unified_fix",
    "postfix",
]


def _expand(phase_str: str) -> set[str]:
    parts = set(phase_str.split(","))
    combined = set()
    for p in parts:
        combined |= GOAL_MAP.get(p, {p})
    return combined


def _post_process(config, goal):
    if "write" not in goal:
        return


def _auto_compare(config, start, end):
    """写章后自动 compare 黄金章节（1-3, 1-10, 1-20）。"""
    # 只 compare 在写章范围内的区间
    checkpoints = [r for r in [(1, 3), (1, 10), (1, 20)] if r[0] >= start and r[1] <= end]
    if not checkpoints:
        return
    for cs, ce in checkpoints:
        try:
            phase_compare(config, cs, ce)
        except Exception as ex:
            print(f"  [WARN] auto-compare ch{cs}-{ce} 失败: {ex}")


def _print_report(t0, config):
    total = time.time() - t0
    p = Path(config.get("rewrites_dir", ""))
    print(f"\n{'=' * 50}\n写章完成！\n{'=' * 50}")
    if p.exists():
        chs = sorted((p / "chapters").glob("ch_*.txt")) if (p / "chapters").exists() else []
        print(f"  chapters/: {len(chs)} 章")
        if chs:
            chars = sum(len(f.read_text("utf-8").replace("\n", "").replace(" ", "")) for f in chs)
            print(f"  总字数: {chars:,}")
    print(f"  耗时: {total:.0f}s")


def _get_execution_mode(config, phase_name: str = "") -> str:
    mode = config.get("execution_mode", "api")
    if isinstance(mode, dict):
        return mode.get(phase_name, mode.get("default", "api"))
    return mode


def _build_handlers(config, state_mgr, config_path=None) -> dict:
    """构建 {phase_name: handler_fn} 映射。handler 签名 (config, start, end)。"""
    h = {}

    def _write_handler(cfg, s, e):
        """写章 + 自动 postfix + 自动 compare（黄金章节）。"""
        phase_write(cfg, s, e)
        phase_postfix(cfg, s, e)
        _auto_compare(cfg, s, e)

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
        g_workers = cfg.get("batch_size", {}).get("guides", min(cfg.get("workers", 10), 10))
        phase_guides(cfg, s, e, workers=g_workers, state_mgr=state_mgr)

    h["guides"] = _guide_handler
    if _get_execution_mode(config, "write") == "agent":
        h["write"] = _write_handler_agent
        print(f"  [MODE] write → agent")
    else:
        h["write"] = _write_handler
    h["postfix"] = phase_postfix
    h["unified_review_fix"] = lambda cfg, s, e: phase_unified_review_fix(
        cfg, cfg.get("_chapter_start", s), cfg.get("_chapter_end", e), state_mgr=state_mgr)
    return h


def _check_required_files(config, goal):
    """检查关键文件是否存在，缺失则报错。"""
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return True
    
    rw = Path(rewrites_dir)
    
    # guides 或 write 需要的文件
    if "guides" in goal or "write" in goal:
        required = [
            ("concept.md", "开书阶段产物"),
            ("characters.md", "角色设定"),
            ("world.md", "世界观设定"),
        ]
        for fname, desc in required:
            fpath = rw / fname
            if not fpath.exists():
                # 也检查 settings/ 子目录
                alt_path = rw / "settings" / fname
                if not alt_path.exists():
                    print(f"  [ERROR] {desc}不存在: {fpath}")
                    print(f"  请先运行开书skill")
                    return False
    
    # write 需要的文件
    if "write" in goal:
        guides_dir = rw / "guides"
        if not guides_dir.exists():
            print(f"  [ERROR] guides目录不存在: {guides_dir}")
            print(f"  请先运行 guides 阶段")
            return False
    
    return True


def _run_phases(handlers, config, goal, start, end):
    """顺序执行所有 phase。返回 (results, errors)。"""
    results = []
    errors = []

    # ── 前置检查 ──
    if not _check_required_files(config, goal):
        return results, ["missing_required_files"]

    def _exec(name, s, e):
        h = handlers.get(name)
        if not h:
            print(f"  [WARN] 无 handler: {name}")
            return False
        print(f"\n--- {name} ch{s}-{e} ---")
        t0 = time.time()
        try:
            h(config, s, e)
            elapsed = time.time() - t0
            print(f"  [{name}] OK ({elapsed:.0f}s)")
            results.append({"phase": name, "start": s, "end": e, "status": "ok", "duration": elapsed})
            return True
        except Exception as ex:
            elapsed = time.time() - t0
            print(f"  [{name}] FAIL: {ex}")
            results.append({"phase": name, "start": s, "end": e, "status": "error", "error": str(ex), "duration": elapsed})
            errors.append(name)
            return False

    # ── 章级 phase ──
    chapter_names = [n for n in _CHAPTER_PHASE_ORDER if n in goal]
    if chapter_names:
        print(f"\n{'=' * 50}")
        print(f"章级阶段 ({len(chapter_names)} phase): {', '.join(chapter_names)}")
        print(f"章节: {start}-{end}")
        print(f"{'=' * 50}")
        for name in chapter_names:
            _exec(name, start, end)

    return results, errors


def main():
    parser = argparse.ArgumentParser(description="写章流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=200)
    parser.add_argument("--phase", default="write")
    parser.add_argument("--mode", choices=["api", "agent", "debug"], help="执行模式：api(默认)/agent/debug")
    parser.add_argument("--include-fanwai", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--health-output")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--auto-rollback", action="store_true")
    parser.add_argument("--debug", action="store_true", help="只输出 prompt 不调 API，保存到 _debug/ 目录")

    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}"); sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("prompts_dir", str(Path(__file__).parent.parent / "prompts"))
    config.setdefault("base_dir", str(config_path.resolve().parent))
    config["workers"] = args.workers
    config["debug"] = args.debug or args.mode == "debug"
    config["prompts_only"] = config["debug"]

    if args.mode:
        if args.mode == "debug":
            config["execution_mode"] = "api"
        else:
            config["execution_mode"] = args.mode

    base_dir = config.get("base_dir", os.getcwd())
    rw = config.get("rewrites_dir", "")
    if rw and not Path(rw).is_absolute():
        config["rewrites_dir"] = str(Path(base_dir) / rw)

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

    # --resume: 断点续传
    if args.phase == "resume":
        if state_mgr:
            resume_phase = state_mgr.get_resume_phase()
            if resume_phase is None:
                print("全部完成，无需续传")
                state_mgr.print_status()
                return
            print(f"断点续传: 从 {resume_phase} 阶段继续")
            args.phase = resume_phase
        else:
            print("未初始化状态管理，无法续传")
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

    book_name = config.get("book_name", "auto")
    if book_name == "auto":
        rw = config.get("rewrites_dir", "")
        if "{新书名}" in rw:
            config["rewrites_dir"] = rw.replace("{新书名}", "_auto_pending")
            print(f"[INFO] book_name=auto，暂用目录: _auto_pending")

    if not any("--end" in a for a in sys.argv):
        initial = config.get("initial_chapters")
        if initial and isinstance(initial, int) and initial > 0:
            args.end = initial
            print(f"[INFO] 使用 initial_chapters={initial} 作为 end")
        else:
            chs = get_chapters_list(config, include_fanwai=args.include_fanwai)
            if chs: args.end = max(chs)

    goal = _expand(args.phase)

    exec_mode = _get_execution_mode(config)
    mode_str = f"mode: {exec_mode}"
    if isinstance(exec_mode, str):
        phase_modes = [f"{p}={_get_execution_mode(config, p)}" for p in goal if _get_execution_mode(config, p) != exec_mode]
        if phase_modes:
            mode_str += f" ({', '.join(phase_modes)})"

    phase_display = {
        "guides": "章纲",
        "write": "写章",
        "postfix": "后处理",
        "unified_review_fix": "统一审改",
    }
    display_names = [phase_display.get(p, p) for p in sorted(goal)]

    setup_pipeline_log(config)

    print(f"{'=' * 50}")
    print(f"{config.get('book_name', 'auto')} | ch{args.start}-{args.end} | workers={args.workers}")
    print(f"目的: {' → '.join(display_names)} | {mode_str}")
    print(f"{'=' * 50}")

    t0 = time.time()
    config["_chapter_start"] = args.start
    config["_chapter_end"] = args.end

    # book_name=auto 时，从 book_info.md 提取真实书名（在 phases 执行前）
    if config.get("book_name") == "auto":
        rewrites_dir = config.get("rewrites_dir", "")
        book_info_path = Path(rewrites_dir) / "settings" / "book_info.md"
        if not book_info_path.exists():
            book_info_path = Path(rewrites_dir) / "book_info.md"
        if book_info_path.exists():
            import re as _re
            content = book_info_path.read_text(encoding="utf-8")
            m = _re.search(r'^\s*(?:\d+\.|[-*])\s*[《](.+?)[》]', content, _re.MULTILINE)
            if m:
                config["book_name"] = m.group(1).strip()
                print(f"[AUTO] book_name: auto → {config['book_name']}")
            else:
                config["book_name"] = Path(rewrites_dir).name
                print(f"[AUTO] book_name: auto → {config['book_name']} (from dir)")
        else:
            config["book_name"] = Path(rewrites_dir).name
            print(f"[AUTO] book_name: auto → {config['book_name']} (from dir)")

    handlers = _build_handlers(config, state_mgr, config_path=args.config)
    results, phase_errors = _run_phases(handlers, config, goal, args.start, args.end)

    _post_process(config, goal)
    _print_report(t0, config)

    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    print(f"  ✓ {ok} done | ✗ {err} failed")

    close_pipeline_log()

    if phase_errors:
        print(f"\n⚠ {len(phase_errors)} 个 phase 失败: {', '.join(phase_errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
