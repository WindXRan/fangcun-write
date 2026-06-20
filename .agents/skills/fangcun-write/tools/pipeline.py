"""
fangcun-write pipeline: 通用写作能力引擎

流程（与原版 fangcun-novel 一致）：
Phase 3: 写章（并行）→ 按需 trim/expand（3轮）→ 统一 polish
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加依赖路径
_SHARED = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
_SHARED_LLM = _SHARED / "llm"
sys.path.insert(0, str(_SHARED))
sys.path.insert(0, str(_SHARED_LLM))

from writer import (
    write_chapter, trim_chapter, expand_chapter, polish_chapter, rewrite_chapter,
    get_writer_dirs, _get_text_chars, count_source_chars, get_source_text
)


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    if "base_dir" not in config:
        config["base_dir"] = str(Path(config_path).parent.parent.parent.parent.parent)
    if "rewrites_dir" in config and not Path(config["rewrites_dir"]).is_absolute():
        config["rewrites_dir"] = str(Path(config["base_dir"]) / config["rewrites_dir"])
    return config


def phase_write(config, start, end, mode="imitation", workers=1):
    """写章 + 按需 trim/expand + 统一 polish（与原版 phase_write 一致）"""
    dirs = get_writer_dirs(config)
    chapters_dir = dirs["chapters_dir"]
    chapters_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"Phase 3: 写章 (ch{start}-{end}, {workers}w)")
    print("="*50)

    t0 = time.time()

    # --- 写章 ---
    chapters = list(range(start, end + 1))
    ok = {}
    fail = {}

    def _write_one(ch):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if ch_file.exists() and ch_file.stat().st_size >= 500:
            return ch, "SKIP", "已存在"
        try:
            result = write_chapter(config, ch, mode=mode)
            if result:
                ch_file.write_text(result, encoding='utf-8')
                return ch, "OK", f"{_get_text_chars(result)}字"
            return ch, "FAIL", ""
        except Exception as e:
            return ch, "FAIL", str(e)

    if workers <= 1:
        for ch in chapters:
            ch, status, info = _write_one(ch)
            if status == "OK":
                print(f"  [OK] ch{ch:03d} ({info})")
                ok[ch] = str(chapters_dir / f"ch_{ch:03d}.txt")
            elif status == "SKIP":
                print(f"  [SKIP] ch{ch:03d} ({info})")
                ok[ch] = str(chapters_dir / f"ch_{ch:03d}.txt")
            else:
                print(f"  [FAIL] ch{ch:03d}: {info}")
                fail[ch] = info
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_write_one, ch): ch for ch in chapters}
            for f in as_completed(futures):
                ch, status, info = f.result()
                if status in ("OK", "SKIP"):
                    print(f"  [{status}] ch{ch:03d} ({info})")
                    ok[ch] = str(chapters_dir / f"ch_{ch:03d}.txt")
                else:
                    print(f"  [FAIL] ch{ch:03d}: {info}")
                    fail[ch] = info

    # --- 按需修复：字数 trim/expand（3轮）---
    for retry_round in range(1, 4):
        retry_list = []
        rewrite_list = []
        for ch in range(start, end + 1):
            ch_file = chapters_dir / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')
            chars = _get_text_chars(text)

            if chars < 500:
                rewrite_list.append(ch)
            elif chars < 2000:
                retry_list.append((ch, "expand"))
            elif chars > 3000:
                retry_list.append((ch, "trim"))

        if rewrite_list:
            print(f"\n  [REWRITE] {len(rewrite_list)}章字数极短: {rewrite_list}")
            for ch in rewrite_list:
                try:
                    result = write_chapter(config, ch, mode=mode)
                    if result:
                        (chapters_dir / f"ch_{ch:03d}.txt").write_text(result, encoding='utf-8')
                        print(f"    [OK] ch{ch:03d} 重写完成")
                except Exception as e:
                    print(f"    [FAIL] ch{ch:03d}: {e}")

        if not retry_list and not rewrite_list:
            break

        if retry_list:
            print(f"\n  [RETRY R{retry_round}] {len(retry_list)}章需调整: {[c for c,_ in retry_list]}")
            for ch, action in retry_list:
                ch_file = chapters_dir / f"ch_{ch:03d}.txt"
                try:
                    if action == "trim":
                        result = trim_chapter(config, ch, mode=mode)
                    else:
                        result = expand_chapter(config, ch, mode=mode)
                    if result:
                        ch_file.write_text(result, encoding='utf-8')
                        print(f"    [{action.upper()}] ch{ch:03d} OK")
                    else:
                        print(f"    [{action.upper()}] ch{ch:03d} 跳过")
                except Exception as e:
                    print(f"    [{action.upper()}] ch{ch:03d} FAIL: {e}")

    # --- 统一润色：每章必 polish ---
    print(f"\n  [POLISH] 对比源文润色...")
    t_polish = time.time()
    polished = 0
    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        try:
            result = polish_chapter(config, ch, mode=mode)
            if result:
                ch_file.write_text(result, encoding='utf-8')
                polished += 1
                print(f"    [OK] ch{ch:03d} 润色完成")
        except Exception as e:
            print(f"    [FAIL] ch{ch:03d}: {e}")
    print(f"  [POLISH] 润色完成 {polished} 章 ({time.time()-t_polish:.0f}s)")

    total = sum(
        _get_text_chars(Path(p).read_text(encoding='utf-8'))
        for p in ok.values() if Path(p).exists()
    )
    print(f"\n  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耽误 {time.time()-t0:.0f}s")
    return ok, fail


def main():
    parser = argparse.ArgumentParser(description="fangcun-write pipeline")
    parser.add_argument("--config", required=True)
    parser.add_argument("--phase", required=True,
                       choices=["write", "trim", "polish", "expand", "rewrite"])
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--mode", default="imitation", choices=["imitation", "continue"])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reason", default="")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.phase == "write":
        phase_write(config, args.start, args.end, mode=args.mode, workers=args.workers)
    elif args.phase == "trim":
        for ch in range(args.start, args.end + 1):
            result = trim_chapter(config, ch, mode=args.mode)
            if result:
                ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                print(f"  [OK] ch{ch:03d}")
    elif args.phase == "polish":
        for ch in range(args.start, args.end + 1):
            result = polish_chapter(config, ch, mode=args.mode)
            if result:
                ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                print(f"  [OK] ch{ch:03d}")
    elif args.phase == "expand":
        for ch in range(args.start, args.end + 1):
            result = expand_chapter(config, ch, mode=args.mode)
            if result:
                ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                print(f"  [OK] ch{ch:03d}")
    elif args.phase == "rewrite":
        for ch in range(args.start, args.end + 1):
            result = rewrite_chapter(config, ch, mode=args.mode, reason=args.reason)
            if result:
                ch_file = Path(config["rewrites_dir"]) / "chapters" / f"ch_{ch:03d}.txt"
                ch_file.write_text(result, encoding='utf-8')
                print(f"  [OK] ch{ch:03d}")


if __name__ == "__main__":
    main()
