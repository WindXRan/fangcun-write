"""Phase 3: 写章（含 key chapter 升级 + 风格自检 + 预检跳过）"""

import os
import re
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import count_source_chars, batch_run, get_source_text

# 添加 fangcun-write 到 path
_WRITER_ENGINE = Path(__file__).parent.parent.parent.parent / "fangcun-write" / "tools"
sys.path.insert(0, str(_WRITER_ENGINE))


def _get_writer_module():
    """延迟导入 fangcun-write 模块"""
    import importlib
    return importlib.import_module("writer")


def _fix_trim(config, ch, chapters_dir):
    """字数超标 → trim。调用 fangcun-write（仿写模式）。"""
    writer = _get_writer_module()
    fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
    result = writer.trim_chapter(fix_config, ch, mode="imitation")
    if result:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')


def _fix_expand(config, ch, text, chapters_dir):
    """字数不足 → expand。调用 fangcun-write（仿写模式）。"""
    writer = _get_writer_module()
    fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
    result = writer.expand_chapter(fix_config, ch, mode="imitation")
    if result:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')


def _fix_polish(config, ch, text, chapters_dir, issue=""):
    """润色修复。调用 fangcun-write（仿写模式）。"""
    writer = _get_writer_module()
    fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
    result = writer.polish_chapter(fix_config, ch, mode="imitation")
    if result:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')


def _fix_rewrite(config, ch, chapters_dir):
    """全章重写。调用 fangcun-write（仿写模式）。"""
    writer = _get_writer_module()
    fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
    result = writer.rewrite_chapter(fix_config, ch, mode="imitation")
    if result:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')


# 按失败类型派发修复动作
def _dispatch_fix(config, ch, chapters_dir):
    """根据失效类型选 trim/polish/rewrite。返回 (action_label, fix_func)。"""
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return "missing", None

    text = ch_file.read_text(encoding='utf-8')
    body = re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text)
    chars = len(body)

    src_text = get_source_text(config, ch)
    src_metrics = None
    our_metrics = None
    if src_text:
        from lib.text_metrics import count_metrics
        src_metrics = count_metrics(src_text)
        our_metrics = count_metrics(text)

    # 字数超标 → trim
    if chars > 3000:
        return "trim", lambda: _fix_trim(config, ch, chapters_dir)

    # 字数不足 → expand
    if chars < 2000:
        return "expand", lambda: _fix_expand(config, ch, text, chapters_dir)

    # AI 路标词超标 → polish
    if src_metrics and our_metrics:
        limit = max(src_metrics["ai_markers"] + 1, 1)
        if our_metrics["ai_markers"] > limit:
            return "polish(ai)", lambda: _fix_polish(config, ch, text, chapters_dir, "AI路标词过多")

        # 代词密度/句长偏离 → polish with style
        if src_metrics.get("pronoun_density", 0) > 0:
            ratio = our_metrics["pronoun_density"] / max(src_metrics["pronoun_density"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                return "polish(pronoun)", lambda: _fix_polish(config, ch, text, chapters_dir, "代词密度偏离源文")

        if src_metrics.get("sent_len_stddev", 0) > 0:
            ratio = our_metrics["sent_len_stddev"] / max(src_metrics["sent_len_stddev"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                return "polish(style)", lambda: _fix_polish(config, ch, text, chapters_dir, "句长节奏偏离源文")

    # fallback: polish（除非彻底没救，不走 rewrite）
    return "polish(style)", lambda: _fix_polish(config, ch, text, chapters_dir, "整体风格需润色")


def _auto_polish(config, ch, chapters_dir):
    """自动润色：对比源文修正风格。调用 fangcun-write。"""
    writer = _get_writer_module()
    fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
    result = writer.polish_chapter(fix_config, ch)
    if result:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')
        print(f"    [OK] ch{ch:03d} 润色完成")
        return True
    return False


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
    """并行写章 + 字数重试 + 风格自检重试。调用 fangcun-write。"""
    writer = _get_writer_module()

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
        run_id = state_mgr.add_run("write", start, end, model=write_cfg.get("model", "mimo-v2.5-pro"))

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
                key_config = {**write_cfg, "model": pro_model, "rewrites_dir": str(Path(chapters_dir).parent)}
                result = writer.write_chapter(key_config, ch, auto_fix=True)
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

    # --- 并行写章（调用 fangcun-write）---
    ok = {}
    fail = {}
    
    def _write_one(ch):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        try:
            write_config = {**write_cfg, "rewrites_dir": str(Path(chapters_dir).parent)}
            result = writer.write_chapter(write_config, ch, auto_fix=True)
            ch_file.parent.mkdir(parents=True, exist_ok=True)
            ch_file.write_text(result, encoding='utf-8')
            if state_mgr:
                state_mgr.chapter_completed(ch)
            return ch, True, None
        except Exception as e:
            return ch, False, str(e)

    with ThreadPoolExecutor(max_workers=min(workers, len(rewrite))) as ex:
        futures = {ex.submit(_write_one, ch): ch for ch in rewrite}
        for future in as_completed(futures):
            ch, success, error = future.result()
            if success:
                ok[ch] = str(Path(chapters_dir) / f"ch_{ch:03d}.txt")
                print(f"  [OK] ch{ch:03d}")
            else:
                fail[ch] = error
                print(f"  [FAIL] ch{ch:03d}: {error}")

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




