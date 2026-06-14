"""Phase 元数据：依赖/产出/并行属性/作用域。"""

from __future__ import annotations
from typing import Literal


class PhaseMeta:
    def __init__(self, name: str, description: str,
                 depends_on: list[str],
                 produces: list[str],
                 scope: Literal["global", "chapter"],
                 parallel: bool,
                 batchable: bool):
        self.name = name
        self.description = description
        self.depends_on = depends_on
        self.produces = produces
        self.scope = scope          # "global" 全局跑一次, "chapter" 每章独立
        self.parallel = parallel
        self.batchable = batchable


PHASES: dict[str, PhaseMeta] = {}

def register(m: PhaseMeta):
    PHASES[m.name] = m
    return m

# ── 全局 phase（串行，跑一次） ──
register(PhaseMeta("prep", "项目准备：创建目录",
                   depends_on=[], produces=["dirs"],
                   scope="global", parallel=False, batchable=False))
register(PhaseMeta("open_book", "开书：concept.md",
                   depends_on=["prep"], produces=["concept.md"],
                   scope="global", parallel=False, batchable=False))
register(PhaseMeta("extract", "提取 book_data.json",
                   depends_on=["prep", "open_book"], produces=["book_data.json"],
                   scope="global", parallel=False, batchable=False))

# ── 章级 phase（每章独立，可流水线并行） ──
register(PhaseMeta("guides", "plot guide 生成",
                   depends_on=["open_book", "extract"], produces=["plot_N.md"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("write", "写章",
                   depends_on=["guides"], produces=["ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("validate", "验证章节",
                   depends_on=["write"], produces=["validation_report"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("compare", "对比源文",
                   depends_on=["write"], produces=["compare_report"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("trim", "精简超字数章",
                   depends_on=["write"], produces=["trimmed_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("rewrite", "重写不达标章",
                   depends_on=["validate"], produces=["rewritten_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("polish", "润色语言",
                   depends_on=["write"], produces=["polished_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("expand", "扩展不足章",
                   depends_on=["write"], produces=["expanded_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("unified_check", "统一审查",
                   depends_on=["write"], produces=["unified_report"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("unified_fix", "统一修复",
                   depends_on=["unified_check"], produces=["fixed_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))
register(PhaseMeta("unified_review_fix", "统一审+修一轮",
                   depends_on=["write"], produces=["reviewed_ch_N.txt"],
                   scope="chapter", parallel=True, batchable=True))


def resolve_order(goal_phases: set[str]) -> list[list[str]]:
    """拓扑排序，返回执行波次。依赖链自动补齐。"""
    included = set(goal_phases)
    added = set(included)
    queue = list(included)
    while queue:
        name = queue.pop(0)
        m = PHASES.get(name)
        if m:
            for dep in m.depends_on:
                if dep not in added:
                    added.add(dep)
                    queue.append(dep)

    in_degree = {n: 0 for n in added}
    for n in added:
        m = PHASES.get(n)
        if m:
            for dep in m.depends_on:
                if dep in added:
                    in_degree[n] = in_degree.get(n, 0) + 1

    waves = []
    remaining = set(added)
    while remaining:
        wave = [n for n in remaining if in_degree.get(n, 0) == 0]
        if not wave:
            raise ValueError(f"依赖循环: {remaining}")
        waves.append(wave)
        for n in wave:
            remaining.discard(n)
            for succ in list(remaining):
                sm = PHASES.get(succ)
                if sm and n in sm.depends_on:
                    in_degree[succ] -= 1
    return waves


def split_by_scope(goal_phases: set[str]):
    """按作用域分离全局 phase 和章级 phase。"""
    global_phases = []
    chapter_phases = []
    for p in resolve_order(goal_phases):
        for name in p:
            m = PHASES.get(name)
            if m and m.scope == "global":
                global_phases.append(name)
            else:
                chapter_phases.append(name)
    return global_phases, chapter_phases
