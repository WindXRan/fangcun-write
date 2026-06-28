"""
writer.py - 通用写作模块 — Direct Generation.
一次 LLM 调用写一章，不做多阶段拆解。
"""

from pathlib import Path

# ── 内联数据读取（不依赖 phase 模块）───────────────────────

def _load_character_data(config):
    """读 meta/characters/*.xml 全部角色卡。"""
    project_dir = Path(config.get("project_dir", ""))
    chars_dir = project_dir / "meta" / "characters"
    if not chars_dir.exists():
        return ""
    parts = []
    for f in sorted(chars_dir.glob("*.xml")):
        parts.append(f.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _load_story_system_prompt(config):
    """加载项目专属 system prompt。
    优先级：project_dir/system-prompt.md → analyze_dir/文风分析.md → 空
    """
    project_dir = config.get("project_dir", "")
    if project_dir:
        baked = Path(project_dir) / "system-prompt.md"
        if baked.exists():
            return baked.read_text(encoding="utf-8")
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        for fname in ["文风分析.md", "文风.md"]:
            sp = Path(analyze_dir) / fname
            if sp.exists():
                return sp.read_text(encoding="utf-8")[:4000]
    return ""


# ── 写章核心 ────────────────────────────────────────────────

def write_chapter(config, ch, mode="imitation", auto_fix=True):
    """写章。只返回文本不保存。
    确认后调 save_chapter(config, ch, text) 写入文件。
    """
    from utils import get_source_text
    import xml.etree.ElementTree as ET

    project_dir = config.get("project_dir") or ""
    base_dir = config.get("base_dir", ".")

    # 构建替换变量
    replacements = {
        "N": str(ch),
        "N03d": f"{ch:03d}",
        "新书名": Path(project_dir).name,
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }

    # 角色数据
    char_data = _load_character_data(config)
    if char_data:
        replacements["name_map"] = char_data
        replacements["characters"] = char_data

    # 字数目标（基于源文字数）
    try:
        src = get_source_text(config, ch)
        if src:
            src_chars = len(src.replace("\n", "").replace(" ", "").replace("\r", ""))
        else:
            src_chars = config.get("target_word_count", 2500)
        target = max(int(src_chars), 1500) if src_chars else 2500
        replacements.setdefault("目标字数", str(target))
        replacements.setdefault("目标字数_min", str(int(target * 0.8)))
        replacements.setdefault("目标字数_max", str(int(target * 1.2)))
    except Exception:
        replacements.setdefault("目标字数", "2500")
        replacements.setdefault("目标字数_min", "2000")
        replacements.setdefault("目标字数_max", "3000")

    # 加载 prompt — 走 load_prompt 统一入口（preset + VariableResolver）
    from prompt_loader import load_prompt
    preset_name = "golden-opening" if ch == 1 else "write-chapter"
    preset_path = str(Path(__file__).resolve().parent / "builtin" / f"{preset_name}.xml")
    try:
        user_prompt = load_prompt(preset_path, base_dir,
            replacements, mode="api", project_dir=project_dir,
            source_dir=config.get("analyze_dir", ""))
    except Exception as e:
        raise Exception(f"加载 prompt 失败: {e}")

    # 二次替换我们的 {key} 占位符（VariableResolver 不认识的）
    for k, v in replacements.items():
        user_prompt = user_prompt.replace("{" + k + "}", v)

    # system prompt（prefix cached，192章不变）
    system_prompt = _load_story_system_prompt(config)

    # user prompt 头部：文风/风格数据
    analyze_dir = config.get("analyze_dir", "")
    style_prepend = ""
    if analyze_dir:
        sp = Path(analyze_dir) / "文风分析.md"
        if sp.exists():
            style_prepend = sp.read_text(encoding="utf-8")
    if not style_prepend:
        sp = Path(project_dir) / "book_style_profile.md"
        if sp.exists():
            style_prepend = sp.read_text(encoding="utf-8")
    if style_prepend:
        user_prompt = f"<style_profile>\n{style_prepend}\n</style_profile>\n\n{user_prompt}"

    # 保存完整渲染 prompt 到 _debug/（始终输出到项目根目录）
    _debug_base = Path(config.get("base_dir", project_dir)) if project_dir else Path.cwd()
    _debug_dir = _debug_base / "_debug"
    try:
        _debug_dir.mkdir(parents=True, exist_ok=True)
        _debug_file = _debug_dir / f"write-chapter_ch{ch:03d}.md"
        _debug_file.write_text(
            f"# ch{ch:03d} — write-chapter\n\n---\n\n## System Prompt\n\n{system_prompt or ''}\n\n"
            f"---\n\n## User Prompt\n\n{user_prompt}\n",
            encoding="utf-8"
        )
        print(f"\n  [DEBUG] 完整 prompt → {_debug_file.resolve()}")
    except Exception as e:
        print(f"\n  [WARN] 无法保存 debug prompt: {e}")

    # 调用 LLM（自动处理 debug / prompts_only）
    from lib.api_client import call_llm
    result = call_llm(config, "write-chapter", user_prompt, system_prompt=system_prompt, ch=ch)

    if config.get("prompts_only"):
        return result

    return result


def preview_chapter(text, ch):
    """预览章节内容（不保存）。"""
    lines = text.strip().split('\n')
    title = lines[0] if lines else f"第{ch}章"
    chars = len(text.replace('\n', '').replace(' ', ''))
    print(f"  [PREVIEW] 第{ch}章 | {chars}字 | 标题: {title}")
    print(f"  {'='*40}")
    print('\n'.join(lines[:8]))
    if len(lines) > 8:
        print(f"  ... 共{len(lines)}行")
    return {"ch": ch, "chars": chars, "title": title}


def save_chapter(config, ch, text):
    """确认后保存章节。返回文件名。"""
    from utils import save_chapter_file as _scf
    project_dir = config.get("project_dir", "")
    fname = _scf(project_dir, ch, text)
    chars = len(text.replace('\n', '').replace(' ', ''))
    print(f"  [SAVED] {fname} ({chars}字)")
    return fname


# ── 章节文件 I/O ────────────────────────────────────────────

def _load_chapter_text(config, ch):
    """加载章节文本。格式: 第X章 章名.txt"""
    from utils import load_chapter_text as _lct
    project_dir = config.get("project_dir", "")
    return _lct(project_dir, ch)


def _save_chapter_text(config, ch, text):
    """保存章节文本。格式: 第X章 章名.txt"""
    from utils import save_chapter_file as _scf
    project_dir = config.get("project_dir", "")
    return _scf(project_dir, ch, text)


# ── 后处理（保留用于手动调用，不再被 pipeline 调度）──

def trim_chapter(config, ch, mode="imitation"):
    """精简章节。"""
    from lib.api_client import call_llm
    text = _load_chapter_text(config, ch)
    current_chars = len(text.replace('\n', '').replace(' ', ''))
    target_chars = int(current_chars * 0.75)
    prompt = f"""请精简以下章节内容，目标字数约{target_chars}字（当前{current_chars}字）。

要求：
1. 保留核心情节和关键对话
2. 删除冗余描写和重复内容
3. 合并相似段落
4. 保持故事连贯性

章节内容：
{text}"""
    result = call_llm(config, "trim-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


def expand_chapter(config, ch, mode="imitation"):
    """扩写章节。"""
    from lib.api_client import call_llm
    text = _load_chapter_text(config, ch)
    current_chars = len(text.replace('\n', '').replace(' ', ''))
    target_chars = int(current_chars * 1.4)
    prompt = f"""请扩写以下章节内容，目标字数约{target_chars}字（当前{current_chars}字）。

要求：
1. 增加环境描写和心理描写
2. 丰富对话内容和互动细节
3. 补充情节过渡和铺垫
4. 保持原有故事框架不变

章节内容：
{text}"""
    result = call_llm(config, "expand-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


def rewrite_chapter(config, ch, mode="imitation", reason=""):
    """重写章节。保留 events.json 章纲，重新生成正文。"""
    from lib.api_client import call_llm
    project_dir = config.get("project_dir", "")
    guide_file = Path(project_dir) / "guides" / f"plot_{ch}.md"
    guide_text = guide_file.read_text(encoding='utf-8') if guide_file.exists() else ""
    reason_hint = f"\n重写原因：{reason}" if reason else ""
    prompt = f"""请根据以下章纲重写第{ch}章正文。

要求：
1. 严格按照章纲的场景设计写作
2. 实现章纲中的关键台词和情节
3. 保持故事连贯性
4. 目标字数：2000-3000字{reason_hint}

章纲：
{guide_text}"""
    result = call_llm(config, "rewrite-chapter", prompt, ch=ch)
    if result:
        _save_chapter_text(config, ch, result)
    return result


# ── 通用 preset 执行器 ──────────────────────────────────────

def run_preset(config, preset_name, ch=1, debug=False, start=None, end=None):
    """运行任意 builtin preset，返回 LLM 输出文本。
    不自动保存——返回后由调用者审查结果，确认后再调 save_multifile_output。

    Args:
        config: 配置字典
        preset_name: preset 文件名（不含 .xml）
        ch: 当前章节号
        debug: 仅输出 prompt 不调 API
        start: 可选范围起始（用于 compare 等需范围的 preset）
        end: 可选范围结束
    Returns:
        LLM 返回文本，或 debug 模式下返回 prompt 文本
    """
    import xml.etree.ElementTree as ET
    from variable_resolver import VariableResolver
    from lib.api_client import call_llm
    from pathlib import Path as _Path

    # 确保 project_dir 在 projects/ 下
    _raw = config.get("project_dir", "")
    if _raw and "projects/" not in _raw.replace("\\", "/"):
        _proj = _Path("projects") / _raw
        if _proj.exists():
            config["project_dir"] = str(_proj)

    _pd = config.get("project_dir") or ""
    preset_path = Path(__file__).resolve().parent / "builtin" / f"{preset_name}.xml"
    if not preset_path.exists():
        raise FileNotFoundError(f"preset 不存在: {preset_path}")

    tree = ET.parse(preset_path)
    root = tree.getroot()
    prompt_text = root.findtext("prompt", "")

    overs = {
        "故事名称": config.get("book_name", "未命名"),
        "source_book": config.get("source_book", ""),
    }
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        events_path = Path(analyze_dir) / "events.json"
        if events_path.exists():
            overs["事件表"] = events_path.read_text(encoding="utf-8")
            overs["源文角色列表"] = overs["事件表"]

    resolver = VariableResolver(str(_pd))
    resolver.set_context(N=ch, start=start or ch, end=end or ch,
                         source_book=config.get("source_book", ""),
                         total_chapters=config.get("total_chapters", "192"))
    resolver.set_user_overrides(overs)
    user_prompt = resolver.render(prompt_text)

    # 检查未解析变量，有则提前返回不调 API，让 LLM 手动处理
    import re as _re
    _missing = sorted(set(_re.findall(r'@\[未(?:定义|找到):[^\]]+\]', user_prompt)))
    if _missing:
        print(f"\n  [BLOCKED] {preset_name}: {len(_missing)} 个变量未解析，跳过 API 调用")
        for _m in _missing:
            print(f"    {_m}")
        return f"[BLOCKED] 以下变量缺失，请先创建对应数据后再重试：\n" + "\n".join(_missing)

    if debug or config.get("prompts_only"):
        _dbg_base = Path(config.get("base_dir") or _pd or ".")
        debug_dir = _dbg_base / "_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / f"{preset_name}.md").write_text(user_prompt, encoding="utf-8")
        print(f"\n  [DEBUG] prompt 已保存 → {(debug_dir / f'{preset_name}.md').resolve()}")
        return user_prompt

    # cover 类 preset 只输出 prompt 不调 API
    if preset_name == "cover-prompt":
        return user_prompt

    return call_llm(config, preset_name, user_prompt, ch=ch)


def save_multifile_output(result, base_dir, preview=False):
    """解析 LLM 输出的 ===FILE:path=== 格式，写入文件。

    Args:
        result: LLM 返回文本
        base_dir: 文件写入根目录
        preview: True 时只打印文件列表不写入（确认预览）
    Returns:
        [(path, chars), ...] 写入（或预览）的文件列表
    """
    import re
    files = re.findall(r'===FILE:(\S+)===\n(.+?)(?=\n===FILE:|\Z)', result, re.DOTALL)
    written = []
    if files:
        base = Path(base_dir)
        for path, content in files:
            if preview:
                print(f"  [PREVIEW] {path} ({len(content)}字)")
            else:
                fp = base / path
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content.strip(), encoding="utf-8")
                print(f"  [OK] {path} ({len(content)}字)")
            written.append((path, len(content)))
    else:
        # 单文件/纯文本输出
        lines = result.strip().split('\n')
        preview_text = '\n'.join(lines[:5])
        print(f"\n{preview_text}\n... (共{len(result)}字)")
        written.append(("(stdout)", len(result)))
    return written


# ── 工具函数（不调 LLM）────────────────────────────────────

def export_book(project_dir, output_path=None):
    """合并 chapters/ 下所有章节为完整 txt。

    Args:
        project_dir: 项目目录
        output_path: 输出文件路径（默认 project_dir/export/全书.txt）
    Returns:
        输出文件路径
    """
    from utils import find_chapter_file, load_chapter_text
    import re
    base = Path(project_dir)
    chapters_dir = base / "chapters"
    if not chapters_dir.exists():
        print("  [ERROR] chapters/ 不存在")
        return ""

    # 获取所有章节号
    files = list(chapters_dir.glob("第*章*.txt")) + list(chapters_dir.glob("ch_*.txt"))
    nums = []
    for f in files:
        m = re.search(r'(\d+)', f.stem)
        if m:
            nums.append(int(m.group(1)))
    nums.sort()

    if not nums:
        print("  [ERROR] 无章节文件")
        return ""

    parts = []
    total = 0
    for n in nums:
        try:
            text = load_chapter_text(str(base), n)
            parts.append(text)
            total += len(text.replace('\n', '').replace(' ', ''))
        except Exception:
            continue

    full = '\n\n'.join(parts)

    if output_path is None:
        output_path = str(base / "export" / "全书.txt")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(full, encoding="utf-8")
    print(f"  [OK] 全书导出: {len(nums)}章 {total:,}字 → {output_path}")
    return output_path


def project_stats(project_dir):
    """输出项目统计：进度、字数、角色出场分布。

    Args:
        project_dir: 项目目录
    Returns:
        dict 统计数据
    """
    from utils import find_chapter_file, load_chapter_text
    import re
    base = Path(project_dir)

    # 章节统计
    chapters_dir = base / "chapters"
    ch_count = 0
    total_chars = 0
    if chapters_dir.exists():
        files = sorted(chapters_dir.glob("第*章*.txt")) + sorted(chapters_dir.glob("ch_*.txt"))
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                ch_count += 1
                total_chars += len(text.replace('\n', '').replace(' ', ''))
            except Exception:
                pass

    # 角色卡统计
    chars_dir = base / "作品信息" / "设定" / "角色"
    char_count = 0
    if chars_dir.exists():
        char_count = len(list(chars_dir.glob("*.xml")))

    # 章纲统计
    guides_dir = base / "正文" / "章纲"
    guide_count = 0
    if guides_dir.exists():
        guide_count = len(list(guides_dir.glob("plot_*.md")))

    stats = {
        "章节数": ch_count,
        "总字数": total_chars,
        "角色卡": char_count,
        "章纲数": guide_count,
    }
    print(f"\n{'='*40}")
    print(f"项目: {base.name}")
    print(f"{'='*40}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return stats


# writer.py 不提供 CLI 入口。函数调用方式：
#
#   from writer import write_chapter, run_preset, save_multifile_output
#
#   # === 两段式：先生成预览，确认后再保存 ===
#   text = write_chapter(config, ch=1)            # 只返回文本
#   preview_chapter(text, ch=1)                    # 预览
#   save_chapter(config, ch=1, text)               # 确认后保存
#
#   result = run_preset(config, "character-extract")
#   save_multifile_output(result, pd, preview=True) # 预览文件列表
#   save_multifile_output(result, pd)                # 确认后写入
#
#   # === 工具函数（不调 LLM） ===
#   export_book(project_dir)                        # 导出全本
#   project_stats(project_dir)                      # 项目统计
