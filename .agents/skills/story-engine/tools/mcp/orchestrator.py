"""DAG 编排器：全局 phase 串行 → 章级 phase 流水线并行 + 自动重试。"""

from __future__ import annotations
import time
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable

from mcp.phase_meta import PHASES, split_by_scope, resolve_order

MAX_RETRIES = 3


@dataclass
class TaskResult:
    phase: str
    chapter: int
    status: str       # ok | skip | error | retry
    error: str = ""
    retries: int = 0
    duration: float = 0.0


class Orchestrator:
    def __init__(self, config: dict, state_mgr=None):
        self.config = config
        self.state_mgr = state_mgr
        self.results: list[TaskResult] = []
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, phase: str, handler: Callable):
        self._handlers[phase] = handler

    def run(self, goal_phases: set[str],
            chapter_start: int = 1, chapter_end: int = 10,
            workers: int = 10) -> list[TaskResult]:
        self.results = []
        global_names, chapter_names = split_by_scope(goal_phases)

        # ── 1. 全局 phase（串行） ──
        if global_names:
            print(f"\n{'=' * 50}\n全局阶段: {', '.join(global_names)}\n{'=' * 50}")
            for name in global_names:
                if self._is_done(name):
                    print(f"  [SKIP] {name} 已完成")
                    continue
                self._execute(name, 0, 0)

        # ── 2. 章级 phase（流水线并行） ──
        if not chapter_names:
            return self.results

        print(f"\n{'=' * 50}")
        print(f"章级阶段 ({len(chapter_names)} phase): {', '.join(chapter_names)}")
        print(f"章节: {chapter_start}-{chapter_end} | workers={workers}")
        print(f"{'=' * 50}")

        chapters = list(range(chapter_start, chapter_end + 1))
        total = len(chapters)

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._process_chapter, ch, chapter_names): ch for ch in chapters}
            done = 0
            for future in concurrent.futures.as_completed(futures):
                ch = futures[future]
                done += 1
                try:
                    ch_results = future.result()
                    self.results.extend(ch_results)
                except Exception as e:
                    self.results.append(TaskResult("pipeline", ch, "error", error=str(e)))
                self._print_progress(done, total)

        return self.results

    def _process_chapter(self, ch: int, chapter_phases: list[str]) -> list[TaskResult]:
        """处理单章的全部章级 phase，按依赖顺序执行。"""
        results = []

        # 解析章级 phase 内部依赖（write 依赖 guides 等）
        ch_set = set(chapter_phases)
        waves = resolve_order(ch_set)

        for wave in waves:
            for phase_name in wave:
                m = PHASES.get(phase_name)
                if not m or m.scope != "chapter":
                    continue
                if self._is_done(phase_name, ch):
                    continue

                # 带重试
                for attempt in range(1, MAX_RETRIES + 1):
                    r = self._execute(phase_name, ch, ch)
                    r.chapter = ch
                    r.retries = attempt - 1
                    if r.status == "ok":
                        results.append(r)
                        break
                    if attempt < MAX_RETRIES:
                        r.status = "retry"
                        r.error = f"retry {attempt}/{MAX_RETRIES}: {r.error}"
                        results.append(r)
                        time.sleep(2)
                    else:
                        results.append(r)
        return results

    def _execute(self, phase: str, start: int, end: int) -> TaskResult:
        handler = self._handlers.get(phase)
        if not handler:
            return TaskResult(phase, start, "error", error=f"no handler")

        t0 = time.time()
        try:
            handler(self.config, start, end)
            elapsed = time.time() - t0
            self._mark_done(phase)
            return TaskResult(phase, start, "ok", duration=elapsed)
        except Exception as e:
            elapsed = time.time() - t0
            return TaskResult(phase, start, "error", error=str(e), duration=elapsed)

    def _print_progress(self, done: int, total: int):
        """进度条。"""
        ok = sum(1 for r in self.results if r.status == "ok")
        err = sum(1 for r in self.results if r.status == "error")
        ret = sum(1 for r in self.results if "retry" in r.status)
        print(f"\r  进度: {done}/{total} 章 | ✓{ok} ✗{err} ↻{ret}", end="")
        if done == total:
            print()

    def _is_done(self, phase: str, chapter: int = 0) -> bool:
        if self.state_mgr is None:
            return False
        if chapter:
            return self.state_mgr.get_chapter_status(chapter) == "done"
        return self.state_mgr.is_phase_done(phase)

    def _mark_done(self, phase: str, chapter: int = 0):
        if self.state_mgr is None:
            return
        if chapter:
            self.state_mgr.chapter_completed(chapter)
        else:
            self.state_mgr.phase_done(phase)

    @property
    def summary(self) -> str:
        lines = []
        ok = sum(1 for r in self.results if r.status == "ok")
        err = sum(1 for r in self.results if r.status == "error")
        ret = sum(1 for r in self.results if "retry" in r.status)
        skip = sum(1 for r in self.results if r.status == "skip")
        lines.append(f"  ✓ {ok} done | ✗ {err} failed | ↻ {ret} retries | - {skip} skipped")
        if err:
            lines.append(f"\n  失败:")
            for r in self.results:
                if r.status == "error":
                    lines.append(f"    ✗ {r.phase} ch{r.chapter}: {r.error}")
        return "\n".join(lines)
