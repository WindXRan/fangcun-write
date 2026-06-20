"""
story-optimize: 审稿→沉淀→修复

用法:
  python optimize.py --config configs/xxx.json --start 1 --end 10
  python optimize.py --config configs/xxx.json --dry-run
"""
import os
import sys
import re
import json
import argparse
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'fangcun-novel' / 'tools'))
from lib.api_client import call_api, get_api_key, get_api_url

BATCH_SIZE = 5  # 每批5章
PROMPTS_DIR = Path(__file__).parent / 'prompts'


def load_prompt_str(name):
    """从 prompts/ 加载 prompt，去掉 frontmatter。"""
    p = PROMPTS_DIR / name
    if not p.exists():
        return ""
    text = p.read_text(encoding='utf-8')
    # 去掉 frontmatter
    if text.startswith('---'):
        end = text.find('---', 3)
        if end != -1:
            text = text[end+3:]
    return text.strip()


def get_chapters(rewrites_dir, start, end):
    """获取指定范围的章节文件。"""
    ch_dir = Path(rewrites_dir) / 'chapters'
    chapters = []
    for f in sorted(ch_dir.glob('ch_*.txt')):
        ch_num = int(re.search(r'ch_(\d+)', f.name).group(1))
        if start <= ch_num <= end:
            chapters.append((ch_num, f))
    return chapters


def read_chapter(fpath):
    """读取章节内容。"""
    with open(fpath, 'r', encoding='utf-8') as f:
        return f.read()


def analyze_batch(batch_num, chapters, book_name, api_key, api_url, model, dry_run=False):
    """分析一批章节。"""
    batch_text = ""
    ch_nums = []
    for ch_num, fpath in chapters:
        text = read_chapter(fpath)
        batch_text += f"\n\n=== 第{ch_num}章 ===\n{text}"
        ch_nums.append(ch_num)

    prompt_template = load_prompt_str("analyze_batch.md")
    prompt = prompt_template.format(
        batch_text=batch_text,
        book_name=book_name,
        batch_range=f"{ch_nums[0]}-{ch_nums[-1]}"
    )

    if dry_run:
        print(f"  [DRY-RUN] 批次{batch_num}: 第{ch_nums[0]}-{ch_nums[-1]}章")
        return {"batch": batch_num, "chapters": ch_nums, "issues": []}

    try:
        result = call_api(api_key, model, prompt,
                         temperature=0.3, max_tokens=4096,
                         api_url=api_url)
        # 解析JSON
        result = result.strip()
        if result.startswith('```'):
            result = re.sub(r'^```(?:json)?\s*', '', result)
            result = re.sub(r'\s*```$', '', result)
        issues = json.loads(result)
        print(f"  ✅ 批次{batch_num}: 第{ch_nums[0]}-{ch_nums[-1]}章, {len(issues)}个问题")
        return {"batch": batch_num, "chapters": ch_nums, "issues": issues}
    except Exception as e:
        print(f"  ❌ 批次{batch_num}: {e}")
        return {"batch": batch_num, "chapters": ch_nums, "issues": [], "error": str(e)}


def summarize_analyses(analyses, book_name, api_key, api_url, model, dry_run=False):
    """汇总所有批次的分析结果。"""
    all_analyses = json.dumps(analyses, ensure_ascii=False, indent=2)

    prompt_template = load_prompt_str("summarize.md")
    prompt = prompt_template.format(
        all_analyses=all_analyses,
        book_name=book_name
    )

    if dry_run:
        print("  [DRY-RUN] 汇总")
        return {"summary": {"total_chapters": 0, "high_issues": 0, "medium_issues": 0, "low_issues": 0}, "issues": []}

    try:
        result = call_api(api_key, model, prompt,
                         temperature=0.3, max_tokens=4096,
                         api_url=api_url)
        result = result.strip()
        if result.startswith('```'):
            result = re.sub(r'^```(?:json)?\s*', '', result)
            result = re.sub(r'\s*```$', '', result)
        summary = json.loads(result)
        print(f"  ✅ 汇总完成: {summary['summary']['high_issues']}个high, {summary['summary']['medium_issues']}个medium")
        return summary
    except Exception as e:
        print(f"  ❌ 汇总失败: {e}")
        return {"summary": {"total_chapters": 0, "high_issues": 0, "medium_issues": 0, "low_issues": 0}, "issues": [], "error": str(e)}


def fix_chapter(ch_num, fpath, issues_json, book_name, api_key, api_url, model, dry_run=False):
    """修复单章。"""
    chapter_text = read_chapter(fpath)

    prompt_template = load_prompt_str("fix_chapter.md")
    prompt = prompt_template.format(
        chapter_text=chapter_text,
        issues_json=issues_json,
        chapter_num=ch_num,
        book_name=book_name
    )

    if dry_run:
        print(f"  [DRY-RUN] 第{ch_num}章")
        return {"ch": ch_num, "status": "dry_run"}

    try:
        result = call_api(api_key, model, prompt,
                         temperature=0.6, max_tokens=8192,
                         api_url=api_url)
        result = result.strip()
        if result.startswith('```'):
            result = re.sub(r'^```(?:txt)?\s*', '', result)
            result = re.sub(r'\s*```$', '', result)

        # 检查是否有实质变化
        if result == chapter_text:
            print(f"  ⏭️ 第{ch_num}章: 无变化")
            return {"ch": ch_num, "status": "no_change"}

        # 写入文件
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(result)

        orig_len = len(re.sub(r'\s', '', chapter_text))
        new_len = len(re.sub(r'\s', '', result))
        print(f"  ✅ 第{ch_num}章: {orig_len}→{new_len}字")
        return {"ch": ch_num, "status": "fixed", "orig": orig_len, "new": new_len}
    except Exception as e:
        print(f"  ❌ 第{ch_num}章: {e}")
        return {"ch": ch_num, "status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='story-optimize: 审稿→沉淀→修复')
    parser.add_argument('--config', required=True, help='配置文件路径')
    parser.add_argument('--start', type=int, default=1, help='起始章')
    parser.add_argument('--end', type=int, default=9999, help='结束章')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='每批章数')
    parser.add_argument('--dry-run', action='store_true', help='只审不修')
    parser.add_argument('--workers', type=int, default=3, help='并发数')
    args = parser.parse_args()

    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = config.get('model', 'deepseek-v4-flash')
    book_name = config['book_name']
    rewrites_dir = config['rewrites_dir']

    # 创建输出目录
    optimize_dir = Path(rewrites_dir) / 'optimize'
    optimize_dir.mkdir(parents=True, exist_ok=True)

    # 获取章节
    chapters = get_chapters(rewrites_dir, args.start, args.end)
    if not chapters:
        print("没有找到章节")
        return

    print(f"\n{'='*60}")
    print(f"story-optimize: {book_name}")
    print(f"范围: 第{args.start}-{args.end}章 ({len(chapters)}章)")
    print(f"{'='*60}")

    # Step 1: 分批审稿
    print(f"\n[1/3] 分批审稿 (每批{args.batch_size}章)...")
    batches = []
    for i in range(0, len(chapters), args.batch_size):
        batch = chapters[i:i+args.batch_size]
        batches.append((len(batches)+1, batch))

    analyses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                analyze_batch, batch_num, batch, book_name,
                api_key, api_url, model, args.dry_run
            ): batch_num
            for batch_num, batch in batches
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            analyses.append(result)

    # 保存批次结果
    for a in analyses:
        batch_file = optimize_dir / f"batch_{a['chapters'][0]}_{a['chapters'][-1]}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False, indent=2)

    # Step 2: 汇总问题
    print(f"\n[2/3] 汇总问题...")
    summary = summarize_analyses(analyses, book_name, api_key, api_url, model, args.dry_run)

    summary_file = optimize_dir / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Step 3: 批量修复
    if not args.dry_run and summary.get('issues'):
        print(f"\n[3/3] 批量修复...")
        issues_json = json.dumps(summary['issues'], ensure_ascii=False, indent=2)

        fix_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    fix_chapter, ch_num, fpath, issues_json, book_name,
                    api_key, api_url, model, args.dry_run
                ): ch_num
                for ch_num, fpath in chapters
            }
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                fix_results.append(result)

        # 保存修复日志
        fix_log = optimize_dir / "fix_log.json"
        with open(fix_log, 'w', encoding='utf-8') as f:
            json.dump(fix_results, f, ensure_ascii=False, indent=2)

        fixed = sum(1 for r in fix_results if r['status'] == 'fixed')
        print(f"\n{'='*60}")
        print(f"完成: {fixed}/{len(chapters)} 章已修复")
    else:
        print(f"\n{'='*60}")
        print(f"完成: 审稿结果已保存到 {optimize_dir}")

    print(f"{'='*60}")


if __name__ == '__main__':
    main()
