"""Phase 2: Guide 生成主流程。

包含 phase_guides、run_one、run_one_with_template 等核心函数。
"""

import os
import re
import time
from pathlib import Path

import _path_setup  # noqa: F401
from utils import (
    get_total_chapters, count_source_chars, batch_run,
)
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from prompt_loader import load_prompt

from guides_cache import (
    _get_system_prompt_cached, _load_skeleton_map, _get_source_text_for_chapter,
    _get_source_chars_for_chapter, _get_book_data, _load_events_mapped,
    _load_skeleton_mapped, _load_adaptation_mapped,
)
from guides_name import (
    _build_name_map, _build_name_map_text, _get_chapter_characters,
    _load_character_cards, _load_char_card,
)
from guides_world import (
    _get_world_text, _get_world_constraint, _get_genre_text,
    _get_blacklist_text,
)
from guides_style import (
    _get_style_fingerprint, _get_style_text_mapped, _extract_highlights,
    get_source_metrics,
)


# ============================================================
# 章级大纲自动补全
# ============================================================

def _ensure_chapter_outline(config, rewrites_dir):
    """从 events.json 提取章纲，写入 guides/章纲.md。不再调用 LLM。"""
    outline_path = Path(rewrites_dir) / "guides" / "章纲.md"
    if outline_path.exists() and outline_path.stat().st_size > 100:
        return True

    print(f"\n  [章纲] 从 events.json 提取...")
    try:
        import json as _json
        # 优先拆文库 events.json（新版9字段），fallback _cache（旧版pipe格式）
        events_path = Path(config.get("analyze_dir", "")) / "events.json"
        if not events_path.exists():
            events_path = Path(rewrites_dir).parent.parent / "_cache" / "events.json"
        if not events_path.exists():
            print(f"  [WARN] events.json 不存在")
            return False

        events = _json.loads(events_path.read_text(encoding="utf-8"))
        lines = []
        for ev in events:
            n = ev.get("id", "?")
            # 新版格式：有"核心事件""开头承接"等字段
            if "核心事件" in ev and "开头承接" in ev:
                event = ev.get("核心事件", "")[:20]
                opening = ev.get("开头承接", "")[:25]
                closing = ev.get("结尾状态", "")[:25]
                link = ev.get("衔接", "").replace("→ ", "").replace("→", "")[:25]
            else:
                # 旧版格式：从 pipe 字段提取
                parts = [p.strip() for p in ev.get("event", "").split("|") if p.strip()]
                event = parts[0][:20] if len(parts) > 0 else ""
                opening = parts[8][:25] if len(parts) > 8 else ""
                closing = parts[9][:25] if len(parts) > 9 else ""
                link = parts[10].replace("→ ", "").replace("→", "")[:25] if len(parts) > 10 else ""
            lines.append(f"第{n}章 | {event} | {opening} | {closing} | {link}")

        outline_path.parent.mkdir(parents=True, exist_ok=True)
        outline_path.write_text("# 章纲\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
        print(f"  [OK] 章纲.md → {len(lines)} 章")
        return True
    except Exception as e:
        print(f"  [WARN] 章纲提取失败: {e}")
        return False


def _print_outline_summary(config):
    """打印章纲前5后3条供审阅。"""
    path = Path(config.get("rewrites_dir", "")) / "guides" / "章纲.md"
    if not path.exists(): return
    lines = [l.strip() for l in path.read_text(encoding="utf-8").split("\n") if l.strip().startswith("第")]
    n = len(lines)
    if not lines: return
    print(f"\n  📋 章纲（共{n}章）：")
    for l in lines[:5]: print(f"     {l[:100]}")
    if n > 8: print(f"     ...")
    for l in lines[-3:]: print(f"     {l[:100]}")
    print(f"  全量：guides/章纲.md")

# ============================================================
# 续写模式支持
# ============================================================

def _is_continue_mode(config):
    """判断是否是续写模式。"""
    return config.get("mode") == "continue"


def _get_continue_plan_event(config, ch_num):
    """从续写方案（plan.md）中提取本章事件。
    
    续写方案格式：
    | 卷/段 | 章节范围 | 核心事件 | 情绪基调 | 爽点 |
    |-------|----------|----------|----------|------|
    | 第一卷 | 1-50章 | {核心事件} | {延续原作基调} | {爽点} |
    
    或者：
    **关键事件：**
    1. 第1-10章：{事件}
    2. 第11-20章：{事件}
    """
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    
    # 尝试读取续写方案
    plan_files = [
        rewrites_dir / "续写方案.md",
        rewrites_dir / "plan.md",
    ]
    
    # 也检查plans目录
    plans_dir = rewrites_dir.parent / "续写引擎" / "plans"
    if plans_dir.exists():
        for f in plans_dir.glob("plan_*.md"):
            plan_files.append(f)
    
    plan_text = None
    for pf in plan_files:
        if pf.exists():
            plan_text = pf.read_text(encoding="utf-8")
            break
    
    if not plan_text:
        return None
    
    # 提取情节线表格中的事件
    # 格式：| 第一卷 | 1-50章 | {核心事件} | ...
    for line in plan_text.split('\n'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|') if c.strip()]
        if len(cells) < 3:
            continue
        
        # 解析章节范围
        range_cell = cells[1]  # 如 "1-50章"
        range_match = re.search(r'(\d+)[-~](\d+)', range_cell)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start <= ch_num <= end:
                return cells[2]  # 核心事件
    
    # 提取关键事件
    # 格式：1. 第1-10章：{事件}
    for line in plan_text.split('\n'):
        match = re.match(r'\d+\.\s*第(\d+)[-~](\d+)章[：:]\s*(.+)', line.strip())
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start <= ch_num <= end:
                return match.group(3).strip()
    
    return None


def _get_continue_style(config, ch_num):
    """续写模式的风格参考：从原作前3章提取详细写法指令。"""
    # 直接读取源文
    base_dir = Path(config.get("base_dir", "."))
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    src_dir = base_dir / "projects" / author / source_book / "_cache" / "chapters"
    
    if not src_dir.exists():
        return None
    
    # 使用原作前3章作为风格参考
    style_parts = []
    write_instructions = []
    
    for i in range(1, 4):
        src_file = src_dir / f"第{i}章.txt"
        if not src_file.exists():
            src_file = src_dir / f"第{i:03d}章.txt"
        if not src_file.exists():
            continue
            
        src_text = src_file.read_text(encoding="utf-8")
        if not src_text:
            continue
        
        # 统计句长
        sentences = re.split(r'[。！？]', src_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sent_len = sum(len(s) for s in sentences) // len(sentences)
            style_parts.append(f"第{i}章风格：句长{avg_sent_len}字")
        
        # 统计对话占比
        dialogue_lines = [line for line in src_text.split('\n') if '"' in line or '"' in line]
        if dialogue_lines:
            dialogue_chars = sum(len(line) for line in dialogue_lines)
            total_chars = len(src_text.replace('\n', '').replace(' ', ''))
            dialogue_ratio = dialogue_chars / total_chars if total_chars > 0 else 0
            write_instructions.append(f"第{i}章对话特点：{len(dialogue_lines)}句对话，占比{dialogue_ratio:.0%}")
        
        # 统计段落结构
        paragraphs = [p.strip() for p in src_text.split('\n') if p.strip() and len(p.strip()) > 20]
        if paragraphs:
            avg_para_len = sum(len(p) for p in paragraphs) // len(paragraphs)
            write_instructions.append(f"第{i}章段落：平均{avg_para_len}字/段")
    
    if style_parts or write_instructions:
        result = "续写风格参考（原作前3章）：\n"
        if style_parts:
            result += "\n".join(style_parts) + "\n"
        if write_instructions:
            result += "\n写法指令：\n" + "\n".join(write_instructions[:6])
        return result
    return None


# ============================================================
# 信息释放清单
# ============================================================

def _extract_info_release(config, chapter_num):
    """从 events.json 提取本章功能描述，支持骨架映射。"""
    from file_io import load_events
    
    events = load_events(config)
    if not events:
        return f"（第{chapter_num}章事件未找到）"
    
    # 检查骨架映射
    skel_map = _load_skeleton_map(config)
    source_chs = []
    action = "keep"
    has_skeleton = bool(skel_map.get("chapters"))
    
    for entry in skel_map.get("chapters", []):
        if entry.get("ch") == chapter_num:
            source_chs = entry.get("source", [])
            action = entry.get("action", "keep")
            break
    
    # 如果有骨架映射且是全新章节，返回骨架映射中的 function 描述
    if has_skeleton and (action == "new" or not source_chs):
        for entry in skel_map.get("chapters", []):
            if entry.get("ch") == chapter_num:
                func = entry.get("function", "")
                title = entry.get("title", "")
                conflict = entry.get("conflict_desc", "")
                page_turn = entry.get("page_turn", "")
                page_turn_desc = entry.get("page_turn_desc", "")
                lines = [f"## 本章任务", f"- 章名：{title}", f"- 功能：{func}", f"- 类型：全新设计（源文无对应）"]
                if conflict:
                    lines.append(f"- 冲突：{conflict}")
                if page_turn:
                    lines.append(f"- 翻页理由：{page_turn}（{page_turn_desc}）")
                return "\n".join(lines)
        return f"（第{chapter_num}章：全新设计）"
    
    # 没有骨架映射时，直接使用 events.json（1:1 映射）
    if not has_skeleton:
        source_chs = [chapter_num]
    
    # 收集所有源文章节的事件
    all_events = []
    for src_ch in source_chs:
        for e in events:
            if e.get("chapter_index") == src_ch or e.get("id") == src_ch:
                all_events.append(e)
    
    if not all_events:
        return f"（第{chapter_num}章事件未找到）"
    
    # 合并事件描述
    info_lines = []
    if has_skeleton:
        for entry in skel_map.get("chapters", []):
            if entry.get("ch") == chapter_num:
                info_lines.append(f"## 本章任务")
                info_lines.append(f"- 章名：{entry.get('title', '')}")
                info_lines.append(f"- 功能：{entry.get('function', '')}")
                if len(source_chs) > 1:
                    info_lines.append(f"- 源文对应：第{', '.join(str(c) for c in source_chs)}章（已合并）")
                conflict = entry.get("conflict_desc", "")
                page_turn = entry.get("page_turn", "")
                page_turn_desc = entry.get("page_turn_desc", "")
                if conflict:
                    info_lines.append(f"- 冲突：{conflict}")
                if page_turn:
                    info_lines.append(f"- 翻页理由：{page_turn}（{page_turn_desc}）")
                break
    
    for e in all_events:
        event_text = e.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 4:
            title = parts[1].strip() if len(parts) > 1 else ""
            characters = parts[2].strip() if len(parts) > 2 else ""
            summary = parts[3].strip() if len(parts) > 3 else ""
            function = parts[4].strip() if len(parts) > 4 else ""
            if title:
                info_lines.append(f"- 源文章节：{title}")
            if characters:
                info_lines.append(f"- 出场角色：{characters}")
            if summary:
                info_lines.append(f"- 事件摘要：{summary}")
            if function:
                info_lines.append(f"- 源文功能：{function}")
    
    return "\n".join(info_lines) if info_lines else f"（第{chapter_num}章事件未找到）"


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def phase_guides(config, start, end, workers=5, state_mgr=None):
    """生成 plot_guide（含文笔指纹提取 + 全书风格聚合）。"""
    from lib.api_client import get_api_url
    
    guides_dir = f"{config['rewrites_dir']}/guides"

    if state_mgr:
        state_mgr.phase_start("guides")

    # 先确保章纲存在，生成后暂停供审阅
    if not _ensure_chapter_outline(config, config['rewrites_dir']):
        return

    # 章纲确认门
    if not config.get("skip_outline_review"):
        _print_outline_summary(config)
        print(f"\n  ⏸ 章纲已生成。确认后加 --skip-outline-review 继续。")
        if state_mgr:
            state_mgr.save()
        return

    # 先提取文笔指纹（如果还没有提取）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: 文笔指纹 + plot_guide (ch{start}-{end}, {workers}w)")
    print("=" * 50)
    
    _extract_style_fingerprints(config, start, end, workers)
    _generate_book_style_profile(config)

    # plot-guide（JSON 输出 + 模板合并）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: plot_guide (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    ok, fail = batch_run(config, "plot-guide", start, end, workers, guides_dir,
                         "plot_{ch}.md", skip_existing=True, state_mgr=state_mgr,
                         run_one_func=run_one_with_template)

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")

    # 验证 Guide 质量
    if ok:
        print(f"\n{'=' * 50}")
        print(f"Guide 质量验证")
        print("=" * 50)
        _validate_guides(config, ok)

    if state_mgr:
        if fail:
            state_mgr.phase_failed("guides", error=f"{len(fail)} fail")
        else:
            state_mgr.phase_done("guides")


def _validate_guides(config, ok_guides):
    """验证 Guide 质量。"""
    issues = []
    for ch, path in ok_guides.items():
        try:
            content = Path(path).read_text(encoding="utf-8")
            
            # 检查是否有占位符
            placeholders = re.findall(r'\{[a-zA-Z\u4e00-\u9fa5]+\}', content)
            if placeholders:
                issues.append(f"ch{ch}: 有占位符 {set(placeholders)}")
            
            # 检查是否有角色名占位符
            if '【女主】' in content or '【男主】' in content:
                issues.append(f"ch{ch}: 角色名还是占位符")
            
            # 检查节拍表是否有内容
            if '| # |' in content and content.count('|') < 20:
                issues.append(f"ch{ch}: 节拍表可能不完整")
            
            # 检查是否有"待确认"
            if '待确认' in content:
                issues.append(f"ch{ch}: 有待确认内容")
            
            # 新增：检查情绪功能是否具体
            if '情绪功能' in content:
                # 提取情绪功能部分
                ef_match = re.search(r'情绪功能[：:]\s*(.+?)(?=\n|$)', content)
                if ef_match:
                    ef_text = ef_match.group(1).strip()
                    # 检查是否过于笼统
                    generic_phrases = ['推进剧情', '发展关系', '制造冲突', '推进故事']
                    if any(phrase in ef_text for phrase in generic_phrases) and len(ef_text) < 20:
                        issues.append(f"ch{ch}: 情绪功能过于笼统: '{ef_text[:30]}...'")
            
            # 新增：检查核心冲突是否有梯度
            if '核心冲突' in content:
                conflict_match = re.search(r'核心冲突[：:]\s*(.+?)(?=\n##|\n\n|$)', content, re.DOTALL)
                if conflict_match:
                    conflict_text = conflict_match.group(1).strip()
                    # 检查是否提到升级/梯度
                    if '升级' not in conflict_text and '梯度' not in conflict_text and '递进' not in conflict_text:
                        if len(conflict_text) > 10:  # 只有当冲突描述足够长时才警告
                            issues.append(f"ch{ch}: 核心冲突可能缺少升级梯度")
            
            # 新增：检查写法技巧是否可执行
            if '写法技巧' in content:
                tech_match = re.search(r'写法技巧[：:]\s*(.+?)(?=\n##|\n\n|$)', content, re.DOTALL)
                if tech_match:
                    tech_text = tech_match.group(1).strip()
                    # 检查是否有具体技巧
                    if len(tech_text) < 20:
                        issues.append(f"ch{ch}: 写法技巧可能不够具体")
            
            # 新增：检查源文高光是否被引用
            if '源文高光' in content and '{源文高光}' in content:
                issues.append(f"ch{ch}: 源文高光占位符未被替换")
                
        except Exception as e:
            issues.append(f"ch{ch}: 读取失败 {e}")
    
    if issues:
        print(f"  [WARN] {len(issues)} 个问题:")
        for issue in issues[:10]:  # 最多显示10个
            print(f"    - {issue}")
    else:
        print(f"  [OK] 全部通过")


def _extract_style_fingerprints(config, start, end, workers):
    """提取源文文笔指纹（算法锚点 + LLM分析）。"""
    from phases.style_extract import phase_style_extract
    phase_style_extract(config, start, end, workers)


def _generate_book_style_profile(config):
    """生成全书级文风摘要（配置 style_profile: true 时启用）。"""
    if not config.get("style_profile", True):
        return
    try:
        from phases.book_style_profile import generate_profile
        generate_profile(config)
    except Exception as e:
        print(f"  [WARN] book_style_profile 生成失败: {e}")


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, 
            system_prompt=None, extra_replacements=None, retry_context=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。
    
    Args:
        retry_context: 重试时附带的修正提示（如"代词密度偏离源文"），注入 system_prompt
    """
    from lib.api_client import call_llm, get_api_url

    prompts_dir = config.get("prompts_dir", str(Path(__file__).resolve().parent.parent.parent / "prompts"))
    base_dir = config.get("base_dir", os.getcwd())

    n = str(chapter_num) if chapter_num else "1"
    n_plus1 = str(chapter_num + 1) if chapter_num else "2"
    total_ch = get_total_chapters(config)

    # 读取本章章纲（从 events.json 新格式，只注入结构字段，不传源文标题）
    chapter_outline = ""
    try:
        import json as _json
        for src_path in [
            Path(config.get("analyze_dir", "")) / "events.json",
            Path(config.get("rewrites_dir", "")).parent.parent / "_cache" / "events.json"
        ]:
            if src_path.exists():
                events = _json.loads(src_path.read_text(encoding="utf-8"))
                for ev in events:
                    if str(ev.get("id", "")) == str(chapter_num):
                        parts = []
                        for k in ["章节功能", "情绪弧线", "开头承接", "结尾状态", "衔接"]:
                            v = ev.get(k, "")
                            if v:
                                v = str(v).replace("→ ", "").replace("→", "")
                                parts.append(f"{k}: {v[:80]}")
                        chapter_outline = " | ".join(parts)
                        break
                if chapter_outline:
                    break
    except Exception:
        pass

    replacements = {
        "新书名": Path(config.get("rewrites_dir", "")).name,
        "N": n,
        "N_plus1": n_plus1,
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
        "analyze_dir": config.get("analyze_dir", ""),
        "outline_entry": chapter_outline,
    }

    # 需要源文字数时，脚本计算
    if prompt_type in ("plot-guide", "write-chapter") and chapter_num:
        src_chars = _get_source_chars_for_chapter(config, chapter_num)
        target_chars = src_chars if src_chars > 0 else 1500
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
        # 源文句长（从文笔指纹提取，供仿写对标）
        if "源文句长" not in replacements:
            src_text = _get_source_text_for_chapter(config, chapter_num)
            if src_text:
                from lib.text_metrics import count_metrics
                src_metrics = count_metrics(src_text)
                replacements["源文句长"] = str(int(src_metrics.get("avg_sent_len", 25)))
            else:
                replacements["源文句长"] = "25"
    
    # trim/expand 目标字数硬编码 2000-3000
    if prompt_type in ("trim-chapter", "expand-chapter") and chapter_num:
        replacements.setdefault("目标字数", "2500")
        replacements.setdefault("目标字数_min", "2000")
        replacements.setdefault("目标字数_max", "3000")
    
    # plot-guide 注入信息释放清单（不传源文全文，防止换皮）
    if prompt_type == "plot-guide" and chapter_num:
        # 从 events.json 提取本章事件信息
        info_release = _extract_info_release(config, chapter_num)
        replacements["event"] = info_release
        
        # 注入黑名单（只加载本章相关的黑名单项）
        if "blacklist" not in replacements:
            replacements["blacklist"] = _get_blacklist_text(config, chapter_num)
        
        # 注入源文结构缓存（per-chapter）
        if "structure" not in replacements:
            from phases.style_extract import load_chapter_structure
            ch_struct = load_chapter_structure(config, chapter_num)
            replacements["structure"] = ch_struct or "（结构未提取）"
        # 注入本章出场角色卡内容
        if "characters" not in replacements and chapter_num:
            replacements["characters"] = _load_character_cards(config, chapter_num)
        # 注入世界观
        if "world" not in replacements:
            replacements["world"] = _get_world_text(config)
        # 注入世界观约束（统一时间线/年龄/地点）
        if "world_constraint" not in replacements:
            replacements["world_constraint"] = _get_world_constraint(config)
        # 注入 name_map（角色名映射）
        if "name_map" not in replacements:
            replacements["name_map"] = _build_name_map_text(config)

    # 写章时注入本章出场角色的卡内容
    if prompt_type == "write-chapter" and chapter_num:
        if "characters" not in replacements:
            replacements["characters"] = _load_character_cards(config, chapter_num)
        if "world" not in replacements:
            replacements["world"] = _get_world_text(config)
        if "style" not in replacements:
            style_text = _get_style_text_mapped(config, chapter_num)
            replacements["style"] = style_text or "（风格未提取）"
        # 注入 name_map
        if "name_map" not in replacements:
            replacements["name_map"] = _build_name_map_text(config)

    # 注入源书级产物（从 _cache/ 读取，使用缓存的映射版本）
    if chapter_num:
        from file_io import get_chapter_event, get_skeleton_context, get_adaptation_principles

        # 判断是否是续写模式
        is_continue = _is_continue_mode(config)
        
        if is_continue:
            # 续写模式：从plan.md提取事件
            ch_event = _get_continue_plan_event(config, chapter_num)
            if ch_event:
                ch_event = f"第{chapter_num}章：{ch_event}"
            else:
                ch_event = "（续写方案中未找到本章事件）"
            
            # 续写模式：从concept.md提取骨架和改编原则
            concept_path = Path(config.get("rewrites_dir", "")) / "concept.md"
            if concept_path.exists():
                concept_text = concept_path.read_text(encoding="utf-8")
                # 提取全局结构
                skel_match = re.search(r'<structure>(.*?)</structure>', concept_text, re.DOTALL)
                if skel_match:
                    skel_ctx = skel_match.group(1).strip()[:1000]
                else:
                    skel_ctx = "（续写模式：请参考concept.md中的剧情结构）"
                # 提取改写原则
                adapt_match = re.search(r'<principles>(.*?)</principles>', concept_text, re.DOTALL)
                if adapt_match:
                    adapt_pr = adapt_match.group(1).strip()[:1000]
                else:
                    adapt_pr = "（续写模式：延续原作核心要素）"
            else:
                skel_ctx = "（续写模式：请参考续写方案中的情节线）"
                adapt_pr = "（续写模式：延续原作核心要素）"
        else:
            # 仿写模式：从源文events.json提取
            events_mapped = _load_events_mapped(config)
            
            ch_event = "（事件未提取）"
            for e in events_mapped:
                if e.get("id") == chapter_num or e.get("chapter_index") == chapter_num:
                    if e.get("event"):
                        ch_event = f"第{chapter_num}章：{e['event']}"
                    break
            
            # 使用缓存的骨架和改编策略
            skeleton_mapped = _load_skeleton_mapped(config)
            adaptation_mapped = _load_adaptation_mapped(config)
            
            skel_ctx = get_skeleton_context(config, chapter_num) or "（骨架未生成）"
            adapt_pr = get_adaptation_principles(config) or "（改编策略未生成）"

            # 对骨架和改编策略的上下文也做替换
            name_map = _build_name_map(config)
            if name_map:
                for old_name, new_name in name_map.items():
                    skel_ctx = skel_ctx.replace(old_name, new_name)
                    adapt_pr = adapt_pr.replace(old_name, new_name)

        replacements.setdefault("event", ch_event)
        replacements.setdefault("structure", skel_ctx)
        replacements.setdefault("principles", adapt_pr)

    # 注入角色行为卡片（写章时需要）
    if prompt_type == "write-chapter" and "角色行为卡片" not in replacements:
        char_card = _load_char_card(config)
        replacements["角色行为卡片"] = char_card

    # 合并额外替换变量
    if extra_replacements:
        replacements.update(extra_replacements)

    # 优先从 tasks/ 目录加载 task prompt，fallback 到 prompts/
    tasks_dir = Path(__file__).parent.parent.parent.parent / "tasks"
    task_path = tasks_dir / f"{prompt_type}.md"
    if task_path.exists():
        prompt_path = str(task_path)
    else:
        prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    if not system_prompt:
        system_prompt = _get_system_prompt_cached(prompt_type)
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "agent.md"

    # XML 标签注入（fangcun-drama 同款，write-chapter 用 markdown+△ 格式不注入）
    xml_tags = {
        "plot-guide": "<plotGuide>章纲内容</plotGuide>",
        "style-guide": "<styleGuide>风格指南内容</styleGuide>",
    }
    if prompt_type in xml_tags:
        system_prompt += f"\n\n你必须使用如下XML格式输出全部内容：\n{xml_tags[prompt_type]}"

    # 重试修正提示：注入 system_prompt 前端
    if retry_context:
        system_prompt = f"【修正提示】上一次写这章存在以下问题：{retry_context}。这次务必修正。\n\n{system_prompt}"

    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)

    # 不限制 max_tokens
    max_tokens = None

    label = f"ch{chapter_num or '?'} {prompt_type}"

    t_req = time.time()
    try:
        result = call_llm(config, prompt_type, user_prompt, system_prompt, ch=chapter_num, max_tokens=max_tokens)
        elapsed = time.time() - t_req
        print(f"  [OK] {label} ({elapsed:.0f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f"  [FAIL] {label} ({elapsed:.0f}s): {e}")
        raise


def process_plot_guide_output(config, chapter_num, ai_output):
    """处理 plot-guide 的输出，填充剩余模板变量。
    
    AI 已在 prompt 中直接输出完整 markdown（模板内嵌），
    这里只做 {N}、{女主名} 等变量的补替换。
    """
    from prompt_loader import make_book_data_replacements

    result = ai_output

    src_chars = count_source_chars(config, chapter_num)
    replacements = {
        "N": str(chapter_num),
        "N03d": f"{chapter_num:03d}",
        "源文字数": str(src_chars),
        "目标字数": str(src_chars),
        "目标字数_min": str(int(src_chars * 0.9)),
        "目标字数_max": str(int(src_chars * 1.1)),
        "作者名": config.get("author", ""),
        "新书名": Path(config.get("rewrites_dir", "")).name,
        "源书名": config.get("source_book", ""),
    }
    book_data = _get_book_data(config.get("rewrites_dir", ""))
    if book_data:
        bd_replacements = make_book_data_replacements(book_data)
        replacements.update(bd_replacements)
    else:
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for role, key in [("男主", "男主名"), ("女主", "女主名")]:
                m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                if m and key not in replacements:
                    replacements[key] = m.group(1)

    result = safe_format(result, replacements)

    return result


def _strip_source_text(plot_guide_text):
    """从 plot_guide 中去掉源文全文部分，防止 write-chapter 照抄。
    
    源文全文通常在"排除项"之后，以大段正文形式出现。
    只保留节拍映射、分析结果、排除项等结构化内容。
    """
    # 方式1：去掉"排除项"之后的所有内容（源文全文通常在最后）
    markers = ["## 排除项", "## 地点约束"]
    cut_pos = len(plot_guide_text)
    for marker in markers:
        pos = plot_guide_text.find(marker)
        if pos != -1:
            # 找到标记后，保留标记本身，去掉后面的大段文字
            end_of_line = plot_guide_text.find("\n", pos + len(marker))
            if end_of_line != -1:
                # 检查标记后是否有大量文字（源文全文）
                after = plot_guide_text[end_of_line:]
                if len(after) > 500:  # 超过500字认为是源文全文
                    cut_pos = min(cut_pos, end_of_line)

    if cut_pos < len(plot_guide_text):
        return plot_guide_text[:cut_pos].rstrip()

    # 方式2：如果上面没找到，检查是否有"源文全文"标记
    # 只在明确标记后截断，不截断长文本
    source_markers = ["## 源文全文", "## Source Text", "---\n\n第"]
    for marker in source_markers:
        pos = plot_guide_text.find(marker)
        if pos != -1:
            return plot_guide_text[:pos].rstrip()

    return plot_guide_text


def run_one_with_template(config, prompt_type, chapter_num=None, **kwargs):
    """包装 run_one，自动处理模板合并和 XML 提取。"""
    result = run_one(config, prompt_type, chapter_num, **kwargs)

    # prompts_only 跳过处理
    if config.get("prompts_only"):
        return result

    # XML 标签提取（fangcun-drama 同款）
    xml_tag_map = {
        "plot-guide": "plotGuide",
        "write-chapter": "chapter",
        "style-guide": "styleGuide",
    }
    if prompt_type in xml_tag_map:
        tag = xml_tag_map[prompt_type]
        m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", result)
        if m:
            result = m.group(1).strip()
        else:
            m_open = re.search(rf"<{tag}[^>]*>", result)
            if m_open:
                result = result[m_open.end():].strip()

    # plot-guide 模板合并
    if prompt_type == "plot-guide":
        result = process_plot_guide_output(config, chapter_num, result)
        # 去掉源文全文（防止 write-chapter 照抄）
        result = _strip_source_text(result)
        # 替换源文角色名（LLM 产出中可能残留源文角色名）
        name_map = _build_name_map(config)
        if name_map:
            for old_name, new_name in sorted(name_map.items(), key=lambda x: -len(x[0])):
                result = result.replace(old_name, new_name)

    return result
