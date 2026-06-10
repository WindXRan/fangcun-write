"""全文修复：读取审稿报告→并行修复章节"""
import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def call_api(api_key, api_url, model, user_prompt, system_prompt=None, max_tokens=8000, temperature=0.8):
    """调用API。"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or "你是专业网文写手。"},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    resp = requests.post(api_url, headers=headers, json=data, timeout=300)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def load_review_reports(compare_dir):
    """加载所有审稿报告。"""
    reviews = {}
    for f in sorted(Path(compare_dir).glob("审稿_第*批_*.md")):
        content = f.read_text(encoding='utf-8')
        # 提取批次号和章节范围
        name = f.stem  # 审稿_第1批_1-20
        parts = name.split('_')
        if len(parts) >= 3:
            batch_num = int(parts[1].replace('第', '').replace('批', ''))
            chapters_range = parts[2]
            start, end = map(int, chapters_range.split('-'))
            reviews[batch_num] = {
                'start': start,
                'end': end,
                'content': content,
                'file': str(f)
            }
    return reviews


def load_summary_report(compare_dir):
    """加载汇总报告。"""
    summary_file = Path(compare_dir) / "全文审稿汇总报告.md"
    if summary_file.exists():
        return summary_file.read_text(encoding='utf-8')
    return ""


def fix_chapter(api_key, api_url, model, ch, ch_file, review_content, summary_content, concept_text):
    """修复单个章节。"""
    original_text = ch_file.read_text(encoding='utf-8')
    orig_chars = len(original_text.replace('\n', '').replace(' ', ''))
    
    prompt = f"""你是专业网文写手。请根据审稿建议，修改以下章节。

【小说设定】
{concept_text[:1000]}

【本批次审稿报告】
{review_content[:3000]}

【全书汇总报告（关键问题）】
{summary_content[:2000]}

【原始章节（第{ch}章）】
{original_text}

【修改要求】
1. 保持原有的故事框架和人物关系
2. 根据审稿建议修复逻辑矛盾、人设问题
3. 保持文风一致
4. 字数必须控制在原文±10%以内（{int(orig_chars*0.9)}~{int(orig_chars*1.1)}字）
5. 直接输出修改后的完整章节，不要解释

【输出格式】
第{ch}章 [章节标题]

[修改后的完整正文]
"""

    try:
        result = call_api(api_key, api_url, model, prompt, 
                         system_prompt="你是专业网文写手，擅长根据审稿建议修改章节。字数必须控制在原文±10%以内。",
                         max_tokens=8000, temperature=0.8)
        
        new_chars = len(result.replace('\n', '').replace(' ', ''))
        
        # 检查字数差异
        if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.15:
            return {'ch': ch, 'status': 'SKIP', 'reason': f'字数差异过大 ({orig_chars}→{new_chars})'}
        
        # 保存
        ch_file.write_text(result, encoding='utf-8')
        return {'ch': ch, 'status': 'FIXED', 'orig': orig_chars, 'new': new_chars}
        
    except Exception as e:
        return {'ch': ch, 'status': 'FAIL', 'reason': str(e)}


def main():
    parser = argparse.ArgumentParser(description="全文修复工具")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=None, help="结束章")
    parser.add_argument("--workers", type=int, default=5, help="并行数")
    parser.add_argument("--dry-run", action="store_true", help="只显示待修复章节，不实际修复")
    
    args = parser.parse_args()
    
    # 读取配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding='utf-8'))
    
    # API配置
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com/v1") + "/chat/completions"
    model = config.get("model", "deepseek-chat")
    
    if not api_key:
        print("未配置API_KEY")
        sys.exit(1)
    
    rewrites_dir = config['rewrites_dir']
    chapters_dir = f"{rewrites_dir}/chapters"
    compare_dir = f"{rewrites_dir}/compare"
    
    # 清理旧的修复报告
    for old_file in Path(compare_dir).glob("修复结果*.json"):
        old_file.unlink()
    print("已清理旧修复报告")
    
    # 读取concept.md
    concept_path = Path(rewrites_dir) / 'concept.md'
    concept_text = ""
    if concept_path.exists():
        concept_text = concept_path.read_text(encoding='utf-8')
    
    # 自动检测结束章节
    if args.end is None:
        chapter_files = sorted(Path(chapters_dir).glob("ch_*.txt"))
        if chapter_files:
            args.end = int(chapter_files[-1].stem.split('_')[1])
        else:
            print("未找到章节文件")
            sys.exit(1)
    
    print(f"\n{'=' * 60}")
    print(f"全文修复 (ch{args.start}-{args.end})")
    print("=" * 60)
    
    # 加载审稿报告
    reviews = load_review_reports(compare_dir)
    summary = load_summary_report(compare_dir)
    
    if not reviews:
        print("未找到审稿报告，请先运行 full_review.py")
        sys.exit(1)
    
    print(f"找到 {len(reviews)} 个批次的审稿报告")
    
    # 收集待修复章节
    todo_chapters = []
    for ch in range(args.start, args.end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        # 找到对应的审稿报告
        review_content = ""
        for batch_num, review in reviews.items():
            if review['start'] <= ch <= review['end']:
                review_content = review['content']
                break
        
        if review_content:
            todo_chapters.append((ch, ch_file, review_content))
    
    print(f"待修复章节: {len(todo_chapters)}章")
    
    if args.dry_run:
        print("\n[DRY RUN] 待修复章节列表:")
        for ch, ch_file, _ in todo_chapters:
            print(f"  - ch{ch:03d}: {ch_file}")
        return
    
    # 并行修复
    print(f"\n{'=' * 50}")
    print(f"开始修复（{args.workers}个并行）")
    print("=" * 50)
    
    t_start = time.time()
    results = []
    done = 0
    total = len(todo_chapters)
    
    def process_chapter(ch, ch_file, review_content):
        return fix_chapter(api_key, api_url, model, ch, ch_file, review_content, summary, concept_text)
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_chapter, ch, ch_file, review_content): ch
            for ch, ch_file, review_content in todo_chapters
        }
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            
            # 打印进度
            elapsed = time.time() - t_start
            speed = elapsed / done
            eta = speed * (total - done)
            pct = done * 100 // total
            bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
            
            status = result['status']
            ch = result['ch']
            if status == 'FIXED':
                print(f"  [{done}/{total}] [{bar}] {pct}% | ch{ch:03d}: [FIXED] ({result['orig']}→{result['new']}字)")
            elif status == 'SKIP':
                print(f"  [{done}/{total}] [{bar}] {pct}% | ch{ch:03d}: [SKIP] {result['reason']}")
            else:
                print(f"  [{done}/{total}] [{bar}] {pct}% | ch{ch:03d}: [FAIL] {result['reason']}")
    
    # 统计结果
    fixed = sum(1 for r in results if r['status'] == 'FIXED')
    skipped = sum(1 for r in results if r['status'] == 'SKIP')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    
    total_time = time.time() - t_start
    
    print(f"\n{'=' * 60}")
    print(f"修复完成！")
    print("=" * 60)
    print(f"总章节: {total}章")
    print(f"已修复: {fixed}章")
    print(f"已跳过: {skipped}章")
    print(f"失败: {failed}章")
    print(f"总耗时: {total_time:.0f}秒")
    
    # 保存修复结果
    result_file = Path(compare_dir) / "修复结果.json"
    result_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n修复结果已保存: {result_file}")


if __name__ == "__main__":
    main()
