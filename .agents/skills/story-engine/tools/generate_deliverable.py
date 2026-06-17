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
    files = sorted(chapters_dir.glob(file_pattern))
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
        "04_chapters": out / "04_chapters",
        "05_对比报告": out / "05_对比报告",
        "06_设定资料": out / "06_设定资料",
        "06_设定资料/guides": out / "06_设定资料" / "guides",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # ── 00_README.md ──
    readme = f"""# 交付说明 — 《{new_book}》

## 项目信息
- **源文**：《{source_book}》（作者：{author}）
- **仿写成品**：《{new_book}》
- **生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **生成工具**：方寸仿写引擎 v2.0

## 目录结构
```
{out.name}/
├── 00_README.md                     # 本文件
├── 01_成品_{new_book}.txt          # 仿写成品（完整全书）
├── 02_源文_{source_book}.txt       # 源文原文（完整全书）
├── 03_交付报告.md                   # 综合数据报告（Token/时间/质量/风险评估）
├── 04_chapters/                     # 逐章文件
├── 05_对比报告/                     # 源文 vs 仿写逐批对比
├── 06_设定资料/                     # concept.md + 前10后5章指南 + 设定
└── 07_交付报告.html                 # HTML 可视化版（浏览器打开）
```

## 关键保障
- **换皮检验**：剥掉人名地名后认不出源文（plot-guide 阶段保障）
- **冲突替换**：每章冲突类型不同（身份→利益/信息差/道德）
- **台词 0 重合**：6 字以上连续匹配 → 违规（validate 检测）
- **AI 痕迹控制**：路标词数 ≤ 源文+1

## 使用方式
- Markdown 报告可直接阅读
- HTML 报告用浏览器打开，更直观
- 对比报告可喂给 AI 分析（`05_对比报告/对比_*_AI分析.md`）
- 审核报告：每章定量指标 + pass/fail 判定
- 改动报告：逐章换皮评分 + 字数/对话/风格变化
"""
    (out / "00_README.md").write_text(readme, encoding="utf-8")
    print(f"  [OK] 00_README.md")

    # ── 01_成品 ──
    dest = out / f"01_成品_{new_book}.txt"
    export_files = sorted(export_dir.glob("*.txt")) if export_dir.exists() else []
    if export_files:
        best = max(export_files, key=lambda f: f.stat().st_size)
        if best.stat().st_size > 1000:
            shutil.copy2(best, dest)
            print(f"  [OK] 01_成品 (from export/{best.name}, {fmt_size(best.stat().st_size)})")
            src_used = "export"
        else:
            book_text = merge_book_text(chapters_dir, "ch_*.txt", new_book)
            dest.write_text(book_text, encoding="utf-8")
            print(f"  [OK] 01_成品 (merged from chapters/)")
            src_used = "chapters"
    else:
        book_text = merge_book_text(chapters_dir, "ch_*.txt", new_book)
        dest.write_text(book_text, encoding="utf-8")
        print(f"  [OK] 01_成品 (merged from chapters/)")
        src_used = "chapters"

    # ── 02_源文 ──
    source_cache = base_dir / "projects" / author / source_book / "_cache" / "chapters"
    dest_src = out / f"02_源文_{source_book}.txt"
    source_text = merge_book_text(source_cache, "*.txt", source_book)
    dest_src.write_text(source_text, encoding="utf-8")
    print(f"  [OK] 02_源文 ({fmt_size(len(source_text.encode('utf-8')))})")

    # ── 04_chapters ──
    n_copied = 0
    for f in sorted(chapters_dir.glob("ch_*.txt")):
        try:
            shutil.copy2(f, dirs["04_chapters"] / f.name)
            n_copied += 1
        except Exception:
            pass
    print(f"  [OK] 04_chapters ({n_copied} 章)")

    # ── 05_对比报告 ──
    n_reports = 0
    if compare_dir.exists():
        for f in sorted(compare_dir.glob("对比_*_*")):
            try:
                shutil.copy2(f, dirs["05_对比报告"] / f.name)
                n_reports += 1
            except Exception:
                pass
        # 新增：审核报告 + 改动报告
        for f in sorted(compare_dir.glob("审核报告_*")):
            try:
                shutil.copy2(f, dirs["05_对比报告"] / f.name)
                n_reports += 1
            except Exception:
                pass
        for f in sorted(compare_dir.glob("改动报告_*")):
            try:
                shutil.copy2(f, dirs["05_对比报告"] / f.name)
                n_reports += 1
            except Exception:
                pass
    print(f"  [OK] 05_对比报告 ({n_reports} 文件)")

    # ── 06_设定资料 ──
    n_settings = 0
    for fname in ["concept.md", "world.md", "characters.md", "book_data.json"]:
        src = rewrites_abs / fname
        if src.exists():
            try:
                shutil.copy2(src, dirs["06_设定资料"] / fname)
                n_settings += 1
            except Exception:
                pass
    if settings_dir.exists():
        for f in settings_dir.glob("*"):
            if f.is_file():
                try:
                    shutil.copy2(f, dirs["06_设定资料"] / f.name)
                    n_settings += 1
                except Exception:
                    pass
    # guides（前10 + 后5）
    if guides_dir.exists():
        plot_files = sorted(guides_dir.glob("plot_*.md"))
        selected = set()
        for f in plot_files[:10]:
            selected.add(f.name)
        for f in plot_files[-5:]:
            selected.add(f.name)
        for fname in sorted(selected):
            try:
                shutil.copy2(guides_dir / fname, dirs["06_设定资料/guides"] / fname)
            except Exception:
                pass
        print(f"  [OK] 06_设定资料 ({n_settings} 文件 + {len(selected)} 指南)")

    # ── metrics ──
    metrics = collect_metrics(str(rewrites_abs))

    # ── 03_交付报告.md ──
    report_md = build_report(config, rewrites_abs, out, metrics)
    (out / "03_交付报告.md").write_text(report_md, encoding="utf-8")
    print(f"  [OK] 03_交付报告.md")

    # ── 07_交付报告.html ──
    html = generate_html(config, rewrites_abs, out)
    (out / "07_交付报告.html").write_text(html, encoding="utf-8")
    print(f"  [OK] 07_交付报告.html")

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
