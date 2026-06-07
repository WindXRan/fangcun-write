"""
统一改写流水线：Agent/API 双模式兼容。

使用同一套 prompt 文件（prompts/*.md），通过 prompt_loader 自动适配：
- Agent 模式：prompt 原样返回，Agent 用 Read 工具读文件
- API 模式：prompt_loader 自动嵌入【标签】引用的文件内容

流水线步骤：
  1. 开书：arc-concept → concept.md + arc-skeleton-core → arc.md, truth.md
  2. Guide: plot-guide → guides/plot_{N}.md + style-guide → guides/style_{N}.md
  3. 写章: write-chapter → chapters/ch_{N}.txt
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入统一 prompt 加载器
sys.path.insert(0, str(Path(__file__).parent))
from prompt_loader import load_prompt, get_output_path

API_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行，不要偷懒。"


def call_deepseek(api_key, model, user_prompt, reasoning_effort="low", max_tokens=8192):
    """调用 DeepSeek API。"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": max_tokens,
        "stream": False,
        "reasoning_effort": reasoning_effort
    }
    resp = requests.post(API_URL, headers=headers, json=data, timeout=600)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_single(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None):
    """
    执行单次 LLM 调用（API 模式）。

    自动通过 prompt_loader 加载并嵌入文件内容。
    支持 pipeline 中所有 prompt 类型：
      - arc-concept, arc-skeleton-core（开书）
      - plot-guide, style-guide（guide 生成）
      - write-chapter（写章）
    """
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置环境变量 $env:API_KEY")

    model = model or config.get("model", "deepseek-v4-flash")
    reasoning_effort = reasoning_effort or config.get("reasoning_effort", "low")

    # 构建 prompt 路径和变量替换
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    prompt_path = f"{prompts_dir}/{prompt_type}.md"

    n_str = str(chapter_num) if chapter_num is not None else "1"
    replacements = {
        "新书名": config["book_name"],
        "N": n_str,
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }

    # === 核心：使用统一 prompt_loader，API 模式自动嵌入文件 ===
    base_dir = config.get("base_dir", os.getcwd())
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api")

    # 调用 API
    result = call_deepseek(api_key, model, user_prompt, reasoning_effort)
    return result


def save_output(output_dir, filename, content):
    """保存输出文件。"""
    os.makedirs(output_dir, exist_ok=True)
    path = Path(output_dir) / filename
    path.write_text(content, encoding='utf-8')
    return str(path)


# ============================================================
# 流水线步骤
# ============================================================

def step_open_book(config):
    """Step 1-2: 开书 — 生成 concept + arc + truth"""
    pro_config = {**config, "model": "deepseek-v4-pro", "reasoning_effort": "high"}
    rewrites_dir = config["rewrites_dir"]

    print("\n" + "=" * 50)
    print("Step 1/2: 开书 — 新书设定 (pro)")
    print("=" * 50)
    try:
        concept = run_single(pro_config, "arc-concept")
        save_output(rewrites_dir, "concept.md", concept)
        print("[OK] concept.md 生成成功")
    except Exception as e:
        print(f"[FAIL] concept.md: {e}")
        return False

    print("\n" + "=" * 50)
    print("Step 2/2: 开书 — 全书弧线 + 真相 (pro)")
    print("=" * 50)
    try:
        arc = run_single(pro_config, "arc-skeleton-core")
        # arc-skeleton-core 输出包含弧线和真相，需拆分
        # 按标记拆分：## 情感曲线 开始是弧线，## 时间线 开始是真相
        if "## 时间线" in arc:
            parts = arc.split("## 时间线", 1)
            arc_content = parts[0].strip()
            truth_content = "## 时间线" + parts[1].strip()
        else:
            arc_content = arc
            truth_content = ""

        save_output(rewrites_dir, "arc.md", arc_content)
        if truth_content:
            save_output(rewrites_dir, "truth.md", truth_content)
        print("[OK] arc.md + truth.md 生成成功")
    except Exception as e:
        print(f"[FAIL] arc.md: {e}")
        return False

    return True


def step_generate_guides(config, start_ch, end_ch, max_workers=5):
    """Step 3: 生成 plot_guide + style_guide"""
    flash_config = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}
    guides_dir = f"{config['rewrites_dir']}/guides"

    for guide_type, label in [("plot-guide", "plot"), ("style-guide", "style")]:
        print(f"\n{'=' * 50}")
        print(f"Step 3: 生成 {label}_guide (flash, {start_ch}-{end_ch})")
        print("=" * 50)

        results, errors = batch_run(
            flash_config, guide_type, start_ch, end_ch, max_workers,
            output_dir=guides_dir,
            filename_pattern=f"{label}_{{ch:03d}}.md"
        )
        ok = len(results)
        fail = len(errors)
        print(f"{label}_guide: 成功 {ok}, 失败 {fail}")
        if errors:
            for ch, e in errors.items():
                print(f"  [FAIL] ch{ch}: {e}")


def step_write_chapters(config, start_ch, end_ch, max_workers=10):
    """Step 4: 写章"""
    flash_config = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Step 4: 写章 (flash, {start_ch}-{end_ch}, {max_workers} workers)")
    print("=" * 50)

    results, errors = batch_run(
        flash_config, "write-chapter", start_ch, end_ch, max_workers,
        output_dir=chapters_dir,
        filename_pattern="ch_{ch:03d}.txt"
    )

    total_chars = 0
    for ch, path in results.items():
        try:
            content = Path(path).read_text(encoding='utf-8')
            chars = len(content.replace('\n', '').replace(' ', '').replace('\r', ''))
            total_chars += chars
            print(f"[OK] ch{ch:03d} ({chars}字)")
        except:
            pass

    print(f"\n总成功: {len(results)}章, 失败: {len(errors)}章, 总字数: {total_chars}")
    return results, errors


# ============================================================
# 批量执行
# ============================================================

def batch_run(config, prompt_type, start_ch, end_ch, max_workers, output_dir, filename_pattern):
    """批量并行执行 LLM 调用。"""
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for ch in range(start_ch, end_ch + 1):
            future = executor.submit(run_single, config, prompt_type, ch)
            futures[future] = ch

        for future in as_completed(futures):
            ch = futures[future]
            try:
                content = future.result()
                filename = filename_pattern.format(ch=ch)
                path = save_output(output_dir, filename, content)
                results[ch] = path
            except Exception as e:
                errors[ch] = str(e)
                print(f"[FAIL] ch{ch}: {e}")

    return results, errors


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="统一改写流水线 (Agent/API 双模式)")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=10, help="结束章")
    parser.add_argument("--workers", type=int, default=10, help="并行数")
    parser.add_argument("--skip-open-book", action="store_true", help="跳过开书")
    parser.add_argument("--skip-guides", action="store_true", help="跳过 guide 生成")
    parser.add_argument("--steps", default="all", help="执行步骤: open-book, guides, write, all")

    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    config["prompts_dir"] = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    config["base_dir"] = config.get("base_dir", os.getcwd())

    print(f"统一改写流水线")
    print(f"书名: {config['book_name']}")
    print(f"章节: 第{args.start}-{args.end}章")
    print(f"模式: API (DeepSeek)")
    print(f"项目目录: {config.get('rewrites_dir', 'N/A')}")
    print()

    start_time = time.time()
    steps = args.steps.split(",")

    # Step 1-2: 开书
    if "all" in steps or "open-book" in steps:
        if not args.skip_open_book:
            step_open_book(config)
        else:
            print("跳过开书")

    # Step 3: Guide 生成
    if "all" in steps or "guides" in steps:
        if not args.skip_guides:
            step_generate_guides(config, args.start, args.end, args.workers)
        else:
            print("跳过 guide 生成")

    # Step 4: 写章
    if "all" in steps or "write" in steps:
        step_write_chapters(config, args.start, args.end, args.workers)

    elapsed = time.time() - start_time
    print(f"\n流水线完成! 总耗时: {elapsed:.1f}秒")


if __name__ == '__main__':
    main()
