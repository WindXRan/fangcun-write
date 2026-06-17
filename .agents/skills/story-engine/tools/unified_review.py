"""
多 Agent 审改系统 — 审查 + 总结层

Agent 架构:
  1a. Batch Review Agents (scatter)   — N个并行，每人审 X 章 (algo+LLM, 7维全检)
  1b. Global Review Agents (scatter)  — 2个并行，通读全书关键章：人设一致性 + 全局节奏/伏笔
  2.  Summary Agent (gather)          — 合并两层结果，去重分级 P0/P1/P2
"""

import os, re, json, time, argparse, warnings
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

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
    """单章算法检查。"""
    ch_dir = Path(f"{config['rewrites_dir']}/chapters")
    ch_file = ch_dir / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return {"score": 0, "issues": [{"type": "missing", "severity": "high", "desc": "文件不存在", "auto_fixable": False}]}

    text = ch_file.read_text(encoding='utf-8')
    metrics = count_metrics(text)
    src = get_source_text(config, ch)
    src_metrics = count_metrics(src) if src else None
    src_chars = get_body_chars(src)

    # 加载白名单（角色名/地名放行，避免误杀）
    whitelist_path = Path(config.get('rewrites_dir', '')) / '_log' / 'deslop-whitelist.txt'
    whitelist = set()
    if whitelist_path.exists():
        for line in whitelist_path.read_text(encoding='utf-8').splitlines():
            line = line.strip().split('#')[0].strip()  # 支持 # 注释
            if line:
                whitelist.add(line)
    _ok = lambda hits: [h for h in hits if h not in whitelist]

    issues = []
    score = 100

    ai_traces = []
    for marker in AI_MARKERS:
        pat = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        found = re.findall(pat, text)
        found = _ok(found)
        if found:
            ai_traces.append(f"{marker}x{len(found)}")
    if ai_traces:
        issues.append({"type": "ai_trace", "severity": "medium",
                       "desc": f"AI痕迹词: {', '.join(ai_traces)}",
                       "fix": "删除句首路标词", "auto_fixable": True})
        score -= 5

    if src_metrics:
        limit = max(src_metrics["ai_markers"] + 1, 1)
        if metrics["ai_markers"] > limit:
            issues.append({"type": "ai_marker", "severity": "high",
                           "desc": f"AI路标词 {metrics['ai_markers']}处 (源文{src_metrics['ai_markers']})",
                           "fix": "删除多余的路标词", "auto_fixable": True})
            score -= 15

    if src_metrics:
        limit = src_metrics["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append({"type": "metaphor", "severity": "medium",
                           "desc": f"比喻过多 {metrics['metaphor']}处 (源文{src_metrics['metaphor']})",
                           "fix": "删除多余比喻", "auto_fixable": False})
            score -= 10

    if src_metrics:
        limit = max(src_metrics["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append({"type": "emotion", "severity": "medium",
                           "desc": f"直抒情 {metrics['direct_emotion']}处 (源文{src_metrics['direct_emotion']})",
                           "fix": "用动作细节代替", "auto_fixable": False})
            score -= 10

    if src_metrics and src_metrics.get("pronoun_density", 0) > 0:
        ratio = metrics["pronoun_density"] / src_metrics["pronoun_density"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append({"type": "pronoun", "severity": "medium",
                           "desc": f"代词密度 {metrics['pronoun_density']}/千字 (源文{src_metrics['pronoun_density']})",
                           "fix": "交替使用名字/身份/零代词替代他/她", "auto_fixable": False})
            score -= 10

    if src_metrics and src_metrics.get("sent_len_stddev", 0) > 0:
        ratio = metrics["sent_len_stddev"] / src_metrics["sent_len_stddev"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append({"type": "sentence_stddev", "severity": "medium",
                           "desc": f"句长标准差 {metrics['sent_len_stddev']} (源文{src_metrics['sent_len_stddev']})",
                           "fix": "交错长短句，避免句长均匀", "auto_fixable": False})
            score -= 10

    if src_chars > 0:
        dev = (metrics["chars"] - src_chars) / src_chars
        if abs(dev) > 0.15:
            direction = "超标" if dev > 0 else "不足"
            issues.append({"type": "word_count", "severity": "high",
                           "desc": f"字数{direction} {metrics['chars']}/{src_chars} ({dev:+.0%})",
                           "fix": f"目标{int(src_chars*0.9)}~{int(src_chars*1.1)}字",
                           "auto_fixable": False})
            score -= 15

    if src:
        plags = find_plagiarism(text, src)
        if plags:
            desc = f"台词雷同 {len(plags)}处: " + ", ".join(f"'{p['text']}...'" for p in plags[:3])
            issues.append({"type": "plagiarism", "severity": "high",
                           "desc": desc, "fix": "重写雷同台词",
                           "auto_fixable": False})
            score -= 15

    # === 6 指标量化评分（轻/中/重） ===
    heavy = 0
    medium = 0

    # 1. 禁用词密度（AI路标词/千字）
    banned_density = metrics["ai_markers"] / max(metrics["chars"], 1) * 1000
    if banned_density > 15:
        heavy += 1
    elif banned_density > 5:
        medium += 1

    # 2. 连续排比
    if metrics.get("max_consecutive", 0) >= 5:
        heavy += 1
    elif metrics.get("max_consecutive", 0) >= 3:
        medium += 1

    # 3. 心理词占比
    if metrics.get("psych_ratio", 0) > 0.25:
        heavy += 1
    elif metrics.get("psych_ratio", 0) > 0.10:
        medium += 1

    # 4. 对话标签密度
    if metrics.get("tag_density", 0) > 0.5:
        heavy += 1
    elif metrics.get("tag_density", 0) > 0.3:
        medium += 1

    # 5. 段均句数
    if metrics.get("avg_sent_per_para", 0) > 5:
        heavy += 1
    elif metrics.get("avg_sent_per_para", 0) > 3:
        medium += 1

    # 6. 重复描写密度（三字母重复检测，中文天然高频需高阈值）
    if metrics.get("repeat_density", 0) >= 150:
        heavy += 1
    elif metrics.get("repeat_density", 0) >= 100:
        medium += 1

    # 7. 段长标准差（低=段落均匀像AI，高=变化过大致阅读体验差）
    para_stddev = metrics.get("para_stddev", 0)
    if para_stddev > 0 and para_stddev < 3:
        heavy += 1
    elif para_stddev > 0 and para_stddev < 5:
        medium += 1
    if para_stddev > 12:
        heavy += 1
    elif para_stddev > 8:
        medium += 1

    if heavy >= 1:
        issues.append({"type": "ai_style_heavy", "severity": "high",
                       "desc": f"AI文风重度 (heavy={heavy}, medium={medium}): 禁用词{banned_density:.0f}/千字 排比{metrics.get('max_consecutive',0)}段 心理词{metrics.get('psych_ratio',0):.0%} 标签{metrics.get('tag_density',0):.0%} 段均{metrics.get('avg_sent_per_para',0)}句 重复{metrics.get('repeat_density',0):.0f}/千字 段长差{para_stddev}",
                       "fix": "逐句重写AI痕迹段落", "auto_fixable": False})
        score -= 20
    elif medium >= 3:
        issues.append({"type": "ai_style_medium", "severity": "medium",
                       "desc": f"AI文风中度 (heavy={heavy}, medium={medium})",
                       "fix": "重点优化超标指标", "auto_fixable": False})
        score -= 10

    # 情绪表达重复（保留，做轻量检查）
    emotion_patterns = {
        '紧张': len(re.findall(r'攥紧|攥了攥|蜷了蜷|指节发白|手指蜷', text)),
        '感动': len(re.findall(r'眼眶红|鼻子酸|眼泪没掉|泪水在眼眶', text)),
        '害怕': len(re.findall(r'后背发凉|汗毛竖|打了个寒|缩了缩脖子', text)),
    }
    for emo, count in emotion_patterns.items():
        if count > 2:
            issues.append({"type": "emotion_repetition", "severity": "low",
                           "desc": f"情绪表达重复: {emo}类表达{count}次",
                           "fix": f"同一情绪最多2次，之后换表达方式", "auto_fixable": False})
            score -= 3

    # === Gate G: 解释腔/上帝感（旁白跳出角色视角） ===
    god_patterns = [
        (r'她不知道的是|她不知道的是|殊不知|她万万没想到', '旁白剧透'),
        (r'命运的齿轮|命运弄人|命运的安排|造化弄人', '命运上帝腔'),
        (r'多年以后|后来她才知道|很久以后她才明白|若干年后', '跨时间剧透'),
        (r'可怜的|可悲的|可叹的|不幸的是', '旁白评判'),
        (r'原来是因为|之所以是因为|正是由于|归根结底', '解释因果'),
        (r'这让她|这使得|这不禁|这也让|这倒让', '解释腔'),
        (r'殊不知|岂不知|哪里知道|哪曾想', '旁白反转'),
    ]
    god_hits = []
    for pat, label in god_patterns:
        found = re.findall(pat, text)
        found = _ok(found)
        if found:
            god_hits.append(f"{label}x{len(found)}")
    if god_hits:
        issues.append({"type": "god_narrator", "severity": "high",
                       "desc": f"解释腔/上帝感: {', '.join(god_hits)}",
                       "fix": "删除旁白跳出角色视角的句式，改为角色自身感知",
                       "auto_fixable": False})
        score -= 15

    # === 6指标量化评分（轻度/中度/重度） ===

    # 1. 禁用词密度（轻度≤5/千字，中度6-15，重度>15）
    ai_marker_density = metrics["ai_markers"] / max(metrics["chars"], 1) * 1000
    if ai_marker_density > 15:
        issues.append({"type": "ai_marker", "severity": "high",
                       "desc": f"禁用词密度 {ai_marker_density:.1f}/千字 (重度>15)",
                       "fix": "删除句首路标词", "auto_fixable": True})
        score -= 15
    elif ai_marker_density > 6:
        issues.append({"type": "ai_marker", "severity": "medium",
                       "desc": f"禁用词密度 {ai_marker_density:.1f}/千字 (中度6-15)",
                       "fix": "删除句首路标词", "auto_fixable": True})
        score -= 10

    # 2. 连续排比（轻度≤2段，中度3-4段，重度>4段）
    para_lines = [l for l in text.split('\n') if l.strip()]
    consecutive_parallel = 0
    max_parallel = 0
    for i in range(len(para_lines) - 1):
        if para_lines[i] and para_lines[i+1]:
            if para_lines[i][:4] == para_lines[i+1][:4] and len(para_lines[i]) > 10:
                consecutive_parallel += 1
                max_parallel = max(max_parallel, consecutive_parallel)
            else:
                consecutive_parallel = 0
    if max_parallel > 4:
        issues.append({"type": "parallel", "severity": "high",
                       "desc": f"连续排比 {max_parallel}段 (重度>4段)",
                       "fix": "打破排比结构，增加变化", "auto_fixable": False})
        score -= 10
    elif max_parallel > 2:
        issues.append({"type": "parallel", "severity": "medium",
                       "desc": f"连续排比 {max_parallel}段 (中度3-4段)",
                       "fix": "打破排比结构，增加变化", "auto_fixable": False})
        score -= 5

    # 3. 心理词占比（轻度≤10%，中度10-25%，重度>25%）
    psych_words = len(re.findall(r'心想|暗道|觉得|感到|心[中里]|不由|忍不[住下]|想到|想起|意识到|明白|知道|感觉', text))
    psych_ratio = psych_words / max(len(para_lines), 1)
    if psych_ratio > 0.25:
        issues.append({"type": "psych_ratio", "severity": "high",
                       "desc": f"心理词占比 {psych_ratio:.0%} (重度>25%)",
                       "fix": "用动作/对话替代心理描写", "auto_fixable": False})
        score -= 10
    elif psych_ratio > 0.10:
        issues.append({"type": "psych_ratio", "severity": "medium",
                       "desc": f"心理词占比 {psych_ratio:.0%} (中度10-25%)",
                       "fix": "用动作/对话替代心理描写", "auto_fixable": False})
        score -= 5

    # 4. 对话标签密度（轻度≤30%，中度30-50%，重度>50%）
    dialogue_lines = re.findall(r'[」""\']\s*([^」""\']{0,6})(?:说|道|问|答|喊|叫)', text)
    total_dialogue = text.count('"') // 2 + text.count('"') // 2 + text.count('「') 
    if total_dialogue > 5 and len(dialogue_lines) > 0:
        tag_ratio = len(dialogue_lines) / max(total_dialogue, 1)
        if tag_ratio > 0.5:
            issues.append({"type": "dialogue_tag", "severity": "high",
                           "desc": f"对话标签密度 {tag_ratio:.0%} (重度>50%)",
                           "fix": "用动作替代标签，如'XX咬了口包子：\"好吃\"'", "auto_fixable": False})
            score -= 10
        elif tag_ratio > 0.3:
            issues.append({"type": "dialogue_tag", "severity": "medium",
                           "desc": f"对话标签密度 {tag_ratio:.0%} (中度30-50%)",
                           "fix": "用动作替代标签，如'XX咬了口包子：\"好吃\"'", "auto_fixable": False})
            score -= 5

    # 5. 段均句数（轻度≤3，中度3-5，重度>5）
    sents_per_para = len(re.split(r'[。！？!?\n]', text)) / max(len(para_lines), 1)
    if sents_per_para > 5:
        issues.append({"type": "para_density", "severity": "high",
                       "desc": f"段均句数 {sents_per_para:.1f} (重度>5)",
                       "fix": "拆分长段落，增加单句段", "auto_fixable": False})
        score -= 10
    elif sents_per_para > 3:
        issues.append({"type": "para_density", "severity": "medium",
                       "desc": f"段均句数 {sents_per_para:.1f} (中度3-5)",
                       "fix": "拆分长段落，增加单句段", "auto_fixable": False})
        score -= 5

    return {"score": max(0, score), "issues": issues, "metrics": metrics,
            "chars": metrics["chars"], "src_chars": src_chars}


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
        "chapters_text": chapters_text[:6000],
        "source_context": source_context[:2000] if source_context else "（无）",
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

    # 意象关键词
    imagery_keywords = [
        '石榴', '歪脖子', '老槐', '杏树', '枣树', '槐树',
        '窗外', '鸟雀', '井水', '月光', '星光', '灯火',
        '花瓣', '落叶', '雪花', '雨滴', '蝉鸣', '蛙声',
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
    """从 SummaryReport 生成 P0/P1/P2 问题合集 Markdown 报告。"""
    s = summary.stats
    lines = []
    _h = lambda t, l: lines.append(f"{'#'*t} {l}")

    _h(1, "P0/P1/P2 问题合集报告")
    lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    _h(2, "概览")
    ch_with_issues = [ch for ch, d in summary.chapters.items() if d.get("issues")]
    total_ch = len(summary.chapters)
    lines.append(f"- 审查范围: {total_ch} 章")
    lines.append(f"- 存在问题: {len(ch_with_issues)} 章")
    lines.append(f"- P0 (严重): **{s['p0']}** 处")
    lines.append(f"- P1 (中等): **{s['p1']}** 处")
    lines.append(f"- P2 (轻微): **{s['p2']}** 处")
    lines.append(f"- 问题总计: {s['total_issues']} 处")
    lines.append(f"- 平均分: {s['avg_score']}")
    if s['avg_score'] >= 80:
        lines.append(f"- 总体评级: ⭐ A (良好)")
    elif s['avg_score'] >= 60:
        lines.append(f"- 总体评级: B (一般)")
    else:
        lines.append(f"- 总体评级: C (需大幅改进)")
    lines.append("")

    prio_order = {"P0": 0, "P1": 1, "P2": 2}
    labels = {"P0": "P0 — 严重问题，须修复", "P1": "P1 — 中等问题，建议修复", "P2": "P2 — 轻微问题"}

    for prio in ("P0", "P1", "P2"):
        prio_issues = []
        for ch in sorted(summary.chapters.keys()):
            data = summary.chapters[ch]
            for iss in data.get("issues", []):
                if iss.get("priority") == prio:
                    prio_issues.append((ch, iss))
        if not prio_issues:
            continue
        _h(2, labels[prio])
        lines.append(f"共 {len(prio_issues)} 处问题")
        lines.append("")
        ch_map = {}
        for ch, iss in prio_issues:
            ch_map.setdefault(ch, []).append(iss)
        for ch in sorted(ch_map.keys()):
            data = summary.chapters[ch]
            score = data.get("score", 0)
            lines.append(f"### 第{ch}章 (评分: {score})")
            for iss in ch_map[ch]:
                typ = iss.get("type", "?")
                sev = iss.get("severity", "?")
                desc = iss.get("desc", "?")
                fix = iss.get("fix", "")
                lines.append(f"- **[{typ}]** ({sev}) {desc}")
                if fix:
                    lines.append(f"  - 修复: {fix}")
            lines.append("")

    if summary.cross_issues:
        _h(2, "跨章问题")
        for ci in summary.cross_issues:
            lines.append(f"- [{ci.priority}] **{ci.type}** — {ci.desc}")
            if ci.fix:
                lines.append(f"  - 修复: {ci.fix}")
        lines.append("")

    _h(2, "问题类型分布")
    type_counts = {}
    for ch, data in summary.chapters.items():
        for iss in data.get("issues", []):
            t = iss.get("type", "?")
            type_counts.setdefault(t, {"count": 0, "P0": 0, "P1": 0, "P2": 0})
            type_counts[t]["count"] += 1
            prio = iss.get("priority", "P2")
            if prio in type_counts[t]:
                type_counts[t][prio] += 1

    type_label = {
        "character": "人设漂移", "emotion": "直抒情过多", "rhythm": "节奏问题",
        "plagiarism": "台词雷同", "word_count": "字数偏差", "hook": "钩子不足",
        "ai_marker": "AI路标词", "ai_trace": "AI痕迹词", "metaphor": "比喻过多",
        "sentence_stddev": "句长异常", "pronoun": "代词密度", "continuity": "连贯性",
        "missing": "文件缺失", "dialogue": "对话问题",
    }
    lines.append(f"| 类型 | 合计 | P0 | P1 | P2 |")
    lines.append(f"|------|------|----|----|----|")
    for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]["count"]):
        label = type_label.get(t, t)
        lines.append(f"| {label} | {cnt['count']} | {cnt['P0']} | {cnt['P1']} | {cnt['P2']} |")
    lines.append("")

    _h(2, "各章评分")
    score_list = [(ch, summary.chapters[ch].get("score", 0)) for ch in sorted(summary.chapters.keys())]
    low = [(ch, sc) for ch, sc in score_list if sc < 60]
    mid = [(ch, sc) for ch, sc in score_list if 60 <= sc < 80]
    high = [(ch, sc) for ch, sc in score_list if sc >= 80]
    if low:
        lines.append(f"- ⚠ 低分 (<60): **{len(low)}** 章 — 第{'、'.join(str(c) for c, _ in low)}章")
    if mid:
        lines.append(f"- 中等 (60-80): **{len(mid)}** 章")
    if high:
        lines.append(f"- 良好 (≥80): **{len(high)}** 章")
    lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding='utf-8')
    print(f"  P0/P1/P2 报告已保存: {output_path}")


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
