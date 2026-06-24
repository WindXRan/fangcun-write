"""全书级文风摘要：聚合所有章节的风格数据为全书风格画像。

输出: rewrites_dir/book_style_profile.md
在 style_extract 完成后自动调用。config 中 style_profile: true 启用。
"""

import os, re, json
from pathlib import Path
from collections import Counter


def load_metrics(styles_dir):
    """加载所有章节的算法锚点指标。"""
    metrics = []
    for fn in sorted(os.listdir(styles_dir)):
        m = re.match(r'style_(\d+)\.md$', fn)
        if not m:
            continue
        ch = int(m.group(1))
        path = os.path.join(styles_dir, fn)
        content = Path(path).read_text(encoding='utf-8')
        ch_metrics = {'ch': ch}
        for line in content.split('\n'):
            kv = re.match(r'- (\w+):\s*([\d.]+)', line)
            if kv:
                key = kv.group(1)
                val = float(kv.group(2))
                ch_metrics[key] = val
        metrics.append(ch_metrics)
    return metrics


def load_llm_anchors(styles_dir):
    """加载所有 LLM 风格分析的锚点列表。"""
    all_anchors = []
    tones = Counter()
    for fn in sorted(os.listdir(styles_dir)):
        m = re.match(r'style_(\d+)_llm\.md$', fn)
        if not m:
            continue
        path = os.path.join(styles_dir, fn)
        content = Path(path).read_text(encoding='utf-8')

        # Extract tone/narrative style
        for line in content.split('\n'):
            if '叙事基调' in line or '幽默风格' in line or '情绪基调' in line:
                val = line.split('：')[-1].strip() if '：' in line else ''
                if val:
                    tones[val] += 1

        # Extract style anchors list
        if '## 风格锚点' in content:
            anchors_section = content.split('## 风格锚点')[1]
            # Take until next section or end
            next_section = re.search(r'## ', anchors_section)
            if next_section:
                anchors_section = anchors_section[:next_section.start()]
            for line in anchors_section.split('\n'):
                a = re.match(r'- (.+)', line.strip())
                if a:
                    all_anchors.append(a.group(1).strip())

    return all_anchors, tones


def generate_profile(config):
    """生成全书级文风摘要，写入 rewrites_dir/book_style_profile.md。"""
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return

    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())

    styles_dir = None
    # 1. 优先拆文库 styles/
    analyze_dir = config.get("analyze_dir", "")
    if analyze_dir:
        d = Path(analyze_dir) / "styles"
        if d.exists():
            styles_dir = d
    # 2. 回退 _cache/styles/
    if not styles_dir:
        d = Path(base_dir) / "projects" / author / source_book / "_cache" / "styles"
        if d.exists():
            styles_dir = d
    if not styles_dir:
        return

    metrics = load_metrics(styles_dir)
    if not metrics:
        return

    anchors, tones = load_llm_anchors(styles_dir)

    # Compute averages
    avg = {}
    keys = ['段长', '单句段', '对话', '代词密度', '词汇丰富度']
    for k in keys:
        vals = [m[k] for m in metrics if k in m]
        if vals:
            avg[k] = sum(vals) / len(vals)

    # Deduplicate anchors (keep first ~8 most common)
    anchor_counts = Counter(anchors)
    top_anchors = [a for a, _ in anchor_counts.most_common(8)]

    # Top tones
    top_tones = [t for t, _ in tones.most_common(5)]

    # Build output
    lines = [
        '# 全书文风摘要',
        '',
        f'> 基于 {len(metrics)} 章算法锚点 + {len(set(anchor_counts.elements())) if anchor_counts else 0} 条风格分析聚合',
        '',
        '## 核心指标（均值）',
        '',
        '| 指标 | 数值 | 说明 |',
        '|------|------|------|',
        f"| 段落平均长度 | {avg.get('段长', 0):.1f}字 | {_explain_para_len(avg.get('段长', 0))} |",
        f"| 单句段比例 | {avg.get('单句段', 0):.0f}% | 每段{1/(1-avg.get('单句段',0)/100):.1f}句平均 |",
        f"| 对话占比 | {avg.get('对话', 0):.0f}% | {'对话驱动' if avg.get('对话', 0) > 30 else '叙述偏多' if avg.get('对话', 0) < 20 else '均衡'} |",
        f"| 代词密度 | {avg.get('代词密度', 0):.1f}/千字 | {'高（心理描写多）' if avg.get('代词密度', 0) > 22 else '低（动作描写多）' if avg.get('代词密度', 0) < 15 else '适中'} |",
        f"| 词汇丰富度 | {avg.get('词汇丰富度', 0):.3f} | {'词汇丰富' if avg.get('词汇丰富度', 0) > 0.35 else '词汇偏少（网文常见）' if avg.get('词汇丰富度', 0) < 0.25 else '适中'} |",
        '',
    ]

    if top_tones:
        lines.append('## 风格基调')
        lines.append('')
        for t in top_tones:
            lines.append(f'- {t}')
        lines.append('')

    if top_anchors:
        lines.append('## 风格锚点（全书高频）')
        lines.append('')
        lines.append('以下锚点在全书中反复出现，仿写时必须保留至少 3 个：')
        lines.append('')
        for a in top_anchors:
            lines.append(f'- {a}')
        lines.append('')

    profile_text = '\n'.join(lines)

    profile_path = Path(rewrites_dir) / "book_style_profile.md"
    profile_path.write_text(profile_text, encoding='utf-8')
    print(f"  [OK] book_style_profile.md ({len(metrics)}章聚合)")


def _explain_para_len(val):
    if val < 30:
        return "极短段，快节奏"
    if val < 45:
        return "短段，阅读轻松"
    if val < 60:
        return "适中"
    return "偏长篇段落"
