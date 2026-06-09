"""书籍审核工具：一次性审核全部章节"""
import os
import sys
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from prompt_loader import load_prompt

API_URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = "你是一名资深网文编辑，擅长审核小说质量。请严格按照要求的格式输出审核报告。"


def call_api(api_key, model, user_prompt, reasoning_effort="low", max_tokens=4096):
    """调用 API"""
    import requests
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": False,
        "reasoning_effort": reasoning_effort
    }
    resp = requests.post(API_URL, headers=headers, json=data, timeout=600)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def read_chapters(source_dir, start, end):
    """读取章节内容"""
    chapters = {}
    for ch in range(start, end + 1):
        patterns = [
            f"第{ch}章*.txt",
            f"第{ch:03d}章*.txt",
        ]
        for pattern in patterns:
            for f in sorted(Path(source_dir).glob(pattern)):
                content = f.read_text(encoding='utf-8')
                chapters[ch] = content
                break
    return chapters


def review_chapters(config, start, end, batch_size=10):
    """分批审核章节"""
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY")
    
    model = config.get("model", "deepseek-v4-flash")
    source_dir = config.get("source_dir", "")
    
    if not source_dir:
        # 自动查找源文目录
        author = config.get("author", "")
        source_book = config.get("source_book", "")
        base_dir = config.get("base_dir", os.getcwd())
        
        patterns = [
            f"projects/{author}/{source_book}/_cache/chapters/",
            f"projects/{author}/{source_book}/源文/",
        ]
        
        for pat in patterns:
            full_path = os.path.join(base_dir, pat)
            if os.path.isdir(full_path):
                source_dir = full_path
                break
    
    if not source_dir:
        print("[FAIL] 未找到源文目录")
        return None
    
    # 读取所有章节
    print(f"读取章节 {start}-{end}...")
    chapters = read_chapters(source_dir, start, end)
    print(f"已读取 {len(chapters)} 章")
    
    # 分批审核
    all_reviews = []
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n审核第{batch_start}-{batch_end}章...")
        
        # 合并本批次章节内容
        batch_content = ""
        for ch in range(batch_start, batch_end + 1):
            if ch in chapters:
                batch_content += f"\n\n## 第{ch}章\n\n{chapters[ch][:3000]}..."  # 每章最多3000字
        
        # 构建审核prompt
        user_prompt = f"""请审核以下小说章节（第{batch_start}-{batch_end}章）：

{batch_content}

---

请按以下维度审核，并给出评分（每项0-10分）：

1. **情节逻辑**（0-10分）：前后设定是否一致？剧情是否有漏洞？
2. **人物塑造**（0-10分）：角色行为是否合理？人设是否稳定？
3. **文笔节奏**（0-10分）：语言表达质量？节奏控制？
4. **网文技法**（0-10分）：钩子设置？情绪线？

输出格式：
```
## 第{batch_start}-{batch_end}章审核

### 评分
- 情节逻辑：X/10
- 人物塑造：X/10
- 文笔节奏：X/10
- 网文技法：X/10
- 综合：X/10

### 问题
1. [问题描述]（涉及章节：第X章）

### 亮点
1. [亮点描述]（涉及章节：第X章）
```"""
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
                "stream": False
            }
            resp = requests.post(API_URL, headers=headers, json=data, timeout=600)
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            all_reviews.append(result)
            print(f"  [OK] 第{batch_start}-{batch_end}章审核完成")
        except Exception as e:
            print(f"  [FAIL] 第{batch_start}-{batch_end}章审核失败: {e}")
    
    return all_reviews


def generate_report(reviews, book_name, start, end):
    """生成完整审核报告"""
    report = f"""# 《{book_name}》审核报告

## 一、作品概况
| 项目 | 内容 |
|------|------|
| 书名 | {book_name} |
| 审核范围 | 第{start}-{end}章 |

## 二、审核结果

"""
    for i, review in enumerate(reviews):
        report += f"\n{review}\n\n"
    
    return report


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="书籍审核工具")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1, help="起始章节")
    parser.add_argument("--end", type=int, default=188, help="结束章节")
    parser.add_argument("--batch-size", type=int, default=10, help="每批审核章节数")
    
    args = parser.parse_args()
    
    # 加载配置
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    config.setdefault("base_dir", os.getcwd())
    
    print(f"审核 {config.get('book_name', '未知')} 第{args.start}-{args.end}章")
    
    # 执行审核
    reviews = review_chapters(config, args.start, args.end, args.batch_size)
    
    if reviews:
        # 生成报告
        report = generate_report(reviews, config.get('book_name', '未知'), args.start, args.end)
        
        # 保存报告
        rewrites_dir = config.get("rewrites_dir", "")
        if rewrites_dir:
            review_dir = os.path.join(rewrites_dir, "review")
            os.makedirs(review_dir, exist_ok=True)
            report_file = os.path.join(review_dir, f"review_{args.start}-{args.end}.md")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n审核报告已保存: {report_file}")
        else:
            print("\n审核报告:")
            print(report)


if __name__ == "__main__":
    main()
