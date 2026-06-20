"""Pipeline：全局 phase 顺序 → 章级 phase 单线程流水线。

优化项（从 fangcun-drama 迁移）：
  - 按阶段配置模型（model_overrides）
  - 断点续传（state.json）
  - 增量保存
  - 输出校验
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
    phase_compare,
    phase_prep, phase_open_book, phase_source_analysis,
    phase_guides,
    phase_write, phase_write_agent,
    phase_postfix, phase_trim, phase_rewrite, phase_polish, phase_expand,
    phase_unified_check, phase_unified_fix, phase_unified_review_fix,
)
import generate_deliverable


# ─── 模型解析（从 fangcun-drama 迁移）──────────────────────────────────────

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


GOAL_MAP = {
    "import": {"prep"},
    "source": {"source_analysis"},
    "open": {"prep", "source_analysis", "open_book", "extract"},
    "write": {"guides", "write", "postfix"},
    "full": {"source_analysis", "open_book", "extract", "guides", "write", "postfix"},  # 全流程
    "review": {"unified_review_fix"},
    "export": {"export"},
    "trim": {"trim"},
    "rewrite": {"rewrite"},
    "polish": {"polish"},
    "expand": {"expand"},
    "deliver": {"deliver"},
}

# 全局 phase 按此顺序执行（一次跑完）
_GLOBAL_PHASE_ORDER = [
    "prep", "source_analysis", "open_book", "extract",
    "unified_review_fix",
    "deliver",
    "export",
]

# 章级 phase 按此顺序执行（每章顺序跑）
# 注意：trim/expand/polish 不自动运行（质量不稳定），需手动 --phase trim 等
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
    if "deliver" in goal:
        return
    if "write" not in goal and "export" not in goal:
        return
    print(f"\n{'=' * 50}\n导出 TXT...\n{'=' * 50}")
    try:
        from merge_chapters import merge_chapters
        d = config["rewrites_dir"]
        book_name = config.get("book_name", "未命名")
        os.makedirs(f"{d}/export", exist_ok=True)
        if merge_chapters(f"{d}/chapters", f"{d}/export/{book_name}.txt",
                          "utf-8", f"{d}/concept.md"):
            print(f"[OK] 已导出: {d}/export/{book_name}.txt")
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
    mode = config.get("execution_mode", "api")
    if isinstance(mode, dict):
        return mode.get(phase_name, mode.get("default", "api"))
    return mode


def _build_handlers(config, state_mgr, config_path=None) -> dict:
    """构建 {phase_name: handler_fn} 映射。handler 签名 (config, start, end)。"""
    h = {}

    def _import_novel(cfg, s, e):
        """导入小说。"""
        from story_import import import_novel
        source_book = cfg.get("source_book", "")
        author = cfg.get("author", "")
        base_dir = cfg.get("base_dir", os.getcwd())
        
        # 查找源文件
        candidates = [
            f"{base_dir}/projects/{author}/{source_book}/{source_book}.txt",
            f"{base_dir}/projects/{author}/{source_book}/original.txt",
        ]
        
        txt_path = None
        for path in candidates:
            if os.path.exists(path):
                txt_path = path
                break
        
        if not txt_path:
            print(f"  [ERROR] 未找到源文件: {candidates}")
            return
        
        output_dir = f"{base_dir}/projects/{author}/{source_book}/_cache"
        import_novel(txt_path, output_dir)

    def _extract(cfg, s, e):
        if cfg.get("prompts_only"):
            print("  [SKIP] extract — prompts_only 模式跳过")
            return
        import importlib
        bd = importlib.import_module("extract_book_data").extract(cfg)
        if not bd:
            print("  [FAIL] extract_book_data 失败")
            sys.exit(1)
        cv = bd.get("meta", {}).get("character_variables", {})
        print(f"  [OK] book_data.json: {len(cv)} 变量")

    def _write_handler(cfg, s, e):
        """写章 + 自动 validate→智能修复 循环。"""
        phase_write(cfg, s, e, cfg.get("workers", 30))
        phase_postfix(cfg, s, e)

    def _write_handler_agent(cfg, s, e):
        ok, fail = phase_write_agent(cfg, s, e, workers=cfg.get("workers", 10), state_mgr=state_mgr)
        if ok:
            rewrites_dir = cfg.get("rewrites_dir", "")
            manifest_path = Path(rewrites_dir) / "_agent_tasks" / "write_manifest.json"
            cfg_path = config_path or "configs/xxx.json"
            print(f"\n  \u26a0 Agent 写章任务已生成: {manifest_path}")
            print(f"  请用 opencode agent 消费任务后，再运行 postfix:")
            print(f"  python pipeline.py --config {cfg_path} --phase postfix")

    def _guide_handler(cfg, s, e):
        g_workers = cfg.get("batch_size", {}).get("guides", min(cfg.get("workers", 10), 10))
        phase_guides(cfg, s, e, workers=g_workers, state_mgr=state_mgr)

    h["prep"] = lambda cfg, s, e: phase_prep(cfg)
    h["import"] = _import_novel
    h["source_analysis"] = lambda cfg, s, e: phase_source_analysis(cfg, state_mgr=state_mgr)
    h["open_book"] = lambda cfg, s, e: phase_open_book(cfg, state_mgr=state_mgr)
    h["extract"] = _extract
    h["guides"] = _guide_handler
    if _get_execution_mode(config, "write") == "agent":
        h["write"] = _write_handler_agent
        print(f"  [MODE] write \u2192 agent")
    else:
        h["write"] = _write_handler
    h["trim"] = phase_trim
    h["rewrite"] = phase_rewrite
    h["polish"] = phase_polish
    h["expand"] = phase_expand
    h["postfix"] = phase_postfix
    h["compare"] = lambda cfg, s, e: phase_compare(cfg, s, e)
    h["unified_check"] = phase_unified_check
    h["unified_fix"] = phase_unified_fix
    h["unified_review_fix"] = lambda cfg, s, e: phase_unified_review_fix(
        cfg, cfg.get("_chapter_start", s), cfg.get("_chapter_end", e), state_mgr=state_mgr)
    h["export"] = lambda cfg, s, e: _export_novel(cfg)
    h["deliver"] = lambda cfg, s, e: generate_deliverable.phase_deliver(cfg, s, e, state_mgr=state_mgr)

    return h


def _export_novel(config):
    """导出小说为完整 txt 文件。"""
    from story_export import export_novel
    rewrites_dir = config.get("rewrites_dir", "")
    book_name = config.get("book_name", "未命名")
    output_file = f"{rewrites_dir}/export/{book_name}.txt"
    export_novel(rewrites_dir, output_file)


def _check_plot_confirmation(config):
    """检查 plot 确认点：open_book 后、guides 前，让用户确认设定。"""
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return True
    
    # 检查是否已确认过
    confirm_file = Path(rewrites_dir) / ".plot_confirmed"
    if confirm_file.exists():
        return True
    
    # 检查关键文件是否存在
    concept_path = Path(rewrites_dir) / "concept.md"
    characters_path = Path(rewrites_dir) / "settings" / "characters.md"
    plot_path = Path(rewrites_dir) / "settings" / "plot.md"
    
    if not concept_path.exists():
        print(f"  [WARN] concept.md 不存在，跳过确认")
        return True
    
    # 输出确认信息
    print(f"\n{'=' * 60}")
    print(f"[PLOT] 确认点 — 请检查以下文件")
    print(f"{'=' * 60}")
    
    # 显示 concept.md 摘要
    try:
        concept_content = concept_path.read_text(encoding="utf-8")
        # 提取核心信息
        lines = concept_content.split('\n')
        print(f"\n[concept.md] 摘要:")
        for line in lines[:30]:  # 只显示前30行
            if line.strip():
                print(f"  {line}")
        if len(lines) > 30:
            print(f"  ... (共 {len(lines)} 行)")
    except Exception as e:
        print(f"  [WARN] 读取 concept.md 失败: {e}")
    
    # 显示 characters.md 中的角色列表
    if characters_path.exists():
        try:
            chars_content = characters_path.read_text(encoding="utf-8")
            import re
            # 提取角色名
            char_names = re.findall(r'^###?\s*(.+)$', chars_content, re.MULTILINE)
            char_names = [n.strip() for n in char_names if n.strip() and not n.startswith('#')]
            if char_names:
                print(f"\n角色列表:")
                for name in char_names[:15]:  # 只显示前15个
                    print(f"  • {name}")
                if len(char_names) > 15:
                    print(f"  ... (共 {len(char_names)} 个角色)")
        except Exception as e:
            print(f"  [WARN] 读取 characters.md 失败: {e}")
    
    # 显示 plot.md 中的章节规划
    if plot_path.exists():
        try:
            plot_content = plot_path.read_text(encoding="utf-8")
            import re
            # 提取前10章锚点
            anchor_match = re.search(r'前10章.*?(?:\n\|.*?\n){1,10}', plot_content, re.DOTALL)
            if anchor_match:
                print(f"\n前10章规划:")
                print(anchor_match.group(0)[:500])
        except Exception as e:
            print(f"  [WARN] 读取 plot.md 失败: {e}")
    
    print(f"\n{'=' * 60}")
    print(f"[提示] 请确认以上设定是否正确！")
    print(f"  确认后将开始生成章纲和正文。")
    print(f"{'=' * 60}")
    
    # 如果配置了 skip_confirm，自动确认
    if config.get("skip_confirm"):
        print(f"  [AUTO] skip_confirm=True，自动确认")
        confirm_file.write_text("confirmed", encoding="utf-8")
        return True
    
    # 等待用户确认
    while True:
        try:
            response = input("\n是否继续？(y=确认/n=取消/q=退出): ").strip().lower()
            if response in ('y', 'yes', '是', '确认'):
                confirm_file.write_text("confirmed", encoding="utf-8")
                print(f"  [OK] 已确认，继续执行")
                return True
            elif response in ('n', 'no', '否', '取消'):
                print(f"  [STOP] 用户取消，请修改设定后重新运行")
                return False
            elif response in ('q', 'quit', '退出'):
                print(f"  [EXIT] 用户退出")
                sys.exit(0)
            else:
                print(f"  请输入 y/n/q")
        except KeyboardInterrupt:
            print(f"\n  [EXIT] 用户中断")
            sys.exit(0)


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
                    print(f"  请先运行开书阶段: --phase open")
                    return False
    
    # write 需要的文件
    if "write" in goal:
        guides_dir = rw / "guides"
        if not guides_dir.exists():
            print(f"  [ERROR] guides目录不存在: {guides_dir}")
            print(f"  请先运行Guide阶段: --phase guides")
            return False
    
    return True


def _run_phases(handlers, config, goal, start, end):
    """顺序执行所有 phase，先全局后章级。返回 (results, errors)。"""
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

    # ── 全局 phase ──
    global_names = [n for n in _GLOBAL_PHASE_ORDER if n in goal]
    if global_names:
        print(f"\n{'=' * 50}\n全局阶段: {', '.join(global_names)}\n{'=' * 50}")
        for name in global_names:
            _exec(name, start, end)

    # ── Plot 确认点 ──（在章级 phase 之前，让用户确认设定）
    if "guides" in goal or "write" in goal:
        if not _check_plot_confirmation(config):
            print(f"\n[STOP] 用户未确认 plot，停止执行")
            return results, ["plot_not_confirmed"]

    # ── 章级 phase ──（每个 phase 并行跑所有章，不是每章串行跑所有 phase）
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
    parser = argparse.ArgumentParser(description="改写流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=200)
    parser.add_argument("--phase", default="all")
    parser.add_argument("--mode", choices=["api", "agent", "debug"], help="执行模式：api(默认)/agent/debug")
    parser.add_argument("--include-fanwai", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--health-output")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--auto-rollback", action="store_true")
    parser.add_argument("--debug", action="store_true", help="只输出 prompt 不调 API，保存到 _debug/ 目录")
    parser.add_argument("--skip-confirm", action="store_true", help="跳过开书阶段的用户确认（批量模式）")

    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}"); sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("prompts_dir", str(Path(__file__).parent.parent / "prompts"))
    # 默认 base_dir 为配置文件所在目录（而非 cwd），确保换机器后路径依然正确
    config.setdefault("base_dir", str(config_path.resolve().parent))
    config["workers"] = args.workers
    config["debug"] = args.debug or args.mode == "debug"
    config["prompts_only"] = config["debug"]
    config["skip_confirm"] = args.skip_confirm

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

    # --resume: 断点续传（从 fangcun-drama 迁移）
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
        "import": "导入", "open": "开书", "write": "写章", "full": "全流程",
        "review": "审改", "export": "导出",
        "prep": "导入", "open_book": "开书", "extract": "提取",
        "guides": "指南", "write-only": "写章", "trim": "精简",
        "validate": "验证", "compare": "对比+审核+改动", "postfix": "后处理",
        "rewrite": "重写", "polish": "润色", "expand": "扩写",
        "unified_check": "统一审查", "unified_fix": "统一修复",
        "unified_review_fix": "统一审改",
        "deliver": "交付物生成",
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

    handlers = _build_handlers(config, state_mgr, config_path=args.config)
    results, phase_errors = _run_phases(handlers, config, goal, args.start, args.end)

    if config.get("book_name") == "auto":
        rewrites_dir = config.get("rewrites_dir", "")
        book_info_path = Path(rewrites_dir) / "settings" / "book_info.md"
        if book_info_path.exists():
            import re
            content = book_info_path.read_text(encoding="utf-8")
            m = re.search(r'^\s*(?:\d+\.|[-*])\s*[《](.+?)[》]', content, re.MULTILINE)
            if m:
                actual_name = m.group(1).strip()
                config["book_name"] = actual_name
                print(f"[AUTO] 从 book_info.md 提取书名: {actual_name}")
                old_path = Path(rewrites_dir)
                new_path = old_path.parent / actual_name
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    config["rewrites_dir"] = str(new_path)
                    print(f"[OK] 目录重命名: {old_path} \u2192 {new_path}")

    _post_process(config, goal)
    _print_report(t0, config)

    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    print(f"  \u2713 {ok} done | \u2717 {err} failed")

    close_pipeline_log()

    if phase_errors:
        print(f"\n\u26a0 {len(phase_errors)} 个 phase 失败: {', '.join(phase_errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
