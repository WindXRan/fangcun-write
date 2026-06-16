"""
剧本引擎 — 一章一集，1分钟短剧。

用法:
  python pipeline.py --config configs/drama_xxx.json
  python pipeline.py --config configs/drama_xxx.json --start 1 --end 10
  python pipeline.py --config configs/drama_xxx.json --phase export
"""
import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'story-engine' / 'tools'))
from lib.api_client import call_api, get_api_key, get_api_url
from prompt_loader import load_prompt_str

TARGET_CHARS = 1200  # 1分钟约1200字


def get_chapters(source_dir, start, end):
    """获取章节列表。"""
    chapters = []
    for f in sorted(Path(source_dir).glob("第*章*.txt")):
        ch_num = int(re.search(r'(\d+)', f.name).group(1))
        if start <= ch_num <= end:
            chapters.append((ch_num, f))
    return chapters


def write_episode(config, ch_num, chapter_file, api_key, api_url, model, dry_run=False):
    """写单集剧本。"""
    chapter_text = chapter_file.read_text(encoding='utf-8')

    # 加载 prompt
    prompt_template = load_prompt_str("write-episode.md")
    if not prompt_template:
        return None, "prompt 不存在"

    prompt = prompt_template.format(
        chapter_text=chapter_text[:3000],  # 限制长度
        episode_num=ch_num,
        target_chars=TARGET_CHARS,
        novel_name=config.get("novel_name", ""),
    )

    if dry_run:
        return None, "dry-run"

    try:
        result = call_api(
            api_key, model, prompt,
            temperature=0.6, max_tokens=2048,
            api_url=api_url,
            system_prompt="你是红果短剧编剧，专注1分钟短剧改编。只输出剧本格式。",
        )

        # 清理输出
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1]
        if result.endswith("```"):
            result = result.rsplit("```", 1)[0]
        result = result.strip()

        return result, "ok"
    except Exception as e:
        return None, str(e)


def export_episodes(config, start, end):
    """导出所有集为单个文件。"""
    output_dir = Path(config["output_dir"])
    episodes = []
    for ch in range(start, end + 1):
        ep_file = output_dir / f"ep_{ch:03d}.txt"
        if ep_file.exists():
            episodes.append(ep_file.read_text(encoding='utf-8'))

    if not episodes:
        print("没有可导出的集")
        return

    # 合并导出
    export_file = output_dir / f"{config.get('drama_name', '剧本')}.txt"
    export_file.write_text("\n\n---\n\n".join(episodes), encoding='utf-8')
    print(f"导出完成: {export_file} ({len(episodes)}集)")


def main():
    parser = argparse.ArgumentParser(description="剧本引擎 — 一章一集1分钟短剧")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=None, help="起始集")
    parser.add_argument("--end", type=int, default=None, help="结束集")
    parser.add_argument("--workers", type=int, default=5, help="并行数")
    parser.add_argument("--phase", default="all", help="all/export")
    parser.add_argument("--dry-run", action="store_true", help="只分析不写")
    args = parser.parse_args()

    # 加载配置
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    source_dir = config["source_dir"]
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定范围
    if args.start is None or args.end is None:
        chapters = list(Path(source_dir).glob("第*章*.txt"))
        if chapters:
            nums = [int(re.search(r'(\d+)', f.name).group(1)) for f in chapters]
            args.start = args.start or min(nums)
            args.end = args.end or max(nums)
    args.start = args.start or 1
    args.end = args.end or 1

    # 导出
    if args.phase == "export":
        export_episodes(config, args.start, args.end)
        return

    # API 配置
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-pro")

    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return

    # 获取章节
    chapters = get_chapters(source_dir, args.start, args.end)
    if not chapters:
        print("没有找到章节")
        return

    print(f"\n{'='*50}")
    print(f"剧本引擎 | {config.get('novel_name', '')} | 第{args.start}-{args.end}集")
    print(f"每集: {TARGET_CHARS}字 | 并行: {args.workers}")
    print(f"{'='*50}")

    # 并行写剧本
    t0 = time.time()
    done = 0
    total = len(chapters)
    results = {}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                write_episode, config, ch_num, ch_file,
                api_key, api_url, model, args.dry_run
            ): ch_num
            for ch_num, ch_file in chapters
        }

        for future in as_completed(futures):
            ch_num = futures[future]
            result, status = future.result()
            done += 1

            if result:
                ep_file = output_dir / f"ep_{ch_num:03d}.txt"
                ep_file.write_text(result, encoding='utf-8')
                results[ch_num] = "ok"
                print(f"  [{done}/{total}] ✓ 第{ch_num}集 ({len(result)}字)")
            else:
                results[ch_num] = status
                print(f"  [{done}/{total}] ✗ 第{ch_num}集 ({status})")

    # 统计
    ok = sum(1 for v in results.values() if v == "ok")
    fail = total - ok
    elapsed = time.time() - t0

    print(f"\n{'='*50}")
    print(f"完成 | {ok}集成功 / {fail}集失败 | {elapsed:.0f}s")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
