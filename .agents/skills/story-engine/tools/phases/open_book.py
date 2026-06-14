"""Phase 0: Prep（提取元数据+章节目录）
Phase 0.5: 曲线分析（读 _toc.txt → 选关键章节）
Phase 1: 开书（生成 concept.md + settings/）"""

import json
import os
import re
import time
from pathlib import Path

from utils import (
    get_total_chapters, get_source_title, call_api, 
    load_trend_knowledge, count_source_chars
)
from state_manager import atomic_write_text
from prompt_loader import load_prompt, load_system_prompt, tag_output, get_prompt_config_with_overrides


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
        raw_txt = _find_source_txt(base_dir, author, source_book)
        if raw_txt:
            head_lines = []
            with open(raw_txt, encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 80:
                        break
                    stripped = line.strip()
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
                    title = first_line.strip()[:60]
                    toc_lines.append(title)
                except:
                    toc_lines.append(cf.stem)
            toc_file.write_text('\n'.join(toc_lines), encoding='utf-8')
            print(f"[OK] _toc.txt ({len(chapter_files)}章，含完整标题)")
        else:
            print(f"[WARN] 未找到拆分章节，_toc.txt 跳过")


def _find_source_txt(base_dir, author, source_book):
    """多路径搜索原始 TXT。"""
    candidates = [
        Path(base_dir) / "projects" / f"{source_book}.txt",
        Path(base_dir) / "projects" / author / f"{source_book}.txt",
        Path(base_dir) / "projects" / author / source_book / f"{source_book}.txt",
        Path(base_dir) / f"{source_book}.txt",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


# ============================================================
# Phase 0.5: 曲线分析 — 读 _toc.txt → 选关键章节
# ============================================================

def _fallback_key_chapters(total_ch):
    """等距采样（toc 不可用时的降级方案）。"""
    chs = [1]
    total_ch = max(total_ch, 5)
    for frac in [0.15, 0.30, 0.45, 0.60, 0.75, 0.88]:
        chs.append(max(2, int(total_ch * frac)))
    for c in range(total_ch, 0, -1):
        if c not in chs:
            chs.append(c)
            break
    return sorted(set(chs))


def _detect_curve(config, api_key, api_url):
    """Stage 1: 读 _toc.txt，用 flash 分析情绪曲线，返回关键章节列表。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    toc_path = Path(base_dir) / "projects" / author / source_book / "_cache" / "_toc.txt"

    if not toc_path.exists():
        print("  [CURVE] _toc.txt 不存在，使用等距采样")
        return _fallback_key_chapters(get_total_chapters(config))

    total_ch = get_total_chapters(config)
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    replacements = {
        "作者名": author,
        "源书名": source_book,
        "总章数": str(total_ch),
    }

    try:
        curve_prompt = load_prompt(
            f"{prompts_dir}/toc-curve.md",
            base_dir, replacements, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )
    except FileNotFoundError:
        print("  [CURVE] toc-curve.md 不存在，使用等距采样")
        return _fallback_key_chapters(total_ch)

    print("  [CURVE] 曲线分析中...")
    try:
        pc = get_prompt_config_with_overrides("toc-curve.md", config)
        if config.get("debug"):
            from utils import debug_dump_prompt
            debug_dump_prompt(config, "toc-curve", 0, f"{prompts_dir}/toc-curve.md", "", curve_prompt, "N/A", pc)
        result = call_api(
            api_key, pc.get("model", "deepseek-v4-flash"), curve_prompt,
            max_tokens=pc.get("max_tokens", 4096), api_url=api_url,
            temperature=pc.get("temperature", 0.8),
        )
    except Exception:
        print("  [CURVE] LLM 调用失败，使用等距采样")
        return _fallback_key_chapters(total_ch)

    chapters = _parse_curve_result(result, total_ch)
    print(f"  [CURVE] 选定 {len(chapters)} 章: {chapters}")
    return chapters


def _parse_curve_result(text, total_ch):
    """从 LLM 输出中解析 key_chapters JSON 数组。"""
    try:
        m = re.search(r'```json\s*(.*?)```', text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
        else:
            data = json.loads(text)
        chs = data.get("key_chapters", [])
        valid = sorted(set(int(c) for c in chs if 1 <= int(c) <= total_ch))
        if len(valid) >= 3:
            return valid
    except Exception:
        pass
    return _fallback_key_chapters(total_ch)


def _build_sample_block(config, chapter_numbers):
    """构建 {源文样本} 内容：每个章节生成一行 【源文_样本N】path。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    lines = []
    for i, ch in enumerate(chapter_numbers, 1):
        path = f"projects/{author}/{source_book}/_cache/chapters/第{ch}章.txt"
        lines.append(f"【源文_样本{i}】{path}")
    return "\n".join(lines)


# ============================================================
# Phase 1: 开书
# ============================================================

def phase_open_book(config, state_mgr=None):
    """两段式开书：曲线分析(flash) → 选章精读 → 开书(pro)。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (两段式: curve→open-book)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("open-book"):
            print("concept.md 已完成，跳过")
            return True
        state_mgr.phase_start("open-book")

    base_dir = config.get("base_dir", os.getcwd())
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    from lib.api_client import get_api_url
    api_url = get_api_url(config)

    # === Stage 1: 曲线分析 → 选关键章节 ===
    key_chapters = _detect_curve(config, api_key, api_url)

    # === Stage 2: 用选定的章节做开书分析 ===
    total_ch = get_total_chapters(config)
    replacements = {
        "新书名": config["book_name"],
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
        "genre": config.get("genre", ""),
        "源文样本": _build_sample_block(config, key_chapters),
    }

    trend_content = ""
    trend_dir = config.get("trend_dir")
    if trend_dir:
        trend_content = load_trend_knowledge(trend_dir, base_dir)

    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    user_prompt = load_prompt(
        f"{prompts_dir}/open-book.md",
        base_dir, replacements, mode="api",
        rewrites_dir=config.get("rewrites_dir"),
    )
    if trend_content:
        user_prompt += trend_content

    system_prompt = load_system_prompt("system-generic.md")

    try:
        pc = get_prompt_config_with_overrides("open-book.md", config)
        if config.get("debug"):
            from utils import debug_dump_prompt
            debug_dump_prompt(config, "open-book", 0, f"{prompts_dir}/open-book.md", system_prompt, user_prompt, "system-generic.md", pc)
        result = call_api(
            api_key, pc.get("model", "deepseek-v4-pro"), user_prompt,
            reasoning_effort=pc.get("reasoning_effort", "high"),
            max_tokens=pc.get("max_tokens", 8192),
            temperature=pc.get("temperature", 0.8),
            system_prompt=system_prompt, api_url=api_url,
        )

        files = parse_multi_file_output(result)
        if files:
            for filepath, content in files.items():
                full_path = Path(config["rewrites_dir"]) / filepath
                atomic_write_text(full_path, tag_output(content, "open-book.md"))
                print(f"[OK] {filepath} → {full_path}")
        else:
            path = Path(config["rewrites_dir"]) / "concept.md"
            atomic_write_text(path, tag_output(result, "open-book.md"))
            print(f"[OK] concept.md → {path}")

        if state_mgr:
            state_mgr.phase_done("open-book")
        return True
    except Exception as e:
        print(f"[FAIL] open-book: {e}")
        if state_mgr:
            state_mgr.phase_failed("open-book", error=str(e))
        return False


def parse_multi_file_output(text):
    """解析 AI 输出的多文件内容。格式：===FILE: path===\n内容"""
    files = {}
    pattern = r'===FILE:\s*(.+?)\s*==='
    parts = re.split(pattern, text)

    if len(parts) < 3:
        return {}

    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            filepath = parts[i].strip()
            content = parts[i + 1].strip()
            if filepath and content:
                files[filepath] = content

    return files
