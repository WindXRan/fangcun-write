"""
批量对比分析：188章分19批，每批10章，19个worker并行调用LLM编辑点评
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# API配置
API_URL = "https://api.deepseek.com/chat/completions"
API_KEY = os.environ.get("API_KEY")

# 编辑点评prompt
EDIT_PROMPT = """你是一位资深网文编辑，请对以下仿写内容进行专业点评。

## 评审维度

1. **洗稿风险**（0-10分，越低越好）
   - 0-3分：无风险，完全原创
   - 4-6分：低风险，有相似但可接受
   - 7-10分：高风险，有抄袭嫌疑

2. **文笔质量**（0-10分，越高越好）
   - 语言是否流畅自然
   - 是否有AI痕迹（路标词、直抒情等）
   - 描写是否生动

3. **情节节奏**（0-10分，越高越好）
   - 节奏是否合理
   - 悬念设置是否到位
   - 高潮点是否突出

4. **人设一致性**（0-10分，越高越好）
   - 角色性格是否前后一致
   - 对话是否符合人设
   - 行为逻辑是否合理

5. **可读性**（0-10分，越高越好）
   - 是否吸引读者
   - 是否有代入感
   - 是否想继续看下一章

## 评分规则

- **总分** = (文笔质量 + 情节节奏 + 人设一致性 + 可读性) / 4（不含洗稿风险）
- **是否可发布** = 洗稿风险 < 7 且 总分 >= 6

## 输出格式

请用以下JSON格式输出：

```json
{{
  "章节": "第X章",
  "洗稿风险": 分数,
  "文笔质量": 分数,
  "情节节奏": 分数,
  "人设一致性": 分数,
  "可读性": 分数,
  "总分": (文笔质量+情节节奏+人设一致性+可读性)/4,
  "问题": ["问题1", "问题2"],
  "建议": ["建议1", "建议2"],
  "是否可发布": true/false
}}
```

## 待评审内容

{content}
"""


def call_api(prompt):
    """调用LLM API"""
    if not API_KEY:
        raise ValueError("未设置API_KEY")
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位资深网文编辑，擅长质量评审和洗稿检测。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "stream": False
    }
    
    resp = requests.post(API_URL, headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def process_batch(batch_num, chapters_dir, output_dir):
    """处理一批章节（10章）"""
    start_ch = (batch_num - 1) * 10 + 1
    end_ch = min(batch_num * 10, 188)
    
    results = []
    for ch_num in range(start_ch, end_ch + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch_num:03d}.txt"
        if not ch_file.exists():
            continue
        
        content = ch_file.read_text(encoding='utf-8')
        
        # 截取前2000字进行评审（避免token过多）
        if len(content) > 2000:
            content = content[:2000] + "\n\n... (内容截断)"
        
        prompt = EDIT_PROMPT.format(content=content)
        
        try:
            result = call_api(prompt)
            # 解析JSON结果
            try:
                # 提取JSON部分
                json_match = result[result.find('{'):result.rfind('}')+1]
                result_data = json.loads(json_match)
                result_data['章节'] = f"第{ch_num}章"
                results.append(result_data)
            except:
                results.append({
                    "章节": f"第{ch_num}章",
                    "错误": "解析失败",
                    "原始结果": result[:500]
                })
        except Exception as e:
            results.append({
                "章节": f"第{ch_num}章",
                "错误": str(e)
            })
    
    # 保存批次结果
    output_file = Path(output_dir) / f"batch_{batch_num:02d}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 生成批次报告
    report_file = Path(output_dir) / f"batch_{batch_num:02d}_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 批次{batch_num} 编辑点评报告\n\n")
        f.write(f"章节范围：第{start_ch}-{end_ch}章\n\n")
        
        for r in results:
            f.write(f"## {r.get('章节', '未知')}\n\n")
            if '错误' in r:
                f.write(f"❌ 错误：{r['错误']}\n\n")
            else:
                f.write(f"- 洗稿风险：{r.get('洗稿风险', 'N/A')}/10\n")
                f.write(f"- 文笔质量：{r.get('文笔质量', 'N/A')}/10\n")
                f.write(f"- 情节节奏：{r.get('情节节奏', 'N/A')}/10\n")
                f.write(f"- 人设一致性：{r.get('人设一致性', 'N/A')}/10\n")
                f.write(f"- 可读性：{r.get('可读性', 'N/A')}/10\n")
                f.write(f"- **总分：{r.get('总分', 'N/A')}/10**\n")
                f.write(f"- 可发布：{'✅' if r.get('是否可发布') else '❌'}\n\n")
                
                if r.get('问题'):
                    f.write("**问题：**\n")
                    for p in r['问题']:
                        f.write(f"- {p}\n")
                    f.write("\n")
                
                if r.get('建议'):
                    f.write("**建议：**\n")
                    for s in r['建议']:
                        f.write(f"- {s}\n")
                    f.write("\n")
            
            f.write("---\n\n")
    
    return batch_num, len(results)


def main():
    chapters_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\projects\闻栖\女配一睁眼，失忆男主冷脸洗床单\rewrites\女配一睁眼，失忆男主冷脸洗床单\chapters"
    output_dir = r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\projects\闻栖\女配一睁眼，失忆男主冷脸洗床单\rewrites\女配一睁眼，失忆男主冷脸洗床单\edit_review"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 计算批次数
    total_chapters = 188
    batch_size = 10
    num_batches = (total_chapters + batch_size - 1) // batch_size
    
    print(f"开始编辑点评：{total_chapters}章，{num_batches}批，每批{batch_size}章")
    print(f"输出目录：{output_dir}")
    
    t0 = time.time()
    
    # 19个worker并行处理
    with ThreadPoolExecutor(max_workers=19) as executor:
        futures = {executor.submit(process_batch, i, chapters_dir, output_dir): i for i in range(1, num_batches + 1)}
        
        done = 0
        for future in as_completed(futures):
            batch_num, count = future.result()
            done += 1
            elapsed = time.time() - t0
            eta = elapsed / done * (num_batches - done)
            print(f"[{done}/{num_batches}] 批次{batch_num}完成 ({count}章) | {elapsed:.0f}s | ETA {eta:.0f}s")
    
    # 生成汇总报告
    summary_file = Path(output_dir) / "summary.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# 编辑点评汇总报告\n\n")
        f.write(f"- 总章节数：{total_chapters}\n")
        f.write(f"- 批次数：{num_batches}\n")
        f.write(f"- 总耗时：{time.time()-t0:.0f}秒\n\n")
        
        # 收集所有批次结果
        all_results = []
        for i in range(1, num_batches + 1):
            batch_file = Path(output_dir) / f"batch_{i:02d}.json"
            if batch_file.exists():
                with open(batch_file, 'r', encoding='utf-8') as bf:
                    batch_results = json.load(bf)
                    all_results.extend(batch_results)
        
        # 统计
        publishable = sum(1 for r in all_results if r.get('是否可发布'))
        high_risk = sum(1 for r in all_results if r.get('洗稿风险', 0) >= 7)
        low_score = sum(1 for r in all_results if r.get('总分', 10) < 6)
        
        f.write(f"- 可发布章节：{publishable}/{len(all_results)}\n")
        f.write(f"- 洗稿风险≥7：{high_risk}/{len(all_results)}\n")
        f.write(f"- 总分<6：{low_score}/{len(all_results)}\n\n")
        
        # 列出洗稿风险高的章节
        if high_risk > 0:
            f.write("## 洗稿风险高（≥7）的章节\n\n")
            for r in all_results:
                if r.get('洗稿风险', 0) >= 7:
                    f.write(f"- {r.get('章节', '未知')}：洗稿风险{r.get('洗稿风险')}/10\n")
            f.write("\n")
        
        # 列出不可发布章节
        non_publishable = [r for r in all_results if not r.get('是否可发布')]
        if non_publishable:
            f.write("## 不可发布章节\n\n")
            for r in non_publishable:
                reason = []
                if r.get('洗稿风险', 0) >= 7:
                    reason.append(f"洗稿风险{r.get('洗稿风险')}/10")
                if r.get('总分', 10) < 6:
                    reason.append(f"总分{r.get('总分', 'N/A')}/10")
                f.write(f"- {r.get('章节', '未知')}：{', '.join(reason)}\n")
    
    print(f"\n完成！汇总报告：{summary_file}")


if __name__ == '__main__':
    main()
