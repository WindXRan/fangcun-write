"""Phase 0: Prep（提取元数据+章节目录）
Phase 0.5: 曲线分析（读 _toc.txt → 选关键章节）
Phase 1: 开书（生成 concept.md + settings/）"""

import json
import os
import re
import time
from pathlib import Path

from utils import (
    get_total_chapters, get_source_title, call_api, count_source_chars
)
from state_manager import atomic_write_text
from prompt_loader import load_prompt, load_system_prompt, tag_output, get_prompt_config_with_overrides, get_system_prompt_name


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


def _heuristic_key_chapters(config):
    """从 _toc.txt 章节标题启发式选关键章节（不调 API）。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    toc_path = Path(base_dir) / "projects" / author / source_book / "_cache" / "_toc.txt"
    if not toc_path.exists():
        return _fallback_key_chapters(get_total_chapters(config))

    lines = [l.strip() for l in toc_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = 0
    chapter_titles = {}
    for line in lines:
        m = re.match(r'第(\d+)章\s*(.*)', line)
        if m:
            ch_num = int(m.group(1))
            title = m.group(2).strip()
            chapter_titles[ch_num] = title
            total = max(total, ch_num)
    if total == 0:
        return _fallback_key_chapters(get_total_chapters(config))

    # 关键词匹配：高光/转折/结局
    KEYWORDS = [
        # 剧情转折
        "反转", "真相", "高潮", "升温", "决裂", "摊牌", "崩溃", "爆发",
        "质问", "离开", "归来", "相认", "黑化", "觉醒", "逆转", "抉择",
        "转折", "危机", "秘密", "发现", "误会", "冲突", "天降",
        # 关系里程碑
        "初见", "告白", "心事", "情敌", "吃醋", "心动", "想见", "在意",
        "牵手", "拥抱", "亲吻", "提亲", "定亲", "婚礼", "大婚", "成亲",
        "和好", "分手", "决裂", "两心", "心悦", "真心", "答应",
        # 结局/番外
        "大结局", "结局", "番外", "新年", "团圆", "结局",
        # 穿越/重生
        "穿越", "重生", "魂穿",
    ]
    scored = []
    for ch_num, title in chapter_titles.items():
        score = 0
        for kw in KEYWORDS:
            if kw in title:
                score += 3
        # 前10章加分：定人设/定调性/定冲突，开书分析必须读
        if 2 <= ch_num <= 10:
            score += 4
        # 首章/末章加分
        if ch_num == 1:
            score += 5
        if ch_num == total:
            score += 4
        if "番外" in title:
            score += 2
        scored.append((ch_num, score, title))

    # 按分数降序取 top 12，再补等距
    scored.sort(key=lambda x: -x[1])
    selected = set(ch for ch, s, t in scored[:12] if s > 0)

    # 补足：每 20% 分位至少一章
    for frac in [0.1, 0.25, 0.4, 0.55, 0.7, 0.85]:
        ch = max(1, int(total * frac))
        selected.add(ch)

    # 第1章必选
    selected.add(1)
    selected.add(total)

    result = sorted(selected)
    if len(result) < 5:
        return _fallback_key_chapters(total)
    return result


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
            api_key, pc.get("model", "deepseek-v4-pro"), curve_prompt,
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
    """从 LLM 输出中解析 key_chapters。支持逗号分隔和 JSON 两种格式。"""
    try:
        m = re.search(r'key_chapters:\s*([\d,\s]+)', text)
        if m:
            chs = [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
            valid = sorted(set(c for c in chs if 1 <= c <= total_ch))
            if len(valid) >= 3:
                return valid
    except Exception:
        pass
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

def _extract_book_name_candidates(book_info_content):
    """从 book_info.md 内容中提取书名候选列表。"""
    candidates = []
    # 匹配格式：1. 《书名》 或 - 《书名》
    pattern = r'^\s*(?:\d+\.|[-*])\s*[《](.+?)[》]'
    for m in re.finditer(pattern, book_info_content, re.MULTILINE):
        candidates.append(m.group(1).strip())
    return candidates


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
    book_name = config.get("book_name", "auto")
    replacements = {
        "新书名": book_name if book_name != "auto" else "（待生成）",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
        "genre": config.get("genre", ""),
        "源文样本": _build_sample_block(config, key_chapters),
    }

    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    user_prompt = load_prompt(
        f"{prompts_dir}/open-book.md",
        base_dir, replacements, mode="api",
        rewrites_dir=config.get("rewrites_dir"),
    )

    sp_name = get_system_prompt_name("open-book.md") or "system-generic.md"
    system_prompt = load_system_prompt(sp_name) or ""

    try:
        pc = get_prompt_config_with_overrides("open-book.md", config)
        if config.get("debug"):
            from utils import debug_dump_prompt
            debug_dump_prompt(config, "open-book", 0, f"{prompts_dir}/open-book.md", system_prompt, user_prompt, sp_name, pc)
        if config.get("prompts_only"):
            print("  [PROMPT] open-book — prompt 已保存至 _debug/")
            if state_mgr:
                state_mgr.phase_done("open-book")
            return True
        result = call_api(
            api_key, pc.get("model", "deepseek-v4-pro"), user_prompt,
            reasoning_effort=pc.get("reasoning_effort", "high"),
            max_tokens=pc.get("max_tokens", 8192),
            temperature=pc.get("temperature", 0.8),
            system_prompt=system_prompt, api_url=api_url,
        )

        files = parse_multi_file_output(result)
        book_info_content = None
        if files:
            for filepath, content in files.items():
                full_path = Path(config["rewrites_dir"]) / filepath
                atomic_write_text(full_path, tag_output(content, "open-book.md"))
                print(f"[OK] {filepath} → {full_path}")
                if filepath == "book_info.md":
                    book_info_content = content
        else:
            path = Path(config["rewrites_dir"]) / "concept.md"
            atomic_write_text(path, tag_output(result, "open-book.md"))
            print(f"[OK] concept.md → {path}")

        # === Stage 3: book_name=auto 时从书名候选中选择 ===
        if book_name == "auto" and book_info_content:
            candidates = _extract_book_name_candidates(book_info_content)
            if candidates:
                selected_name = candidates[0]
                config["book_name"] = selected_name
                print(f"[AUTO] 书名候选: {candidates}")
                print(f"[AUTO] 选定书名: {selected_name}")
                # 更新 rewrites_dir 中的新书名
                old_dir = config.get("rewrites_dir", "")
                if old_dir and "/rewrites/" in old_dir:
                    # 替换路径中的 {新书名} 部分
                    parts = old_dir.split("/rewrites/")
                    if len(parts) == 2:
                        new_dir = f"{parts[0]}/rewrites/{selected_name}"
                        config["rewrites_dir"] = new_dir
                        # 重命名目录
                        old_path = Path(old_dir)
                        new_path = Path(new_dir)
                        if old_path.exists() and not new_path.exists():
                            old_path.rename(new_path)
                            print(f"[OK] 目录重命名: {old_path} → {new_path}")
            else:
                print("[WARN] 未找到书名候选，请手动设置 book_name")

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

