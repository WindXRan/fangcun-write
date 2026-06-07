"""
API批量调用脚本：直接调用LLM API批量生成内容
支持：OpenAI、Anthropic、DeepSeek等
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def load_prompt(template_path, replacements):
    """加载prompt模板并替换变量。"""
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, value in replacements.items():
        content = content.replace(f'{{{key}}}', str(value))
    return content


def call_openai_api(api_key, model, system_prompt, user_prompt, base_url=None):
    """调用OpenAI API。"""
    if not HAS_OPENAI:
        raise ImportError("请安装openai: pip install openai")
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,
        max_tokens=4096
    )
    return response.choices[0].message.content


def call_anthropic_api(api_key, model, system_prompt, user_prompt):
    """调用Anthropic API。"""
    if not HAS_ANTHROPIC:
        raise ImportError("请安装anthropic: pip install anthropic")
    
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.content[0].text


def call_generic_api(api_url, api_key, model, system_prompt, user_prompt):
    """调用通用API（OpenAI兼容格式）。"""
    if not HAS_REQUESTS:
        raise ImportError("请安装requests: pip install requests")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 4096
    }
    response = requests.post(api_url, headers=headers, json=data, timeout=300)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_deepseek_api(api_key, model, system_prompt, user_prompt, reasoning_effort="low"):
    """直接调用DeepSeek API（不依赖openai库）。"""
    if not HAS_REQUESTS:
        raise ImportError("请安装requests: pip install requests")
    
    api_url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 4096,
        "stream": False,
        "reasoning_effort": reasoning_effort
    }
    response = requests.post(api_url, headers=headers, json=data, timeout=600)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_chapter(config, chapter_num, prompt_type="write-chapter"):
    """生成单章内容。"""
    # 构建替换变量
    replacements = {
        "新书名": config["book_name"],
        "N": chapter_num,
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }
    
    # 加载prompt
    prompt_path = Path(config["prompts_dir"]) / f"{prompt_type}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt文件不存在: {prompt_path}")
    
    user_prompt = load_prompt(prompt_path, replacements)
    system_prompt = config.get("system_prompt", "你是一个专业的网文写手。")
    
    # 调用API
    provider = config.get("provider", "openai")
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    
    if not api_key:
        raise ValueError("未配置API_KEY")
    
    if provider == "deepseek":
        # DeepSeek API调用
        result = call_deepseek_api(
            api_key,
            config.get("model", "deepseek-v4-pro"),
            system_prompt,
            user_prompt,
            reasoning_effort=config.get("reasoning_effort", "low")
        )
    elif provider == "openai":
        result = call_openai_api(
            api_key, 
            config.get("model", "gpt-4"),
            system_prompt, 
            user_prompt,
            config.get("base_url")
        )
    elif provider == "anthropic":
        result = call_anthropic_api(
            api_key,
            config.get("model", "claude-3-opus-20240229"),
            system_prompt,
            user_prompt
        )
    else:
        result = call_generic_api(
            config.get("api_url", "https://api.openai.com/v1/chat/completions"),
            api_key,
            config.get("model", "gpt-4"),
            system_prompt,
            user_prompt
        )
    
    return result


def save_chapter(output_dir, chapter_num, content, prompt_type="write-chapter"):
    """保存章节内容。"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 根据prompt_type确定文件名
    if prompt_type == "plot-guide":
        filename = f"plot_guide_{chapter_num}.md"
    elif prompt_type == "style-guide":
        filename = f"style_guide_{chapter_num}.md"
    elif prompt_type == "arc-concept":
        filename = "新书设定.md"
    elif prompt_type == "arc-skeleton-core":
        filename = "全书弧线.md"
    else:
        filename = f"第{chapter_num}章.txt"
    
    output_path = Path(output_dir) / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return str(output_path)


def batch_generate(config, start_chapter, end_chapter, max_workers=10, prompt_type="write-chapter"):
    """批量生成章节。"""
    results = {}
    errors = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for ch in range(start_chapter, end_chapter + 1):
            future = executor.submit(generate_chapter, config, ch, prompt_type)
            futures[future] = ch
        
        for future in as_completed(futures):
            ch = futures[future]
            try:
                content = future.result()
                output_path = save_chapter(config["output_dir"], ch, content, prompt_type)
                results[ch] = output_path
                print(f"[OK] 第{ch}章生成成功: {output_path}")
            except Exception as e:
                errors[ch] = str(e)
                print(f"[FAIL] 第{ch}章生成失败: {e}")
    
    return results, errors


def main():
    parser = argparse.ArgumentParser(description="API批量调用脚本")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, required=True, help="起始章节")
    parser.add_argument("--end", type=int, required=True, help="结束章节")
    parser.add_argument("--workers", type=int, default=10, help="并行数")
    parser.add_argument("--type", default="write-chapter", help="prompt类型")
    
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 设置prompt类型
    config["prompt_type"] = args.type
    
    print(f"开始生成: 第{args.start}-{args.end}章")
    print(f"并行数: {args.workers}")
    print(f"API提供商: {config.get('provider', 'openai')}")
    print(f"模型: {config.get('model', 'gpt-4')}")
    print()
    
    start_time = time.time()
    results, errors = batch_generate(config, args.start, args.end, args.workers, args.type)
    end_time = time.time()
    
    print()
    print(f"生成完成!")
    print(f"成功: {len(results)}章")
    print(f"失败: {len(errors)}章")
    print(f"耗时: {end_time - start_time:.1f}秒")
    
    if errors:
        print("\n失败章节:")
        for ch, error in errors.items():
            print(f"  第{ch}章: {error}")


if __name__ == '__main__':
    main()