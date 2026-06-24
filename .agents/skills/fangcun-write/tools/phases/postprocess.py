"""Phase 3.2-3.8: 后处理（后处理、精简、重写、润色、扩写）

调用 fangcun-write 实现，保留 fangcun-novel 的并行和状态管理。
"""

import os
import re
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import _path_setup  # noqa: F401
from utils import get_source_title

# 添加 fangcun-write 到 path
# phases/ → tools/ → fangcun-novel/ → skills/ → fangcun-write/tools
_WRITER_ENGINE = Path(__file__).parent.parent.parent.parent / "fangcun-write" / "tools"
sys.path.insert(0, str(_WRITER_ENGINE))


def _get_writer_module():
    """延迟导入 fangcun-write 模块"""
    import importlib
    return importlib.import_module("writer")


# ============================================================
# Phase 3.2: Post-Fix（全靠大模型一次生成正确内容，不做兜底处理）
# ============================================================

def _get_source_chars(config, ch):
    """获取源文章节字数。"""
    try:
        from lib.source_locator import get_source_text
        src = get_source_text(config, ch)
        if src:
            return len(re.sub(r'\s', '', src))
    except Exception:
        pass
    return 0


def phase_postfix(config, start, end):
    """后处理：字数检查+自动trim/expand。"""
    chapters_dir = Path(f"{config['rewrites_dir']}/chapters")

    print(f"\n{'=' * 50}")
    print(f"Phase 3.2: 后处理 (ch{start}-{end})")
    print("=" * 50)

    trim_list, expand_list = [], []

    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        text = ch_file.read_text(encoding='utf-8')
        if len(text.strip()) < 50:
            print(f"  ch{ch:03d}: 内容过短，跳过")
            continue

        chars = len(re.sub(r'\s', '', text))
        src_chars = _get_source_chars(config, ch) or 2000
        deviation = (chars - src_chars) / src_chars * 100

        if deviation > 30:
            trim_list.append(ch)
            print(f"  ch{ch:03d}: {chars}字 超{deviation:+.0f}% → 待trim")
        elif deviation < -30:
            expand_list.append(ch)
            print(f"  ch{ch:03d}: {chars}字 低{deviation:+0.f}% → 待expand")
        else:
            print(f"  ch{ch:03d}: {chars}字 ({deviation:+.0f}%) ✓")

    if trim_list:
        print(f"\n  自动trim {len(trim_list)}章...")
        phase_trim(config, start, end, chapter_list=trim_list)
    if expand_list:
        print(f"\n  自动expand {len(expand_list)}章...")
        phase_expand(config, start, end, chapter_list=expand_list)

    return True


# ============================================================
# Phase 3.5: Post-Trim（调用 fangcun-write）
# ============================================================

def phase_trim(config, start, end, workers=None, chapter_list=None):
    """超字数章节自动精简（>3000字触发）。调用 fangcun-write。"""
    writer = _get_writer_module()
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.5: 字数精简 (ch{start}-{end}, 上限源文×1.3)")
    print("=" * 50)

    candidates = []
    for ch in range(start, end + 1):
        if chapter_list is not None and ch not in chapter_list:
            continue
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        text = ch_file.read_text(encoding='utf-8')
        chars = len(re.sub(r'\s', '', text))
        # 用源文字数上限（1.3x）替代固定3000
        src_chars = _get_source_chars(config, ch) or 2000
        limit = max(src_chars * 1.3, 2600)
        if chars > limit:
            candidates.append((ch, chars))

    if not candidates:
        print(f"  所有章节在 3000 字以内，无需精简")
        return 0

    print(f"  {len(candidates)}章需要精简，并行执行...")

    def _trim_one(ch, chars):
        try:
            fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
            result = writer.trim_chapter(fix_config, ch)
            if result:
                ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                print(f"  [TRIM] ch{ch:03d}: {chars}字")
                return True
        except Exception as e:
            print(f"  [FAIL] trim ch{ch}: {e}")
        return False

    t0 = time.time()
    trimmed = 0
    with ThreadPoolExecutor(max_workers=min(w, len(candidates))) as ex:
        futures = {ex.submit(_trim_one, ch, chars): ch for ch, chars in candidates}
        for f in as_completed(futures):
            if f.result():
                trimmed += 1

    print(f"  [OK] 精简了 {trimmed}/{len(candidates)} 章 ({time.time()-t0:.0f}s)")
    return trimmed


# ============================================================
# Phase 3.6: 整章重写（调用 fangcun-write）
# ============================================================

def phase_rewrite(config, start, end, workers=None, state_mgr=None, chapters=None):
    """整章重写：保留guide，从头重写正文。并行执行。调用 fangcun-write。"""
    writer = _get_writer_module()
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.6: 整章重写 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    if chapters:
        todo = [ch for ch in chapters if Path(chapters_dir, f"ch_{ch:03d}.txt").exists()]
    else:
        todo = [ch for ch in range(start, end + 1) if Path(chapters_dir, f"ch_{ch:03d}.txt").exists()]

    if not todo:
        print(f"  无章节可重写")
        return 0

    def _rewrite_one(ch):
        try:
            if state_mgr:
                state_mgr.chapter_writing(ch)
            fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
            result = writer.rewrite_chapter(fix_config, ch)
            if result:
                ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                if state_mgr:
                    state_mgr.chapter_completed(ch)
                print(f"  [REWRITE] ch{ch:03d}")
                return True
        except Exception as e:
            if state_mgr:
                state_mgr.chapter_failed(ch, error=str(e))
            print(f"  [FAIL] rewrite ch{ch}: {e}")
        return False

    t0 = time.time()
    rewritten = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_rewrite_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                rewritten += 1

    if state_mgr:
        state_mgr.save()
    print(f"  [OK] 重写了 {rewritten}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return rewritten


# ============================================================
# Phase 3.7: 润色（调用 fangcun-write）
# ============================================================

def phase_polish(config, start, end, workers=None, state_mgr=None):
    """润色：只改文笔，不改情节。并行执行。调用 fangcun-write。"""
    writer = _get_writer_module()
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.7: 润色 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    todo = [ch for ch in range(start, end + 1) if Path(chapters_dir, f"ch_{ch:03d}.txt").exists()]

    if not todo:
        print(f"  无章节可润色")
        return 0

    def _polish_one(ch):
        try:
            fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
            result = writer.polish_chapter(fix_config, ch)
            if result:
                ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                if state_mgr:
                    state_mgr.chapter_completed(ch)
                print(f"  [POLISH] ch{ch:03d}")
                return True
        except Exception as e:
            if state_mgr:
                state_mgr.chapter_failed(ch, error=str(e))
            print(f"  [FAIL] polish ch{ch}: {e}")
        return False

    t0 = time.time()
    polished = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_polish_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                polished += 1

    if state_mgr:
        state_mgr.save()
    print(f"  [OK] 润色了 {polished}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return polished


# ============================================================
# Phase 3.8: 扩写（调用 fangcun-write）
# ============================================================

def phase_expand(config, start, end, target_ratio=1.3, workers=None, state_mgr=None, chapter_list=None):
    """扩写：增加内容扩充字数。并行执行。调用 fangcun-write。"""
    writer = _get_writer_module()
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.8: 扩写 (ch{start}-{end}, 目标+{(target_ratio-1)*100:.0f}%, {w}w)")
    print("=" * 50)

    # 扫描需要扩写的章节
    from utils import get_source_text
    from lib.text_metrics import get_body_chars
    todo = []
    for ch in range(start, end + 1):
        if chapter_list is not None and ch not in chapter_list:
            continue
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        # 获取源文字数
        source_text = get_source_text(config, ch)
        source_chars = get_body_chars(source_text) if source_text else 0
        original = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original.replace('\n', '').replace(' ', ''))
        if source_chars > 0:
            if orig_chars < source_chars * 0.9:
                todo.append(ch)
        else:
            # 没有源文字数信息，检查是否过短
            if orig_chars < 1800:
                todo.append(ch)

    if not todo:
        print(f"  所有章节字数已达标，无需扩写")
        return 0

    print(f"  {len(todo)}章需要扩写，并行执行...")

    def _expand_one(ch):
        try:
            fix_config = {**config, "rewrites_dir": str(Path(chapters_dir).parent)}
            result = writer.expand_chapter(fix_config, ch)
            if result:
                ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                if state_mgr:
                    state_mgr.chapter_completed(ch)
                print(f"  [EXPAND] ch{ch:03d}")
                return True
        except Exception as e:
            if state_mgr:
                state_mgr.chapter_failed(ch, error=str(e))
            print(f"  [FAIL] expand ch{ch}: {e}")
        return False

    t0 = time.time()
    expanded = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_expand_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                expanded += 1

    if state_mgr:
        state_mgr.save()
    print(f"  [OK] 扩写了 {expanded}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return expanded
