"""
全书自动生成脚本：走标准流程
流程：拆章 → 开书 → 生成guide → 写章 → 修复标题 → 合并 → 对比
"""
import os
import sys
import json
import time
import argparse
import subprocess
import tempfile
from pathlib import Path


def run_cmd(cmd, cwd=None):
    """运行命令。"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, encoding='gbk', errors='ignore')
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"错误: {result.stderr}")
    print(f"退出码: {result.returncode}")
    return result.returncode == 0


def step1_split(source_path, output_dir):
    """Step 1: 拆章"""
    print("\n" + "=" * 50)
    print("Step 1: 拆章")
    print("=" * 50)
    
    split_script = ".agents/skills/story-engine/tools/split_chapters_generic.py"
    cmd = f'python "{split_script}" "{source_path}" "{output_dir}"'
    return run_cmd(cmd)


def step2_style(source_path, output_path):
    """Step 2: 风格分析"""
    print("\n" + "=" * 50)
    print("Step 2: 风格分析")
    print("=" * 50)
    
    style_script = ".agents/skills/story-engine/tools/calc_style_profile.py"
    cmd = f'python "{style_script}" "{source_path}" -o "{output_path}"'
    return run_cmd(cmd)


def step3_setup(project_dir, chapter_count):
    """Step 3: 创建项目目录"""
    print("\n" + "=" * 50)
    print("Step 3: 创建项目目录")
    print("=" * 50)
    
    setup_script = ".agents/skills/story-engine/tools/create_templates.py"
    cmd = f'python "{setup_script}" setup {chapter_count} "{project_dir}"'
    return run_cmd(cmd)


def step4_open_book(config, chapter_count):
    """Step 4: 开书（生成新书设定、全书弧线、真相）"""
    print("\n" + "=" * 50)
    print("Step 4: 开书（pro模型）")
    print("=" * 50)
    
    # 开书用pro模型
    pro_config = config.copy()
    pro_config["model"] = "deepseek-v4-pro"
    pro_config["reasoning_effort"] = "high"
    
    # 生成新书设定
    print("\n生成新书设定...")
    api_script = ".agents/skills/story-engine/tools/api_batch_generate.py"
    
    # 创建临时配置文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(pro_config, f, ensure_ascii=False)
        config_path = f.name
    
    try:
        cmd = f'python "{api_script}" --config "{config_path}" --start 1 --end 1 --workers 1 --type arc-concept'
        if not run_cmd(cmd):
            print("警告: 新书设定生成失败")
    finally:
        os.unlink(config_path)
    
    # 生成全书弧线
    print("\n生成全书弧线...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(pro_config, f, ensure_ascii=False)
        config_path = f.name
    
    try:
        cmd = f'python "{api_script}" --config "{config_path}" --start 1 --end 1 --workers 1 --type arc-skeleton-core'
        if not run_cmd(cmd):
            print("警告: 全书弧线生成失败")
    finally:
        os.unlink(config_path)


def step5_generate_guides(config, chapter_count):
    """Step 5: 生成guide（flash模型）"""
    print("\n" + "=" * 50)
    print("Step 5: 生成guide（flash模型）")
    print("=" * 50)
    
    flash_config = config.copy()
    flash_config["model"] = "deepseek-v4-flash"
    flash_config["reasoning_effort"] = "low"
    # guide输出到 guides/ 目录
    flash_config["output_dir"] = f"{config['output_dir']}/guides"
    
    api_script = ".agents/skills/story-engine/tools/api_batch_generate.py"
    
    # 生成plot_guide
    print("\n生成plot_guide...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(flash_config, f, ensure_ascii=False)
        config_path = f.name
    
    try:
        cmd = f'python "{api_script}" --config "{config_path}" --start 1 --end {chapter_count} --workers 10 --type plot-guide'
        if not run_cmd(cmd):
            print("警告: plot_guide生成失败")
    finally:
        os.unlink(config_path)
    
    # 生成style_guide
    print("\n生成style_guide...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(flash_config, f, ensure_ascii=False)
        config_path = f.name
    
    try:
        cmd = f'python "{api_script}" --config "{config_path}" --start 1 --end {chapter_count} --workers 10 --type style-guide'
        if not run_cmd(cmd):
            print("警告: style_guide生成失败")
    finally:
        os.unlink(config_path)


def step6_write_chapters(config, chapter_count):
    """Step 6: 写章（flash模型）"""
    print("\n" + "=" * 50)
    print("Step 6: 写章（flash模型）")
    print("=" * 50)
    
    flash_config = config.copy()
    flash_config["model"] = "deepseek-v4-flash"
    flash_config["reasoning_effort"] = "low"
    # 写章输出到 chapters/ 目录
    flash_config["output_dir"] = f"{config['output_dir']}/chapters"
    
    api_script = ".agents/skills/story-engine/tools/api_batch_generate.py"
    
    print(f"\n生成第1-{chapter_count}章...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(flash_config, f, ensure_ascii=False)
        config_path = f.name
    
    try:
        cmd = f'python "{api_script}" --config "{config_path}" --start 1 --end {chapter_count} --workers 10 --type write-chapter'
        if not run_cmd(cmd):
            print("警告: 章节生成失败")
    finally:
        os.unlink(config_path)


def step7_fix_titles(project_dir, source_path):
    """Step 7: 修复章节标题"""
    print("\n" + "=" * 50)
    print("Step 7: 修复章节标题")
    print("=" * 50)
    
    fix_script = ".agents/skills/story-engine/tools/fix_chapter_titles.py"
    cmd = f'python "{fix_script}" "{project_dir}/chapters" "{source_path}"'
    return run_cmd(cmd)


def step8_merge(project_dir, book_name):
    """Step 8: 合并导出"""
    print("\n" + "=" * 50)
    print("Step 8: 合并导出")
    print("=" * 50)
    
    merge_script = ".agents/skills/story-engine/tools/merge_chapters.py"
    export_dir = f"{project_dir}/export"
    os.makedirs(export_dir, exist_ok=True)
    output_file = f"{export_dir}/{book_name}.txt"
    cmd = f'python "{merge_script}" "{project_dir}/chapters" "{output_file}"'
    return run_cmd(cmd)


def step9_compare(project_dir, chapter_count):
    """Step 9: 对比"""
    print("\n" + "=" * 50)
    print("Step 9: 对比")
    print("=" * 50)
    
    compare_script = ".agents/skills/story-compare/compare.py"
    cmd = f'python "{compare_script}" "{project_dir}" 1 {chapter_count}'
    return run_cmd(cmd)


def generate_book(config, source_path, chapter_count):
    """生成整本书。"""
    book_name = config["book_name"]
    project_dir = config["output_dir"]
    
    print(f"开始生成整本书: {book_name}")
    print(f"源文: {source_path}")
    print(f"章节数: {chapter_count}")
    print(f"项目目录: {project_dir}")
    
    start_time = time.time()
    
    # Step 1: 拆章 → source book _cache/chapters/
    source_book_dir = os.path.dirname(source_path)
    split_dir = os.path.join(source_book_dir, "_cache", "chapters")
    if not os.path.exists(split_dir) or not os.listdir(split_dir):
        step1_split(source_path, split_dir)

    # Step 2: 风格分析 → source book _cache/analysis/
    cache_analysis_dir = os.path.join(source_book_dir, "_cache", "analysis")
    os.makedirs(cache_analysis_dir, exist_ok=True)
    style_file = os.path.join(cache_analysis_dir, "style_profile.json")
    if not os.path.exists(style_file):
        step2_style(source_path, style_file)
    
    # Step 3: 创建项目目录
    step3_setup(project_dir, chapter_count)
    
    # Step 4: 开书
    step4_open_book(config, chapter_count)
    
    # Step 5: 生成guide
    step5_generate_guides(config, chapter_count)
    
    # Step 6: 写章
    step6_write_chapters(config, chapter_count)
    
    # Step 7: 修复章节标题
    step7_fix_titles(project_dir, source_path)
    
    # Step 8: 合并导出
    step8_merge(project_dir, book_name)
    
    # Step 9: 对比
    step9_compare(project_dir, chapter_count)
    
    end_time = time.time()
    
    print("\n" + "=" * 50)
    print("生成完成!")
    print("=" * 50)
    print(f"总耗时: {end_time - start_time:.1f}秒")
    print(f"输出文件: {export_dir}/{book_name}.txt")
    print(f"对比报告: {project_dir}/compare/")


def main():
    parser = argparse.ArgumentParser(description="全书自动生成脚本")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--source", required=True, help="源文路径")
    parser.add_argument("--chapters", type=int, required=True, help="总章节数")
    
    args = parser.parse_args()
    
    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 运行
    generate_book(config, args.source, args.chapters)


if __name__ == '__main__':
    main()