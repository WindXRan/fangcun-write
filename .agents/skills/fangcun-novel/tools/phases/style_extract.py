"""Phase 1.5: 文笔指纹 — 算法锚点 + LLM 分析，与 plot-guide 同级并行。

输出: rewrites_dir/styles/style_{N}.md  (人可读 + prompt 可嵌入)
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import _path_setup  # noqa: F401
from utils import get_source_text
from lib.text_metrics import count_style_fingerprint, format_style_anchors
from prompt_meta import load_system_prompt, load_prompt_str, get_system_prompt_name, get_prompt_config_with_overrides, safe_format


def _text_hash(text):
    """源文内容哈希（前 2000 字取 md5，防源文微调导致缓存失效）。"""
    return hashlib.md5(text[:2000].encode("utf-8")).hexdigest()[:12]


def _cache_valid(styles_dir, ch, src_text):
    """检查缓存是否有效：文件存在 + 哈希匹配 + LLM 风格 + 结构。"""
    f = styles_dir / f"style_{ch:03d}.md"
    if not f.exists():
        return False
    content = f.read_text(encoding="utf-8")
    if "<!-- hash:" in content:
        cached_hash = content.split("<!-- hash:")[1].split("-->")[0].strip()
        if cached_hash != _text_hash(src_text):
            return False
    else:
        return False
    
    if not (styles_dir / f"style_{ch:03d}_llm.md").exists():
        return False
    if not (styles_dir / f"structure_{ch:03d}.md").exists():
        return False
    
    return True


def phase_style_extract(config, start, end, workers=None):
    """并行提取源文每章文笔指纹，跳过已存在文件。"""
    import os
    w = workers or config.get("workers", 30)
    # 风格缓存放源书级别（共享，不随仿写版本重复计算）
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    styles_dir = Path(base_dir) / "projects" / author / source_book / "_cache" / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)

    api_key = config.get("api_key") or config.get("API_KEY")
    if not api_key:
        api_key = os.environ.get("API_KEY")

    print(f"\n{'=' * 50}")
    print(f"Phase 1.5: 文笔指纹 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    # 判断是否是续写模式
    is_continue = config.get("mode") == "continue"
    
    if is_continue:
        # 续写模式：只提取原作前3章的风格
        print("  续写模式：提取原作前3章风格作为参考")
        todo = []
        for ch in range(1, 4):
            src_text = get_source_text(config, ch)
            if not src_text:
                continue
            if _cache_valid(styles_dir, ch, src_text):
                continue
            todo.append(ch)
    else:
        # 仿写模式：提取指定范围的章节
        todo = []
        for ch in range(start, end + 1):
            src_text = get_source_text(config, ch)
            if not src_text:
                continue
            if _cache_valid(styles_dir, ch, src_text):
                continue
            todo.append(ch)

    if not todo:
        print(f"  所有章节已完成，跳过")
        return

    print(f"  {len(todo)}章待提取...")

    # Layer 1: 算法锚点（并行，0 token）
    t0 = time.time()
    algo_count = 0
    with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
        futures = {ex.submit(_algo_one, config, ch, styles_dir): ch for ch in todo}
        for f in as_completed(futures):
            if f.result():
                algo_count += 1
    print(f"  Layer1 算法锚点: {algo_count}/{len(todo)} ({time.time() - t0:.1f}s)")

    # Layer 2: LLM 分析（已弃用，使用 cyber_author_prompt.md 替代）
    # if api_key:
    #     ...
    else:
        print(f"  Layer2 LLM分析: 跳过 (无 API_KEY)")

    total = list(styles_dir.glob("style_*.md"))
    print(f"  完成: {len(total)} styles 文件")


def _algo_one(config, ch, styles_dir):
    """算法锚点 → 写入 style_{N}.md 前半部分。"""
    text = get_source_text(config, ch)
    if not text:
        return False
    fp = count_style_fingerprint(text)
    items = [
        f"- 段长: {fp.get('paragraph_avg_len','?')}字",
        f"- 单句段: {fp.get('single_sent_ratio',0):.0%} (均段{fp.get('avg_sent_per_para','?')}句)",
        f"- 对话: {fp.get('dialogue_ratio',0):.0%}",
        f"- 代词密度: {fp.get('pronoun_density','?')}/千字",
        f"- 词汇丰富度: {fp.get('ttr','?')}",
    ]
    # 段长分布（短/中/长）
    body = text
    paras = [re.sub(r'\s', '', p) for p in body.split('\n') if p.strip()]
    p_lens = [len(p) for p in paras]
    if p_lens:
        short_p = sum(1 for l in p_lens if l < 15)
        mid_p = sum(1 for l in p_lens if 15 <= l <= 40)
        long_p = sum(1 for l in p_lens if l > 40)
        n_paras = len(p_lens)
        items.append(f"- 段长分布: 短段({short_p*100//n_paras}%) 中段({mid_p*100//n_paras}%) 长段({long_p*100//n_paras}%)")
    _write_md(styles_dir, ch, anchor="## 算法锚点\n" + "\n".join(items), src_text=text)
    return True


def _llm_one(config, ch, styles_dir):
    """LLM 分析 → 追加到 style_{N}.md 后半部分。"""
    from lib.api_client import call_llm

    text = get_source_text(config, ch)
    if not text:
        print(f"  [STYLE] ch{ch:03d} err: 源文不存在")
        return False

    fp = count_style_fingerprint(text)
    anchors = format_style_anchors(fp)
    
    prompt_template = load_prompt_str("style-analyze.md")
    if not prompt_template:
        print(f"  [STYLE] ch{ch:03d} err: style-analyze.md 不存在")
        return False

    prompt = safe_format(prompt_template, {"chapter_text": text[:8000], "style_anchors": anchors})

    sp_name = get_system_prompt_name("style-analyze.md") or "system-generic.md"
    if config.get("debug") and ch <= 3:
        from utils import debug_dump_prompt
        pc = get_prompt_config_with_overrides("style-analyze.md", config)
        sys_prompt = load_system_prompt(sp_name) or ""
        debug_dump_prompt(config, "style-analyze", ch,
                          "prompts/style-analyze.md", sys_prompt,
                          prompt, sp_name, pc)

    if config.get("prompts_only"):
        return False

    sys_prompt = load_system_prompt(sp_name) or "你是资深文学编辑，分析文笔风格。"
    try:
        analysis = call_llm(config, "style-analyze", prompt, sys_prompt).strip()
        _write_md(styles_dir, ch, analysis=f"## LLM 风格分析\n{analysis}", src_text=text)
        print(f"  [STYLE] ch{ch:03d} OK")
        return True
    except Exception as e:
        print(f"  [STYLE] ch{ch:03d} err: {e}")
    return False


def _write_md(styles_dir, ch, anchor=None, analysis=None, src_text=None):
    """提取 XML 标签，直接写文件。不解析内容。"""
    # 算法锚点
    if anchor:
        f = styles_dir / f"style_{ch:03d}.md"
        content = f"# 第{ch}章 文笔指纹\n"
        if src_text:
            content += f"<!-- hash: {_text_hash(src_text)} -->\n"
        content += "\n" + anchor.strip() + "\n"
        f.write_text(content, encoding="utf-8")
    
    if not analysis:
        return
    
    # 提取 XML 标签内容
    def _extract(tag):
        m = re.search(rf'<{tag}>(.*?)</{tag}>', analysis, re.DOTALL)
        return m.group(1).strip() if m else ""
    
    style = _extract("style")
    structure = _extract("structure")
    blacklist = _extract("blacklist")
    
    # 写风格文件
    if style:
        f = styles_dir / f"style_{ch:03d}_llm.md"
        f.write_text(f"# 第{ch}章 风格分析\n\n{style}\n", encoding="utf-8")
    
    # 写结构文件
    if structure:
        f = styles_dir / f"structure_{ch:03d}.md"
        f.write_text(f"# 第{ch}章 结构约束\n\n{structure}\n", encoding="utf-8")
    
    # 写黑名单（增量）
    if blacklist:
        _append_blacklist(styles_dir / "blacklist.md", ch, blacklist)


def _append_blacklist(bl_path, ch, raw_text):
    """增量追加黑名单（直接写原始文本，不解析）。"""
    import platform
    
    # 去重检查：如果本章已写入，跳过
    if bl_path.exists():
        existing = bl_path.read_text(encoding="utf-8")
        if f"来源: 第{ch}章" in existing:
            return
    
    with open(bl_path, 'a', encoding='utf-8') as f:
        if platform.system() != 'Windows':
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            if not bl_path.stat().st_size:
                f.write("# 全书级黑名单\n\n")
                f.write("> 以下元素在仿写中不可复用（包括同义替换）。\n\n")
            f.write(f"<!-- 来源: 第{ch}章 -->\n")
            f.write(raw_text.strip() + "\n\n")
        finally:
            if platform.system() != 'Windows':
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_style_text(config, ch):
    """加载风格文本（供写章 prompt 注入）。
    
    优先级：
    1. cyber_author_prompt.md（赛博作者风格理解）
    2. style_understanding.md（风格理解文档）
    3. style_{N}.md（算法锚点）
    """
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = Path(config.get("base_dir", os.getcwd()))
    source_dir = base_dir / "projects" / author / source_book
    
    # 优先加载赛博作者风格理解
    cyber_author = source_dir / "cyber_author" / "cyber_author_prompt.md"
    if cyber_author.exists():
        return cyber_author.read_text(encoding="utf-8")
    
    # 备选：风格理解文档
    style_understanding = source_dir / "cyber_author" / "style_understanding.md"
    if style_understanding.exists():
        return style_understanding.read_text(encoding="utf-8")
    
    # 兜底：算法锚点
    styles_dir = source_dir / "_cache" / "styles"
    algorithmic = styles_dir / f"style_{ch:03d}.md"
    if algorithmic.exists():
        return algorithmic.read_text(encoding="utf-8")
    
    # 兼容旧结构
    local = Path(config["rewrites_dir"]) / "styles" / f"style_{ch:03d}.md"
    if local.exists():
        return local.read_text(encoding="utf-8")
    
    return None


def load_chapter_structure(config, ch):
    """加载 per-chapter structure_{N}.md + 本章 blacklist 条目（给 plot-guide 用）。

    章对章仿写，每章只看自己的禁用清单，不需要全局黑名单。
    """
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    styles_dir = Path(base_dir) / "projects" / author / source_book / "_cache" / "styles"
    
    parts = []
    
    # 从 blacklist.md 提取本章的条目（按 <!-- 来源: 第N章 --> 分割）
    bl_path = styles_dir / "blacklist.md"
    if bl_path.exists():
        bl_text = bl_path.read_text(encoding="utf-8")
        marker = f"<!-- 来源: 第{ch}章 -->"
        if marker in bl_text:
            # 提取本章条目：从 marker 到下一个 marker 或文件末尾
            start = bl_text.index(marker) + len(marker)
            next_marker = bl_text.find("\n<!-- 来源: 第", start)
            if next_marker == -1:
                entry = bl_text[start:].strip()
            else:
                entry = bl_text[start:next_marker].strip()
            if entry:
                parts.append(f"## 本章禁用清单\n\n{entry}")
    
    # 本章场景功能
    f = styles_dir / f"structure_{ch:03d}.md"
    if f.exists():
        parts.append(f.read_text(encoding="utf-8"))
    
    return "\n\n".join(parts) if parts else None

