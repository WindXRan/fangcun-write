"""Phase 3.1: 质量验证（源文指标 vs 仿写指标）"""

import re
from pathlib import Path

from utils import get_source_text, count_source_chars
from lib.text_metrics import count_metrics


def validate_one(config, ch):
    """验证单章质量：源文指标 vs 仿写指标。返回 (pass: bool, report: str, metrics: dict)。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return False, f"ch{ch:03d}: 文件不存在", {}

    text = ch_file.read_text(encoding='utf-8')
    metrics = count_metrics(text)
    src_text = get_source_text(config, ch)
    src = count_metrics(src_text) if src_text else None

    issues = []
    warnings = []

    # 1. 字数检查（对标源文）
    target = count_source_chars(config, ch)
    if target > 0:
        deviation = (metrics["chars"] - target) / target
        if deviation > 0.15:
            issues.append(f"字数超标 {metrics['chars']}/{target} (+{deviation:.0%})")
        elif deviation < -0.15:
            issues.append(f"字数不足 {metrics['chars']}/{target} ({deviation:.0%})")
        elif abs(deviation) > 0.10:
            warnings.append(f"字数偏差 {metrics['chars']}/{target} ({deviation:+.0%})")

    # 2. 比喻句检查（不超过源文+3）
    if src:
        limit = src["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append(f"比喻过多 {metrics['metaphor']} (源文{src['metaphor']}, 上限{limit})")

    # 3. AI 路标词（源文水平+1以内）
    if src:
        limit = max(src["ai_markers"] + 1, 1)
        if metrics["ai_markers"] > limit:
            issues.append(f"AI路标词 {metrics['ai_markers']}处 (源文{src['ai_markers']}, 上限{limit})")

    # 4. 直抒情（源文水平+2以内）
    if src:
        limit = max(src["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append(f"直抒情 {metrics['direct_emotion']}处 (源文{src['direct_emotion']}, 上限{limit})")

    # 5. 代词密度（朱雀防线，源文±50%以内）
    if src and src.get("pronoun_density") and src["pronoun_density"] > 0:
        ratio = metrics["pronoun_density"] / src["pronoun_density"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"代词密度 {metrics['pronoun_density']}/千字 (源文{src['pronoun_density']}, ±50%界限)")
        elif ratio > 1.3 or ratio < 0.7:
            warnings.append(f"代词密度偏离 {metrics['pronoun_density']}/千字 (源文{src['pronoun_density']})")

    # 6. 句长标准差（朱雀防线，AI句法均匀度检测，源文±50%以内）
    if src and src.get("sent_len_stddev") and src["sent_len_stddev"] > 0:
        ratio = metrics["sent_len_stddev"] / src["sent_len_stddev"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"句长标准差 {metrics['sent_len_stddev']} (源文{src['sent_len_stddev']}, ±50%界限)")
        elif ratio > 1.3 or ratio < 0.7:
            warnings.append(f"句长标准差偏离 {metrics['sent_len_stddev']} (源文{src['sent_len_stddev']})")

    # 7. 台词抄袭检测（连续8字以上与源文重合）
    if src_text:
        from lib.plagiarism import find_plagiarism
        plagiarisms = find_plagiarism(text, src_text)
        if plagiarisms:
            issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
            for p in plagiarisms[:3]:
                issues.append(f"  '{p['text']}...' ({p['length']}字重合)")

    # 汇总
    all_ok = len(issues) == 0
    status = "[PASS]" if all_ok else "[FAIL]"
    report_parts = [f"ch{ch:03d} {status} | {metrics['chars']}字 | metaphor={metrics['metaphor']} | AI={metrics['ai_markers']} | direct_emo={metrics['direct_emotion']} | pronoun_d={metrics.get('pronoun_density','?')}/千 | sent_sd={metrics.get('sent_len_stddev','?')}"]
    if src:
        report_parts.append(f"  源文: {src['chars']}字 | metaphor={src['metaphor']} | AI={src['ai_markers']} | direct_emo={src['direct_emotion']} | pronoun_d={src.get('pronoun_density','?')}/千 | sent_sd={src.get('sent_len_stddev','?')}")
    for i in issues:
        report_parts.append(f"  *ISSUE* {i}")
    for w in warnings:
        report_parts.append(f"  *WARN* {w}")

    return all_ok, '\n'.join(report_parts), metrics


def phase_validate(config, start, end):
    """验证章节质量，报告不达标指标。返回详细结果列表。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 3.1: 质量验证 (ch{start}-{end})")
    print("=" * 50)

    results = []
    chapter_metrics = []
    ok_count, fail_count = 0, 0
    for ch in range(start, end + 1):
        passed, report, metrics = validate_one(config, ch)
        print(report)
        if passed:
            ok_count += 1
            results.append({'ch': ch, 'status': 'PASS'})
        else:
            fail_count += 1
            results.append({'ch': ch, 'status': 'FAIL'})
        chapter_metrics.append({
            'ch': ch, 'status': 'PASS' if passed else 'FAIL',
            **{k: metrics.get(k, 0) for k in ('chars', 'metaphor', 'ai_markers', 'direct_emotion', 'pronoun_density', 'sent_len_stddev')}
        })

    if fail_count > 0:
        print(f"\n[WARN] {fail_count}章不达标，建议手动修改或重写。")
    else:
        print(f"\n[OK] 全部通过")

    # 存档 metrics 快照
    try:
        from metrics_history import save_snapshot
        save_snapshot(config['rewrites_dir'], chapter_metrics)
        print(f"  [METRICS] 已存档")
    except Exception as e:
        print(f"  [METRICS] 存档失败: {e}")

    return results
