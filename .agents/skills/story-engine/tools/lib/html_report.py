"""发布会级 HTML 报告 — 外行友好，只看大图。"""

import json, sys, re
from pathlib import Path
from datetime import datetime

_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib.report_builder import collect_metrics
from state_manager import StateManager


def generate(config, rewrites_abs, output_dir):
    metrics = collect_metrics(str(rewrites_abs))
    source_book = config.get("source_book", "源文")
    new_book = config.get("book_name", "仿写书")
    author = config.get("author", "")
    n_ch = len(metrics)
    total_chars = sum(m["chars"] for m in metrics) if metrics else 0

    # 读简介
    intro_text = ""
    book_info_path = rewrites_abs / "book_info.md"
    if book_info_path.exists():
        txt = book_info_path.read_text(encoding="utf-8")
        in_intro = False
        for line in txt.split("\n"):
            if "简介" in line and "##" in line:
                in_intro = True
                continue
            if in_intro:
                if line.strip().startswith("##") or line.strip().startswith("==="):
                    break
                if line.strip() and not line.strip().startswith("|") and not line.strip().startswith("---"):
                    intro_text += line.strip() + " "
        intro_text = intro_text[:300]

    # 读书名候选
    book_names = []
    if book_info_path.exists():
        txt = book_info_path.read_text(encoding="utf-8")
        names = re.findall(r'[《](.+?)[》]', txt)
        book_names = [n for n in names if n != source_book][:5]

    # 前10章对比
    chapters_dir = rewrites_abs / "chapters"
    src_cache = Path(config.get("base_dir", ".")) / "projects" / author / source_book / "_cache" / "chapters"
    compare_rows = ""
    for i in range(1, min(11, n_ch + 1)):
        nf = chapters_dir / f"ch_{i:03d}.txt"
        sf = src_cache / f"第{i}章.txt"
        nt = sf.read_text(encoding="utf-8").strip().split("\n")[0][:40] if sf.exists() else "—"
        st = nf.read_text(encoding="utf-8").strip().split("\n")[0][:40] if nf.exists() else "—"
        compare_rows += f"""
    <tr>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#999;width:8%;font-size:.8em">#{i}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#666;font-size:.85em">{nt}</td>
      <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;color:#2d3436;font-weight:500;font-size:.85em">{st}</td>
    </tr>"""

    # 书名候选 HTML
    name_rows = "".join(f'<div style="border:1px solid #f0f0f0;border-radius:8px;padding:12px;text-align:center;font-size:.82em;color:#2d3436">《{n}》</div>\n' for n in book_names[:3])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>方寸仿写引擎 · 交付报告</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,'Microsoft YaHei','PingFang SC',sans-serif; background:#f8f9fa; color:#2d3436; }}
.wrap {{ max-width:800px; margin:0 auto; padding:40px 20px; }}
.hero {{ text-align:center; margin-bottom:40px; }}
.hero h1 {{ font-size:1.8em; font-weight:700; background:linear-gradient(135deg,#6c5ce7,#a29bfe); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:6px; }}
.hero .tagline {{ font-size:1em; color:#636e72; letter-spacing:2px; }}
.hero .demo {{ font-size:.82em; color:#b2bec3; margin-top:10px; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:36px; }}
.card {{ background:#fff; border-radius:14px; padding:18px; text-align:center; box-shadow:0 2px 12px rgba(0,0,0,.04); }}
.card .emoji {{ font-size:1.5em; margin-bottom:4px; }}
.card .title {{ font-size:.85em; font-weight:600; color:#2d3436; }}
.card .desc {{ font-size:.75em; color:#636e72; margin-top:2px; }}
.section {{ background:#fff; border-radius:14px; padding:24px; margin-bottom:16px; box-shadow:0 2px 12px rgba(0,0,0,.04); }}
.section h2 {{ font-size:.9em; font-weight:600; margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid #f0f0f0; }}
.section .sub {{ font-size:.82em; color:#636e72; margin-bottom:12px; line-height:1.8; }}
.book-row {{ display:flex; gap:16px; margin-bottom:16px; }}
.book-card {{ flex:1; border-radius:12px; padding:20px; text-align:center; }}
.book-card.source {{ background:#f1f2f6; }}
.book-card.rewrite {{ background:#6c5ce7; color:#fff; }}
.book-card .label {{ font-size:.75em; opacity:.7; margin-bottom:6px; }}
.book-card .title {{ font-size:1.1em; font-weight:700; }}
.book-card .author {{ font-size:.8em; opacity:.7; margin-top:4px; }}
.name-grid {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }}
table {{ width:100%; border-collapse:collapse; font-size:.85em; }}
th {{ text-align:left; padding:8px 12px; color:#636e72; font-weight:600; font-size:.8em; }}
.stats {{ display:flex; gap:12px; margin-bottom:20px; }}
.stat {{ flex:1; background:#fff; border-radius:14px; padding:18px; text-align:center; box-shadow:0 2px 12px rgba(0,0,0,.04); }}
.stat .num {{ font-size:1.6em; font-weight:700; color:#6c5ce7; }}
.stat .label {{ font-size:.75em; color:#636e72; margin-top:2px; }}
.footer {{ text-align:center; color:#b2bec3; font-size:.75em; margin-top:40px; padding-top:20px; border-top:1px solid #f0f0f0; }}
</style>
</head>
<body>
<div class="wrap">

<div class="hero">
  <h1>方寸仿写引擎</h1>
  <div class="tagline">吃透骨架 · 血肉全换 · 一次直出</div>
  <div class="demo">{datetime.now().strftime('%Y年%m月%d日')} · {n_ch}章 · {total_chars:,}字</div>
</div>

<div class="section">
  <h2>📖 本书简介</h2>
  <div class="sub">{intro_text[:200] if intro_text else ""}</div>
</div>

<div class="book-row">
  <div class="book-card source">
    <div class="label">源文</div>
    <div class="title">《{source_book}》</div>
    <div class="author">{author}</div>
  </div>
  <div class="book-card rewrite">
    <div class="label">仿写</div>
    <div class="title">《{new_book}》</div>
    <div class="author">方寸引擎 生成</div>
  </div>
</div>

"""

    if name_rows:
        html += f"""
<div class="section">
  <h2>🏷️ 书名候选</h2>
  <div class="name-grid">{name_rows}</div>
</div>"""

    html += f"""
<div class="grid">
  <div class="card"><div class="emoji">🎯</div><div class="title">核心DNA锁定</div><div class="desc">🔴不可换/🟡可微调/🟢可调整</div></div>
  <div class="card"><div class="emoji">🔄</div><div class="title">全自动Pipeline</div><div class="desc">开书→写章→审改→交付</div></div>
  <div class="card"><div class="emoji">🔍</div><div class="title">算法+LLM双层审查</div><div class="desc">抄袭/AI痕迹/身份一致性</div></div>
  <div class="card"><div class="emoji">📊</div><div class="title">量化评分体系</div><div class="desc">7大指标自动检测</div></div>
  <div class="card"><div class="emoji">🛡️</div><div class="title">换皮保障</div><div class="desc">剥名不认源文</div></div>
  <div class="card"><div class="emoji">📦</div><div class="title">一键交付</div><div class="desc">成品+报告+设定打包</div></div>
</div>

<div class="stats">
  <div class="stat"><div class="num">{n_ch}</div><div class="label">总章节</div></div>
  <div class="stat"><div class="num">{total_chars:,}</div><div class="label">总字数</div></div>
  <div class="stat"><div class="num">< 2h</div><div class="label">全本耗时</div></div>
</div>

<div class="section">
  <h2>源文 vs 仿写 · 前10章对照</h2>
  <table>
    <tr><th></th><th style="color:#b2bec3;font-weight:400">源文</th><th style="color:#6c5ce7;font-weight:600">仿写</th></tr>
    {compare_rows}
  </table>
</div>

<div class="footer">
  方寸仿写引擎 · {datetime.now().strftime('%Y-%m-%d')}
</div>

</div>
</body>
</html>"""
    return html
