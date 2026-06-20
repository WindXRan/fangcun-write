"""
fangcun-write pipeline: 通用写作能力引擎

支持独立使用或被其他引擎调用。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加 fangcun-analyze 到 path
_SHARED_ENGINE = Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"
_SHARED_ENGINE_LLM = _SHARED_ENGINE / "llm"
sys.path.insert(0, str(_SHARED_ENGINE))
sys.path.insert(0, str(_SHARED_ENGINE_LLM))

from writer import write_chapter, trim_chapter, polish_chapter, expand_chapter, rewrite_chapter


def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 自动检测 base_dir（如果未指定）
    if "base_dir" not in config:
        config["base_dir"] = str(Path(config_path).parent.parent.parent.parent.parent)
    
    # 如果 rewrites_dir 是相对路径，基于 base_dir 解析
    if "rewrites_dir" in config and not Path(config["rewrites_dir"]).is_absolute():
        config["rewrites_dir"] = str(Path(config["base_dir"]) / config["rewrites_dir"])
    
    return config


def _write_single(config, ch_num, mode):
    """写单章（用于并发）"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    ch_file = rewrites_dir / "chapters" / f"ch_{ch_num:03d}.txt"
    
    if ch_file.exists():
        return ch_num, "SKIP", f"已存在"
    
    result = write_chapter(config, ch_num, mode=mode)
    if result:
        ch_file.write_text(result, encoding='utf-8')
        return ch_num, "OK", f"{len(result)}字"
    return ch_num, "FAIL", ""


def _process_single(config, ch_num, mode, action):
    """处理单章（trim/polish/expand，用于并发）"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    ch_file = rewrites_dir / "chapters" / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        return ch_num, "SKIP", "不存在"
    
    fn_map = {"trim": trim_chapter, "polish": polish_chapter, "expand": expand_chapter}
    result = fn_map[action](config, ch_num, mode=mode)
    if result:
        ch_file.write_text(result, encoding='utf-8')
        return ch_num, "OK", ""
    return ch_num, "FAIL", ""


def _rewrite_single(config, ch_num, mode, reason):
    """重写单章"""
    result = rewrite_chapter(config, ch_num, mode=mode, reason=reason)
    if result:
        rewrites_dir = Path(config.get("rewrites_dir", ""))
        ch_file = rewrites_dir / "chapters" / f"ch_{ch_num:03d}.txt"
        ch_file.write_text(result, encoding='utf-8')
        return ch_num, "OK", f"{len(result)}字"
    return ch_num, "FAIL", ""


def phase_write(config, start, end, mode="imitation", workers=1):
    """写章"""
    print(f"\n{'='*50}")
    print(f"Phase: 写章 (mode={mode}, workers={workers})")
    print(f"{'='*50}")
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    (rewrites_dir / "chapters").mkdir(parents=True, exist_ok=True)
    
    chapters = list(range(start, end + 1))
    ok, fail, skip = 0, 0, 0
    
    if workers <= 1:
        for ch_num in chapters:
            ch_num, status, info = _write_single(config, ch_num, mode)
            if status == "OK":
                print(f"    [OK] 第{ch_num}章 ({info})")
                ok += 1
            elif status == "SKIP":
                print(f"    [SKIP] 第{ch_num}章 ({info})")
                skip += 1
            else:
                print(f"    [FAIL] 第{ch_num}章")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_write_single, config, ch_num, mode): ch_num for ch_num in chapters}
            for future in as_completed(futures):
                ch_num, status, info = future.result()
                if status == "OK":
                    print(f"    [OK] 第{ch_num}章 ({info})")
                    ok += 1
                elif status == "SKIP":
                    print(f"    [SKIP] 第{ch_num}章 ({info})")
                    skip += 1
                else:
                    print(f"    [FAIL] 第{ch_num}章")
                    fail += 1
    
    print(f"\n  完成: {ok} OK / {skip} SKIP / {fail} FAIL")


def phase_trim(config, start, end, mode="imitation", workers=1):
    """精简"""
    print(f"\n{'='*50}")
    print(f"Phase: 精简 (mode={mode}, workers={workers})")
    print(f"{'='*50}")
    
    chapters = list(range(start, end + 1))
    ok, fail, skip = 0, 0, 0
    
    if workers <= 1:
        for ch_num in chapters:
            ch_num, status, info = _process_single(config, ch_num, mode, "trim")
            if status == "OK":
                print(f"    [OK] 第{ch_num}章")
                ok += 1
            elif status == "SKIP":
                print(f"    [SKIP] 第{ch_num}章 ({info})")
                skip += 1
            else:
                print(f"    [FAIL] 第{ch_num}章")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_single, config, ch_num, mode, "trim"): ch_num for ch_num in chapters}
            for future in as_completed(futures):
                ch_num, status, info = future.result()
                if status == "OK":
                    print(f"    [OK] 第{ch_num}章")
                    ok += 1
                elif status == "SKIP":
                    print(f"    [SKIP] 第{ch_num}章 ({info})")
                    skip += 1
                else:
                    print(f"    [FAIL] 第{ch_num}章")
                    fail += 1
    
    print(f"\n  完成: {ok} OK / {skip} SKIP / {fail} FAIL")


def phase_polish(config, start, end, mode="imitation", workers=1):
    """润色"""
    print(f"\n{'='*50}")
    print(f"Phase: 润色 (mode={mode}, workers={workers})")
    print(f"{'='*50}")
    
    chapters = list(range(start, end + 1))
    ok, fail, skip = 0, 0, 0
    
    if workers <= 1:
        for ch_num in chapters:
            ch_num, status, info = _process_single(config, ch_num, mode, "polish")
            if status == "OK":
                print(f"    [OK] 第{ch_num}章")
                ok += 1
            elif status == "SKIP":
                print(f"    [SKIP] 第{ch_num}章 ({info})")
                skip += 1
            else:
                print(f"    [FAIL] 第{ch_num}章")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_single, config, ch_num, mode, "polish"): ch_num for ch_num in chapters}
            for future in as_completed(futures):
                ch_num, status, info = future.result()
                if status == "OK":
                    print(f"    [OK] 第{ch_num}章")
                    ok += 1
                elif status == "SKIP":
                    print(f"    [SKIP] 第{ch_num}章 ({info})")
                    skip += 1
                else:
                    print(f"    [FAIL] 第{ch_num}章")
                    fail += 1
    
    print(f"\n  完成: {ok} OK / {skip} SKIP / {fail} FAIL")


def phase_expand(config, start, end, mode="imitation", workers=1):
    """扩写"""
    print(f"\n{'='*50}")
    print(f"Phase: 扩写 (mode={mode}, workers={workers})")
    print(f"{'='*50}")
    
    chapters = list(range(start, end + 1))
    ok, fail, skip = 0, 0, 0
    
    if workers <= 1:
        for ch_num in chapters:
            ch_num, status, info = _process_single(config, ch_num, mode, "expand")
            if status == "OK":
                print(f"    [OK] 第{ch_num}章")
                ok += 1
            elif status == "SKIP":
                print(f"    [SKIP] 第{ch_num}章 ({info})")
                skip += 1
            else:
                print(f"    [FAIL] 第{ch_num}章")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_single, config, ch_num, mode, "expand"): ch_num for ch_num in chapters}
            for future in as_completed(futures):
                ch_num, status, info = future.result()
                if status == "OK":
                    print(f"    [OK] 第{ch_num}章")
                    ok += 1
                elif status == "SKIP":
                    print(f"    [SKIP] 第{ch_num}章 ({info})")
                    skip += 1
                else:
                    print(f"    [FAIL] 第{ch_num}章")
                    fail += 1
    
    print(f"\n  完成: {ok} OK / {skip} SKIP / {fail} FAIL")


def phase_rewrite(config, start, end, mode="imitation", reason="", workers=1):
    """重写"""
    print(f"\n{'='*50}")
    print(f"Phase: 重写 (mode={mode}, workers={workers})")
    print(f"{'='*50}")
    
    chapters = list(range(start, end + 1))
    ok, fail = 0, 0
    
    if workers <= 1:
        for ch_num in chapters:
            ch_num, status, info = _rewrite_single(config, ch_num, mode, reason)
            if status == "OK":
                print(f"    [OK] 第{ch_num}章 ({info})")
                ok += 1
            else:
                print(f"    [FAIL] 第{ch_num}章")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_rewrite_single, config, ch_num, mode, reason): ch_num for ch_num in chapters}
            for future in as_completed(futures):
                ch_num, status, info = future.result()
                if status == "OK":
                    print(f"    [OK] 第{ch_num}章 ({info})")
                    ok += 1
                else:
                    print(f"    [FAIL] 第{ch_num}章")
                    fail += 1
    
    print(f"\n  完成: {ok} OK / {fail} FAIL")


def main():
    parser = argparse.ArgumentParser(description="fangcun-write: 通用写作能力引擎")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", required=True, 
                       choices=["write", "trim", "polish", "expand", "rewrite"],
                       help="执行阶段")
    parser.add_argument("--start", type=int, required=True, help="开始章节")
    parser.add_argument("--end", type=int, required=True, help="结束章节")
    parser.add_argument("--mode", default="imitation", choices=["imitation", "continue"],
                       help="模式: imitation(仿写) 或 continue(续写)")
    parser.add_argument("--workers", type=int, default=1, help="并发数")
    parser.add_argument("--reason", default="", help="重写原因")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.phase == "write":
        phase_write(config, args.start, args.end, mode=args.mode, workers=args.workers)
    elif args.phase == "trim":
        phase_trim(config, args.start, args.end, mode=args.mode, workers=args.workers)
    elif args.phase == "polish":
        phase_polish(config, args.start, args.end, mode=args.mode, workers=args.workers)
    elif args.phase == "expand":
        phase_expand(config, args.start, args.end, mode=args.mode, workers=args.workers)
    elif args.phase == "rewrite":
        phase_rewrite(config, args.start, args.end, mode=args.mode, reason=args.reason, workers=args.workers)


if __name__ == "__main__":
    main()
