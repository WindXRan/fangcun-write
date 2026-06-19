"""Phase 3: 写章（含 key chapter 升级 + 风格自检 + 预检跳过）"""

import os
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import count_source_chars, batch_run, get_source_text


# 按失败类型派发修复动作
def _dispatch_fix(config, ch, chapters_dir):
    """根据失效类型选 trim/polish/rewrite。返回 (action_label, fix_func)。"""
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return "missing", None

    text = ch_file.read_text(encoding='utf-8')
    body = re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text)
    chars = len(body)
    target = count_source_chars(config, ch)
    if target > 0:
        deviation = (chars - target) / target
    else:
        deviation = 0.0

    src_text = get_source_text(config, ch)
    src_metrics = None
    our_metrics = None
    if src_text:
        from lib.text_metrics import count_metrics
        src_metrics = count_metrics(src_text)
        our_metrics = count_metrics(text)

    # 字数超标 → trim
    if deviation > 0.3:
        from phases.guides import run_one
        return "trim", lambda: _fix_trim(config, ch, chapters_dir)

    # 字数不足 → expand
    if target > 0 and deviation < -0.2:
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


def _dispatch_fix(config, ch, chapters_dir):
    """根据失效类型选 trim/polish/rewrite。返回 (action_label, fix_func)。"""
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return "missing", None

    text = ch_file.read_text(encoding='utf-8')
    body = re.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text)
    chars = len(body)
    target = count_source_chars(config, ch)
    if target > 0:
        deviation = (chars - target) / target
    else:
        deviation = 0.0

    src_text = get_source_text(config, ch)
    src_metrics = None
    our_metrics = None
    if src_text:
        from lib.text_metrics import count_metrics
        src_metrics = count_metrics(src_text)
        our_metrics = count_metrics(text)

    # 字数超标 >20% → trim（优先级最高，避免 fallback 到 rewrite）
    if deviation > 0.2:
        from phases.guides import run_one
        return "trim", lambda: _fix_trim(config, ch, chapters_dir)

    # 字数不足 <-20% → expand
    if target > 0 and deviation < -0.2:
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


def _fix_trim(config, ch, chapters_dir):
    """字数超标 → trim。"""
    from phases.guides import run_one
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    content = ch_file.read_text(encoding='utf-8')
    result = run_one(config, "trim-chapter", ch, extra_replacements={"内容": content})
    ch_file.write_text(result, encoding='utf-8')


def _fix_expand(config, ch, text, chapters_dir):
    """字数不足 → expand。"""
    from prompt_meta import load_prompt_str, validate_prompt_variables, load_system_prompt, get_system_prompt_name, safe_format
    from lib.api_client import call_llm
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    orig_chars = len(re.sub(r'\s', '', text))
    target_chars = int(orig_chars * 1.3)
    r = {"content": text, "orig_chars": orig_chars, "target_chars": target_chars,
         "min_chars": int(target_chars * 0.9), "max_chars": int(target_chars * 1.1)}
    prompt = load_prompt_str("expand-chapter.md")
    validate_prompt_variables("expand-chapter.md", r)
    prompt = safe_format(prompt, r)
    sp_name = get_system_prompt_name("expand-chapter.md") or "system-generic.md"
    sys_prompt = load_system_prompt(sp_name) or ""
    # 计算 max_tokens（目标字数 × 1.6，防止超时）
    max_tokens = int(target_chars * 1.6) if target_chars > 100 else None
    result = call_llm(config, "expand-chapter", prompt, sys_prompt, ch=ch, max_tokens=max_tokens)
    ch_file.write_text(result, encoding='utf-8')


def _fix_polish(config, ch, text, chapters_dir, issue):
    """AI痕迹/代词/句长 → 润色。"""
    from prompt_meta import load_prompt_str, validate_prompt_variables, load_system_prompt, get_system_prompt_name, safe_format
    from lib.api_client import call_llm
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    orig_chars = len(re.sub(r'\s', '', text))
    r = {"content": text, "min_chars": int(orig_chars * 0.9), "max_chars": int(orig_chars * 1.1)}
    prompt = load_prompt_str("polish-chapter.md")
    validate_prompt_variables("polish-chapter.md", r)
    prompt = safe_format(prompt, r)
    sp_name = get_system_prompt_name("polish-chapter.md") or "system-generic.md"
    base = load_system_prompt(sp_name) or ""
    sys_prompt = f"精修以下章节，特别关注：{issue}。保持字数在 ±10% 内，不要增删情节。\n\n{base}"
    # 计算 max_tokens（目标字数 × 1.6，防止超时）
    max_tokens = int(orig_chars * 1.6) if orig_chars > 100 else None
    result = call_llm(config, "polish-chapter", prompt, sys_prompt, ch=ch, max_tokens=max_tokens)
    ch_file.write_text(result, encoding='utf-8')


def _fix_rewrite(config, ch, chapters_dir):
    """全章重写。"""
    from phases.guides import run_one
    result = run_one(config, "write-chapter", ch)
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
    ch_file.write_text(result, encoding='utf-8')


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
        run_id = state_mgr.add_run("write", start, end, model=write_cfg.get("model", "deepseek-v4-pro"))

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

    # --- 按需修复：字数/风格/内容问题派发 trim/polish/expand/rewrite ---
    for retry_round in range(1, 3):
        retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            action, fix_func = _dispatch_fix(write_cfg, ch, chapters_dir)
            if fix_func:
                retry_list.append((ch, action, fix_func))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章: {[(c, a) for c,a,_ in retry_list]}")
        t_retry = time.time()
        w = write_cfg.get("workers", 10)
        with ThreadPoolExecutor(max_workers=min(w, len(retry_list) or 1)) as ex:
            def _retry_one(ch_action_fix):
                ch, action, fix_func = ch_action_fix
                try:
                    fix_func()
                    return ch, action, None
                except Exception as e:
                    return ch, action, str(e)
            futures = {ex.submit(_retry_one, item): item for item in retry_list}
            for f in as_completed(futures):
                ch, action, err = f.result()
                if err:
                    print(f"    [FAIL] {action} ch{ch:03d}: {err}")
                    fail[ch] = action
                else:
                    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                    ok[ch] = str(ch_file)
                    fail.pop(ch, None)
                    if state_mgr:
                        state_mgr.chapter_completed(ch)
                    print(f"    [{action}] ch{ch:03d}")
        print(f"  重试轮次 {retry_round} 完成 ({time.time()-t_retry:.0f}s)")

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




