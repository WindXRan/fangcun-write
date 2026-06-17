"""专业 HTML 交付报告 — 甲方友好可视化。"""

import json
import sys
from pathlib import Path
from datetime import datetime

_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib.token_tracker import get_usage, aggregate, format_report
from lib.report_builder import collect_metrics, file_hash, fmt_size, risk_badge, _calc_elapsed
from state_manager import StateManager


def _risk_class(val, thresholds):
    if val <= thresholds[0]:
        return "ok"
    if val <= thresholds[1]:
        return "warn"
    return "fail"


def _bar(width_pct, cls="ok"):
    return f'<div class="bar"><div class="bar-fill {cls}" style="width:{min(width_pct,100):.0f}%"></div></div>'


def generate(config, rewrites_abs, output_dir):
    """生成 07_交付报告.html。"""
    usage_records = get_usage(str(rewrites_abs))
    metrics = collect_metrics(str(rewrites_abs))
    sm = StateManager(str(rewrites_abs))
    state = sm.load()

    source_book = config.get("source_book", "源文")
    new_book = config.get("book_name", "仿写书")
    author = config.get("author", "")
    out = Path(output_dir)

    _, total_token = aggregate(usage_records) if usage_records else (None, {"total": 0, "cost": 0.0})
    total_chars = sum(m["chars"] for m in metrics) if metrics else 0
    avg_ai = sum(m["ai_markers"] for m in metrics) / len(metrics) if metrics else 0
    avg_emotion = sum(m["direct_emotion"] for m in metrics) / len(metrics) if metrics else 0
    avg_metaphor = sum(m["metaphor"] for m in metrics) / len(metrics) if metrics else 0
    avg_pronoun = sum(m.get("pronoun_density", 0) for m in metrics) / len(metrics) if metrics else 0
    avg_chars = total_chars / len(metrics) if metrics else 0
    low, high = avg_chars * 0.8, avg_chars * 1.2
    outliers = sum(1 for m in metrics if m["chars"] < low or m["chars"] > high) if metrics else 0
    elapsed = _calc_elapsed(state)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>交付报告 — {new_book}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Microsoft YaHei', 'PingFang SC', sans-serif;
       background: #f0f2f5; color: #1a1a2e; line-height: 1.7; }}
.wrap {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 60px; }}

/* header */
.header {{ background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); color: #fff;
            border-radius: 12px; padding: 32px; margin-bottom: 24px; }}
.header h1 {{ font-size: 1.6em; margin-bottom: 8px; }}
.header .meta {{ opacity: .85; font-size: .9em; }}
.header .meta span {{ margin-right: 20px; }}

/* cards */
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.card {{ background: #fff; border-radius: 10px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
.card .num {{ font-size: 1.8em; font-weight: 700; color: #1a73e8; }}
.card .label {{ color: #666; font-size: .82em; margin-top: 4px; }}

/* sections */
.section {{ background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
.section h2 {{ font-size: 1.1em; color: #1a73e8; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #e8edf2; }}

/* table */
table {{ width: 100%; border-collapse: collapse; font-size: .9em; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ font-weight: 600; color: #555; background: #f8f9fa; }}
tr:hover td {{ background: #f5f7fa; }}

/* badges */
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: .8em; font-weight: 500; }}
.badge.ok {{ background: #e6f4ea; color: #137333; }}
.badge.warn {{ background: #fef7e0; color: #b8860b; }}
.badge.fail {{ background: #fce8e6; color: #c5221f; }}

/* progress bar */
.bar {{ height: 6px; background: #eee; border-radius: 3px; overflow: hidden; margin: 8px 0; }}
.bar-fill {{ height: 100%; border-radius: 3px; transition: width .6s ease; }}
.bar-fill.ok {{ background: #34a853; }}
.bar-fill.warn {{ background: #fbbc04; }}
.bar-fill.fail {{ background: #ea4335; }}

/* risk table */
.risk {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }}
.risk-item {{ padding: 12px; border-radius: 8px; border-left: 4px solid #34a853; background: #f8f9fa; }}
.risk-item.warn {{ border-left-color: #fbbc04; }}
.risk-item.fail {{ border-left-color: #ea4335; }}
.risk-item .title {{ font-weight: 600; font-size: .9em; }}
.risk-item .value {{ font-size: 1.4em; font-weight: 700; margin: 4px 0; }}
.risk-item .desc {{ font-size: .8em; color: #666; }}

.footer {{ text-align: center; color: #999; font-size: .8em; margin-top: 40px; padding-top: 16px; border-top: 1px solid #e8edf2; }}
a {{ color: #1a73e8; text-decoration: none; }}
code {{ background: #f0f2f5; padding: 1px 5px; border-radius: 3px; font-size: .85em; }}
</style>
</head>
<body>
<div class="wrap">

<div class="header">
  <h1>📖 交付报告 — 《{new_book}》</h1>
  <div class="meta">
    <span>📄 源文：《{source_book}》（{author}）</span>
    <span>📅 {datetime.now().strftime('%Y-%m-%d')}</span>
    <span>🔑 <code>{file_hash(out / f'01_成品_{new_book}.txt') if (out / f'01_成品_{new_book}.txt').exists() else ''}</code></span>
  </div>
</div>

<div class="grid">
  <div class="card"><div class="num">{len(metrics)}</div><div class="label">总章节</div></div>
  <div class="card"><div class="num">{total_chars:,}</div><div class="label">总字数</div></div>
  <div class="card"><div class="num">{total_token.get('total', 0):,}</div><div class="label">Token 消耗</div></div>
  <div class="card"><div class="num">¥{total_token.get('cost', 0):.2f}</div><div class="label">API 费用</div></div>
  <div class="card"><div class="num">{f'{elapsed:.0f}min' if elapsed else '—'}</div><div class="label">总耗时</div></div>
  <div class="card"><div class="num">{avg_ai:.1f}</div><div class="label">AI路标词/章</div></div>
  <div class="card"><div class="num">{avg_chars:.0f}</div><div class="label">平均字数/章</div></div>
  <div class="card"><div class="num">{outliers}</div><div class="label">字数偏差章</div></div>
</div>

<div class="section">
  <h2>📊 AI 痕迹风险热力图</h2>
  <div class="risk">
"""
    items = [
        ("AI 路标词", f"{avg_ai:.1f}/章", "因此/然而/总之 等关联词", _risk_class(avg_ai, [1, 3])),
        ("直抒情感", f"{avg_emotion:.1f}/章", "她感到/她心里 等直白描述", _risk_class(avg_emotion, [2, 5])),
        ("比喻密度", f"{avg_metaphor:.1f}/章", "像/仿佛/如同 等修辞", _risk_class(avg_metaphor, [1, 5])),
        ("代词密度", f"{avg_pronoun:.1f}/千字", "她/他/它 使用频率", _risk_class(avg_pronoun, [30, 60])),
    ]
    for title, value, desc, cls in items:
        html += f'    <div class="risk-item {cls}"><div class="title">{title}</div><div class="value">{value}</div><div class="desc">{desc}</div></div>\n'

    html += """  </div>
</div>

<div class="section">
  <h2>⏱ 各阶段耗时</h2>
  <table>
    <tr><th>阶段</th><th>状态</th><th>耗时</th><th></th></tr>
"""
    order = ["prep", "open_book", "extract", "guides", "write", "validate",
             "postfix", "compare", "unified_review_fix", "trim", "rewrite", "polish", "expand"]
    max_minutes = 0.1
    for pname in order:
        info = state.get("phases", {}).get(pname)
        if not info:
            continue
        s, f = info.get("started"), info.get("finished")
        dur, pct = "", 0
        if s and f:
            try:
                mins = (datetime.fromisoformat(f) - datetime.fromisoformat(s)).total_seconds() / 60
                dur = f"{mins:.1f}min"
                pct = mins
                max_minutes = max(max_minutes, mins)
            except Exception:
                pass
        bar_cls = "ok" if info.get("status") == "done" else "warn" if info.get("status") == "running" else "fail"
        html += f'    <tr><td>{pname}</td><td><span class="badge {bar_cls}">{info.get("status", "?")}</span></td><td>{dur}</td><td>{_bar(pct / max_minutes * 100, bar_cls)}</td></tr>\n'

    html += f'    <tr style="font-weight:600"><td>总计</td><td>—</td><td>{elapsed:.0f}min ({elapsed/60:.1f}h)</td><td></td></tr>\n' if elapsed else ''
    html += """  </table>
</div>

<div class="section">
  <h2>📋 质量明细表</h2>
  <table>
    <tr><th>#</th><th>字数</th><th>AI词</th><th>直抒情</th><th>比喻</th><th>代词/千字</th><th>句长σ</th><th>字数偏差</th></tr>
"""
    for m in metrics[:200]:
        deviation = (m["chars"] - avg_chars) / avg_chars * 100 if avg_chars else 0
        dev_cls = "ok" if abs(deviation) <= 20 else "warn" if abs(deviation) <= 30 else "fail"
        idx = m["file"].replace("ch_", "").replace(".txt", "")
        html += f'    <tr><td>{idx}</td><td>{m["chars"]}</td><td>{m["ai_markers"]}</td><td>{m["direct_emotion"]}</td><td>{m["metaphor"]}</td><td>{m["pronoun_density"]}</td><td>{m["sent_len_stddev"]}</td><td><span class="badge {dev_cls}">{"+" if deviation > 0 else ""}{deviation:.0f}%</span></td></tr>\n'
    if len(metrics) > 200:
        html += f'    <tr><td colspan="8">... 共 {len(metrics)} 章，仅展示前 200 章</td></tr>\n'

    html += """  </table>
</div>

<div class="section">
  <h2>💰 Token 消耗</h2>
"""
    # Token 摘要
    _, total_token = aggregate(usage_records) if usage_records else (None, {})
    if usage_records:
        html += "  <table>\n    <tr><th>阶段</th><th>调用次数</th><th>输入 tokens</th><th>输出 tokens</th><th>合计</th><th>费用</th></tr>\n"
        phases, _ = aggregate(usage_records)
        for pt in sorted(phases.keys()):
            s = phases[pt]
            html += f'    <tr><td>{pt}</td><td>{s["calls"]}</td><td>{s["prompt"]:,}</td><td>{s["completion"]:,}</td><td>{s["total"]:,}</td><td>¥{s["cost"]:.4f}</td></tr>\n'
        html += f'    <tr style="font-weight:600"><td>总计</td><td>{total_token["calls"]}</td><td>{total_token["prompt"]:,}</td><td>{total_token["completion"]:,}</td><td>{total_token["total"]:,}</td><td>¥{total_token["cost"]:.4f}</td></tr>\n'
        html += "  </table>\n"
    else:
        html += "  <p style='color:#999'>（暂未记录）</p>\n"

    html += """</div>

<div class="section">
  <h2>📁 文件清单</h2>
  <table>
    <tr><th>文件</th><th>大小</th><th>SHA256</th></tr>
"""
    for f in sorted(out.iterdir()):
        if f.is_file() and f.suffix in (".md", ".txt", ".html"):
            html += f'    <tr><td>{f.name}</td><td>{fmt_size(f.stat().st_size)}</td><td><code>{file_hash(f)}</code></td></tr>\n'
    for d in sorted(out.iterdir()):
        if d.is_dir():
            nf = len(list(d.rglob("*")))
            html += f'    <tr><td>{d.name}/</td><td>{nf} 个文件</td><td>—</td></tr>\n'

    html += """  </table>
</div>

<div class="footer">
  由 <a href="https://opencode.ai">方寸仿写引擎</a> 自动生成 ·
"""
    if usage_records:
        times = sorted([r.get("timestamp", "") for r in usage_records if r.get("timestamp")])
        if len(times) >= 2:
            html += f'  {times[0]} → {times[-1]} · '
    html += f"""  生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>

</div>
</body>
</html>"""
    return html
