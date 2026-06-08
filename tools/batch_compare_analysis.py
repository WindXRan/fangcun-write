#!/usr/bin/env python3
"""分批对比分析脚本：每次处理10章，调用AI进行深度评估"""

import re
import sys
import time
from pathlib import Path
from openai import OpenAI

def extract_chapters(content: str) -> dict:
    """提取所有章节内容，按章节号分组"""
    # 分割成版本A和版本B
    parts = content.split('# 版本B（新书）')
    if len(parts) != 2:
        print("错误：无法分割版本A和版本B")
        return {}
    
    version_a = parts[0]
    version_b = parts[1]
    
    # 提取章节内容
    chapters = {}
    
    # 提取版本A的章节
    a_chapters = re.split(r'## 第(\d+)章', version_a)
    for i in range(1, len(a_chapters), 2):
        ch_num = int(a_chapters[i])
        ch_content = a_chapters[i+1].strip() if i+1 < len(a_chapters) else ""
        if ch_num not in chapters:
            chapters[ch_num] = {'a': '', 'b': ''}
        chapters[ch_num]['a'] = ch_content
    
    # 提取版本B的章节
    b_chapters = re.split(r'## 第(\d+)章', version_b)
    for i in range(1, len(b_chapters), 2):
        ch_num = int(b_chapters[i])
        ch_content = b_chapters[i+1].strip() if i+1 < len(b_chapters) else ""
        if ch_num not in chapters:
            chapters[ch_num] = {'a': '', 'b': ''}
        chapters[ch_num]['b'] = ch_content
    
    return chapters

def build_batch_prompt(chapters: dict, start: int, end: int) -> str:
    """构建某批次的分析提示"""
    prompt = """请你以资深网文编辑的身份，对下面两份文本进行对比分析。

## 分析要求

1. **差异分析**：版本A和版本B在叙事风格、节奏控制、人设塑造、信息密度上有什么核心差异？
2. **优劣评估**：分别指出两版各自的优势和不足。哪个版本的阅读体验更好？好在哪里？
3. **市场判断**：从网文市场的角度，哪一版更容易留住读者？为什么？
4. **改进建议**：给较弱的那一版提出具体修改方向。
5. **抄袭风险评估**：逐章对比两版的具体情节、对话、场景设计，判断是否存在抄袭嫌疑。重点关注：(1) 情节走向是否高度雷同 (2) 关键场景/对话是否有大段相似 (3) 人设/关系框架是否照搬 (4) 两版的差异化程度是否足够。给出具体的风险等级（低/中/高）和需要重点修改的段落。

请逐章分析，最后给出总体评价。**不要猜测哪版是仿写**，仅基于文本本身做判断。

---

"""
    
    for ch_num in range(start, min(end + 1, max(chapters.keys()) + 1)):
        if ch_num in chapters:
            prompt += f"# 版本A（源文）\n\n## 第{ch_num}章\n\n{chapters[ch_num]['a']}\n\n"
            prompt += f"# 版本B（新书）\n\n## 第{ch_num}章\n\n{chapters[ch_num]['b']}\n\n"
    
    return prompt

def analyze_with_ai(prompt: str, api_key: str, batch_num: int, base_url: str = "https://api.deepseek.com") -> str:
    """调用AI进行分析"""
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一位资深网文编辑，擅长分析小说的叙事风格、节奏控制、人设塑造和市场潜力。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"分析失败：{str(e)}"

def main():
    # 配置
    base_dir = Path(r"C:\Users\Administrator\Documents\trae_projects\AI网文小说项目")
    compare_file = base_dir / "projects" / "闻栖" / "女配一睁眼，失忆男主冷脸洗床单" / "rewrites" / "女配一睁眼，失忆男主冷脸洗床单" / "compare" / "对比_1-188_AI分析.md"
    output_dir = base_dir / "projects" / "闻栖" / "女配一睁眼，失忆男主冷脸洗床单" / "rewrites" / "女配一睁眼，失忆男主冷脸洗床单" / "compare" / "analysis"
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    # 从配置文件读取API密钥
    api_key = None
    config_file = base_dir / "configs" / "config_rewrite_闻栖_女配.json"
    
    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            api_key = config.get('api_key')
    except Exception as e:
        print(f"读取配置文件失败：{e}")
    
    if not api_key:
        print("错误：未找到API密钥")
        print(f"请在 {config_file} 中配置 api_key")
        sys.exit(1)
    
    # 读取对比文件
    print(f"读取对比文件：{compare_file}")
    with open(compare_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取章节
    print("提取章节内容...")
    chapters = extract_chapters(content)
    print(f"共提取 {len(chapters)} 章")
    
    # 分批处理
    batch_size = 10
    total_chapters = len(chapters)
    batch_num = 1
    
    for start in range(1, total_chapters + 1, batch_size):
        end = min(start + batch_size - 1, total_chapters)
        print(f"\n处理第 {start}-{end} 章（批次 {batch_num}）...")
        
        # 构建提示
        prompt = build_batch_prompt(chapters, start, end)
        
        # 调用AI分析
        print(f"调用AI分析中...")
        result = analyze_with_ai(prompt, api_key, batch_num, "https://api.deepseek.com")
        
        # 保存结果
        output_file = output_dir / f"analysis_{start}-{end}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 仿写对比分析：第{start}-{end}章\n\n")
            f.write(result)
        
        print(f"分析完成，保存至：{output_file.name}")
        
        # 避免API限流
        if batch_num < (total_chapters + batch_size - 1) // batch_size:
            print("等待5秒避免API限流...")
            time.sleep(5)
        
        batch_num += 1
    
    print(f"\n所有分析完成！共 {batch_num - 1} 个批次")
    print(f"结果保存在：{output_dir}")

if __name__ == "__main__":
    main()
