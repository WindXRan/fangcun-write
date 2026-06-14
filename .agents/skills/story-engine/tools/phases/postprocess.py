"""Phase 3.2-3.8: 后处理（后处理、精简、重写、润色、扩写）"""

import os
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import count_source_chars, get_source_title, call_api, print_progress, debug_dump_prompt
from lib.api_client import get_api_url
from prompt_loader import load_prompt_str, validate_prompt_variables, tag_output, get_prompt_config_with_overrides


# ============================================================
# Phase 3.2: Post-Fix（机械后处理——不调LLM）
# ============================================================

def phase_postfix(config, start, end):
    """机械修复：段尾补省略号、去#号、砍超标字数。不调LLM。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.2: 后处理 (ch{start}-{end})")
    print("=" * 50)

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        fixed = 0

        # 1. 去标题 # 号；过滤源文标题；删重复标题行
        if lines and lines[0].startswith('# '):
            lines[0] = lines[0][2:]
            fixed += 1
        src_title = get_source_title(config, ch)
        if src_title and lines and lines[0].strip() == src_title.strip():
            lines[0] = f"第{ch}章"  # 替换为通用标题
            fixed += 1
        # 删除紧跟标题后的重复标题行（如 line 0 和 line 2 都是"第N章"）
        if len(lines) >= 3 and lines[2].startswith('第') and '章' in lines[2][:10]:
            del lines[2]  # 删掉重复标题
            if len(lines) > 2 and lines[2].strip() == '':
                del lines[2]  # 顺便删空行
            fixed += 1

        if fixed > 0:
            ch_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f"  ch{ch:03d}: {fixed}处修复")
        else:
            print(f"  ch{ch:03d}: 无需修复")

    return True


# ============================================================
# Phase 3.5: Post-Trim
# ============================================================

def phase_trim(config, start, end, workers=None):
    """超字数章节自动精简（>20% 偏差触发）。并行执行。"""
    from phases.guides import run_one

    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.5: 字数精简 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    # 先扫描全章，找出需要精简的
    candidates = []
    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        body = '\n'.join(lines[1:]) if lines and lines[0].startswith('第') else text
        chars = len(re.sub(r'\s', '', body))
        target = count_source_chars(config, ch)
        if target > 0 and (chars - target) / target > 0.2:
            candidates.append((ch, chars, target, lines[0] if lines and lines[0].startswith('第') else f"第{ch}章"))

    if not candidates:
        print(f"  所有章节在 ±20% 内，无需精简")
        return 0

    print(f"  {len(candidates)}章需要精简，并行执行...")

    def _trim_one(ch, chars, target, title):
        try:
            result = run_one(config, "trim-chapter", ch)
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.write_text(tag_output(title + '\n\n' + result.strip(), "trim-chapter.md"), encoding='utf-8')
            print(f"  [TRIM] ch{ch:03d}: {chars}→{target}")
            return True
        except Exception as e:
            print(f"  [FAIL] trim ch{ch}: {e}")
            return False

    t0 = time.time()
    trimmed = 0
    with ThreadPoolExecutor(max_workers=min(w, len(candidates))) as ex:
        futures = {ex.submit(_trim_one, ch, chars, target, title): ch for ch, chars, target, title in candidates}
        for f in as_completed(futures):
            if f.result():
                trimmed += 1

    print(f"  [OK] 精简了 {trimmed}/{len(candidates)} 章 ({time.time()-t0:.0f}s)")
    return trimmed


# ============================================================
# Phase 3.6: 整章重写（人设崩塌、节奏失控时使用）
# ============================================================

def phase_rewrite(config, start, end, workers=None):
    """整章重写：保留guide，从头重写正文。并行执行。"""
    from phases.guides import run_one

    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.6: 整章重写 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    todo = []
    for ch in range(start, end + 1):
        if Path(chapters_dir, f"ch_{ch:03d}.txt").exists():
            todo.append(ch)

    if not todo:
        print(f"  无章节可重写")
        return 0

    def _rewrite_one(ch):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        try:
            result = run_one(config, "write-chapter", ch)
            title = f"第{ch}章"
            ch_file.write_text(tag_output(title + '\n\n' + result.strip(), "write-chapter.md"), encoding='utf-8')
            print(f"  [REWRITE] ch{ch:03d}")
            return True
        except Exception as e:
            print(f"  [FAIL] rewrite ch{ch}: {e}")
            return False

    t0 = time.time()
    rewritten = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_rewrite_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                rewritten += 1

    print(f"  [OK] 重写了 {rewritten}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return rewritten


# ============================================================
# Phase 3.7: 润色（只改文笔，不改内容）
# ============================================================

def phase_polish(config, start, end, workers=None):
    """润色：只改文笔（删AI味、加细节、改对话），不改情节。并行执行。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.7: 润色 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")

    # 扫描存在的章节
    todo = []
    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if ch_file.exists():
            todo.append(ch)

    if not todo:
        print(f"  无章节可润色")
        return 0

    prompt_template = load_prompt_str("polish-chapter.md")
    pc = get_prompt_config_with_overrides("polish-chapter.md", config)

    def _polish_one(ch):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        try:
            original = ch_file.read_text(encoding='utf-8')
            orig_chars = len(original.replace('\n', '').replace(' ', ''))

            r = {"content": original, "min_chars": int(orig_chars * 0.9), "max_chars": int(orig_chars * 1.1)}
            validate_prompt_variables("polish-chapter.md", r)
            prompt = prompt_template.format(**r)

            if config.get("debug"):
                debug_dump_prompt(config, "polish", ch, "prompts/polish-chapter.md", "", prompt, "N/A", pc)

            result = call_api(
                api_key, pc.get("model", model), prompt,
                reasoning_effort=pc.get("reasoning_effort", "low"),
                max_tokens=pc.get("max_tokens", 8000),
                temperature=pc.get("temperature", 0.8),
                system_prompt="",
                api_url=api_url
            )

            new_chars = len(result.replace('\n', '').replace(' ', ''))
            if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.15:
                print(f"  [SKIP] ch{ch:03d}: 字数差异过大 ({orig_chars}→{new_chars})")
                return False
            else:
                ch_file.write_text(tag_output(result, "polish-chapter.md"), encoding='utf-8')
                print(f"  [POLISH] ch{ch:03d}: {orig_chars}→{new_chars}字")
                return True
        except Exception as e:
            print(f"  [FAIL] polish ch{ch}: {e}")
            return False

    t0 = time.time()
    polished = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_polish_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                polished += 1

    print(f"  [OK] 润色了 {polished}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return polished


# ============================================================
# Phase 3.8: 扩写（增加内容扩充字数）
# ============================================================

def phase_expand(config, start, end, target_ratio=1.3, workers=None):
    """扩写：增加内容扩充字数，默认扩充30%。并行执行。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    w = workers or config.get("workers", 30)

    print(f"\n{'=' * 50}")
    print(f"Phase 3.8: 扩写 (ch{start}-{end}, 目标+{(target_ratio-1)*100:.0f}%, {w}w)")
    print("=" * 50)

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")

    # 扫描需要扩写的章节
    todo = []
    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        source_chars = count_source_chars(config, ch)
        if source_chars > 0:
            original = ch_file.read_text(encoding='utf-8')
            orig_chars = len(original.replace('\n', '').replace(' ', ''))
            if orig_chars < source_chars * 0.9:
                todo.append(ch)

    if not todo:
        print(f"  所有章节字数已达标，无需扩写")
        return 0

    print(f"  {len(todo)}章需要扩写，并行执行...")

    prompt_template = load_prompt_str("expand-chapter.md")
    pc = get_prompt_config_with_overrides("expand-chapter.md", config)

    def _expand_one(ch):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        try:
            original = ch_file.read_text(encoding='utf-8')
            orig_chars = len(original.replace('\n', '').replace(' ', ''))
            target_chars = int(orig_chars * target_ratio)

            r = {"content": original, "orig_chars": orig_chars, "target_chars": target_chars,
                 "min_chars": int(target_chars * 0.9), "max_chars": int(target_chars * 1.1)}
            validate_prompt_variables("expand-chapter.md", r)
            prompt = prompt_template.format(**r)

            if config.get("debug"):
                debug_dump_prompt(config, "expand", ch, "prompts/expand-chapter.md", "", prompt, "N/A", pc)

            result = call_api(
                api_key, pc.get("model", model), prompt,
                reasoning_effort=pc.get("reasoning_effort", "low"),
                max_tokens=pc.get("max_tokens", 10000),
                temperature=pc.get("temperature", 0.8),
                system_prompt="",
                api_url=api_url
            )

            new_chars = len(result.replace('\n', '').replace(' ', ''))
            if new_chars < orig_chars * 1.1:
                print(f"  [SKIP] ch{ch:03d}: 扩写不足 ({orig_chars}→{new_chars})")
                return False
            else:
                ch_file.write_text(tag_output(result, "expand-chapter.md"), encoding='utf-8')
                print(f"  [EXPAND] ch{ch:03d}: {orig_chars}→{new_chars}字 (+{(new_chars/orig_chars-1)*100:.0f}%)")
                return True
        except Exception as e:
            print(f"  [FAIL] expand ch{ch}: {e}")
            return False

    t0 = time.time()
    expanded = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_expand_one, ch): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                expanded += 1

    print(f"  [OK] 扩写了 {expanded}/{len(todo)} 章 ({time.time()-t0:.0f}s)")
    return expanded
