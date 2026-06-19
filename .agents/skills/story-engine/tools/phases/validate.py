"""Phase 3.1: 质量验证（源文指标 vs 仿写指标）"""

import re
import json
from pathlib import Path

from utils import get_source_text, count_source_chars
from lib.text_metrics import count_metrics


def _check_character_names(config, text):
    """检查角色名称是否漂移。返回 issues 列表。"""
    issues = []
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return issues

    # 加载 book_data.json 获取角色名
    book_data_path = Path(rewrites_dir) / "book_data.json"
    if not book_data_path.exists():
        return issues

    try:
        book_data = json.loads(book_data_path.read_text(encoding="utf-8"))
    except Exception:
        return issues

    # 获取所有角色名
    characters = book_data.get("characters", [])
    if not characters:
        return issues

    # 构建角色名映射：{tag: name}
    char_names = {}
    for ch_data in characters:
        tag = ch_data.get("tag_short", ch_data.get("tag", ""))
        name = ch_data.get("name", "")
        if tag and name:
            char_names[tag] = name

    # 从 character_variables 获取变量名
    char_vars = book_data.get("meta", {}).get("character_variables", {})
    
    # 1. 检查所有角色名称是否一致（包括主角、配角、关系型角色）
    all_char_names = list(char_names.values())
    
    # 检查文本中是否出现角色名的变体（如：张三 vs 张三哥、李四 vs 李四爷）
    for name in all_char_names:
        if not name:
            continue
        # 检查是否有变体（加哥/爷/姐/嫂等后缀）
        suffixes = ["哥", "爷", "姐", "嫂", "叔", "婶", "伯", "姨", "弟", "妹"]
        for suffix in suffixes:
            variant = name + suffix
            if variant in text and variant != name:
                issues.append(f"角色名漂移：'{name}' 被写成 '{variant}'")
    
    # 2. 检查关系型角色称谓是否一致
    for ch_data in characters:
        tag = ch_data.get("tag_short", ch_data.get("tag", ""))
        name = ch_data.get("name", "")
        address = ch_data.get("address", "")
        
        if not name or not address:
            continue
        
        # 检查文本中是否出现错误的称谓
        # 例如：设定称谓是"漫漫"，但文本中写成"小漫"或"漫姐"
        # 这里可以添加更复杂的检查逻辑
    
    # 3. 检查是否有源文角色名混入（从源文提取角色名）
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    if source_book and author:
        # 尝试从源文的 characters.md 获取角色名
        source_chars_path = Path("projects") / author / source_book / "characters.md"
        if not source_chars_path.exists():
            source_chars_path = Path("projects") / author / source_book / "settings" / "characters.md"
        
        if source_chars_path.exists():
            try:
                source_chars_text = source_chars_path.read_text(encoding="utf-8")
                # 提取源文角色名（简单正则：## 开头的角色名行）
                source_names = re.findall(r'^##\s*(.+)$', source_chars_text, re.MULTILINE)
                source_names = [n.strip() for n in source_names if n.strip()]
                
                # 检查文本中是否出现源文角色名
                for src_name in source_names:
                    if src_name in text and src_name not in char_names.values():
                        issues.append(f"源文角色名混入：'{src_name}' 出现在仿写文本中")
            except Exception:
                pass
    
    # 4. 检查同一角色在不同章节是否使用不同名字
    # 这需要跨章节检查，暂时在单章检查中不实现
    
    return issues


def _check_trope_repetition(config, text, ch):
    """检查梗重复：同类桥段在多个章节中反复出现。返回 issues 列表。"""
    issues = []
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return issues
    
    # 定义常见梗/桥段模式
    trope_patterns = {
        "吃东西": [
            r"吃[了着着]?\w+",
            r"喝[了着着]?\w+",
            r"馋[着嘴]?",
            r"肚子[饿叫咕]",
            r"红薯|鸡蛋|咸菜|红糖|糖水|桃酥|馍|粥|饭",
        ],
        "怀孕反应": [
            r"孕[吐反]?",
            r"恶心|干呕|吐[了]?",
            r"肚子[大隆起]",
            r"胎[动]?",
        ],
        "婆婆训话": [
            r"婆婆[说骂训念叨]",
            r"陈刘氏[说骂训]",
            r"[严肃板着]脸",
        ],
        "丈夫关心": [
            r"陈建国[看递塞拿给]",
            r"[沉默寡言不说]话",
            r"看了[她一眼]",
        ],
        "工分/劳动": [
            r"工分",
            r"下地|干活|出工",
            r"记[工分账]",
        ],
    }
    
    # 统计当前章中各类梗的出现次数
    trope_counts = {}
    for trope_name, patterns in trope_patterns.items():
        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            count += len(matches)
        if count > 0:
            trope_counts[trope_name] = count
    
    # 检查是否超过阈值（单章中同一梗出现超过3次）
    for trope_name, count in trope_counts.items():
        if count >= 3:
            issues.append(f"梗重复：'{trope_name}' 在本章出现 {count} 次")
    
    # 跨章节检查需要读取其他章节，这里只做单章检查
    # 如果需要跨章节检查，需要在 phase_validate 中实现
    
    return issues


def _check_timeline_continuity(config, ch):
    """检查时间线连续性：前后章时间锚点是否连续。返回 issues 列表。"""
    issues = []
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return issues
    
    # 读取当前章的 plot_guide
    guides_dir = Path(rewrites_dir) / "guides"
    plot_guide_path = guides_dir / f"plot_{ch:03d}.md"
    
    if not plot_guide_path.exists():
        return issues
    
    try:
        plot_guide = plot_guide_path.read_text(encoding="utf-8")
        
        # 提取时间锚点
        time_match = re.search(r'本章时间点[：:]\s*(.+)', plot_guide)
        if time_match:
            current_time = time_match.group(1).strip()
            
            # 如果不是第一章，检查前一章的时间锚点
            if ch > 1:
                prev_plot_path = guides_dir / f"plot_{ch-1:03d}.md"
                if prev_plot_path.exists():
                    prev_plot_guide = prev_plot_path.read_text(encoding="utf-8")
                    prev_time_match = re.search(r'本章时间点[：:]\s*(.+)', prev_plot_guide)
                    if prev_time_match:
                        prev_time = prev_time_match.group(1).strip()
                        
                        # 简单检查：如果时间点相同，可能是重复
                        if current_time == prev_time:
                            issues.append(f"时间线：第{ch}章时间点与第{ch-1}章相同（{current_time}）")
                        
                        # 检查是否有时间倒退（简单检查）
                        # 这里可以添加更复杂的时间解析逻辑
    except Exception:
        pass
    
    return issues


def _check_character_motivation(config):
    """检查配角是否有核心动机。返回 issues 列表。"""
    issues = []
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return issues
    
    # 读取 characters.md
    chars_path = Path(rewrites_dir) / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = Path(rewrites_dir) / "characters.md"
    
    if not chars_path.exists():
        return issues
    
    try:
        chars_text = chars_path.read_text(encoding="utf-8")
        
        # 按角色分块
        blocks = re.split(r'^(## .+)$', chars_text, flags=re.MULTILINE)
        
        for i, block in enumerate(blocks):
            if block.startswith("## "):
                role_name = block.strip().lstrip("#").strip()
                
                # 获取该角色的完整内容
                content = ""
                for j in range(i+1, min(i+10, len(blocks))):
                    if blocks[j].startswith("## "):
                        break
                    content += blocks[j]
                
                # 检查是否有核心动机
                if "核心动机" not in content:
                    # 只对配角和关系型角色报警，主角默认有
                    if role_name not in ("女主", "男主", "女二", "男二"):
                        issues.append(f"配角缺动机：'{role_name}' 没有核心动机字段")
    except Exception:
        pass
    
    return issues


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

    # 8. 角色名称漂移检测
    char_issues = _check_character_names(config, text)
    if char_issues:
        issues.extend(char_issues)

    # 9. 梗重复检测
    trope_issues = _check_trope_repetition(config, text, ch)
    if trope_issues:
        issues.extend(trope_issues)

    # 10. 时间线连续性检测
    timeline_issues = _check_timeline_continuity(config, ch)
    if timeline_issues:
        issues.extend(timeline_issues)

    # 11. 配角动机检测（只在第一章检查一次）
    if ch == 1:
        motivation_issues = _check_character_motivation(config)
        if motivation_issues:
            warnings.extend(motivation_issues)

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

    # 跨章全局一致性检查
    global_issues = _check_global_consistency(config, start, end)
    if global_issues:
        print(f"\n{'=' * 50}")
        print(f"跨章全局一致性检查:")
        print(f"{'=' * 50}")
        for issue in global_issues:
            print(f"  *GLOBAL* {issue}")

    # 存档 metrics 快照
    try:
        from metrics_history import save_snapshot
        save_snapshot(config['rewrites_dir'], chapter_metrics)
        print(f"  [METRICS] 已存档")
    except Exception as e:
        print(f"  [METRICS] 存档失败: {e}")

    return results


def _check_global_consistency(config, start, end):
    """跨章全局一致性检查。返回 issues 列表。"""
    issues = []
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return issues
    
    chapters_dir = Path(rewrites_dir) / "chapters"
    if not chapters_dir.exists():
        return issues
    
    # 收集所有章节的角色名使用情况
    all_char_mentions = {}  # {chapter: [names]}
    all_time_anchors = {}   # {chapter: time_string}
    
    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        try:
            text = ch_file.read_text(encoding="utf-8")
            
            # 提取本章提到的角色名
            # 这里简单用正则匹配，实际可以用NER
            import re
            # 匹配中文人名（2-4个字）
            name_pattern = r'[\u4e00-\u9fa5]{2,4}(?:哥|爷|姐|嫂|叔|婶|伯|姨|弟|妹)?'
            names = re.findall(name_pattern, text)
            all_char_mentions[ch] = list(set(names))
            
            # 提取时间锚点（从plot_guide）
            guides_dir = Path(rewrites_dir) / "guides"
            plot_guide_path = guides_dir / f"plot_{ch:03d}.md"
            if plot_guide_path.exists():
                plot_text = plot_guide_path.read_text(encoding="utf-8")
                time_match = re.search(r'本章时间点[：:]\s*(.+)', plot_text)
                if time_match:
                    all_time_anchors[ch] = time_match.group(1).strip()
        except Exception:
            pass
    
    # 检查角色名一致性
    # 如果某个角色名在前几章频繁出现，但后面突然消失，可能是名字变了
    # 这里可以添加更复杂的检查逻辑
    
    # 检查时间线连续性
    chapters_with_time = sorted(all_time_anchors.keys())
    for i in range(1, len(chapters_with_time)):
        prev_ch = chapters_with_time[i-1]
        curr_ch = chapters_with_time[i]
        prev_time = all_time_anchors[prev_ch]
        curr_time = all_time_anchors[curr_ch]
        
        # 如果时间点相同，可能是重复
        if prev_time == curr_time:
            issues.append(f"时间线：第{curr_ch}章时间点与第{prev_ch}章相同（{curr_time}）")
    
    return issues
