"""Phase 1.5: 文笔指纹 — 算法锚点 + LLM 分析，与 plot-guide 同级并行。

输出: rewrites_dir/styles/style_{N}.md  (人可读 + prompt 可嵌入)
"""

import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import get_source_text, debug_dump_prompt
from lib.text_metrics import count_style_fingerprint, format_style_anchors
from lib.api_client import get_api_url
from prompt_loader import load_system_prompt, load_prompt_str, get_prompt_config_with_overrides


def phase_style_extract(config, start, end, workers=None):
    """并行提取源文每章文笔指纹，跳过已存在文件。"""
    w = workers or config.get("workers", 30)
    styles_dir = Path(config["rewrites_dir"]) / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)

    api_key = config.get("api_key") or config.get("API_KEY")
    if not api_key:
        import os
        api_key = os.environ.get("API_KEY")

    print(f"\n{'=' * 50}")
    print(f"Phase 1.5: 文笔指纹 (ch{start}-{end}, {w}w)")
    print("=" * 50)

    # 扫描待处理章节
    todo = []
    for ch in range(start, end + 1):
        if (styles_dir / f"style_{ch:03d}.md").exists():
            continue
        if get_source_text(config, ch):
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
        api_url = get_api_url(config)
        model = config.get("model", "deepseek-v4-flash")
        llm_count = 0
        with ThreadPoolExecutor(max_workers=min(w, len(todo))) as ex:
            futures = {ex.submit(_llm_one, config, ch, styles_dir, api_key, api_url, model): ch for ch in todo}
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
        f"- 句长: {fp.get('sentence_avg_len','?')}字/句 (短句<8字: {fp.get('sentence_short_ratio',0):.0%})",
        f"- 对话: {fp.get('dialogue_ratio',0):.0%}",
        f"- 段均: {fp.get('paragraph_avg_len','?')}字",
        f"- 代词密度: {fp.get('pronoun_density','?')}/千字",
        f"- 词汇丰富度: {fp.get('ttr','?')}",
        f"- 标点: {fp.get('punct_style','?')}",
        f"- 开头: {fp.get('opening_type','?')} / 结尾: {fp.get('closing_type','?')}",
    ]
    _write_md(styles_dir, ch, anchor="## 算法锚点\n" + "\n".join(items))
    return True


def _llm_one(config, ch, styles_dir, api_key, api_url, model):
    """LLM 分析 → 追加到 style_{N}.md 后半部分。"""
    import requests

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

    pc = get_prompt_config_with_overrides("style-analyze.md", config)
    sys_prompt = load_system_prompt("system-generic.md") or "你是资深文学编辑，分析文笔风格。"

    if config.get("debug") and ch <= 3:
        debug_dump_prompt(config, "style-analyze", ch,
                          "prompts/style-analyze.md", sys_prompt,
                          prompt, "system-generic.md", pc)

    if config.get("prompts_only"):
        return False

    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": pc.get("model", model),
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": pc.get("temperature", 0.3),
                "max_tokens": pc.get("max_tokens", 512),
            },
            timeout=60,
        )
        if resp.status_code == 200:
            analysis = resp.json()["choices"][0]["message"]["content"].strip()
            _write_md(styles_dir, ch, analysis=f"## LLM 风格分析\n{analysis}")
            print(f"  [STYLE] ch{ch:03d}")
            return True
    except Exception as e:
        print(f"  [STYLE] ch{ch:03d} err: {e}")
    return False


def _write_md(styles_dir, ch, anchor=None, analysis=None):
    """合并写入 style_{N}.md。"""
    f = styles_dir / f"style_{ch:03d}.md"
    # 读已有内容
    sections = {}
    if f.exists():
        parts = f.read_text(encoding="utf-8").split("\n## ")
        for p in parts:
            if p.startswith("算法锚点"):
                sections["anchor"] = "## " + p
            elif p.startswith("LLM 风格分析"):
                sections["analysis"] = "## " + p
    if anchor:
        sections["anchor"] = anchor
    if analysis:
        sections["analysis"] = analysis

    content = f"# 第{ch}章 文笔指纹\n\n"
    for key in ["anchor", "analysis"]:
        if key in sections:
            content += sections[key].strip() + "\n\n"
    f.write_text(content.rstrip() + "\n", encoding="utf-8")


def load_style_text(config, ch):
    """加载 style_{N}.md 全文（供写章 prompt 注入）。"""
    f = Path(config["rewrites_dir"]) / "styles" / f"style_{ch:03d}.md"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None
