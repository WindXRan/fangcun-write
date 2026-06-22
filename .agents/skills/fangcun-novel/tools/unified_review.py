"""
多 Agent 审改系统 — 审查 + 总结层

Agent 架构:
  1a. Batch Review Agents (scatter)   — N个并行，每人审 X 章 (algo+LLM, 7维全检)
  1b. Global Review Agents (scatter)  — 3个并行，通读全书关键章：人设一致性 + 感情逻辑 + 节奏伏笔
  2.  Summary Agent (gather)          — 合并两层结果，去重分级 P0/P1/P2
"""

import os, re, json, time, argparse, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

import _path_setup  # noqa: F401
from lib.constants import AI_MARKERS, AI_MARKER_PATTERN
from lib.text_metrics import count_metrics, get_body_chars
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text
from prompt_meta import load_system_prompt, load_prompt_str, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
try:
    from logger import setup_pipeline_log
except ImportError:
    setup_pipeline_log = lambda cfg: None


@dataclass
class Issue:
    type: str
    severity: str
    priority: str = ""
    desc: str = ""
    fix: str = ""
    auto_fixable: bool = False
    ch: int = 0

@dataclass
class ReviewResult:
    chapters: dict[int, dict] = field(default_factory=dict)
    cross_issues: list[dict] = field(default_factory=list)

@dataclass
class SummaryReport:
    chapters: dict[int, dict] = field(default_factory=dict)
    cross_issues: list[Issue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def issue_dict(i):
    return {"type": i.type, "severity": i.severity, "priority": i.priority,
            "desc": i.desc, "fix": i.fix, "auto_fixable": i.auto_fixable, "ch": i.ch}


def review_agent(config, chapter_batch, agent_id=0):
    """单个审查 agent。LLM 审所有章 + algo 补充机械检测。"""
    result = ReviewResult()
    n = len(chapter_batch)

    # Step 1: LLM 审所有章（主力）
    print(f"    [审查#{agent_id}] LLM 审稿: {n} 章...", flush=True)
    try:
        ch_data, cross = _llm_batch_review(config, chapter_batch)
        for ch_str, data in ch_data.items():
            ch = int(ch_str)
            result.chapters[ch] = {"score": data.get("score", 50), "issues": data.get("issues", [])}
        result.cross_issues.extend(cross)
        print(f"    [审查#{agent_id}] LLM 审稿完成", flush=True)
    except Exception as e:
        print(f"    [审查#{agent_id}] LLM 审稿失败: {e}", flush=True)
        # LLM 失败时用 algo 结果兜底
        for ch in chapter_batch:
            result.chapters[ch] = {"score": 0, "issues": [{"type": "error", "severity": "high", "desc": f"LLM失败: {e}"}]}

    # Step 2: algo 补充机械检测（快速、低成本）
    done_algo = 0
    with ThreadPoolExecutor(max_workers=len(chapter_batch)) as ex:
        futures = {ex.submit(_algo_check, config, ch): ch for ch in chapter_batch}
        for f in as_completed(futures):
            ch = futures[f]
            try:
                algo_result = f.result()
                if ch not in result.chapters:
                    result.chapters[ch] = algo_result
                else:
                    # 合并 algo 结果到 LLM 结果
                    existing = {i["desc"][:30] for i in result.chapters[ch].get("issues", [])}
                    for issue in algo_result.get("issues", []):
                        if issue["desc"][:30] not in existing:
                            result.chapters[ch]["issues"].append(issue)
                            existing.add(issue["desc"][:30])
                    result.chapters[ch]["score"] = min(
                        result.chapters[ch].get("score", 100),
                        algo_result.get("score", 50)
                    )
            except Exception as e:
                if ch not in result.chapters:
                    result.chapters[ch] = {"score": 0, "issues": [{"type": "error", "severity": "high", "desc": str(e)}]}
            done_algo += 1
            print(f"    [审查#{agent_id}] algo 补充: {done_algo}/{n} 章", flush=True)

    return result


def _algo_check(config, ch):
    """单章算法检查（复用 validate.py 的 validate_one）。"""
    from phases.validate import validate_one
    passed, report, metrics = validate_one(config, ch)
    
    # 转换为统一格式
    issues = []
    if not passed:
        for line in report.split('\n'):
            if '*ISSUE*' in line:
                desc = line.replace('*ISSUE*', '').strip()
                issues.append({"type": "algo", "severity": "high", "desc": desc, "auto_fixable": False})
            elif '*WARN*' in line:
                desc = line.replace('*WARN*', '').strip()
                issues.append({"type": "algo", "severity": "medium", "desc": desc, "auto_fixable": False})
    
    score = 100 if passed else 60
    return {"score": score, "issues": issues}


# ============================================================
# Layer 1b: 全局维度审查（3 个 agent 并行）
# ============================================================

def _select_key_chapters(chapter_nums, n=10):
    """选择代表性章节：头3 + 每20%分位 + 尾3，最多 n 章。"""
    if len(chapter_nums) <= n:
        return list(chapter_nums)
    picks = set(chapter_nums[:3])  # 头3
    picks.add(chapter_nums[-1])    # 尾1
    picks.add(chapter_nums[-2])    # 尾2
    picks.add(chapter_nums[-3])    # 尾3
    # 每20%分位
    for pct in (0.2, 0.4, 0.6, 0.8):
        idx = int(len(chapter_nums) * pct)
        idx = min(idx, len(chapter_nums) - 1)
        picks.add(chapter_nums[idx])
    return sorted(picks)[:n]


def _load_concept(config):
    """加载 concept.md 内容。"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    for name in ("concept.md", "settings/concept.md"):
        p = rewrites_dir / name
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def _load_key_chapters_text(config, key_chapters, max_chars_per_ch=1500):
    """加载关键章节文本。"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    chapters_dir = rewrites_dir / "chapters"
    parts = []
    for ch in key_chapters:
        f = chapters_dir / f"ch_{ch:03d}.txt"
        if f.exists():
            text = f.read_text(encoding="utf-8")
            parts.append(f"--- 第{ch}章 ---\n{text[:max_chars_per_ch]}")
    return "\n\n".join(parts)


def _parse_global_issues(llm_output, dimension):
    """解析全局维度 agent 的输出为 issue 列表。"""
    issues = []
    # 匹配 P0/P1/P2 标记的问题
    for m in re.finditer(
        r'[-•]\s*\[?(P[012])\]?\s*[:：]\s*(.+?)(?:\n|$)', llm_output
    ):
        prio = m.group(1)
        desc = m.group(2).strip()
        if desc:
            issues.append({
                "type": dimension,
                "severity": "high" if prio == "P0" else ("medium" if prio == "P1" else "low"),
                "priority": prio,
                "desc": f"【全局{dimension}】{desc}",
                "fix": "",
                "auto_fixable": False,
            })
    # 也匹配 markdown 表格行
    for m in re.finditer(
        r'\|\s*(P[012])\s*\|(.+?)\|(.+?)\|', llm_output
    ):
        prio = m.group(1)
        desc = m.group(2).strip()
        fix = m.group(3).strip()
        if desc:
            issues.append({
                "type": dimension,
                "severity": "high" if prio == "P0" else ("medium" if prio == "P1" else "low"),
                "priority": prio,
                "desc": f"【全局{dimension}】{desc}",
                "fix": fix,
                "auto_fixable": False,
            })
    return issues


_GLOBAL_PROMPT_TEMPLATE = """你是资深网文编辑，负责全局维度审查：{dimension_name}。

## 审查对象

{concept_section}

## 关键章节内容

{chapters_text}

## 审查任务

{task_desc}

## 输出格式

逐条列出问题，每条格式：
- [P0/P1/P2] 问题描述

没有问题则输出"未发现全局{dimension_name}问题"。
"""


def _global_agent_character(config, key_chapters, concept):
    """全局 Agent A：人设一致性 + 人名检查（对照行为卡片逐章检查）。"""
    from lib.api_client import call_llm

    chapters_text = _load_key_chapters_text(config, key_chapters)
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    base_dir = Path(config.get("base_dir", "."))
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    # 加载角色卡（新书）
    chars_path = rewrites_dir / "characters.md"
    characters = chars_path.read_text(encoding="utf-8") if chars_path.exists() else ""

    # 加载源文角色名（用于检测混入）
    source_chars_section = ""
    source_chars_path = base_dir / "projects" / author / source_book / "characters.md"
    if not source_chars_path.exists():
        source_chars_path = base_dir / "projects" / author / source_book / "settings" / "characters.md"
    if source_chars_path.exists():
        source_text = source_chars_path.read_text(encoding="utf-8")
        source_names = re.findall(r'【([^】]+)】', source_text)
        if source_names:
            source_chars_section = f"\n\n## 源文角色名（禁止在仿写中出现）\n\n{'、'.join(source_names)}"

    # 加载角色名映射表（如有）
    name_map_section = ""
    for map_name in ("name_map.md", "settings/name_map.md"):
        map_path = rewrites_dir / map_name
        if map_path.exists():
            name_map_section = f"\n\n## 角色名映射表\n\n{map_path.read_text(encoding='utf-8')[:2000]}"
            break

    concept_section = f"## 角色设定\n\n{characters}{source_chars_section}{name_map_section}\n\n## 核心策略\n\n{concept[:3000]}"
    task_desc = """检查以下问题：

### 人名一致性
1. 是否有源文角色名混入仿写文本（对照"源文角色名"列表，发现一个就是P0）
2. 同一角色在不同章节是否使用了不同名字（跨章人名不一致）
3. 角色称谓/身份是否前后一致（如某章叫"张三哥"另一章叫"张三"）
4. 角色名是否符合映射表（对照"角色名映射表"）

### 人设一致性
5. 角色核心性格在各章是否一致（对照角色设定）
6. 角色行为模式是否随剧情合理渐进（不能突然转变）
7. 配角是否在需要时出场（不能消失或凭空出现）
8. 角色的能力边界是否一致（不能跨章波动）"""

    prompt = _GLOBAL_PROMPT_TEMPLATE.format(
        dimension_name="人设一致性",
        concept_section=concept_section,
        chapters_text=chapters_text,
        task_desc=task_desc,
    )

    try:
        content = call_llm(config, "unified-review", prompt, "")
        return _parse_global_issues(content, "character")
    except Exception as e:
        print(f"    [全局-人设] 失败: {e}", flush=True)
        return []


def _global_agent_emotion(config, key_chapters, concept):
    """全局 Agent B：感情逻辑（阶段渐进+情绪真实性）。"""
    from lib.api_client import call_llm

    chapters_text = _load_key_chapters_text(config, key_chapters)
    concept_section = f"## 核心策略\n\n{concept[:3000]}"
    task_desc = """检查以下问题：
1. 主角的感情线是否按阶段合理渐进（不能跳跃）
2. 亲情/友情/爱情的转变是否有铺垫（不能突变）
3. 情绪反应是否符合角色性格（不能所有人都一样的反应）
4. 高潮情绪是否有足够的压抑铺垫（不能平地起高楼）
5. 情绪节奏是否张弛有度（不能一直高强度或一直低沉）"""

    prompt = _GLOBAL_PROMPT_TEMPLATE.format(
        dimension_name="感情逻辑",
        concept_section=concept_section,
        chapters_text=chapters_text,
        task_desc=task_desc,
    )

    try:
        content = call_llm(config, "unified-review", prompt, "")
        return _parse_global_issues(content, "emotion")
    except Exception as e:
        print(f"    [全局-感情] 失败: {e}", flush=True)
        return []


def _global_agent_rhythm(config, key_chapters, concept):
    """全局 Agent C：节奏/伏笔。"""
    from lib.api_client import call_llm

    chapters_text = _load_key_chapters_text(config, key_chapters)
    concept_section = f"## 核心策略\n\n{concept[:3000]}"
    task_desc = """检查以下问题：
1. 伏笔是否在后续章节有回收（不能只埋不收）
2. 主线推进是否每章都有（不能跑偏写支线）
3. 章节间的节奏是否合理（不能连续多章同一节奏）
4. 信息释放是否均匀（不能前松后紧或前紧后松）
5. 高潮位置是否在全局节奏图的预期位置"""

    prompt = _GLOBAL_PROMPT_TEMPLATE.format(
        dimension_name="节奏伏笔",
        concept_section=concept_section,
        chapters_text=chapters_text,
        task_desc=task_desc,
    )

    try:
        content = call_llm(config, "unified-review", prompt, "")
        return _parse_global_issues(content, "rhythm")
    except Exception as e:
        print(f"    [全局-节奏] 失败: {e}", flush=True)
        return []


def global_dimension_review(config, chapter_nums):
    """Layer 1b: 3 个全局维度 agent 并行审查。"""
    key_chapters = _select_key_chapters(chapter_nums)
    concept = _load_concept(config)
    if not concept:
        print("    [全局] concept.md 不存在，跳过全局维度审查", flush=True)
        return []

    print(f"  [全局] 3 个维度 agent 并行启动（关键章: {key_chapters}）", flush=True)
    all_issues = []

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(_global_agent_character, config, key_chapters, concept): "人设",
            ex.submit(_global_agent_emotion, config, key_chapters, concept): "感情",
            ex.submit(_global_agent_rhythm, config, key_chapters, concept): "节奏",
        }
        for f in as_completed(futures):
            name = futures[f]
            try:
                issues = f.result()
                all_issues.extend(issues)
                print(f"    [全局-{name}] 发现 {len(issues)} 个问题", flush=True)
            except Exception as e:
                print(f"    [全局-{name}] 失败: {e}", flush=True)

    return all_issues


def _parse_review_output(text):
    """解析 markdown 格式的审稿输出。

    格式：
      ### 章节 N
      评分: XX
      问题:
      - 类型: X | 严重度: high|medium|low | 描述: X | 修复: X

      ### 跨章问题
      - 涉及章节: 1,2,3 | 类型: X | 严重度: X | 描述: X | 修复: X

    返回 ({ch_str: {score, issues}}, [{type, severity, desc, fix}])
    """
    chapters = {}
    cross = []

    ch_blocks = re.findall(r'###\s+章节\s+(\d+)\s*\n(.*?)(?=###\s+(?:章节|\u8de8\u7ae0\u95ee\u9898)|\Z)', text, re.DOTALL)
    for ch_str, body in ch_blocks:
        score_m = re.search(r'评分:\s*(\d+)', body)
        score = int(score_m.group(1)) if score_m else 50
        issues = []
        in_issues = re.split(r'问题:', body, maxsplit=1)
        if len(in_issues) > 1:
            for line in in_issues[1].split('\n'):
                line = line.strip()
                m = re.match(r'-\s*类型:\s*(\S+)', line)
                if m:
                    typ = m.group(1)
                    sev = _extract_field(line, '严重度', 'medium')
                    desc = _extract_field(line, '描述', '')
                    fix = _extract_field(line, '修复', '')
                    issues.append({"type": typ, "severity": sev, "desc": desc, "fix": fix, "auto_fixable": False})
        chapters[ch_str] = {"score": score, "issues": issues}

    cross_block = re.search(r'###\s+跨章问题\s*\n(.*?)(?=###|\Z)', text, re.DOTALL)
    if cross_block:
        for line in cross_block.group(1).split('\n'):
            line = line.strip()
            m = re.match(r'-\s*涉及章节:\s*([\d,]+)', line)
            if m:
                chs = [int(x.strip()) for x in m.group(1).split(',') if x.strip()]
                typ = _extract_field(line, '类型', 'continuity')
                sev = _extract_field(line, '严重度', 'medium')
                desc = _extract_field(line, '描述', '')
                fix = _extract_field(line, '修复', '')
                cross.append({"chapters": chs, "type": typ, "severity": sev, "desc": desc, "fix": fix})

    return chapters, cross


def _extract_field(line, label, default):
    m = re.search(re.escape(label) + r':\s*([^|]+)', line)
    return m.group(1).strip() if m else default


def _llm_batch_review(config, chapter_nums):
    """LLM 批量审稿一批章节。"""
    from lib.api_client import call_llm

    prompt_template = load_prompt_str("unified-review.md")
    if not prompt_template:
        return {}, []

    chapters_dir = f"{config['rewrites_dir']}/chapters"
    parts = []
    for ch in chapter_nums:
        cf = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if cf.exists():
            parts.append(f"=== 第{ch}章 ===\n{cf.read_text(encoding='utf-8')}")
    chapters_text = '\n\n'.join(parts)

    src_samples = []
    picks = [chapter_nums[0]]
    if len(chapter_nums) > 2:
        picks.append(chapter_nums[len(chapter_nums)//2])
    if len(chapter_nums) > 1:
        picks.append(chapter_nums[-1])
    for ch in picks:
        src = get_source_text(config, ch)
        if src:
            src_samples.append(f"--- 源文第{ch}章 ---\n{src[:1000]}")
    source_context = '\n\n'.join(src_samples)

    prompt = safe_format(prompt_template, {
        "count": len(chapter_nums),
        "chapters_text": chapters_text,
        "source_context": source_context if source_context else "（无）",
    })

    # 加载平台专属审查标准
    target_platform = config.get("target_platform", "")
    if target_platform:
        rubric_name = f"review-rubric-{target_platform}.md"
        rubric_text = load_prompt_str(rubric_name)
        if rubric_text:
            prompt = prompt + "\n\n---\n\n## 平台专项审查（{target_platform}）\n\n".format(target_platform=target_platform) + rubric_text[:1500]

    sp_name = get_system_prompt_name("unified-review.md") or "system-generic.md"
    sys_prompt = load_system_prompt(sp_name) or ""

    if config.get("debug"):
        from utils import debug_dump_prompt
        pc = get_prompt_config_with_overrides("unified-review.md", config)
        debug_dump_prompt(config, "unified-review", chapter_nums[0],
                          "prompts/unified-review.md", sys_prompt,
                          prompt, sp_name, pc)

    content = call_llm(config, "unified-review", prompt, sys_prompt)
    return _parse_review_output(content)


# ============================================================
# Summary Agent
# ============================================================

_P0_TYPES = {"plagiarism", "continuity", "missing", "character", "timeline", "imagery_repetition"}
_P1_TYPES = {"ai_marker", "emotion", "hook", "rhythm", "word_count"}
_P2_TYPES = {"metaphor", "ai_trace", "dialogue", "repetition", "emotion_repetition", "dialogue_tag"}

def severity_to_priority(severity, type_):
    if type_ in _P0_TYPES:
        return "P0"
    if severity == "high":
        return "P0"
    if type_ in _P1_TYPES:
        return "P1"
    if severity == "medium" and type_ in _P2_TYPES:
        return "P2"
    if type_ in _P2_TYPES:
        return "P2"
    return "P1"


def _check_cross_chapter_imagery(config, merged):
    """跨章意象重复检查。"""
    issues = []
    chapters_dir = Path(f"{config['rewrites_dir']}/chapters")
    if not chapters_dir.exists():
        return issues

    # 从源文动态提取意象关键词（替代硬编码）
    from lib.trope_extractor import get_imagery_keywords_for_review
    try:
        imagery_keywords = get_imagery_keywords_for_review(config)
    except Exception:
        # 降级到通用意象
        imagery_keywords = [
            '阳光', '月光', '星光', '灯火', '窗外',
            '雨', '雪', '风', '花', '树', '叶',
        ]

    # 收集每章出现的意象
    chapter_imagery = {}
    for ch in sorted(merged.keys()):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        text = ch_file.read_text(encoding='utf-8')
        found = set()
        for kw in imagery_keywords:
            if kw in text:
                found.add(kw)
        chapter_imagery[ch] = found

    # 检查意象在多章重复
    imagery_count = {}
    for ch, imageries in chapter_imagery.items():
        for img in imageries:
            imagery_count.setdefault(img, []).append(ch)

    for img, chapters in imagery_count.items():
        if len(chapters) >= 3:
            issues.append({
                "type": "imagery_repetition",
                "severity": "high",
                "desc": f"意象重复: \"{img}\" 在 {len(chapters)} 章出现 (第{','.join(map(str, chapters[:5]))}章)",
                "fix": f"每个意象只用一次，\"{img}\" 只保留在最需要的那章，其他章换新意象",
                "auto_fixable": False,
            })

    return issues


def summary_agent(review_results: list[ReviewResult], config=None) -> SummaryReport:
    """汇总 N 个 review agent 的输出。"""
    merged = {}
    all_cross = []

    for rr in review_results:
        for ch, data in rr.chapters.items():
            if ch not in merged:
                merged[ch] = {"score": 100, "issues": [], "sources": []}
            merged[ch]["sources"].append("algo")
            merged[ch]["score"] = min(merged[ch]["score"], data.get("score", 50))
            existing = {i["desc"][:30] for i in merged[ch]["issues"]}
            for issue in data.get("issues", []):
                if issue["desc"][:30] not in existing:
                    issue["priority"] = severity_to_priority(issue.get("severity", "low"), issue.get("type", ""))
                    merged[ch]["issues"].append(issue)
                    existing.add(issue["desc"][:30])
        all_cross.extend(rr.cross_issues)

    # 跨章意象重复检查
    if config:
        imagery_issues = _check_cross_chapter_imagery(config, merged)
        all_cross.extend(imagery_issues)

    _ISSUE_FIELDS = {"type", "severity", "priority", "desc", "fix", "auto_fixable", "ch"}
    seen_cross = set()
    cross_list = []
    for c in all_cross:
        key = c.get("desc", "")[:60]
        if key not in seen_cross:
            c["priority"] = severity_to_priority(c.get("severity", "medium"), c.get("type", "continuity"))
            cross_list.append(Issue(**{k: v for k, v in c.items() if k in _ISSUE_FIELDS}))
            seen_cross.add(key)

    type_ch_map = {}
    for ch, data in merged.items():
        for iss in data["issues"]:
            t = iss.get("type", "")
            type_ch_map.setdefault(t, set())
            type_ch_map[t].add(ch)

    type_label = {
        "character": "人设", "emotion": "情感", "rhythm": "节奏",
        "plagiarism": "台词雷同", "word_count": "字数", "hook": "钩子",
        "ai_marker": "AI路标词", "ai_trace": "AI痕迹", "metaphor": "比喻",
        "sentence_stddev": "句长", "pronoun": "代词",
    }
    for t, ch_set in type_ch_map.items():
        if len(ch_set) < 3:
            continue
        sorted_ch = sorted(ch_set)
        label = type_label.get(t, t)
        key = f"跨章{label}"
        if key not in seen_cross:
            cross_list.append(Issue(
                type=t, severity="high", priority="P0" if t in _P0_TYPES else "P1",
                desc=f"【跨章{label}】{len(ch_set)}章存在{label}类问题: 第{','.join(map(str,sorted_ch[:5]))}章"
                      + (f"...共{len(ch_set)}章" if len(ch_set) > 5 else ""),
                fix="各章问题综合修复",
                auto_fixable=False,
            ))
            seen_cross.add(key)

    prio_order = {"P0": 0, "P1": 1, "P2": 2}
    for ch in merged:
        merged[ch]["issues"].sort(key=lambda i: prio_order.get(i.get("priority", "P2"), 9))

    total_p0 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P0")
    total_p1 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P1")
    total_p2 = sum(1 for d in merged.values() for i in d["issues"] if i.get("priority") == "P2")
    scores = [d["score"] for d in merged.values()]
    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    stats = {
        "total_ch": len(merged),
        "p0": total_p0,
        "p1": total_p1,
        "p2": total_p2,
        "total_issues": total_p0 + total_p1 + total_p2,
        "avg_score": avg_score,
    }

    return SummaryReport(chapters=merged, cross_issues=cross_list, stats=stats)


# ============================================================
# P0/P1/P2 报告生成
# ============================================================

def generate_p012_report(summary, output_path):
    """从 SummaryReport 生成简化版 P0/P1/P2 报告。"""
    s = summary.stats
    lines = []
    
    lines.append("# 审查报告")
    lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 概览")
    lines.append(f"- 审查范围: {s['total_ch']} 章")
    lines.append(f"- P0 (严重): **{s['p0']}** 处")
    lines.append(f"- P1 (中等): **{s['p1']}** 处")
    lines.append(f"- P2 (轻微): **{s['p2']}** 处")
    lines.append(f"- 平均分: {s['avg_score']}")
    lines.append("")
    
    # 按优先级列出问题
    for prio in ("P0", "P1", "P2"):
        prio_issues = []
        for ch in sorted(summary.chapters.keys()):
            data = summary.chapters[ch]
            for iss in data.get("issues", []):
                if iss.get("priority") == prio:
                    prio_issues.append((ch, iss))
        if not prio_issues:
            continue
        
        lines.append(f"## {prio} 问题 ({len(prio_issues)}处)")
        for ch, iss in prio_issues[:20]:  # 最多显示20条
            lines.append(f"- 第{ch}章: [{iss.get('type')}] {iss.get('desc')}")
        if len(prio_issues) > 20:
            lines.append(f"- ... 共{len(prio_issues)}处")
        lines.append("")
    
    # 跨章问题
    if summary.cross_issues:
        lines.append("## 跨章问题")
        for ci in summary.cross_issues[:10]:  # 最多显示10条
            lines.append(f"- [{ci.priority}] {ci.desc}")
        lines.append("")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding='utf-8')
    print(f"  审查报告已保存: {output_path}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="统一审查 — 只审不改")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding='utf-8'))
    cfg.setdefault("base_dir", os.getcwd())

    if args.start is None or args.end is None:
        ch_dir = Path(cfg['rewrites_dir']) / 'chapters'
        if ch_dir.exists():
            nums = [int(re.search(r'(\d+)', f.stem).group(1)) for f in ch_dir.glob("ch_*.txt")]
            if nums:
                args.start = args.start or min(nums)
                args.end = args.end or max(nums)
    args.start = args.start or 1
    args.end = args.end or 10

    chapters = list(range(args.start, args.end + 1))
    batches = [chapters[i:i+args.batch_size] for i in range(0, len(chapters), args.batch_size)]
    review_results = []

    print(f"统一审查 | ch{args.start}-{args.end} | {len(batches)} agents")
    with ThreadPoolExecutor(max_workers=min(args.workers, len(batches))) as ex:
        futures = {
            ex.submit(review_agent, cfg, batch, agent_id=i): i
            for i, batch in enumerate(batches)
        }
        for f in as_completed(futures):
            try:
                review_results.append(f.result())
            except Exception as e:
                print(f"    [FAIL] Review Agent {futures[f]}: {e}")

    summary = summary_agent(review_results, config=cfg)
    s = summary.stats
    print(f"\n结果: {s['total_ch']} 章 | P0:{s['p0']} P1:{s['p1']} P2:{s['p2']} | 均分:{s['avg_score']}")

    report_path = os.path.join(cfg.get('rewrites_dir', ''), 'compare', 'p012_issues_report.md')
    if cfg.get('rewrites_dir'):
        generate_p012_report(summary, report_path)


if __name__ == "__main__":
    main()
