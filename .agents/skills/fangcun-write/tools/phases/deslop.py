"""Phase: 去AI味——并行 API 调 LLM 逐章改写。"""
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import _path_setup  # noqa: F401
from lib.api_client import call_llm


def phase_deslop(config, start=1, end=10, state_mgr=None):
    """逐章去AI味。读 chapters/ch_{N}.txt → LLM改写 → 写回。"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    if not chapters_dir.exists():
        print("  [SKIP] chapters/ 不存在")
        return True

    chapters = sorted([f for f in chapters_dir.glob("ch_*.txt")
                       if start <= int(f.stem.split("_")[1]) <= end],
                      key=lambda f: int(f.stem.split("_")[1]))
    if not chapters:
        print("  [SKIP] 无章节")
        return True

    prompts_dir = str(Path(__file__).resolve().parent.parent.parent / "prompts")
    base_dir = config.get("base_dir", ".")
    workers = config.get("workers", 200)

    print(f"  去AI味 | {len(chapters)}章 | 并行: {workers}")
    t0 = time.time()

    def deslop_one(ch_file):
        text = ch_file.read_text(encoding="utf-8")
        before = len(text)

        from prompt_loader import load_prompt
        user_prompt = load_prompt(
            f"{prompts_dir}/deslop.md", base_dir,
            {"chapter_text": text}, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )
        try:
            result = call_llm(config, "deslop", user_prompt)
            after = len(result)
            ch_file.write_text(result, encoding="utf-8")
            return ch_file.name, "ok", before, after
        except Exception as e:
            return ch_file.name, str(e), before, before

    results = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(chapters))) as executor:
        futures = {executor.submit(deslop_one, f): f for f in chapters}
        for future in as_completed(futures):
            name, status, before, after = future.result()
            delta = after - before
            done = len(results) + 1
            results[name] = status
            if status == "ok":
                print(f"    [{done}/{len(chapters)}] V {name} ({before}→{after} {delta:+d})")
            else:
                print(f"    [{done}/{len(chapters)}] X {name} ({status})")

    elapsed = time.time() - t0
    ok = sum(1 for v in results.values() if v == "ok")
    print(f"  完成 | {ok}/{len(chapters)} | {elapsed:.0f}s")
    return ok == len(chapters)
