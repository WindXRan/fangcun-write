"""Phase 3: 写章 + 衔接修复"""

import os
import re
import time
import json
from pathlib import Path

from utils import count_source_chars, batch_run, call_api
from state_manager import atomic_write_text
from prompt_loader import load_prompt, load_system_prompt, tag_output, get_prompt_config_with_overrides


def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 异常章自动重跑 + 衔接修复。
    
    写完后自动跑 continuity-fix 修章间重叠（N-1 并行）。
    """
    from phases.guides import run_one

    chapters_dir = f"{config['rewrites_dir']}/chapters"
    write_cfg = {**config}
    model_label = write_cfg.get("model", "default")

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章 (model={model_label}, ch{start}-{end}, {workers}w)")
    print("=" * 50)

    if state_mgr:
        state_mgr.phase_start("write")

    t0 = time.time()
    run_id = None
    if state_mgr:
        run_id = state_mgr.add_run("write", start, end, model=write_cfg.get("model", "deepseek-v4-flash"))

    ok, fail = batch_run(write_cfg, "write-chapter", start, end, workers, chapters_dir,
                         "ch_{ch:03d}.txt", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one)

    for retry_round in range(1, 3):
        retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            target = count_source_chars(config, ch)
            chars = len(re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text))
            if target > 0:
                deviation = abs(chars - target) / target
                if deviation > 0.3:
                    retry_list.append((ch, f"字数{chars}/{target}"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章字数异常: {[(c, w) for c,w in retry_list]}")
        for ch, _ in retry_list:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.unlink(missing_ok=True)
            if state_mgr:
                state_mgr.chapter_writing(ch)

        ok2, fail2 = batch_run(write_cfg, "write-chapter",
            min(c for c, _ in retry_list), max(c for c, _ in retry_list),
            workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=False,
            state_mgr=state_mgr, run_one_func=run_one)
        ok.update(ok2)
        fail.update(fail2)

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n', '').replace(' ', '').replace('\r', ''))
        for path in ok.values()
    )
    print(f"  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耗时 {time.time()-t0:.0f}s")

    # 衔接修复（N-1 并行，修章间重叠）
    continuity_fixed = phase_continuity_fix(config, start, end, workers)

    if state_mgr:
        if fail:
            state_mgr.phase_failed("write", error=f"{len(fail)}章失败")
        else:
            state_mgr.phase_done("write", extra={"total_chars": total})
        if run_id:
            state_mgr.finish_run(run_id, ok=len(ok), fail=len(fail))

    return ok, fail


def phase_continuity_fix(config, start, end, workers=10):
    """批量修复章间衔接（N-1 并行）。每对相邻章用 LLM 修下章开头 200 字。
    
    返回修复成功的章数。
    """
    if end <= start:
        return 0

    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    base_dir = config.get("base_dir", os.getcwd())
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("  [SKIP] continuity-fix: 无 API_KEY")
        return 0

    from lib.api_client import get_api_url
    api_url = get_api_url(config)
    pc = get_prompt_config_with_overrides("continuity-fix.md", config)
    model = pc.get("model", config.get("model", "deepseek-v4-flash"))
    pairs = [(ch, ch + 1) for ch in range(start, end) if (chapters_dir / f"ch_{ch+1:03d}.txt").exists()]

    if not pairs:
        return 0

    print(f"  衔接修复: {len(pairs)}对章节, {workers}w")

    import concurrent.futures, time

    t0 = time.time()
    fixed = 0

    def fix_one(pair):
        ch, next_ch = pair
        replacements = {
            "N": str(ch), "N_plus1": str(next_ch),
            "N03d": f"{ch:03d}", "N03d_plus1": f"{next_ch:03d}",
            "作者名": config.get("author", ""),
            "源书名": config.get("source_book", ""),
            "新书名": config["book_name"],
        }
        prompt_path = f"{prompts_dir}/continuity-fix.md"
        try:
            user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api",
                                      rewrites_dir=config.get("rewrites_dir"))
            system_prompt = load_system_prompt("system-continuity-fix.md")
            result = call_api(api_key, model, user_prompt,
                              reasoning_effort=pc.get("reasoning_effort", "low"),
                              max_tokens=pc.get("max_tokens", 4096),
                              temperature=pc.get("temperature", 0.8),
                              system_prompt=system_prompt, api_url=api_url)
            out_path = chapters_dir / f"ch_{next_ch:03d}.txt"
            atomic_write_text(out_path, tag_output(result, "continuity-fix.md"))
            return True
        except Exception as e:
            print(f"    [FAIL] ch{next_ch} 衔接修复: {e}")
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(fix_one, pairs))
        fixed = sum(1 for r in results if r)

    elapsed = time.time() - t0
    print(f"  衔接修复: {fixed}/{len(pairs)} 完成 ({elapsed:.0f}s)")
    return fixed
