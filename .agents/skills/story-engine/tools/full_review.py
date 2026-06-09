"""全文审稿：分批读取→分批审稿→汇总分析"""
import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from prompt_loader import load_prompt


def call_api(api_key, api_url, model, user_prompt, system_prompt=None, max_tokens=4000, temperature=0.7):
    """调用API。"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or "你是资深女频网文编辑。"},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    resp = requests.post(api_url, headers=headers, json=data, timeout=300)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def read_chapters_batch(chapters_dir, start, end):
    """读取一批章节，返回(章节号, 内容)列表。"""
    chapters = []
    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if ch_file.exists():
            content = ch_file.read_text(encoding='utf-8')
            chapters.append((ch, content))
    return chapters


def review_batch(api_key, api_url, model, batch_chapters, concept_text, batch_num, total_batches):
    """审稿一批章节。"""
    # 合并章节内容
    merged = "\n\n---\n\n".join([f"## 第{ch}章\n\n{content}" for ch, content in batch_chapters])
    
    # 限制长度（避免上下文溢出）
    max_chars = 80000  # ~10万token的安全值
    if len(merged) > max_chars:
        merged = merged[:max_chars] + "\n\n[内容截断...]"
    
    prompt = f"""你是资深女频网文编辑，请对以下章节进行专业审稿。

【小说设定】
{concept_text[:2000]}

【审稿章节】
{merged}

【审稿要求】
请从以下维度分析：

1. **单章质量**：每章的钩子、冲突、情绪、节奏
2. **跨章连贯**：时间线、人物状态、事件因果是否一致
3. **逻辑矛盾**：是否有前后矛盾的设定或情节
4. **人设一致性**：角色行为是否符合人设
5. **爽点分布**：是否每章都有推进或爽点

【输出格式】
## 批次审稿报告（第{batch_num}/{total_batches}批）

### 单章评价
| 章节 | 质量 | 主要问题 |
|------|------|----------|
| 第X章 | ⭐⭐⭐⭐ | ... |

### 跨章问题
1. [问题描述]
2. [问题描述]

### 逻辑矛盾
1. [矛盾描述]（涉及章节：第X章、第Y章）
2. [矛盾描述]

### 人设问题
1. [问题描述]

### 修改建议
1. [建议]
"""

    try:
        result = call_api(api_key, api_url, model, prompt, max_tokens=4000)
        return {
            'batch': batch_num,
            'chapters': [ch for ch, _ in batch_chapters],
            'content': result
        }
    except Exception as e:
        return {
            'batch': batch_num,
            'chapters': [ch for ch, _ in batch_chapters],
            'content': f"[审稿失败: {e}]"
        }


def summary_analysis(api_key, api_url, model, all_reviews, concept_text):
    """汇总分析所有批次的审稿结果。"""
    # 合并所有批次的审稿报告
    reviews_text = "\n\n---\n\n".join([
        f"## 第{r['batch']}批（第{r['chapters'][0]}-{r['chapters'][-1]}章）\n\n{r['content']}"
        for r in all_reviews
    ])
    
    prompt = f"""你是资深女频网文编辑，请汇总分析以下分批审稿结果，找出跨章节的系统性问题。

【小说设定】
{concept_text[:2000]}

【分批审稿结果】
{reviews_text}

【分析要求】
请找出以下类型的系统性问题：

1. **致命逻辑矛盾**：跨章节的核心设定矛盾（如人物生死、身份、时间线）
2. **人设漂移**：角色行为前后不一致
3. **时间线混乱**：事件顺序混乱或矛盾
4. **债务/数值矛盾**：金额、数量等数据前后不一致
5. **重复桥段**：相似情节重复出现

【输出格式】
# 全书审稿汇总报告

## 一、致命问题（必须修复）
| 问题 | 涉及章节 | 严重程度 | 修复建议 |
|------|----------|----------|----------|
| ... | ... | 🔴 | ... |

## 二、严重问题（影响阅读）
| 问题 | 涉及章节 | 严重程度 | 修复建议 |
|------|----------|----------|----------|
| ... | ... | 🟡 | ... |

## 三、中轻度问题
| 问题 | 涉及章节 | 严重程度 | 修复建议 |
|------|----------|----------|----------|
| ... | ... | 🟢 | ... |

## 四、亮点总结
- ...

## 五、修订优先级
1. ...
2. ...
"""

    try:
        result = call_api(api_key, api_url, model, prompt, max_tokens=6000)
        return result
    except Exception as e:
        return f"[汇总分析失败: {e}]"


def main():
    parser = argparse.ArgumentParser(description="全文审稿工具")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=None, help="结束章（默认自动检测）")
    parser.add_argument("--batch-size", type=int, default=20, help="每批章节数")
    parser.add_argument("--workers", type=int, default=5, help="并行数")
    
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
    os.makedirs(compare_dir, exist_ok=True)
    
    # 清理旧的审稿报告
    for old_file in Path(compare_dir).glob("审稿_*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("全文审稿*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("全文审稿*.json"):
        old_file.unlink()
    print("已清理旧审稿报告")
    
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
    print(f"全文审稿 (ch{args.start}-{args.end}, 每{args.batch_size}章)")
    print("=" * 60)
    
    # 分批
    batches = []
    for batch_start in range(args.start, args.end + 1, args.batch_size):
        batch_end = min(batch_start + args.batch_size - 1, args.end)
        batches.append((batch_start, batch_end))
    
    print(f"总章节数: {args.end - args.start + 1}")
    print(f"批次数: {len(batches)}")
    
    # 第一阶段：分批审稿
    print(f"\n{'=' * 50}")
    print(f"第一阶段：分批审稿")
    print("=" * 50)
    
    all_reviews = []
    t_start = time.time()
    
    def process_batch(batch_num, batch_start, batch_end):
        """处理单个批次。"""
        batch_chapters = read_chapters_batch(chapters_dir, batch_start, batch_end)
        if not batch_chapters:
            return {'batch': batch_num, 'chapters': [], 'content': '[无内容]'}
        
        result = review_batch(api_key, api_url, model, batch_chapters, concept_text, batch_num, len(batches))
        
        # 保存单批报告
        review_file = Path(compare_dir) / f"审稿_第{batch_num}批_{batch_start}-{batch_end}.md"
        review_file.write_text(f"# 审稿报告：第{batch_num}批（第{batch_start}-{batch_end}章）\n\n{result['content']}", encoding='utf-8')
        
        # 打印进度
        elapsed = time.time() - t_start
        pct = batch_num * 100 // len(batches)
        bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
        print(f"  [{batch_num}/{len(batches)}] [{bar}] {pct}% | {elapsed:.0f}s | 第{batch_start}-{batch_end}章")
        
        return result
    
    # 并行处理
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_batch, i+1, start, end): (i+1, start, end)
            for i, (start, end) in enumerate(batches)
        }
        for future in as_completed(futures):
            result = future.result()
            all_reviews.append(result)
    
    # 按批次排序
    all_reviews.sort(key=lambda x: x['batch'])
    
    # 第二阶段：汇总分析
    print(f"\n{'=' * 50}")
    print(f"第二阶段：汇总分析")
    print("=" * 50)
    
    summary = summary_analysis(api_key, api_url, model, all_reviews, concept_text)
    
    # 保存汇总报告
    summary_file = Path(compare_dir) / "全文审稿汇总报告.md"
    summary_file.write_text(summary, encoding='utf-8')
    
    # 保存完整审稿结果
    full_review_file = Path(compare_dir) / "全文审稿完整结果.json"
    full_review_file.write_text(json.dumps(all_reviews, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # 打印总结
    total_time = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"全文审稿完成！")
    print("=" * 60)
    print(f"总章节: {args.end - args.start + 1}章")
    print(f"批次数: {len(batches)}")
    print(f"总耗时: {total_time:.0f}秒")
    print(f"\n报告位置:")
    print(f"  - 单批报告: {compare_dir}/审稿_第*批_*.md")
    print(f"  - 汇总报告: {summary_file}")
    print(f"  - 完整结果: {full_review_file}")


if __name__ == "__main__":
    main()
