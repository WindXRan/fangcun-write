"""Phase 3: 写章（含 key chapter 升级 + 风格自检 + 预检跳过）"""

import os
import re
import time
from pathlib import Path

from utils import count_source_chars, batch_run, get_source_text


def _pre_validate(config, start, end):
    """写前预检：已 PASS 的章跳过，只返回需要重写的章列表。"""
    from phases.validate import validate_one
    chapters_dir = Path(config['rewrites_dir']) / 'chapters'
    skip = []
    rewrite = []
    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists() or ch_file.stat().st_size < 500:
            rewrite.append(ch)
            continue
        try:
            passed, report, _ = validate_one(config, ch)
            if passed:
                skip.append(ch)
            else:
                rewrite.append(ch)
        except Exception:
            rewrite.append(ch)
    return skip, rewrite


def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 字数重试 + 风格自检重试。"""
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

    # --- Key chapter 升级：开头章用 Pro ---
    pro_model = write_cfg.get("key_chapter_model")
    key_chapters = set(write_cfg.get("key_chapters", [1, 2]))
    if pro_model:
        for ch in sorted(key_chapters):
            if ch < start or ch > end:
                continue
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if ch_file.exists() and ch_file.stat().st_size >= 500:
                continue
            if state_mgr:
                state_mgr.chapter_writing(ch)
            try:
                result = run_one(write_cfg, "write-chapter", ch, model=pro_model)
                ch_file.parent.mkdir(parents=True, exist_ok=True)
                ch_file.write_text(result, encoding='utf-8')
                if state_mgr:
                    state_mgr.chapter_completed(ch, model=pro_model)
                print(f"  [KEY] ch{ch:03d} → {pro_model}")
            except Exception as e:
                print(f"  [FAIL] key ch{ch}: {e}")

    # --- 预检：跳过已 PASS 的章，只写需要修复的 ---
    skip, rewrite = _pre_validate(write_cfg, start, end)
    if skip:
        print(f"  [SKIP] {len(skip)}章已PASS: {skip}")
    if not rewrite:
        print(f"  所有章已PASS，跳过写章")
        return {}, {}
    print(f"  [WRITE] {len(rewrite)}章需要写: {rewrite}")
    # 只写需要修复的章
    write_cfg["_rewrite_chapters"] = set(rewrite)

    ok, fail = batch_run(write_cfg, "write-chapter", start, end, workers, chapters_dir,
                         "ch_{ch:03d}.txt", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one)

    # prompts_only 跳过字数检查和重试
    if write_cfg.get("prompts_only"):
        total = sum(len(Path(path).read_text(encoding='utf-8')) for path in ok.values()) if ok else 0
        print(f"  完成: 已生成 {len(ok)} 个 prompt | 耗时 {time.time()-t0:.0f}s")
        return ok, fail

    # --- 字数重试 ---
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
            elif chars < 500:
                retry_list.append((ch, f"字数{chars}/0(源文缺失)"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章: {[(c, w) for c,w in retry_list]}")
        t_retry = time.time()
        for ch, reason in retry_list:
            if state_mgr:
                state_mgr.chapter_writing(ch)
            try:
                result = run_one(write_cfg, "write-chapter", ch)
                ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                ch_file.parent.mkdir(parents=True, exist_ok=True)
                ch_file.write_text(result, encoding='utf-8')
                ok[ch] = str(ch_file)
                fail.pop(ch, None)
                if state_mgr:
                    state_mgr.chapter_completed(ch)
            except Exception as e:
                print(f"    [FAIL] retry ch{ch}: {e}")
                fail[ch] = reason
        print(f"  重试轮次 {retry_round} 完成 ({time.time()-t_retry:.0f}s)")

    # --- 风格自检（朱雀防线）---
    if not write_cfg.get("skip_style_check"):
        from lib.text_metrics import count_metrics
        style_retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            metrics = count_metrics(text)
            src_text = get_source_text(config, ch)
            if not src_text:
                continue
            src = count_metrics(src_text)
            issues = []
            if src.get("pronoun_density", 0) > 0:
                ratio = metrics["pronoun_density"] / src["pronoun_density"]
                if ratio > 1.5 or ratio < 0.5:
                    issues.append(f"代词密度{metrics['pronoun_density']}(源文{src['pronoun_density']})")
            if src.get("sent_len_stddev", 0) > 0:
                ratio = metrics["sent_len_stddev"] / src["sent_len_stddev"]
                if ratio > 1.5 or ratio < 0.5:
                    issues.append(f"句长标准差{metrics['sent_len_stddev']}(源文{src['sent_len_stddev']})")
            if issues:
                style_retry_list.append((ch, "风格偏离: " + ", ".join(issues)))

        if style_retry_list:
            print(f"  [STYLE-RETRY] {len(style_retry_list)}章风格偏离")
            t_retry = time.time()
            for ch, reason in style_retry_list:
                if state_mgr:
                    state_mgr.chapter_writing(ch)
                try:
                    result = run_one(write_cfg, "write-chapter", ch, retry_context=reason)
                    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                    ch_file.parent.mkdir(parents=True, exist_ok=True)
                    ch_file.write_text(result, encoding='utf-8')
                    ok[ch] = str(ch_file)
                    fail.pop(ch, None)
                    if state_mgr:
                        state_mgr.chapter_completed(ch)
                    print(f"    [STYLE-FIX] ch{ch:03d}")
                except Exception as e:
                    print(f"    [FAIL] style-retry ch{ch}: {e}")
                    fail[ch] = reason
            print(f"  风格重试完成 ({time.time()-t_retry:.0f}s)")

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n', '').replace(' ', '').replace('\r', ''))
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



