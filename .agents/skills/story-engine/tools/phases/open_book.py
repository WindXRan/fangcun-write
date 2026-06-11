"""Phase 0: Prep（提取元数据+章节目录）
Phase 1: 开书（生成 concept.md + settings/）"""

import os
import re
import sys
import time
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)

from utils import (
    get_total_chapters, get_source_title, call_api, 
    load_trend_knowledge, count_source_chars
)
from state_manager import atomic_write_text
from prompt_loader import load_prompt


# ============================================================
# Phase 0: Prep（提取元数据+章节目录）
# ============================================================

def phase_prep(config):
    """从原始 TXT 提取头部元数据和章节目录，供 open-book 使用。兼容 projects/ 下各种目录结构。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    cache_dir = Path(base_dir) / "projects" / author / source_book / "_cache"
    os.makedirs(cache_dir, exist_ok=True)

    # 1. 提取原始 TXT 头部（书名/作者/简介/标签/等级体系）
    header_file = cache_dir / "_header.txt"
    if not header_file.exists():
        # 多路径搜索原始 TXT
        raw_paths = [
            Path(base_dir) / "projects" / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / source_book / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / f"{source_book}.txt",
            Path(base_dir) / f"{source_book}.txt",
        ]
        raw_txt = None
        for p in raw_paths:
            if p.exists():
                raw_txt = p
                break

        if raw_txt:
            with open(raw_txt, encoding='utf-8') as f:
                head_lines = []
                for i, line in enumerate(f):
                    if i >= 80:
                        break
                    stripped = line.strip()
                    # 多种章节标题模式：第1章 / 第一章 / 第001章 / Chapter 1
                    if stripped and (
                        (stripped.startswith('第') and '章' in stripped[:15]) or
                        stripped.lower().startswith('chapter')
                    ):
                        break
                    head_lines.append(line)
            header_file.write_text(''.join(head_lines), encoding='utf-8')
            print(f"[OK] _header.txt ({len(head_lines)}行) -> {raw_txt}")
        else:
            print(f"[WARN] 未找到原始 TXT，_header.txt 跳过")

    # 2. 生成章节目录（从已拆分的章节）
    toc_file = cache_dir / "_toc.txt"
    if not toc_file.exists():
        # 多路径搜索拆分章节
        chapters_dirs = [
            cache_dir / "chapters",
            Path(base_dir) / "projects" / author / source_book / "源文",
        ]
        chapter_files = []
        for d in chapters_dirs:
            if d.exists():
                cf = sorted(
                    d.glob("第*章*.txt"),
                    key=lambda f: int(re.search(r'第(\d+)章', f.stem).group(1)) if re.search(r'第(\d+)章', f.stem) else 0
                )
                if cf:
                    chapter_files = cf
                    break

        if chapter_files:
            toc_lines = [f"总章数: {len(chapter_files)}\n\n"]
            for cf in chapter_files:
                try:
                    first_line = cf.read_text(encoding='utf-8').strip().split('\n')[0]
                    # 只取前60字（标题行），去掉空白
                    title = first_line.strip()[:60]
                    toc_lines.append(title)
                except:
                    toc_lines.append(cf.stem)
            toc_file.write_text('\n'.join(toc_lines), encoding='utf-8')
            print(f"[OK] _toc.txt ({len(chapter_files)}章，含完整标题)")
        else:
            print(f"[WARN] 未找到拆分章节，_toc.txt 跳过")


# ============================================================
# Phase 1: 开书
# ============================================================

def phase_open_book(config, state_mgr=None):
    """生成 concept.md + settings/ 目录下的独立文件。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (pro, reasoning=high)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("open-book"):
            print("concept.md 已完成，跳过")
            return True
        state_mgr.phase_start("open-book")

    # 动态样本章节（开局5章+中间3章+最后5章）
    total_ch = get_total_chapters(config)
    replacements = {
        "新书名": config["book_name"],
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
        "genre": config.get("genre", ""),
    }
    
    if total_ch > 0:
        # 开局5章
        replacements["章号_开篇1"] = "1"
        replacements["章号_开篇2"] = "2"
        replacements["章号_开篇3"] = "3"
        replacements["章号_开篇4"] = "4"
        replacements["章号_开篇5"] = "5"
        # 中间3章（25%/50%/75%位置）
        replacements["章号_中段1"] = str(max(1, int(total_ch * 0.25)))
        replacements["章号_中段2"] = str(max(1, int(total_ch * 0.50)))
        replacements["章号_中段3"] = str(max(1, int(total_ch * 0.75)))
        # 最后5章（跳过番外）
        tail_chs = []
        for c in range(total_ch, 0, -1):
            tail_title = get_source_title(config, c)
            if '番外' in tail_title:
                continue
            tail_chs.append(str(c))
            if len(tail_chs) >= 5:
                break
        tail_chs.reverse()
        for i in range(5):
            replacements[f"章号_结尾{i+1}"] = tail_chs[i] if i < len(tail_chs) else str(total_ch)

    # 热梗素材注入
    trend_content = ""
    trend_dir = config.get("trend_dir")
    if trend_dir:
        trend_content = load_trend_knowledge(trend_dir, config.get("base_dir", os.getcwd()))

    # 加载 prompt
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    base_dir = config.get("base_dir", os.getcwd())
    prompt_path = f"{prompts_dir}/open-book.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))
    
    if trend_content:
        user_prompt += trend_content

    # 调用 API（使用 pro 模型）
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    from lib.api_client import get_api_url
    api_url = get_api_url(config)
    system_prompt = "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"

    try:
        result = call_api(
            api_key, "deepseek-v4-pro", user_prompt,
            reasoning_effort="high", max_tokens=8192,
            system_prompt=system_prompt, api_url=api_url
        )
        
        # 解析多文件输出：AI 用 ===FILE: path=== 分隔不同文件
        files = parse_multi_file_output(result)
        
        if files:
            # 多文件模式：拆分到 settings/ 目录
            for filepath, content in files.items():
                full_path = Path(config["rewrites_dir"]) / filepath
                atomic_write_text(full_path, content)
                print(f"[OK] {filepath} → {full_path}")
        else:
            # 单文件模式：直接保存为 concept.md
            path = Path(config["rewrites_dir"]) / "concept.md"
            atomic_write_text(path, result)
            print(f"[OK] concept.md → {path}")
        
        if state_mgr:
            state_mgr.phase_done("open-book")
        return True
    except Exception as e:
        print(f"[FAIL] concept.md: {e}")
        if state_mgr:
            state_mgr.phase_failed("open-book", error=str(e))
        return False


def parse_multi_file_output(text):
    """解析 AI 输出的多文件内容。格式：===FILE: path===\n内容"""
    files = {}
    # 匹配 ===FILE: path=== 分隔符
    pattern = r'===FILE:\s*(.+?)\s*==='
    parts = re.split(pattern, text)
    
    if len(parts) < 3:
        # 没有找到分隔符，返回空
        return {}
    
    # parts[0] 是第一个分隔符之前的内容（通常是说明文字，跳过）
    # parts[1] 是第一个文件路径，parts[2] 是第一个文件内容
    # parts[3] 是第二个文件路径，parts[4] 是第二个文件内容，以此类推
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            filepath = parts[i].strip()
            content = parts[i + 1].strip()
            if filepath and content:
                files[filepath] = content
    
    return files
