"""
全书一键生成：拆章 + 风格分析 + 创建目录 + rewrite_chapters(开书+guide+写章) + 修复标题 + 合并 + 对比
LLM 部分委托给 rewrite_chapters.py（统一流水线，prompt_loader 双模式兼容）。
"""
import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

SCRIPTS_DIR = ".agents/skills/story-engine/tools"
REWRITE_SCRIPT = f"{SCRIPTS_DIR}/rewrite_chapters.py"


def run(cmd):
    print(f"执行: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='gbk', errors='ignore')
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print(f"错误: {r.stderr}")
    print(f"退出码: {r.returncode}")
    return r.returncode == 0


# ============================================================
# 非 LLM 步骤（generate_book 独有）
# ============================================================

def step_split(source_path, output_dir):
    print("\n" + "=" * 50)
    print("Step 1: 拆章")
    print("=" * 50)
    return run(f'python "{SCRIPTS_DIR}/split_chapters_generic.py" "{source_path}" "{output_dir}"')


def step_setup(project_dir, chapter_count):
    print("\n" + "=" * 50)
    print("Step 3: 创建项目目录")
    print("=" * 50)
    return run(f'python "{SCRIPTS_DIR}/create_templates.py" setup {chapter_count} "{project_dir}"')


def step_fix_titles(project_dir, source_path):
    print("\n" + "=" * 50)
    print("Step 7: 修复章节标题")
    print("=" * 50)
    return run(f'python "{SCRIPTS_DIR}/fix_chapter_titles.py" "{project_dir}/chapters" "{source_path}"')


def step_merge(project_dir, book_name):
    print("\n" + "=" * 50)
    print("Step 8: 合并导出")
    print("=" * 50)
    export_dir = f"{project_dir}/export"
    os.makedirs(export_dir, exist_ok=True)
    return run(f'python "{SCRIPTS_DIR}/merge_chapters.py" "{project_dir}/chapters" "{export_dir}/{book_name}.txt"')


def step_compare(project_dir, chapter_count):
    print("\n" + "=" * 50)
    print("Step 9: 对比")
    print("=" * 50)
    compare_script = ".agents/skills/story-compare/compare.py"
    return run(f'python "{compare_script}" "{project_dir}" 1 {chapter_count}')


# ============================================================
# LLM 步骤（委托 rewrite_chapters.py）
# ============================================================

def step_rewrite(config_path, start, end, workers, steps):
    """委托 rewrite_chapters.py 执行 LLM 步骤。"""
    return run(f'python "{REWRITE_SCRIPT}" --config "{config_path}" --start {start} --end {end} --workers {workers} --steps {steps}')


# ============================================================
# 主流程
# ============================================================

def generate_book(config, source_path, chapter_count):
    book_name = config["book_name"]
    rewrites_dir = config["rewrites_dir"]

    print(f"开始生成整本书: {book_name}")
    print(f"源文: {source_path}")
    print(f"章节数: {chapter_count}")
    print(f"项目目录: {rewrites_dir}")

    start_time = time.time()

    # 准备缓存路径
    source_book_dir = os.path.dirname(source_path)
    split_dir = os.path.join(source_book_dir, "_cache", "chapters")

    # Step 1-3: 非 LLM 准备
    if not os.path.exists(split_dir) or not os.listdir(split_dir):
        step_split(source_path, split_dir)

    step_setup(rewrites_dir, chapter_count)

    # Step 4-6: LLM（委托 rewrite_chapters.py 统一流水线）
    # 生成临时配置（传递给 rewrite_chapters）
    rewrite_config = dict(config)
    rewrite_config["prompts_dir"] = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    rewrite_config["base_dir"] = config.get("base_dir", os.getcwd())

    with open("_temp_rewrite_config.json", 'w', encoding='utf-8') as f:
        json.dump(rewrite_config, f, ensure_ascii=False, indent=2)

    try:
        step_rewrite("_temp_rewrite_config.json", 1, chapter_count, 10, "open-book,guides,write")
    finally:
        os.unlink("_temp_rewrite_config.json")

    # Step 7-9: 后处理
    step_fix_titles(rewrites_dir, source_path)
    step_merge(rewrites_dir, book_name)
    step_compare(rewrites_dir, chapter_count)

    elapsed = time.time() - start_time

    print("\n" + "=" * 50)
    print("生成完成!")
    print("=" * 50)
    print(f"总耗时: {elapsed:.1f}秒")
    print(f"输出文件: {rewrites_dir}/export/{book_name}.txt")
    print(f"对比报告: {rewrites_dir}/compare/")


def main():
    parser = argparse.ArgumentParser(description="全书一键生成（委托 rewrite_chapters.py 统一流水线）")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--source", required=True, help="源文路径")
    parser.add_argument("--chapters", type=int, required=True, help="总章节数")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    generate_book(config, args.source, args.chapters)


if __name__ == '__main__':
    main()
