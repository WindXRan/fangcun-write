"""Phase 3.1: 质量验证（源文指标 vs 仿写指标）"""

import os
import re
import sys
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)

from utils import get_source_text, count_source_chars
from lib.text_metrics import count_metrics


def validate_one(config, ch):
    """验证单章质量：源文指标 vs 仿写指标。返回 (pass: bool, report: str)。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return False, f"ch{ch:03d}: 文件不存在"

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

    # 5. 台词抄袭检测（连续8字以上与源文重合）
    if src_text:
        # 构建源文所有8-gram集合（O(n)）
        src_clean = re.sub(r'[。！？…\n\s]+', '', src_text)
        src_grams = set()
        for i in range(len(src_clean) - 7):
            src_grams.add(src_clean[i:i+8])
        
        # 检测仿写文中的8-gram匹配
        imt_clean = re.sub(r'[。！？…\n\s]+', '', text)
        plagiarisms = []
        matched_ranges = []
        i = 0
        while i < len(imt_clean) - 7:
            gram = imt_clean[i:i+8]
            if gram in src_grams:
                # 找到匹配，扩展找最长匹配
                j = i + 8
                while j < len(imt_clean) and imt_clean[i:j+1] in src_grams:
                    j += 1
                match_len = j - i
                # 避免重叠计数
                if not matched_ranges or i >= matched_ranges[-1][1]:
                    plagiarisms.append((imt_clean[max(0,i-5):i+20], match_len))
                    matched_ranges.append((i, j))
                i = j
            else:
                i += 1
        
        if len(plagiarisms) > 0:
            issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
            for p in plagiarisms[:3]:
                issues.append(f"  '{p[0]}...' ({p[1]}字重合)")

    # 汇总
    all_ok = len(issues) == 0
    status = "[PASS]" if all_ok else "[FAIL]"
    report_parts = [f"ch{ch:03d} {status} | {metrics['chars']}字 | metaphor={metrics['metaphor']} | AI={metrics['ai_markers']} | direct_emo={metrics['direct_emotion']}"]
    if src:
        report_parts.append(f"  源文: {src['chars']}字 | metaphor={src['metaphor']} | AI={src['ai_markers']} | direct_emo={src['direct_emotion']}")
    for i in issues:
        report_parts.append(f"  *ISSUE* {i}")
    for w in warnings:
        report_parts.append(f"  *WARN* {w}")

    return all_ok, '\n'.join(report_parts)


def phase_validate(config, start, end):
    """验证章节质量，报告不达标指标。返回详细结果列表。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 3.1: 质量验证 (ch{start}-{end})")
    print("=" * 50)

    results = []
    ok_count, fail_count = 0, 0
    for ch in range(start, end + 1):
        passed, report = validate_one(config, ch)
        print(report)
        if passed:
            ok_count += 1
            results.append({'ch': ch, 'status': 'PASS'})
        else:
            fail_count += 1
            results.append({'ch': ch, 'status': 'FAIL'})

    if fail_count > 0:
        print(f"\n[WARN] {fail_count}章不达标，建议手动修改或重写。")
    else:
        print(f"\n[OK] 全部通过")

    return results
