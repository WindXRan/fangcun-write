"""自动对比：调用API分析新书和源文的抄袭风险"""
import os
import sys
import json
import requests
from pathlib import Path

API_URL = "https://api.deepseek.com/chat/completions"
SYSTEM_PROMPT = """你是资深网文编辑，负责评估仿写作品的质量。

版本A是源文（原作），版本B是仿写作品。请基于这个前提进行分析。

## 差异分析（四维评估）
1. **叙事风格**：开篇方式、视角、基调、幽默来源
2. **节奏控制**：信息密度、铺垫长度、高潮位置
3. **人设塑造**：角色层次感、行为动机、互动细节
4. **信息密度**：信息是否服务于情节和人物关系

## 抄袭风险评估（四维）
1. **情节走向**：核心情节链是否高度相似
2. **关键场景/对话**：核心桥段的功能和设计是否雷同
3. **人设/关系框架**：三角关系、角色定位是否照搬
4. **差异化程度**：局部细节创新是否足够脱离源文模式

## 输出格式
1. 核心差异（2-3句话）
2. 抄袭风险等级（低/中/高）
3. 具体雷同点（情节走向、关键场景、人设框架）
4. 改进建议（针对高风险点的具体修改方案）
5. Prompt优化建议：根据仿写成品暴露的问题，反推写作prompt应该如何调整（2-3条具体可执行的修改建议）"""


def call_api(api_key, model, user_prompt, reasoning_effort="low", max_tokens=4096):
    """调用 DeepSeek API。"""
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
    resp = requests.post(API_URL, headers=headers, json=data, timeout=300)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_compare(config, start, end):
    """运行对比分析"""
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY")
    
    rewrites_dir = config["rewrites_dir"]
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    # 读取新书章节
    new_book_text = ""
    for ch in range(start, end + 1):
        ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
        if ch_file.exists():
            new_book_text += f"\n\n## 新书第{ch}章\n\n{ch_file.read_text(encoding='utf-8')}"
    
    # 读取源文章节
    source_text = ""
    for ch in range(start, end + 1):
        import glob
        patterns = [
            f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
            f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        ]
        for pat in patterns:
            for f in sorted(glob.glob(os.path.join(base_dir, pat))):
                source_text += f"\n\n## 源文第{ch}章\n\n{Path(f).read_text(encoding='utf-8')}"
                break
    
    # 构建prompt
    user_prompt = f"""请对比以下两份文本（版本A是源文，版本B是仿写作品）：

# 版本A（源文）
{source_text}

# 版本B（仿写）
{new_book_text}

---

请从以下角度分析：

1. **核心差异**（2-3句话）：版本B和版本A最大的不同是什么？
2. **质量判断**：哪个版本阅读体验更好？好在哪？各自的硬伤是什么？
3. **抄袭风险**：两版是否存在情节骨架/关键台词/人设框架的雷同？给出风险等级（低/中/高），若有雷同指出具体哪里像。

**必须逐项检查以下具体元素**：
4. **配角名检查**：两版是否有相同的配角名？
5. **地名检查**：两版是否有相同的地名？
6. **道具/意象检查**：两版是否有相同的道具或意象？
7. **情节装置检查**：两版是否有相同的关键情节装置？
8. **Prompt优化建议**：根据仿写成品暴露的问题，反推写作prompt应该如何调整（2-3条具体可执行的修改建议）"""
    
    # 调用API
    print("  [COMPARE] 正在分析...")
    result = call_api(api_key, "deepseek-v4-flash", user_prompt)
    
    # 保存结果
    compare_dir = Path(rewrites_dir) / "compare"
    compare_dir.mkdir(exist_ok=True)
    result_file = compare_dir / f"auto_compare_{start}-{end}.md"
    result_file.write_text(f"# 自动对比分析（第{start}-{end}章）\n\n{result}", encoding='utf-8')
    
    print(f"  [OK] 对比完成 → {result_file}")
    
    # 提取风险等级
    if "高" in result and "风险" in result:
        risk = "高"
    elif "中" in result and "风险" in result:
        risk = "中"
    else:
        risk = "低"
    
    return result, risk


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="自动对比分析")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=10, help="结束章")
    parser.add_argument("--batch", type=int, default=10, help="每批章数（默认10章）")
    
    args = parser.parse_args()
    
    # 读取配置
    with open(args.config, encoding='utf-8') as f:
        config = json.load(f)
    
    config["base_dir"] = os.path.dirname(args.config)
    if not config.get("api_key"):
        config["api_key"] = os.environ.get("API_KEY")
    
    # 分批处理
    batch_size = args.batch
    for batch_start in range(args.start, args.end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, args.end)
        print(f"\n对比第{batch_start}-{batch_end}章...")
        try:
            result, risk = run_compare(config, batch_start, batch_end)
            print(f"  风险等级: {risk}")
        except Exception as e:
            print(f"  [FAIL] {e}")
