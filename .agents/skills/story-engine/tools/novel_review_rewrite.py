"""
大规模小说审改架构 - 核心模块
功能：依赖DAG生成、波次执行器、策略分化、验证闭环
"""
import os
import sys
import json
import time
import requests
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))


# ============================================================
# 模块1：依赖DAG生成
# ============================================================

def generate_dependency_dag(api_key, api_url, model, review_reports, concept_text):
    """从审核报告生成修改依赖DAG。
    
    Args:
        api_key: API密钥
        api_url: API地址
        model: 模型名称
        review_reports: 审核报告列表
        concept_text: 小说设定
        
    Returns:
        dict: DAG结构，包含波次计划
    """
    # 合并所有审核报告
    all_reviews = "\n\n---\n\n".join([
        f"## 第{r['batch']}批\n\n{r['content'][:2000]}"
        for r in review_reports
    ])
    
    prompt = f"""你是小说审改专家。请分析以下审核报告，生成修改依赖DAG。

【小说设定】
{concept_text[:1500]}

【审核报告】
{all_reviews}

【任务】
请分析所有问题，生成修改依赖DAG，按波次执行：

1. **波次1：设定统一**（串行决策+并行替换）
   - 人物名字统一
   - 数字/金额统一
   - 时间线统一
   - 地点统一

2. **波次2：结构修复**（可并行）
   - 逻辑矛盾修复
   - 时间线错位修复
   - 章节重写/移位

3. **波次3：基建补建**（可与波次2并行）
   - 总纲补写
   - 人物设定表
   - 章纲补写

4. **波次4：批量润色**（完全并行）
   - 去AI味
   - 增钩子
   - 对话润色
   - 字数均衡

【输出格式】
```json
{{
  "summary": "问题总数：X个，P0: X个，P1: X个，P2: X个",
  "waves": [
    {{
      "wave": 1,
      "name": "设定统一",
      "parallel": false,
      "tasks": [
        {{
          "id": "fix_name_1",
          "type": "setting",
          "action": "全局替换",
          "description": "统一人物名字",
          "pattern": "旧名字",
          "replacement": "新名字",
          "affected_chapters": [1, 5, 10],
          "depends_on": []
        }}
      ]
    }},
    {{
      "wave": 2,
      "name": "结构修复",
      "parallel": true,
      "tasks": [
        {{
          "id": "fix_logic_1",
          "type": "structure",
          "action": "重写",
          "description": "修复逻辑矛盾",
          "chapter": 102,
          "instruction": "具体修改指令",
          "depends_on": ["fix_name_1"]
        }}
      ]
    }}
  ]
}}
```

请只输出JSON，不要其他内容。"""

    try:
        result = call_api(api_key, api_url, model, prompt, 
                         system_prompt="你是小说审改专家，擅长分析问题并生成修改计划。",
                         max_tokens=6000, temperature=0.3)
        
        # 提取JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            dag = json.loads(json_match.group())
            return dag
        else:
            print("[WARN] 无法解析DAG JSON，使用默认DAG")
            return generate_default_dag(review_reports)
            
    except Exception as e:
        print(f"[WARN] DAG生成失败: {e}，使用默认DAG")
        return generate_default_dag(review_reports)


def generate_default_dag(review_reports):
    """生成默认DAG（当API调用失败时使用）。"""
    # 收集所有章节
    all_chapters = set()
    for r in review_reports:
        all_chapters.update(r.get('chapters', []))
    
    return {
        "summary": "默认DAG：批量润色",
        "waves": [
            {
                "wave": 1,
                "name": "批量润色",
                "parallel": True,
                "tasks": [
                    {
                        "id": "batch_polish",
                        "type": "polish",
                        "action": "润色",
                        "description": "批量润色所有章节",
                        "affected_chapters": sorted(list(all_chapters)),
                        "depends_on": []
                    }
                ]
            }
        ]
    }


# ============================================================
# 模块2：波次执行器
# ============================================================

def execute_wave(api_key, api_url, model, wave, chapters_dir, concept_text, workers=5):
    """执行单个波次的修改任务。
    
    Args:
        api_key: API密钥
        api_url: API地址
        model: 模型名称
        wave: 波次配置
        chapters_dir: 章节目录
        concept_text: 小说设定
        workers: 并行数
        
    Returns:
        dict: 执行结果
    """
    wave_name = wave['name']
    tasks = wave['tasks']
    parallel = wave.get('parallel', True)
    
    print(f"\n{'=' * 50}")
    print(f"执行波次：{wave_name}")
    print(f"任务数：{len(tasks)}")
    print(f"并行策略：{'并行' if parallel else '串行'}")
    print("=" * 50)
    
    results = []
    t_start = time.time()
    
    if parallel:
        # 并行执行
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(execute_task, api_key, api_url, model, task, chapters_dir, concept_text): task
                for task in tasks
            }
            
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  [OK] {task['id']}: {result['status']}")
                except Exception as e:
                    results.append({'id': task['id'], 'status': 'FAIL', 'reason': str(e)})
                    print(f"  [FAIL] {task['id']}: {e}")
    else:
        # 串行执行
        for task in tasks:
            try:
                result = execute_task(api_key, api_url, model, task, chapters_dir, concept_text)
                results.append(result)
                print(f"  [OK] {task['id']}: {result['status']}")
            except Exception as e:
                results.append({'id': task['id'], 'status': 'FAIL', 'reason': str(e)})
                print(f"  [FAIL] {task['id']}: {e}")
    
    total_time = time.time() - t_start
    
    return {
        'wave': wave_name,
        'results': results,
        'total_time': total_time
    }


def execute_task(api_key, api_url, model, task, chapters_dir, concept_text):
    """执行单个修改任务。
    
    Args:
        api_key: API密钥
        api_url: API地址
        model: 模型名称
        task: 任务配置
        chapters_dir: 章节目录
        concept_text: 小说设定
        
    Returns:
        dict: 执行结果
    """
    task_type = task['type']
    task_id = task['id']
    
    if task_type == 'setting':
        # 设定类：全局替换
        return execute_setting_task(api_key, api_url, model, task, chapters_dir)
    elif task_type == 'structure':
        # 结构类：单章重写
        return execute_structure_task(api_key, api_url, model, task, chapters_dir, concept_text)
    elif task_type == 'polish':
        # 润色类：批量润色
        return execute_polish_task(api_key, api_url, model, task, chapters_dir, concept_text)
    else:
        return {'id': task_id, 'status': 'SKIP', 'reason': f'未知任务类型: {task_type}'}


def execute_setting_task(api_key, api_url, model, task, chapters_dir):
    """执行设定类任务（全局替换）。"""
    task_id = task['id']
    pattern = task.get('pattern', '')
    replacement = task.get('replacement', '')
    affected_chapters = task.get('affected_chapters', [])
    
    if not pattern or not replacement:
        return {'id': task_id, 'status': 'SKIP', 'reason': '缺少pattern或replacement'}
    
    fixed_count = 0
    for ch in affected_chapters:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        text = ch_file.read_text(encoding='utf-8')
        if pattern in text:
            new_text = text.replace(pattern, replacement)
            ch_file.write_text(new_text, encoding='utf-8')
            fixed_count += 1
    
    return {'id': task_id, 'status': 'FIXED', 'fixed_count': fixed_count}


def execute_structure_task(api_key, api_url, model, task, chapters_dir, concept_text):
    """执行结构类任务（单章重写）。"""
    task_id = task['id']
    chapter = task.get('chapter')
    instruction = task.get('instruction', '')
    
    if not chapter:
        return {'id': task_id, 'status': 'SKIP', 'reason': '缺少chapter'}
    
    ch_file = Path(chapters_dir) / f"ch_{chapter:03d}.txt"
    if not ch_file.exists():
        return {'id': task_id, 'status': 'SKIP', 'reason': f'章节{chapter}不存在'}
    
    original_text = ch_file.read_text(encoding='utf-8')
    orig_chars = len(original_text.replace('\n', '').replace(' ', ''))
    
    # 读取上下文（前后各1章）
    context_before = ""
    context_after = ""
    
    prev_file = Path(chapters_dir) / f"ch_{chapter-1:03d}.txt"
    if prev_file.exists():
        context_before = prev_file.read_text(encoding='utf-8')[-500:]
    
    next_file = Path(chapters_dir) / f"ch_{chapter+1:03d}.txt"
    if next_file.exists():
        context_after = next_file.read_text(encoding='utf-8')[:500]
    
    prompt = f"""你是专业网文写手。请根据修改指令重写以下章节。

【小说设定】
{concept_text[:1000]}

【修改指令】
{instruction}

【上一章结尾（用于承接）】
{context_before}

【当前章节（第{chapter}章）】
{original_text}

【下一章开头（用于衔接）】
{context_after}

【修改要求】
1. 根据修改指令重写
2. 保持与前后章的衔接
3. 字数控制在原文±10%以内（{int(orig_chars*0.9)}~{int(orig_chars*1.1)}字）
4. 直接输出重写后的完整章节

【输出格式】
第{chapter}章 [章节标题]

[重写后的完整正文]
"""

    try:
        new_text = call_api(api_key, api_url, model, prompt,
                           system_prompt="你是专业网文写手，擅长根据指令重写章节。",
                           max_tokens=8000, temperature=0.8)
        
        new_chars = len(new_text.replace('\n', '').replace(' ', ''))
        
        # 检查字数差异
        if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.15:
            return {'id': task_id, 'status': 'SKIP', 'reason': f'字数差异过大 ({orig_chars}→{new_chars})'}
        
        ch_file.write_text(new_text, encoding='utf-8')
        return {'id': task_id, 'status': 'FIXED', 'orig': orig_chars, 'new': new_chars}
        
    except Exception as e:
        return {'id': task_id, 'status': 'FAIL', 'reason': str(e)}


def execute_polish_task(api_key, api_url, model, task, chapters_dir, concept_text):
    """执行润色类任务（批量润色）。"""
    task_id = task['id']
    affected_chapters = task.get('affected_chapters', [])
    
    fixed_count = 0
    for ch in affected_chapters:
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        original_text = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original_text.replace('\n', '').replace(' ', ''))
        
        prompt = f"""你是专业网文写手。请润色以下章节，提升文笔质量。

【当前章节（第{ch}章）】
{original_text}

【润色要求】
1. 删除AI高频词：「……般的」「仿佛」「似乎」「不禁」「忍不住」
2. 删除连续3句以上的排比句
3. 检查对话是否像人话（太书面化则改口语化）
4. 保持原文情节和人物不变，仅做语言层优化
5. 字数控制在原文±5%以内

【输出格式】
第{ch}章 [章节标题]

[润色后的完整正文]
"""

        try:
            new_text = call_api(api_key, api_url, model, prompt,
                               system_prompt="你是专业网文写手，擅长润色文笔。",
                               max_tokens=8000, temperature=0.7)
            
            new_chars = len(new_text.replace('\n', '').replace(' ', ''))
            
            # 检查字数差异
            if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.1:
                continue
            
            ch_file.write_text(new_text, encoding='utf-8')
            fixed_count += 1
            
        except Exception as e:
            print(f"    [FAIL] ch{ch}: {e}")
    
    return {'id': task_id, 'status': 'FIXED', 'fixed_count': fixed_count}


# ============================================================
# 模块3：验证闭环
# ============================================================

def validate_changes(api_key, api_url, model, chapters_dir, compare_dir, original_issues, sample_rate=0.1):
    """验证修改是否有效，是否引入新问题。
    
    Args:
        api_key: API密钥
        api_url: API地址
        model: 模型名称
        chapters_dir: 章节目录
        compare_dir: 对比目录
        original_issues: 原始问题列表
        sample_rate: 抽样率
        
    Returns:
        dict: 验证结果
    """
    print(f"\n{'=' * 50}")
    print("验证修改效果")
    print("=" * 50)
    
    # 抽样检查
    chapter_files = sorted(Path(chapters_dir).glob("ch_*.txt"))
    sample_size = max(5, int(len(chapter_files) * sample_rate))
    sample_files = chapter_files[::len(chapter_files)//sample_size][:sample_size]
    
    print(f"抽样检查：{len(sample_files)}章")
    
    # 读取抽样章节
    sample_content = []
    for f in sample_files:
        ch_num = int(f.stem.split('_')[1])
        content = f.read_text(encoding='utf-8')
        sample_content.append(f"## 第{ch_num}章\n\n{content[:1000]}")
    
    merged = "\n\n---\n\n".join(sample_content)
    
    # 检查原始问题是否已修复
    issues_summary = "\n".join([f"- {i}" for i in original_issues[:20]])
    
    prompt = f"""请检查以下章节，验证原始问题是否已修复，是否引入新问题。

【原始问题】
{issues_summary}

【抽样章节】
{merged}

【检查要求】
1. 原始问题是否已修复？
2. 是否引入新问题？
3. 整体质量是否提升？

【输出格式】
## 验证报告

### 原始问题修复情况
| 问题 | 状态 | 说明 |
|------|------|------|
| ... | ✅已修复/❌未修复 | ... |

### 新发现问题
| 问题 | 严重程度 | 涉及章节 |
|------|----------|----------|
| ... | P0/P1/P2 | ... |

### 整体评价
- 质量提升：是/否
- 建议：继续/回退/完成
"""

    try:
        result = call_api(api_key, api_url, model, prompt,
                         system_prompt="你是小说审核专家，擅长验证修改效果。",
                         max_tokens=3000, temperature=0.3)
        
        # 保存验证报告
        report_file = Path(compare_dir) / "验证报告.md"
        report_file.write_text(result, encoding='utf-8')
        
        print(f"验证报告已保存：{report_file}")
        
        return {
            'status': 'completed',
            'report': result,
            'sample_size': len(sample_files)
        }
        
    except Exception as e:
        return {'status': 'failed', 'reason': str(e)}


# ============================================================
# 工具函数
# ============================================================

def call_api(api_key, api_url, model, user_prompt, system_prompt=None, max_tokens=4000, temperature=0.7):
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


# ============================================================
# 主流程
# ============================================================

def full_review_and_rewrite(config, start, end, batch_size=20, workers=5, max_rounds=3):
    """完整的审改流程：审核→规划→执行→验证。
    
    Args:
        config: 配置
        start: 起始章
        end: 结束章
        batch_size: 每批章节数
        workers: 并行数
        max_rounds: 最大验证轮数
    """
    import subprocess
    
    rewrites_dir = config['rewrites_dir']
    chapters_dir = f"{rewrites_dir}/chapters"
    compare_dir = f"{rewrites_dir}/compare"
    os.makedirs(compare_dir, exist_ok=True)
    
    # 清理所有旧报告
    for old_file in Path(compare_dir).glob("*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("*.json"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("*.txt"):
        old_file.unlink()
    print("已清理所有旧报告")
    
    # API配置
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com/v1") + "/chat/completions"
    model = config.get("model", "deepseek-chat")
    
    # 读取设定
    concept_path = Path(rewrites_dir) / 'concept.md'
    concept_text = ""
    if concept_path.exists():
        concept_text = concept_path.read_text(encoding='utf-8')
    
    print(f"\n{'=' * 60}")
    print(f"大规模小说审改 (ch{start}-{end})")
    print("=" * 60)
    
    # ============ Phase 1: 全局体检 ============
    print(f"\n{'=' * 50}")
    print("Phase 1: 全局体检")
    print("=" * 50)
    
    # 调用full_review.py进行分片审核
    config_file = config.get("config_file", "configs/config_fenshou_rewrite.json")
    cmd = [
        "python", ".agents/skills/story-engine/tools/full_review.py",
        "--config", config_file,
        "--start", str(start),
        "--end", str(end),
        "--batch-size", str(batch_size),
        "--workers", str(workers)
    ]
    
    print("运行全文审稿...")
    subprocess.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=1800)
    
    # 加载审核报告
    review_reports = []
    for f in sorted(Path(compare_dir).glob("审稿_第*批_*.md")):
        content = f.read_text(encoding='utf-8')
        name = f.stem
        parts = name.split('_')
        if len(parts) >= 3:
            batch_num = int(parts[1].replace('第', '').replace('批', ''))
            chapters_range = parts[2]
            batch_start, batch_end = map(int, chapters_range.split('-'))
            review_reports.append({
                'batch': batch_num,
                'start': batch_start,
                'end': batch_end,
                'content': content,
                'chapters': list(range(batch_start, batch_end + 1))
            })
    
    # 加载汇总报告
    summary_file = Path(compare_dir) / "全文审稿汇总报告.md"
    summary_text = ""
    if summary_file.exists():
        summary_text = summary_file.read_text(encoding='utf-8')
    
    print(f"加载审核报告：{len(review_reports)}批")
    
    # ============ Phase 2: 修改规划 ============
    print(f"\n{'=' * 50}")
    print("Phase 2: 修改规划（生成DAG）")
    print("=" * 50)
    
    dag = generate_dependency_dag(api_key, api_url, model, review_reports, concept_text)
    
    # 保存DAG
    dag_file = Path(compare_dir) / "修改DAG.json"
    dag_file.write_text(json.dumps(dag, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"DAG已保存：{dag_file}")
    print(f"问题摘要：{dag.get('summary', '未知')}")
    
    # ============ Phase 3: 执行修改 ============
    print(f"\n{'=' * 50}")
    print("Phase 3: 执行修改")
    print("=" * 50)
    
    waves = dag.get('waves', [])
    all_results = []
    
    for wave in waves:
        result = execute_wave(api_key, api_url, model, wave, chapters_dir, concept_text, workers)
        all_results.append(result)
    
    # 保存执行结果
    results_file = Path(compare_dir) / "修改执行结果.json"
    results_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"执行结果已保存：{results_file}")
    
    # ============ Phase 4: 验证闭环 ============
    for round_num in range(1, max_rounds + 1):
        print(f"\n{'=' * 50}")
        print(f"Phase 4: 验证（第{round_num}轮）")
        print("=" * 50)
        
        # 提取原始问题
        original_issues = []
        for r in review_reports:
            # 简单提取：每行以"问题"或"Issue"开头的
            for line in r['content'].split('\n'):
                if '问题' in line or 'Issue' in line or '矛盾' in line:
                    original_issues.append(line.strip())
        
        # 验证
        validation = validate_changes(
            api_key, api_url, model,
            chapters_dir, compare_dir,
            original_issues, sample_rate=0.1
        )
        
        if validation['status'] == 'completed':
            report = validation.get('report', '')
            
            # 检查是否需要继续
            if '继续' in report or '回退' in report:
                print(f"验证结果：需要继续修改")
                if round_num < max_rounds:
                    print("重新执行修改...")
                    for wave in waves:
                        execute_wave(api_key, api_url, model, wave, chapters_dir, concept_text, workers)
                else:
                    print("达到最大轮数，停止")
                    break
            else:
                print("验证结果：修改完成")
                break
        else:
            print(f"验证失败：{validation.get('reason', '未知')}")
            break
    
    # ============ 完成 ============
    print(f"\n{'=' * 60}")
    print("审改完成！")
    print("=" * 60)
    print(f"总章节：{end - start + 1}章")
    print(f"审核批次：{len(review_reports)}批")
    print(f"修改波次：{len(waves)}波")
    print(f"验证轮数：{round_num}轮")
    print(f"\n报告位置：")
    print(f"  - 审核报告：{compare_dir}/审稿_*.md")
    print(f"  - 汇总报告：{summary_file}")
    print(f"  - 修改DAG：{dag_file}")
    print(f"  - 执行结果：{results_file}")
    print(f"  - 验证报告：{compare_dir}/验证报告.md")


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="大规模小说审改架构")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=None, help="结束章")
    parser.add_argument("--batch-size", type=int, default=20, help="每批章节数")
    parser.add_argument("--workers", type=int, default=5, help="并行数")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大验证轮数")
    
    args = parser.parse_args()
    
    # 读取配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['config_file'] = args.config
    
    # 自动检测结束章节
    if args.end is None:
        rewrites_dir = config['rewrites_dir']
        chapters_dir = f"{rewrites_dir}/chapters"
        chapter_files = sorted(Path(chapters_dir).glob("ch_*.txt"))
        if chapter_files:
            args.end = int(chapter_files[-1].stem.split('_')[1])
        else:
            print("未找到章节文件")
            sys.exit(1)
    
    # 执行审改
    full_review_and_rewrite(
        config, args.start, args.end,
        batch_size=args.batch_size,
        workers=args.workers,
        max_rounds=args.max_rounds
    )


if __name__ == "__main__":
    main()
