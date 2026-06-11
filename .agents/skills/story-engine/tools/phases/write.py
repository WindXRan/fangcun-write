"""Phase 3: 写章（并行写章 + 异常章自动重跑）"""

import os
import re
import sys
import time
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)

from utils import count_source_chars, batch_run, print_progress
from state_manager import atomic_write_text


def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 异常章自动重跑（字数触发）。"""
    from phases.guides import run_one
    
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章 (flash, ch{start}-{end}, {workers}w)")
    print("=" * 50)

    if state_mgr:
        state_mgr.phase_start("write")

    t0 = time.time()

    # 记录运行
    run_id = None
    if state_mgr:
        run_id = state_mgr.add_run("write", start, end, model="deepseek-v4-flash")

    # 第一轮
    ok, fail = batch_run(flash, "write-chapter", start, end, workers, chapters_dir,
                         "ch_{ch:03d}.txt", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one)

    # 重跑异常章（最多2轮）
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
            elif chars < 900 or chars > 3000:
                retry_list.append((ch, f"字数{chars}"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章异常: {[(c, w) for c,w in retry_list]}")
        for ch, _ in retry_list:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.unlink(missing_ok=True)
            if state_mgr:
                state_mgr.chapter_writing(ch)  # 重置为 writing

        ok2, fail2 = batch_run(flash, "write-chapter",
            min(c for c, _ in retry_list), max(c for c, _ in retry_list),
            workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=False, 
            state_mgr=state_mgr, run_one_func=run_one)
        ok.update(ok2)
        fail.update(fail2)

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n','').replace(' ','').replace('\r',''))
        for path in ok.values()
    )
    print(f"  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耗时 {time.time()-t0:.0f}s")

    if state_mgr:
        if fail:
            state_mgr.phase_failed("write", error=f"{len(fail)}章失败")
        else:
            state_mgr.phase_done("write", extra={"total_chars": total})
        if run_id:
            state_mgr.finish_run(run_id, ok=len(ok), fail=len(fail))

    return ok, fail
