"""交付物生成器 — 一键打包交付甲方所需的所有材料。

用法：
  python tools/generate_deliverable.py --config configs/xxx.json
  python tools/generate_deliverable.py --config configs/xxx.json --zip
  python pipeline.py --config configs/xxx.json --phase deliver --end N

输出：
  deliver/{新书名}/
  ├── 00_README.md           # 交付说明
  ├── 01_成品_{新书名}.txt   # 仿写成品
  ├── 02_源文_{源书名}.txt   # 源文全文
  ├── 03_交付报告.md          # 综合数据报告
  ├── 04_chapters/           # 逐章文件
  ├── 05_对比报告/           # 对比详情
  ├── 06_设定资料/           # concept + guides + settings
  └── 07_交付报告.html       # HTML 可视化
"""

import os
import sys
import json
import shutil
import zipfile
import re
import argparse
from pathlib import Path
from datetime import datetime

_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS_DIR))
sys.path.insert(0, str(_TOOLS_DIR / "lib"))

from lib.token_tracker import get_usage
from lib.report_builder import build_report, collect_metrics, fmt_size
from lib.html_report import generate as generate_html
from state_manager import StateManager


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def merge_book_text(root_dir, file_pattern, title, strip=False):
    chapters_dir = Path(root_dir)
    if not chapters_dir.exists():
        return f"# {title}\n\n（目录不存在：{chapters_dir}）\n"
    files = sorted(chapters_dir.glob(file_pattern),
                   key=lambda f: int(re.search(r'(\d+)', f.stem).group(1)) if re.search(r'(\d+)', f.stem) else 0)
    if not files:
        return f"# {title}\n\n（未找到匹配文件：{file_pattern}）\n"
    parts = [f"# {title}\n\n"]
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            parts.append(text.strip() if strip else text)
            parts.append("\n\n")
        except Exception as e:
            parts.append(f"\n\n---\n[{f.name} 读取失败: {e}]\n\n")
    return "".join(parts)


def _make_zip(output_dir, zip_path):
    """压缩交付目录。"""
    base = Path(output_dir)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(base):
            for f in sorted(files):
                fp = Path(root) / f
                arcname = str(fp.relative_to(base.parent))
                z.write(fp, arcname)
    return zip_path


def write_deliverable(config, output_dir, make_zip=False):
    """生成交付物到 output_dir。"""
    rewrites_dir = config.get("rewrites_dir", "")
    author = config.get("author", "未知作者")
    source_book = config.get("source_book", "未知源文")
    new_book = config.get("book_name", "仿写书")

    out = Path(output_dir)
    base_dir = Path(config.get("base_dir", ".")).resolve()
    rewrites_abs = (base_dir / rewrites_dir).resolve() if rewrites_dir else base_dir

    chapters_dir = rewrites_abs / "chapters"
    compare_dir = rewrites_abs / "compare"
    settings_dir = rewrites_abs / "settings"
    export_dir = rewrites_abs / "export"
    guides_dir = rewrites_abs / "guides"

    # ── 准备目录 ──
    dirs = {
        "chapters": out / "chapters",
        "compare": out / "compare",
        "settings": out / "settings",
        "settings/guides": out / "settings" / "guides",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # ── 读取设定文件 ──
    concept_text = ""
    book_info_text = ""
    plot_text = ""
    source_analysis_text = ""
    characters_text = ""
    world_text = ""
    for fname in ["concept.md", "book_info.md", "plot.md", "source_analysis.md", "characters.md", "world.md"]:
        fpath = rewrites_abs / fname
        if fpath.exists():
            txt = fpath.read_text(encoding="utf-8")
            if fname == "concept.md":
                concept_text = txt
            elif fname == "book_info.md":
                book_info_text = txt
            elif fname == "plot.md":
                plot_text = txt
            elif fname == "source_analysis.md":
                source_analysis_text = txt
            elif fname == "characters.md":
                characters_text = txt
            elif fname == "world.md":
                world_text = txt

    # ── 提取简介和书名 ──
    intro_text = ""
    if book_info_text:
        in_intro = False
        intro_lines = []
        for line in book_info_text.split("\n"):
            if "简介" in line and "##" in line:
                in_intro = True
                continue
            if in_intro:
                stripped = line.strip()
                if stripped.startswith("##") or stripped.startswith("==="):
                    break
                if stripped and not stripped.startswith("|") and not stripped.startswith("---"):
                    intro_lines.append(stripped)
        intro_text = "\n".join(intro_lines[:5]) if intro_lines else ""

    # ── 提取源文锁定表 ──
    dna_table = ""
    if source_analysis_text:
        in_dna = False
        dna_lines = []
        for line in source_analysis_text.split("\n"):
            if ("源文锁定" in line or "核心DNA锁定" in line) and "##" in line:
                in_dna = True
            elif in_dna and line.startswith("## "):
                break
            if in_dna:
                dna_lines.append(line)
        dna_table = "\n".join(dna_lines) if dna_lines else ""

    # ── 章节统计 ──
    ch_files = sorted(chapters_dir.glob("ch_*.txt")) if chapters_dir.exists() else []
    total_chars = 0
    ch_stats = []
    for f in ch_files:
        txt = f.read_text(encoding="utf-8")
        body = re.sub(r'\s', '', txt.split("\n", 1)[1] if "\n" in txt else txt)
        chars = len(body)
        total_chars += chars
        ch_stats.append((f.stem, chars))
    total_ch = len(ch_files)

    # ── 00_项目说明书.md（LLM 辅助生成） ──
    # 质量评分
    p012_path = rewrites_abs / "compare" / "p012_issues_report.md"
    quality_rating = "暂无数据"
    if p012_path.exists():
        txt = p012_path.read_text(encoding="utf-8")
        m = re.search(r'总体评级:\s*([\w\s]+)', txt)
        if m:
            quality_rating = m.group(1).strip()

    # 如配置了 llm_enhance，用 LLM 生成 README
    llm_readme = ""
    if config.get("llm_enhance"):
        try:
            from lib.api_client import call_llm
            dna_part = dna_table[:800] if dna_table else ""
            intro_part = intro_text[:600] if intro_text else ""
            prompt = f"""为仿写小说写一份发布会级README。

项目信息：
- 书名：《{new_book}》
- 源文：《{source_book}》（{author}）
- 体量：{total_ch}章 / {total_chars:,}字
- 核心设定：{dna_part}
- 简介：{intro_part}

请写markdown，包含：一句话定位、三大卖点、质量保障、煽动性收尾。不要代码块包裹。"""
            llm_readme = call_llm(config, "deliver-readme", prompt, "")
        except Exception:
            llm_readme = ""

    # ── 源文 vs 仿写章节标题对比 ──
    source_cache_dir = base_dir / "projects" / author / source_book / "_cache" / "chapters"
    ch_compare_rows = []
    for stem, chars in ch_stats:
        ch_num = re.search(r'(\d+)', stem)
        n = int(ch_num.group(1)) if ch_num else 0
        # 仿写标题
        new_title = stem  # fallback
        for f in ch_files:
            if stem in f.stem:
                lines = f.read_text(encoding="utf-8").strip().split("\n")
                if lines:
                    new_title = lines[0][:40]
                break
        # 源文标题
        src_title = ""
        src_file = source_cache_dir / f"第{n}章.txt"
        if src_file.exists():
            lines = src_file.read_text(encoding="utf-8").strip().split("\n")
            if lines:
                src_title = lines[0][:40]
        ch_compare_rows.append(f"| {n} | {src_title} | {new_title} |")
    ch_compare_table = "\n".join(ch_compare_rows[:20])  # 只展示前20章

    readme = llm_readme if llm_readme else f"""# 方寸仿写引擎 — 交付说明书

## 一句话定位

**吃透骨架 · 血肉全换 · 一次直出** —— 方寸仿写引擎自动化 Pipeline，
从开书到交付全流程：开书→写章→审改→对比→交付，一键出稿。

> Demo 项目：《{new_book}》（源文《{source_book}》，{author}）

## 引擎能力

| 能力 | 说明 |
|------|------|
| 🔬 源文锁定 | 自动提取源文不可替代卖点，🔴不可换/🟡可微调/🟢可调整 |
| 📝 全自动写章 | 60 章全本 < 2 小时，含算法审校 + 自动 Trim/Polish/Retry |
| 🛡️ 反抄袭 | 8-gram 台词雷同检测 + 换皮检验（剥名不认源文） |
| 🔍 6+1 指标评分 | 禁用词/排比/心理词/标签密度/段均句数/重复度/段长方差 |
| 🤖 LLM 审稿 | 角色身份/时间线/能力一致性检查 + AI 模式检测 |
| 📦 一键交付 | 成品+源文+对比报告+设定资料+HTML看板，ZIP 打包 |

## 项目概览

| 项目 | 内容 |
|------|------|
| 源文 | 《{source_book}》（{author}） |
| 仿写 | 《{new_book}》 |
| 体量 | {total_ch} 章，{total_chars:,} 字 |
| 整体评级 | {quality_rating} |

## 核心设定

{dna_table if dna_table else "（未生成）"}

## 源文 vs 仿写 · 章节对比（前20章）

| 章 | 源文标题 | 仿写标题 |
|----|---------|---------|
{ch_compare_table}

## 目录说明

```
{out.name}/
├── 00_项目说明书.md       ← 本文件（引擎能力 + 项目概览 + 核心设定）
├── 01_成品.md             ← 仿写全文
├── 02_源文全文.md         ← 源文对照
├── 03_仿写对比报告.md     ← 引擎质量报告
├── chapters/              ← 逐章文件
├── compare/               ← P0/P1/P2 问题详情
└── settings/              ← 完整设定
    ├── concept.md          · 定位+卖点
    ├── book_info.md        · 书名+赛道
    ├── characters.md       · 角色设定
    ├── world.md            · 世界观
    ├── plot.md             · 剧情规划
    └── source_analysis.md  · 源文分析
```

---

*方寸仿写引擎 · 吃透骨架 · 血肉全换 · 一次直出*
"""

    if characters_text:
        import re as _re
        char_names = _re.findall(r'### (.+?)[（(]', characters_text) or _re.findall(r'### (.+)', characters_text)
        if char_names:
            readme += "\n## 👥 主要角色\n\n"
            for name in char_names[:8]:
                readme += f"- {name.strip()}\n"

    readme += """

---

*本文件由方寸仿写引擎自动生成*
"""
    (out / "00_项目说明书.md").write_text(readme, encoding="utf-8")
    print(f"  [OK] 00_项目说明书.md")

    # ── 01_成品.md（合并全文） ──
    dest = out / f"01_成品.md"
    export_files = sorted(export_dir.glob("*.txt")) if export_dir.exists() else []
    if export_files:
        best = max(export_files, key=lambda f: f.stat().st_size)
        if best.stat().st_size > 1000:
            shutil.copy2(best, dest)
            print(f"  [OK] 01_成品 (from export/{best.name}, {fmt_size(best.stat().st_size)})")
        else:
            book_text = merge_book_text(chapters_dir, "ch_*.txt", new_book)
            dest.write_text(book_text, encoding="utf-8")
            print(f"  [OK] 01_成品 (merged from chapters/)")
    else:
        book_text = merge_book_text(chapters_dir, "ch_*.txt", new_book)
        dest.write_text(book_text, encoding="utf-8")
        print(f"  [OK] 01_成品 (merged from chapters/)")

    # ── 02_源文全文.md ──
    source_cache = base_dir / "projects" / author / source_book / "_cache" / "chapters"
    dest_src = out / f"02_源文全文.md"
    source_text = merge_book_text(source_cache, "*.txt", source_book)
    dest_src.write_text(source_text, encoding="utf-8")
    print(f"  [OK] 02_源文全文 ({fmt_size(len(source_text.encode('utf-8')))})")

    # ── metrics ──
    metrics = collect_metrics(str(rewrites_abs))

    # ── 03_仿写对比报告.md ──
    report_md = build_report(config, rewrites_abs, out, metrics)
    (out / "03_仿写对比报告.md").write_text(report_md, encoding="utf-8")
    print(f"  [OK] 03_仿写对比报告.md")

    # ── 07_交付报告.html ──
    try:
        html = generate_html(config, rewrites_abs, out)
        (out / "07_交付报告.html").write_text(html, encoding="utf-8")
        print(f"  [OK] 07_交付报告.html")
    except Exception as e:
        print(f"  [WARN] HTML 报告生成失败: {e}")

    # ── chapters/ ──
    n_copied = 0
    for f in ch_files:
        try:
            shutil.copy2(f, dirs["chapters"] / f.name)
            n_copied += 1
        except Exception:
            pass
    print(f"  [OK] chapters/ ({n_copied} 章)")

    # ── compare/ ──
    n_reports = 0
    if compare_dir.exists():
        for f in sorted(compare_dir.glob("*")):
            if f.is_file() and f.stat().st_size > 0:
                try:
                    shutil.copy2(f, dirs["compare"] / f.name)
                    n_reports += 1
                except Exception:
                    pass
    print(f"  [OK] compare/ ({n_reports} 文件)")

    # ── settings/ ──
    n_settings = 0
    for fname in ["concept.md", "book_info.md", "characters.md", "world.md", "plot.md", "source_analysis.md"]:
        src = rewrites_abs / fname
        if src.exists():
            try:
                shutil.copy2(src, dirs["settings"] / fname)
                n_settings += 1
            except Exception:
                pass
    if settings_dir.exists():
        for f in settings_dir.glob("*"):
            if f.is_file():
                try:
                    shutil.copy2(f, dirs["settings"] / f.name)
                    n_settings += 1
                except Exception:
                    pass
    # guides（前10 + 后5）
    if guides_dir.exists():
        plot_files = sorted(guides_dir.glob("plot_*.md") if guides_dir.exists() else [])
        selected = set()
        for f in plot_files[:10]:
            selected.add(f.name)
        for f in plot_files[-5:]:
            selected.add(f.name)
        for fname in sorted(selected):
            try:
                shutil.copy2(guides_dir / fname, dirs["settings/guides"] / fname)
            except Exception:
                pass
        print(f"  [OK] settings/ ({n_settings} 文件 + {len(selected)} 指南)")

    total_size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\n✅ 交付物已生成 → {out}")
    print(f"   大小: {fmt_size(total_size)}")

    # ── ZIP ──
    if make_zip:
        zip_path = out.parent / f"{new_book}_交付物.zip"
        _make_zip(out, zip_path)
        print(f"   ZIP: {zip_path} ({fmt_size(zip_path.stat().st_size)})")

    return out


def phase_deliver(config, start=None, end=None, state_mgr=None):
    """Pipeline 阶段入口。"""
    rewrites_dir = config.get("rewrites_dir", "")
    base_dir = Path(config.get("base_dir", ".")).resolve()
    new_book = config.get("book_name", "仿写书")
    output_dir = base_dir / rewrites_dir / "deliver" / new_book

    print(f"\n{'=' * 50}")
    print(f"Phase: 交付物生成")
    print(f"{'=' * 50}")
    if state_mgr:
        state_mgr.phase_start("deliver")
    try:
        write_deliverable(config, str(output_dir), make_zip=True)
        if state_mgr:
            state_mgr.phase_done("deliver")
        return {}, {}
    except Exception as e:
        print(f"  [FAIL] {e}")
        if state_mgr:
            state_mgr.phase_failed("deliver", error=str(e))
        return {}, {}


def main():
    parser = argparse.ArgumentParser(description="方寸仿写引擎 — 交付物生成器")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", help="输出目录")
    parser.add_argument("--zip", action="store_true", help="同时生成 ZIP 压缩包")
    args = parser.parse_args()

    config = load_config(args.config)
    base_dir = Path(config.get("base_dir", ".")).resolve()
    rewrites_dir = config.get("rewrites_dir", "")

    if args.output:
        output_dir = Path(args.output)
    else:
        new_book = config.get("book_name", "仿写书")
        output_dir = base_dir / rewrites_dir / "deliver" / new_book

    print(f"交付物生成...\n  配置: {args.config}\n  输出: {output_dir}")
    write_deliverable(config, str(output_dir), make_zip=args.zip)


if __name__ == "__main__":
    main()
