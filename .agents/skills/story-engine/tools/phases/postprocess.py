"""Phase 3.2-3.8: 后处理（后处理、精简、重写、润色、扩写）"""

import os
import re
import time
from pathlib import Path

from utils import count_source_chars, get_source_title, call_api, print_progress
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

def phase_trim(config, start, end):
    """超字数章节自动精简（>20% 偏差触发）。"""
    from phases.guides import run_one
    
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.5: 字数精简 (ch{start}-{end})")
    print("=" * 50)

    trimmed = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        body = '\n'.join(lines[1:]) if lines and lines[0].startswith('第') else text
        chars = len(re.sub(r'\s', '', body))
        target = count_source_chars(config, ch)

        if target == 0:
            done_chapters += 1
            continue

        over = (chars - target) / target
        if over <= 0.2:
            done_chapters += 1
            continue  # 在 ±20% 内，跳过

        print(f"  [TRIM] ch{ch:03d}: {chars}->{target} ({over:+.0%})")
        try:
            result = run_one(config, "trim-chapter", ch)
            # 保留原标题
            title = lines[0] if lines and lines[0].startswith('第') else f"第{ch}章"
            ch_file.write_text(tag_output(title + '\n\n' + result.strip(), "trim-chapter.md"), encoding='utf-8')
            trimmed += 1
        except Exception as e:
            print(f"  [FAIL] trim ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        print_progress(done_chapters, total_chapters, t_start)

    if trimmed:
        print(f"\n[OK] 精简了 {trimmed} 章")
    else:
        print(f"\n所有章节在 ±20% 内，无需精简")
    return trimmed


# ============================================================
# Phase 3.6: 整章重写（人设崩塌、节奏失控时使用）
# ============================================================

def phase_rewrite(config, start, end, workers=5):
    """整章重写：保留guide，从头重写正文。"""
    from phases.guides import run_one
    
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.6: 整章重写 (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    rewritten = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        print(f"  [REWRITE] ch{ch:03d}")
        try:
            # 删除旧文件，重新生成
            ch_file.unlink(missing_ok=True)
            result = run_one(config, "write-chapter", ch)
            
            # 生成标题
            title = f"第{ch}章"
            ch_file.write_text(tag_output(title + '\n\n' + result.strip(), "write-chapter.md"), encoding='utf-8')
            rewritten += 1
        except Exception as e:
            print(f"  [FAIL] rewrite ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        print_progress(done_chapters, total_chapters, t_start)

    if rewritten:
        print(f"\n[OK] 重写了 {rewritten} 章")
    return rewritten


# ============================================================
# Phase 3.7: 润色（只改文笔，不改内容）
# ============================================================

def phase_polish(config, start, end, workers=5):
    """润色：只改文笔（删AI味、加细节、改对话），不改情节。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.7: 润色 (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    polished = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        original = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original.replace('\n', '').replace(' ', ''))

        prompt_template = load_prompt_str("polish-chapter.md")
        r = {"content": original, "min_chars": int(orig_chars * 0.9), "max_chars": int(orig_chars * 1.1)}
        validate_prompt_variables("polish-chapter.md", r)
        prompt = prompt_template.format(**r)

        pc = get_prompt_config_with_overrides("polish-chapter.md", config)

        try:
            result = call_api(
                api_key, pc.get("model", model), prompt,
                reasoning_effort=pc.get("reasoning_effort", "low"),
                max_tokens=pc.get("max_tokens", 8000),
                temperature=pc.get("temperature", 0.8),
                system_prompt="",
                api_url=api_url
            )
            
            new_chars = len(result.replace('\n', '').replace(' ', ''))
            
            # 检查字数差异
            if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.15:
                print(f"  [SKIP] ch{ch:03d}: 字数差异过大 ({orig_chars}→{new_chars})")
            else:
                ch_file.write_text(tag_output(result, "polish-chapter.md"), encoding='utf-8')
                polished += 1
                print(f"  [POLISH] ch{ch:03d}: {orig_chars}→{new_chars}字")
        except Exception as e:
            print(f"  [FAIL] polish ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        print_progress(done_chapters, total_chapters, t_start)

    if polished:
        print(f"\n[OK] 润色了 {polished} 章")
    return polished


# ============================================================
# Phase 3.8: 扩写（增加内容扩充字数）
# ============================================================

def phase_expand(config, start, end, target_ratio=1.3, workers=5):
    """扩写：增加内容扩充字数，默认扩充30%。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.8: 扩写 (ch{start}-{end}, 目标+{(target_ratio-1)*100:.0f}%, {workers}w)")
    print("=" * 50)

    expanded = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        original = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original.replace('\n', '').replace(' ', ''))
        target_chars = int(orig_chars * target_ratio)

        # 检查是否需要扩写
        source_chars = count_source_chars(config, ch)
        if source_chars > 0 and orig_chars >= source_chars * 0.9:
            done_chapters += 1
            continue  # 字数已够，跳过

        prompt_template = load_prompt_str("expand-chapter.md")
        r = {"content": original, "orig_chars": orig_chars, "target_chars": target_chars,
             "min_chars": int(target_chars * 0.9), "max_chars": int(target_chars * 1.1)}
        validate_prompt_variables("expand-chapter.md", r)
        prompt = prompt_template.format(**r)

        pc = get_prompt_config_with_overrides("expand-chapter.md", config)

        try:
            result = call_api(
                api_key, pc.get("model", model), prompt,
                reasoning_effort=pc.get("reasoning_effort", "low"),
                max_tokens=pc.get("max_tokens", 10000),
                temperature=pc.get("temperature", 0.8),
                system_prompt="",
                api_url=api_url
            )
            
            new_chars = len(result.replace('\n', '').replace(' ', ''))
            
            # 检查字数
            if new_chars < orig_chars * 1.1:
                print(f"  [SKIP] ch{ch:03d}: 扩写不足 ({orig_chars}→{new_chars})")
            else:
                ch_file.write_text(tag_output(result, "expand-chapter.md"), encoding='utf-8')
                expanded += 1
                print(f"  [EXPAND] ch{ch:03d}: {orig_chars}→{new_chars}字 (+{(new_chars/orig_chars-1)*100:.0f}%)")
        except Exception as e:
            print(f"  [FAIL] expand ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        print_progress(done_chapters, total_chapters, t_start)

    if expanded:
        print(f"\n[OK] 扩写了 {expanded} 章")
    return expanded
