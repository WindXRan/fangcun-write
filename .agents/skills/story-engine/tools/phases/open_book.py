"""Phase 0: Prep（提取元数据+章节目录）
Phase 1: 开书（全读全文 → 源文分析 → 生成设定文件）"""

import json
import os
import re
from pathlib import Path

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
# 源书级分析（独立 phase，调用 source-engine）
# ============================================================

    return "\n\n---\n\n".join(blocks)


def _generate_source_analysis(config):
    """源书级分析（events + skeleton + adaptation），存入 _cache/。独立于开书，可单独调用。"""
    from source_analysis import extract_events, build_skeleton, build_adaptation
    from file_io import load_events, load_skeleton, load_adaptation, get_cache_dir
    from lib.api_client import get_api_key, get_api_url

    cache_dir = get_cache_dir(config)
    api_key = get_api_key(config)
    api_url = get_api_url(config)
    model = config.get("model", "mimo-v2.5-pro")

    if not api_key:
        print("  [SKIP] 未设置 API_KEY，跳过源书级分析")
        return

    prompts_dir = Path(__file__).parent.parent.parent / "prompts"

    # Events
    events = load_events(config)
    if not events:
        print("\n  [源书分析] 事件提取...")
        prompt_file = prompts_dir / "event_extraction.md"
        if prompt_file.exists():
            prompt_text = prompt_file.read_text(encoding="utf-8")
            events = extract_events(config, api_key, api_url, model, prompt_text, workers=5)
        else:
            print("  [SKIP] event_extraction.md 不存在")
    else:
        print(f"\n  [源书分析] 事件表已有 {len(events)} 章，跳过")

    # Skeleton
    skeleton = load_skeleton(config)
    if not skeleton:
        print("\n  [源书分析] 故事骨架...")
        prompt_file = prompts_dir / "skeleton.md"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text(encoding="utf-8")
            system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<storySkeleton>故事骨架内容</storySkeleton>"
            build_skeleton(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
        else:
            print("  [SKIP] skeleton.md 不存在")
    else:
        print(f"\n  [源书分析] 故事骨架已有，跳过")

    # Adaptation
    adaptation = load_adaptation(config)
    if not adaptation:
        print("\n  [源书分析] 改编策略...")
        prompt_file = prompts_dir / "adaptation.md"
        if prompt_file.exists():
            system_prompt = prompt_file.read_text(encoding="utf-8")
            system_prompt += "\n\n你必须使用如下XML格式写入工作区：\n<adaptationStrategy>改编策略内容</adaptationStrategy>"
            build_adaptation(config, api_key, api_url, model, system_prompt, config.get("source_book", ""))
        else:
            print("  [SKIP] adaptation.md 不存在")
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


def _enforce_unique_names(rewrites_dir):
    """强制去重：characters.md 中与源文同名的角色自动改名。"""
    chars_path = Path(rewrites_dir) / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = Path(rewrites_dir) / "characters.md"
    if not chars_path.exists():
        return

    chars_text = chars_path.read_text(encoding="utf-8")
    changed = False
    replacements = {}

    # 找出所有未改名的角色
    for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars_text):
        new_name = m.group(1).strip()
        old_name = m.group(2).strip()
        if new_name == old_name:
            # 生成新名：加姓氏前缀（从角色上下文推断）
            role_section = chars_text[m.end():m.end()+500]
            if re.search(r'女性|女孩|女儿|女主|小姐|姐姐|妹妹', role_section):
                # 女性角色：加"苏"姓（与女主同族）
                generated = f"苏{old_name}" if not old_name.startswith("苏") else f"林{old_name}"
            elif re.search(r'男性|男孩|男主|先生|哥哥|弟弟', role_section):
                # 男性角色：加"秦"姓（与养父同族）
                generated = f"秦{old_name}" if not old_name.startswith("秦") else f"凌{old_name}"
            else:
                # 默认：加"顾"姓
                generated = f"顾{old_name}" if not old_name.startswith("顾") else f"沈{old_name}"

            # 确保新名不与已有角色冲突
            existing = [m2.group(1) for m2 in re.finditer(r'【(.+?)】', chars_text)]
            if generated in existing:
                generated = f"{generated}儿"

            replacements[old_name] = generated
            changed = True
            print(f"  [RENAME] {old_name} → {generated}")

    if not changed:
        return

    # 替换 characters.md
    for old, new in replacements.items():
        chars_text = chars_text.replace(f"【{old}】", f"【{new}】")
        # 正文中也替换（但只替换独立出现的名字，避免误替换）
        chars_text = re.sub(rf'(?<![【\w]){re.escape(old)}(?![】\w])', new, chars_text)

    chars_path.write_text(chars_text, encoding="utf-8")
    print(f"  [OK] characters.md 已更新 {len(replacements)} 个角色名")

    # 替换其他设定文件中的角色名
    settings_dir = Path(rewrites_dir) / "settings"
    for f in settings_dir.glob("*.md"):
        if f.name == "characters.md":
            continue
        text = f.read_text(encoding="utf-8")
        modified = False
        for old, new in replacements.items():
            if old in text:
                text = text.replace(old, new)
                modified = True
        if modified:
            f.write_text(text, encoding="utf-8")
            print(f"  [OK] {f.name} 已同步更新")


def phase_open_book(config, state_mgr=None):
    """开书：从 source-engine 产物生成设定文件。不重新读源文。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (source-engine 产物 → 设定生成)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("open-book"):
            print("concept.md 已完成，跳过")
            return True
        state_mgr.phase_start("open-book")

    base_dir = config.get("base_dir", os.getcwd())
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    rewrites_dir.mkdir(parents=True, exist_ok=True)

    # === 读取 source-engine 产物（不重新读源文）===
    from file_io import load_events, load_skeleton, load_adaptation, get_events_text

    events = load_events(config)
    skeleton = load_skeleton(config)
    adaptation = load_adaptation(config)
    events_text = get_events_text(config)

    if not events:
        print("  [FAIL] events.json 不存在，请先运行 source-engine: --phase event")
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
    source_analysis = f"""# 源文分析

## 事件表（{len(events)}章）
{events_text}

## 故事骨架
{skeleton if skeleton else "（未生成，请先运行 source-engine: --phase skeleton）"}

## 改编策略
{adaptation if adaptation else "（未生成，请先运行 source-engine: --phase adaptation）"}

## 源文角色清单
{"、".join(sorted(all_source_chars))}
"""

    atomic_write_text(rewrites_dir / "source_analysis.md", source_analysis)
    print(f"  [OK] source_analysis.md（从 source-engine 产物组装，{len(source_analysis)}字）")

    # === Stage 2: 5 个并行 agent 生成设定文件 ===
    book_name = config.get("book_name", "auto")
    prompts_dir = config.get("prompts_dir", str(Path(__file__).parent.parent.parent / "prompts"))

    replacements_stage2 = {
        "新书名": book_name if book_name != "auto" else "（待生成）",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "源文分析": source_analysis[:6000],
    }

    print(f"\n  [STAGE 2] 生成设定文件（5 并行 agent）...")

    agents = [
        ("open-book-bookinfo.md",    "bookInfo",    "book_info.md"),
        ("open-book-characters.md",  "characters",  "characters.md"),
        ("open-book-world.md",       "world",       "world.md"),
        ("open-book-plot.md",        "plot",        "plot.md"),
        ("open-book-concept.md",     "concept",     "concept.md"),
    ]

    def run_setting_agent(prompt_file, xml_tag, output_file):
        try:
            user_prompt = load_prompt(
                f"{prompts_dir}/{prompt_file}",
                base_dir, replacements_stage2, mode="api",
                rewrites_dir=config.get("rewrites_dir"),
            )
            sp_name = get_system_prompt_name(prompt_file) or "system-generic.md"
            system_prompt = load_system_prompt(sp_name) or ""
            system_prompt += f"\n\n你必须使用如下XML格式输出全部内容：\n<{xml_tag}>内容</{xml_tag}>"

            result = call_llm(config, prompt_file.replace(".md", ""), user_prompt, system_prompt)

            m = re.search(rf"<{xml_tag}[^>]*>([\s\S]*?)</{xml_tag}>", result)
            content = m.group(1).strip() if m else result.strip()

            full_path = rewrites_dir / output_file
            atomic_write_text(full_path, content)
            print(f"  [OK] {output_file}")
            return output_file, content
        except Exception as e:
            print(f"  [FAIL] {output_file}: {e}")
            return output_file, None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    book_info_content = None
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(run_setting_agent, pf, tag, out): out
            for pf, tag, out in agents
        }
        for future in as_completed(futures):
            output_file, content = future.result()
            if output_file == "book_info.md" and content:
                book_info_content = content

    # === Stage 2.5: 强制去重角色名 ===
    _enforce_unique_names(rewrites_dir)

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
