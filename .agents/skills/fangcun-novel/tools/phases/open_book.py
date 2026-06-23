"""Phase 0: Prep（提取元数据+章节目录）
Phase 1: 开书（全读全文 → 源文分析 → 生成设定文件）"""

import json
import os
import re
from pathlib import Path

import _path_setup  # noqa: F401
from utils import (
    get_total_chapters, get_source_title, count_source_chars
)
from state_manager import atomic_write_text
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name
from prompt_loader import load_prompt
from lib.api_client import call_llm


# ============================================================
# Phase 0: Prep（提取元数据+章节目录）
# ============================================================

def phase_prep(config):
    """从原始 TXT 提取头部元数据和章节目录，供 open-book 使用。"""
    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    cache_dir = Path(base_dir) / "projects" / author / source_book / "_cache"
    os.makedirs(cache_dir, exist_ok=True)

    # 提取原始 TXT 头部（书名/作者/简介/标签/等级体系）
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

    # 生成章节目录（从已拆分的章节）
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
# 源书级分析（独立 phase，调用 fangcun-analyze）
# ============================================================


def _generate_source_analysis(config):
    """源书级分析（events + skeleton + adaptation），存入 _cache/。独立于开书，可单独调用。"""
    from source_analysis import extract_events, build_skeleton, build_adaptation
    from source_io import load_events, load_skeleton, load_adaptation, get_cache_dir
    from lib.api_client import get_api_key, get_api_url

    cache_dir = get_cache_dir(config)
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = config.get("model", "mimo-v2.5-pro")

    if not api_key:
        print("  [SKIP] 未设置 API_KEY，跳过源书级分析")
        return

    prompts_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / ".prompts" / "user"

    # Events
    events = load_events(config)
    if not events:
        print("\n  [源书分析] 事件提取...")
        prompt_file = prompts_dir / "事件提取.md"
        if prompt_file.exists():
            prompt_text = prompt_file.read_text(encoding="utf-8")
            events = extract_events(config, api_key, api_url, model, prompt_text, workers=5)
        else:
            print("  [SKIP] 事件提取.md 不存在")
    else:
        print(f"\n  [源书分析] 事件表已有 {len(events)} 章，跳过")

    # Skeleton
    skeleton = load_skeleton(config)
    if not skeleton:
        print("\n  [源书分析] 故事骨架...")
        prompt_file = prompts_dir / "故事骨架.md"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text(encoding="utf-8")
            system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<storySkeleton>故事骨架内容</storySkeleton>"
            build_skeleton(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
        else:
            print("  [SKIP] 故事骨架.md 不存在")
    else:
        print(f"\n  [源书分析] 故事骨架已有，跳过")

    # Adaptation
    adaptation = load_adaptation(config)
    if not adaptation:
        print("\n  [源书分析] 改编策略...")
        prompt_file = prompts_dir / "改编策略.md"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text(encoding="utf-8")
            system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<adaptationStrategy>改编策略内容</adaptationStrategy>"
            build_adaptation(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
        else:
            print("  [SKIP] 改编策略.md 不存在")
    else:
        print(f"\n  [源书分析] 改编策略已有，跳过")

    print(f"\n  [OK] 源书级产物: {cache_dir}")


def phase_source_analysis(config, state_mgr=None):
    """独立 phase：源书级分析。在 open-book 之前调用。"""
    print("\n" + "=" * 50)
    print("Phase 0.5: 源书级分析 (events + skeleton + adaptation)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("source-analysis"):
            print("源书分析已完成，跳过")
            return True
        state_mgr.phase_start("source-analysis")

    try:
        _generate_source_analysis(config)
        if state_mgr:
            state_mgr.phase_done("source-analysis")
        return True
    except Exception as e:
        print(f"\n  [FAIL] source-analysis: {e}")
        if state_mgr:
            state_mgr.phase_failed("source-analysis", error=str(e))
        return False


# ============================================================
# Phase 1: 开书（全读全文 → 源文分析 → 生成设定文件）
# ============================================================

def _extract_book_name_candidates(book_info_content):
    """从 book_info.md 内容中提取书名候选列表。"""
    candidates = []
    pattern = r'^\s*(?:\d+\.|[-*])\s*[《](.+?)[》]'
    for m in re.finditer(pattern, book_info_content, re.MULTILINE):
        candidates.append(m.group(1).strip())
    return candidates


def _split_character_cards(rewrites_dir):
    """将 characters.md 拆分为独立角色卡文件 characters/{名}.md。"""
    chars_path = Path(rewrites_dir) / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = Path(rewrites_dir) / "characters.md"
    if not chars_path.exists():
        return

    chars_text = chars_path.read_text(encoding="utf-8")
    cards_dir = Path(rewrites_dir) / "characters"
    cards_dir.mkdir(parents=True, exist_ok=True)

    # 按 【角色名】 分割
    sections = re.split(r'(?=【[^】]+】)', chars_text)
    count = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        m = re.match(r'【(.+?)】', section)
        if not m:
            continue
        name = m.group(1).strip()
        # 处理合并条目：【林建华 / 林远征 / 林兴源】→ 拆成多个文件
        names = re.split(r'\s*/\s*', name)
        for n in names:
            n = n.strip()
            if not n:
                continue
            # 清理文件名中的非法字符
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', n)
            card_path = cards_dir / f"{safe_name}.md"
            card_path.write_text(section, encoding="utf-8")
            count += 1

    if count > 0:
        print(f"  [OK] 拆分 {count} 个角色卡 → {cards_dir}")


def _format_events_table(events):
    """格式化事件表为可读的markdown表格。"""
    if not events:
        return "（无事件数据）"
    
    # 表头
    lines = ["| 章 | 章名 | 角色 | 事件 | 强度 | 情绪 | 时长 | 类型 |"]
    lines.append("|---|------|------|------|------|------|------|------|")
    
    for e in events:
        ch = e.get("id", "")
        event_text = e.get("event", "")
        
        # 解析event字段（格式：| 章名 | 角色 | 事件 | 强度 | 情绪 | 时长 | 类型 |）
        if event_text.startswith("|"):
            parts = [p.strip() for p in event_text.split("|") if p.strip()]
            if len(parts) >= 7:
                chapter_name = parts[0]
                characters = parts[1]
                description = parts[2]
                intensity = parts[3]
                emotion = parts[4]
                duration = parts[5]
                genre = parts[6]
                
                # 截断过长的描述
                if len(description) > 50:
                    description = description[:47] + "..."
                
                lines.append(f"| {ch} | {chapter_name} | {characters} | {description} | {intensity} | {emotion} | {duration} | {genre} |")
            else:
                # 格式不正确，直接显示原文
                lines.append(f"| {ch} | - | - | {event_text[:80]}... | - | - | - | - |")
        else:
            # 非标准格式，直接显示原文
            lines.append(f"| {ch} | - | - | {event_text[:80]}... | - | - | - | - |")
    
    return "\n".join(lines)


def phase_open_book(config, state_mgr=None):
    """开书：从 fangcun-analyze 产物生成设定文件。不重新读源文。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (fangcun-analyze 产物 → 设定生成)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("open-book"):
            print("concept.md 已完成，跳过")
            return True
        state_mgr.phase_start("open-book")

    base_dir = config.get("base_dir", os.getcwd())
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    rewrites_dir.mkdir(parents=True, exist_ok=True)

    # === 读取 fangcun-analyze 产物（不重新读源文）===
    from source_io import load_events, load_skeleton, load_adaptation, get_events_text

    events = load_events(config)
    skeleton = load_skeleton(config)
    adaptation = load_adaptation(config)
    events_text = get_events_text(config)

    if not events:
        print("  [FAIL] events.json 不存在，请先运行 fangcun-analyze: --phase event")
        if state_mgr:
            state_mgr.phase_failed("open-book", error="events.json 不存在")
        return False

    # 从事件表提取角色列表（源文所有具名角色）
    all_source_chars = set()
    for e in events:
        event_text = e.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 3:
            for c in re.split(r"[、，,]", parts[2].strip()):
                c = c.strip()
                if c:
                    all_source_chars.add(c)

    # 构建 source_analysis.md（从已有产物组装，不调 LLM）
    # 格式化事件表
    formatted_events = _format_events_table(events)
    
    source_analysis = f"""# 源文分析

## 统计信息
- 总章数：{len(events)} 章
- 源文角色：{"、".join(sorted(all_source_chars))}

## 事件表

{formatted_events}

## 故事骨架
{skeleton if skeleton else "（未生成，请先运行 fangcun-analyze: --phase skeleton）"}

## 改编策略
{adaptation if adaptation else "（未生成，请先运行 fangcun-analyze: --phase adaptation）"}
"""

    atomic_write_text(rewrites_dir / "source_analysis.md", source_analysis)
    print(f"  [OK] source_analysis.md（从 fangcun-analyze 产物组装，{len(source_analysis)}字）")

    # === Stage 2: 5 个并行 agent 生成设定文件 ===
    book_name = config.get("book_name", "auto")
    prompts_dir = config.get("prompts_dir", str(Path(__file__).resolve().parent.parent.parent.parent.parent / ".prompts" / "user"))

    replacements_stage2 = {
        "新书名": book_name if book_name != "auto" else "（待生成）",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "源文分析": source_analysis[:6000],
        "源文角色清单": "、".join(sorted(all_source_chars)),
    }

    print(f"\n  [STAGE 2] 生成设定文件...")

    # === Stage 2a: 先生成 characters.md ===
    print(f"  [STAGE 2a] 生成角色设定...")
    try:
        user_prompt = load_prompt(
            f"{prompts_dir}/open-book-characters.md",
            base_dir, replacements_stage2, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )
        sp_name = get_system_prompt_name("open-book-characters.md") or "agent.md"
        system_prompt = load_system_prompt(sp_name) or ""
        system_prompt += "\n\n你必须使用如下XML格式输出全部内容：\n<characters>内容</characters>"
        
        result = call_llm(config, "open-book-characters", user_prompt, system_prompt)
        m = re.search(r"<characters[^>]*>([\s\S]*?)</characters>", result)
        content = m.group(1).strip() if m else result.strip()
        atomic_write_text(rewrites_dir / "characters.md", content)
        print(f"  [OK] characters.md")
    except Exception as e:
        print(f"  [FAIL] characters.md: {e}")
        content = None

    # === Stage 2b: 生成其他设定文件，注入角色名映射 ===
    print(f"  [STAGE 2b] 生成其他设定文件（4 并行 agent）...")

    # 从 characters.md 提取角色名映射，注入到其他 prompt
    characters_content = ""
    chars_path = rewrites_dir / "characters.md"
    if chars_path.exists():
        characters_content = chars_path.read_text(encoding="utf-8")
    
    # 提取角色名映射表
    char_mapping = {}
    for m in re.finditer(r'\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*[男女]\s*\|', characters_content):
        old_name = m.group(1).strip()
        new_name = m.group(2).strip()
        if old_name != "源文名" and new_name != "新名":
            char_mapping[old_name] = new_name
    
    # 构建角色名注入文本
    char_names_text = ""
    if char_mapping:
        char_names_lines = ["## 角色名映射（必须使用这些名字，不可自编）"]
        for old, new in char_mapping.items():
            char_names_lines.append(f"- {old} → {new}")
        char_names_text = "\n".join(char_names_lines)
    
    # 更新 replacements，注入角色名
    replacements_stage2_with_chars = replacements_stage2.copy()
    replacements_stage2_with_chars["角色名映射"] = char_names_text
    replacements_stage2_with_chars["characters.md内容"] = characters_content[:3000]
    
    # 注入市场数据
    try:
        from market_data import load_market_summary
        market_data = load_market_summary(config)
        if market_data:
            replacements_stage2_with_chars["市场数据"] = market_data
    except:
        pass

    # 使用合并后的 open-book-settings.md 一次生成所有设定
    try:
        user_prompt = load_prompt(
            f"{prompts_dir}/open-book-settings.md",
            base_dir, replacements_stage2_with_chars, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )
        sp_name = get_system_prompt_name("open-book-settings.md") or "agent.md"
        system_prompt = load_system_prompt(sp_name) or ""

        result = call_llm(config, "open-book-settings", user_prompt, system_prompt)

        # 从结果中提取各部分内容
        
        # 提取世界观设定
        world_match = re.search(r'(?:## 世界观设定|### 世界观设定)(.*?)(?=## 剧情设定|### 剧情设定|\Z)', result, re.DOTALL)
        world_content = world_match.group(1).strip() if world_match else ""
        
        # 提取剧情设定
        plot_match = re.search(r'(?:## 剧情设定|### 剧情设定)(.*?)(?=## 书籍信息|### 书籍信息|\Z)', result, re.DOTALL)
        plot_content = plot_match.group(1).strip() if plot_match else ""
        
        # 提取书籍信息
        bookinfo_match = re.search(r'(?:## 书籍信息|### 书籍信息)(.*?)$', result, re.DOTALL)
        bookinfo_content = bookinfo_match.group(1).strip() if bookinfo_match else ""
        
        # 提取概念（从书籍信息中提取定位+策略+卖点）
        concept_match = re.search(r'(?:### 定位|定位)(.*?)(?=### 赛道表|\Z)', result, re.DOTALL)
        concept_content = concept_match.group(1).strip() if concept_match else ""
        if not concept_content:
            # 如果没有单独的定位部分，从整个结果中提取
            concept_content = f"# 概念\n\n{result[:1000]}"

        # 保存到文件
        atomic_write_text(rewrites_dir / "world.md", world_content)
        print(f"  [OK] world.md")
        
        atomic_write_text(rewrites_dir / "book_info.md", bookinfo_content)
        print(f"  [OK] book_info.md")
        
        atomic_write_text(rewrites_dir / "concept.md", concept_content)
        print(f"  [OK] concept.md")
        
        book_info_content = bookinfo_content
    except Exception as e:
        print(f"  [FAIL] open-book-settings: {e}")
        book_info_content = None

    # === Stage 2.5: 拆分角色卡 ===
    _split_character_cards(rewrites_dir)

    # === Stage 3: book_name=auto 时从书名候选中选择 ===
    if book_name == "auto" and book_info_content:
        candidates = _extract_book_name_candidates(book_info_content)
        if candidates:
            selected_name = candidates[0]
            config["book_name"] = selected_name
            print(f"\n  [AUTO] 书名候选: {candidates}")
            print(f"  [AUTO] 选定书名: {selected_name}")
            old_dir = config.get("rewrites_dir", "")
            if old_dir and "/rewrites/" in old_dir:
                parts = old_dir.split("/rewrites/")
                if len(parts) == 2:
                    new_dir = f"{parts[0]}/rewrites/{selected_name}"
                    config["rewrites_dir"] = new_dir
                    old_path = Path(old_dir)
                    new_path = Path(new_dir)
                    if old_path.exists() and not new_path.exists():
                        old_path.rename(new_path)
                        print(f"  [OK] 目录重命名: {old_path} → {new_path}")
        else:
            print("\n  [WARN] 未找到书名候选，请手动设置 book_name")

    # === Stage 4: 汇总 book_info.md ===
    _assemble_book_info(config)

    # === 用户确认方向 ===
    if not config.get("prompts_only") and not config.get("skip_confirm"):
        confirmed = _confirm_direction(config)
        if not confirmed:
            print("\n  [STOP] 用户否决开书方向，可修改后重跑")
            if state_mgr:
                state_mgr.phase_failed("open-book", error="用户否决方向")
            return False

    if state_mgr:
        state_mgr.phase_done("open-book")
    return True


def _assemble_book_info(config):
    """汇总各产物，生成完整的 book_info.md。"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.exists():
        return

    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    # 读取源文元数据
    source_meta = ""
    header_path = Path(base_dir) / "projects" / author / source_book / "_cache" / "_header.txt"
    if header_path.exists():
        source_meta = header_path.read_text(encoding="utf-8")

    # 提取源文简介
    source_intro = ""
    if source_meta:
        intro_match = re.search(r'简介[：:]\s*\n(.*?)(?=\n={3,}|\Z)', source_meta, re.DOTALL)
        if intro_match:
            source_intro = intro_match.group(1).strip()

    # 读取 concept.md
    concept = ""
    concept_path = rewrites_dir / "concept.md"
    if concept_path.exists():
        concept = concept_path.read_text(encoding="utf-8")

    # 读取 characters.md
    characters = ""
    chars_path = rewrites_dir / "characters.md"
    if chars_path.exists():
        characters = chars_path.read_text(encoding="utf-8")

    # 提取角色名列表
    char_names = []
    if characters:
        char_names = re.findall(r'【([^】]+)】', characters)
        # 去掉合并条目的斜杠
        cleaned = []
        for n in char_names:
            for part in re.split(r'\s*/\s*', n):
                part = part.strip()
                if part:
                    cleaned.append(part)
        char_names = cleaned

    # 读取已有 book_info.md（LLM 生成的赛道表+书名+简介）
    existing = ""
    info_path = rewrites_dir / "book_info.md"
    if info_path.exists():
        existing = info_path.read_text(encoding="utf-8")

    # 从 concept.md 提取各段
    def _extract_section(text, header):
        pattern = rf'##\s*{re.escape(header)}\s*\n(.*?)(?=\n##\s|\Z)'
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    strategy = _extract_section(concept, "策略")
    selling = _extract_section(concept, "卖点")
    story_core = _extract_section(concept, "故事核")
    pleasure = _extract_section(concept, "核心心理级爽点")
    golden_finger = _extract_section(concept, "金手指及其约束")
    hidden_line = _extract_section(concept, "隐线（人物弧）")
    rhythm = _extract_section(concept, "全局节奏图")
    style = _extract_section(concept, "风格类型")

    # 组装完整 book_info.md
    parts = []

    # 源文信息
    if source_meta:
        # 提取源文基础信息（书名、作者、评分、字数、章数等）
        meta_lines = []
        for line in source_meta.split("\n"):
            line = line.strip()
            if line and not line.startswith("=") and "简介" not in line:
                meta_lines.append(line)
                if len(meta_lines) >= 9:  # 取前9行元数据
                    break
        if meta_lines:
            parts.append("**源文信息**\n")
            parts.append("\n".join(meta_lines))

    if source_intro:
        parts.append(f"\n**源文简介**\n\n{source_intro}")

    parts.append("\n---\n")

    # LLM 生成的赛道表+书名+简介
    if existing:
        parts.append(existing.strip())

    # 核心策略
    if strategy or selling or story_core:
        parts.append("\n---\n")
        parts.append("**核心策略**\n")
        if strategy:
            parts.append(f"- **改编策略**：{strategy}")
        if story_core:
            parts.append(f"- **故事核**：{story_core}")
        if selling:
            parts.append(f"- **卖点**：{selling}")

    # 爽点与金手指
    if pleasure or golden_finger:
        parts.append("\n**爽点与金手指**\n")
        if pleasure:
            parts.append(f"- **核心爽点**：{pleasure}")
        if golden_finger:
            parts.append(f"- **金手指**：{golden_finger}")

    # 人物弧
    if hidden_line:
        parts.append(f"\n**人物弧**：{hidden_line}")

    # 风格
    if style:
        parts.append(f"\n**风格类型**：{style}")

    # 角色清单
    if char_names:
        parts.append(f"\n**角色清单**（{len(char_names)}人）：{'、'.join(char_names)}")

    # 全局节奏图
    if rhythm:
        parts.append(f"\n---\n\n**全局节奏图**\n\n{rhythm}")

    result = "\n".join(parts)
    atomic_write_text(rewrites_dir / "book_info.md", result)
    print(f"  [OK] book_info.md 已汇总（{len(result)}字）")


def _confirm_direction(config):
    """打印开书摘要，等用户确认方向。"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.exists():
        return True

    source_analysis = ""
    concept = ""
    book_info = ""
    for fname, var in [("source_analysis.md", "source_analysis"), ("concept.md", "concept"), ("book_info.md", "book_info")]:
        fpath = rewrites_dir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            if fname == "source_analysis.md":
                source_analysis = content
            elif fname == "concept.md":
                concept = content
            elif fname == "book_info.md":
                book_info = content

    print("\n" + "=" * 60)
    print("  开书方向确认")
    print("=" * 60)

    if source_analysis:
        # 提取核心分析表
        in_table = False
        table_lines = []
        for line in source_analysis.split("\n"):
            if "锁定" in line and ("|" in line or "核心" in line):
                in_table = True
            elif in_table and line.startswith("## "):
                break
            if in_table:
                table_lines.append(line)
        if table_lines:
            print("\n  源文分析：")
            for line in table_lines:
                print(f"  {line}")

    if book_info:
        names = re.findall(r'[《](.+?)[》]', book_info)
        if names:
            print(f"\n  书名候选：{' / '.join(names[:5])}")
        lines = [l.strip() for l in book_info.split("\n") if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("|") and not l.strip().startswith("---")]
        if lines:
            in_intro = False
            intro_lines = []
            for line in book_info.split("\n"):
                if "简介" in line and "##" in line:
                    in_intro = True
                    continue
                if in_intro:
                    stripped = line.strip()
                    if stripped.startswith("##") or stripped.startswith("==="):
                        break
                    if stripped and not stripped.startswith("|") and not stripped.startswith("---"):
                        intro_lines.append(stripped)
            if intro_lines:
                print(f"\n  简介：{''.join(intro_lines[:3])}")

    print("\n" + "=" * 60)

    try:
        answer = input("  方向OK？(y=继续 / n=重跑): ").strip().lower()
        return answer in ("y", "yes", "是", "ok", "")
    except (EOFError, KeyboardInterrupt):
        print("\n  [INFO] 无法交互，默认通过")
        return True


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
