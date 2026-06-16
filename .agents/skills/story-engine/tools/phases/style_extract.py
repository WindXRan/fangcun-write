"""Phase 1.5: 文笔指纹 — 算法锚点 + LLM 分析，与 plot-guide 同级并行。

输出: rewrites_dir/styles/style_{N}.md  (人可读 + prompt 可嵌入)
"""

import hashlib
import json
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import get_source_text
from lib.text_metrics import count_style_fingerprint, format_style_anchors
from prompt_loader import load_system_prompt, load_prompt_str


def _text_hash(text):
    """源文内容哈希（前 2000 字取 md5，防源文微调导致缓存失效）。"""
    return hashlib.md5(text[:2000].encode("utf-8")).hexdigest()[:12]


def _cache_valid(styles_dir, ch, src_text):
    """检查缓存是否有效：文件存在 + 哈希匹配。"""
    f = styles_dir / f"style_{ch:03d}.md"
    if not f.exists():
        return False
    content = f.read_text(encoding="utf-8")
    # 检查哈希标记 <!-- hash: xxx -->
    if "<!-- hash:" in content:
        cached_hash = content.split("<!-- hash:")[1].split("-->")[0].strip()
        return cached_hash == _text_hash(src_text)
    return False  # 旧格式无哈希，视为无效


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

    # 扫描待处理章节（哈希校验：源文变了重算）
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

    # Layer 2: LLM 分析（并行，需 API key）
    if api_key:
        t0 = time.time()
        llm_count = 0
        with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
            futures = {ex.submit(_llm_one, config, ch, styles_dir): ch for ch in todo}
            for f in as_completed(futures):
                if f.result():
                    llm_count += 1
        print(f"  Layer2 LLM分析: {llm_count}/{len(todo)} ({time.time() - t0:.1f}s)")
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
        f"- 单句段: {fp.get('single_sent_ratio',0):.0%} (平均每段{fp.get('avg_sent_per_para','?')}句)",
        f"- 对话: {fp.get('dialogue_ratio',0):.0%}",
        f"- 代词密度: {fp.get('pronoun_density','?')}/千字",
        f"- 词汇丰富度: {fp.get('ttr','?')}",
        f"- 标点: {fp.get('punct_style','?')}",
        f"- 开头: {fp.get('opening_type','?')} / 结尾: {fp.get('closing_type','?')}",
    ]
    _write_md(styles_dir, ch, anchor="## 算法锚点\n" + "\n".join(items), src_text=text)
    return True


def _llm_one(config, ch, styles_dir):
    """LLM 分析 → 追加到 style_{N}.md 后半部分。"""
    from lib.api_client import call_llm

    text = get_source_text(config, ch)
    if not text:
        return False

    fp = count_style_fingerprint(text)
    anchors = format_style_anchors(fp)

    prompt_template = load_prompt_str("style-analyze.md")
    if not prompt_template:
        return False

    prompt = prompt_template.format(
        chapter_text=text[:3000],
        style_anchors=anchors,
    )

    if config.get("debug") and ch <= 3:
        from utils import debug_dump_prompt
        pc = get_prompt_config_with_overrides("style-analyze.md", config)
        sys_prompt = load_system_prompt("system-generic.md") or ""
        debug_dump_prompt(config, "style-analyze", ch,
                          "prompts/style-analyze.md", sys_prompt,
                          prompt, "system-generic.md", pc)

    if config.get("prompts_only"):
        return False

    sys_prompt = load_system_prompt("system-generic.md") or "你是资深文学编辑，分析文笔风格。"
    try:
        analysis = call_llm(config, "style-analyze", prompt, sys_prompt).strip()
        _write_md(styles_dir, ch, analysis=f"## LLM 风格分析\n{analysis}", src_text=text)
        print(f"  [STYLE] ch{ch:03d}")
        return True
    except Exception as e:
        print(f"  [STYLE] ch{ch:03d} err: {e}")
    return False


def _write_md(styles_dir, ch, anchor=None, analysis=None, src_text=None):
    """分开写入：算法锚点 → style_{N}.md，LLM 分析 → style_{N}_llm.md。"""
    # 算法锚点
    if anchor:
        f = styles_dir / f"style_{ch:03d}.md"
        content = f"# 第{ch}章 文笔指纹\n"
        if src_text:
            content += f"<!-- hash: {_text_hash(src_text)} -->\n"
        content += "\n" + anchor.strip() + "\n"
        f.write_text(content, encoding="utf-8")
    
    # LLM 分析（单独文件）
    if analysis:
        f_llm = styles_dir / f"style_{ch:03d}_llm.md"
        content = f"# 第{ch}章 LLM 风格分析\n\n" + analysis.strip() + "\n"
        f_llm.write_text(content, encoding="utf-8")


def load_style_text(config, ch):
    """加载 style_{N}.md + style_{N}_llm.md（供写章 prompt 注入）。"""
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    parts = []
    
    # 算法锚点
    shared = Path(base_dir) / "projects" / author / source_book / "_cache" / "styles" / f"style_{ch:03d}.md"
    if shared.exists():
        parts.append(shared.read_text(encoding="utf-8"))
    
    # LLM 分析
    shared_llm = Path(base_dir) / "projects" / author / source_book / "_cache" / "styles" / f"style_{ch:03d}_llm.md"
    if shared_llm.exists():
        parts.append(shared_llm.read_text(encoding="utf-8"))
    
    if parts:
        return "\n\n".join(parts)
    
    # fallback: 仿写版本内（兼容旧结构）
    local = Path(config["rewrites_dir"]) / "styles" / f"style_{ch:03d}.md"
    if local.exists():
        return local.read_text(encoding="utf-8")
    return None

