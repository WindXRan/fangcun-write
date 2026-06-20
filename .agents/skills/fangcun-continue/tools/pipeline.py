"""
fangcun-continue pipeline: 小说续写/第二部引擎

架构：
  config.json 只包含源文路径和API配置
  书名/时间跳跃等信息在流程中动态生成

流程：
  1. 分析源文 → 生成 analysis/
  2. AI生成方案 → 输出 plans/ → 用户选择
  3. 用户确认后 → 确定书名/时间跳跃等 → 生成 outline/
  4. 逐章写作 → 生成 chapters/
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 添加 fangcun-analyze 和 fangcun-novel 到 path
_ANALYZE_TOOLS = Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"
_ANALYZE_LIB = _ANALYZE_TOOLS / "lib"
_NOVEL_TOOLS = Path(__file__).parent.parent.parent / "fangcun-novel" / "tools"
sys.path.insert(0, str(_ANALYZE_TOOLS))
sys.path.insert(0, str(_ANALYZE_LIB))
sys.path.insert(0, str(_NOVEL_TOOLS))

from lib.api_client import call_llm, get_api_key, get_api_url
from source_io import load_events, get_source_text


def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 自动检测 base_dir（如果未指定）
    if "base_dir" not in config:
        # 从 config_path 推断：.agents/skills/fangcun-continue/config/xxx.json -> 项目根目录
        config["base_dir"] = str(Path(config_path).parent.parent.parent.parent.parent)
    
    return config


def get_dirs(config):
    """获取目录结构"""
    base_dir = Path(config.get("base_dir", "."))
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    
    # 源文目录
    source_dir = base_dir / "projects" / author / source_book
    
    # 续写专用目录（在source_dir下，不在cache下）
    continue_dir = source_dir / "续写引擎"
    
    return {
        "source_dir": source_dir,
        "cache_dir": source_dir / "_cache",
        "continue_dir": continue_dir,
        "analysis_dir": continue_dir / "analysis",
        "plans_dir": continue_dir / "plans",
    }


# ─── Phase 1: 分析源文 ──────────────────────────────────────────────────────

def phase_analyze(config):
    """分析源文，提取角色库、世界观、结局状态"""
    print("\n" + "=" * 50)
    print("Phase 1: 分析源文")
    print("=" * 50)
    
    dirs = get_dirs(config)
    analysis_dir = dirs["analysis_dir"]
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取事件表（从cache中读取）
    events = load_events(config)
    if not events:
        print("[FAIL] 未找到事件表，请先运行 fangcun-analyze")
        return False
    
    total_chapters = len(events)
    print(f"  源文：{total_chapters} 章")
    
    # 提取角色
    print("  提取角色...")
    characters = _extract_characters(events)
    _save_md(analysis_dir / "characters.md", _format_characters(characters))
    
    # 提取关系线
    print("  提取关系线...")
    relationships = _extract_relationships(events)
    _save_md(analysis_dir / "relationships.md", relationships)
    
    # 提取结局状态
    print("  提取结局状态...")
    ending_text = get_source_text(config, total_chapters)
    ending_state = _extract_ending_state(events, ending_text)
    _save_md(analysis_dir / "ending_state.md", ending_state)
    
    # 提取情节线
    print("  提取情节线...")
    plot_lines = _extract_plot_lines(events)
    _save_md(analysis_dir / "plot_lines.md", plot_lines)
    
    # 保存元数据
    meta = {
        "source_dir": str(dirs["source_dir"]),
        "total_chapters": total_chapters,
        "characters_count": len(characters),
    }
    (analysis_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    
    print(f"\n[OK] 分析完成 → {analysis_dir}")
    return True


def _extract_characters(events):
    """提取角色"""
    characters = {}
    for event in events:
        event_text = event.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 3:
            for char in parts[2].strip().split("、"):
                char = char.strip()
                if char and len(char) >= 2:
                    if char not in characters:
                        characters[char] = {"name": char, "count": 0}
                    characters[char]["count"] += 1
    return characters


def _format_characters(characters):
    """格式化角色信息"""
    lines = ["# 角色库\n"]
    lines.append("| 角色 | 出场次数 |")
    lines.append("|------|----------|")
    for c in sorted(characters.values(), key=lambda x: -x["count"]):
        lines.append(f"| {c['name']} | {c['count']} |")
    return "\n".join(lines)


def _extract_relationships(events):
    """提取关系线"""
    rel_counts = {}
    for event in events:
        event_text = event.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 3:
            chars = [c.strip() for c in parts[2].strip().split("、") if c.strip() and len(c.strip()) >= 2]
            for i in range(len(chars)):
                for j in range(i+1, len(chars)):
                    key = tuple(sorted([chars[i], chars[j]]))
                    rel_counts[key] = rel_counts.get(key, 0) + 1
    
    lines = ["# 关系线\n"]
    lines.append("| 关系 | 共现次数 |")
    lines.append("|------|----------|")
    for (c1, c2), count in sorted(rel_counts.items(), key=lambda x: -x[1])[:30]:
        lines.append(f"| {c1} ↔ {c2} | {count} |")
    return "\n".join(lines)


def _extract_ending_state(events, ending_text):
    """提取结局状态"""
    last_events = events[-3:] if len(events) >= 3 else events
    
    lines = ["# 结局状态\n"]
    lines.append("## 最后3章\n")
    for event in last_events:
        event_text = event.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 4:
            lines.append(f"- **{parts[1].strip()}**: {parts[3].strip()}")
    
    lines.append("\n## 结局原文摘要\n")
    lines.append(ending_text[:800] if ending_text else "（无）")
    
    return "\n".join(lines)


def _extract_plot_lines(events):
    """提取情节线"""
    lines = ["# 情节线\n"]
    lines.append("| 章 | 标题 | 强度 | 类型 |")
    lines.append("|---|------|------|------|")
    for event in events:
        event_text = event.get("event", "")
        parts = event_text.split("|")
        if len(parts) >= 7:
            ch = event.get("id", "")
            title = parts[1].strip()
            intensity = parts[4].strip()
            genre = parts[6].strip()
            lines.append(f"| {ch} | {title} | {intensity} | {genre} |")
    return "\n".join(lines)


def _save_md(path, content):
    """保存markdown文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f"    [OK] {path.name}")


# ─── Phase 2: 生成方案 ──────────────────────────────────────────────────────

def phase_plan(config):
    """AI生成续写方案"""
    print("\n" + "=" * 50)
    print("Phase 2: 生成续写方案")
    print("=" * 50)
    
    dirs = get_dirs(config)
    analysis_dir = dirs["analysis_dir"]
    plans_dir = dirs["plans_dir"]
    plans_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取分析结果
    characters = (analysis_dir / "characters.md").read_text(encoding='utf-8')
    relationships = (analysis_dir / "relationships.md").read_text(encoding='utf-8')
    ending_state = (analysis_dir / "ending_state.md").read_text(encoding='utf-8')
    plot_lines = (analysis_dir / "plot_lines.md").read_text(encoding='utf-8')
    
    # 生成方案
    print("  AI 生成续写方案...")
    plans = _generate_plans(config, characters, relationships, ending_state, plot_lines)
    
    # 保存方案
    for i, plan in enumerate(plans):
        plan_path = plans_dir / f"plan_{i+1}.md"
        plan_path.write_text(plan, encoding='utf-8')
        print(f"    [OK] plan_{i+1}.md")
    
    # 输出摘要
    print(f"\n[OK] 生成 {len(plans)} 个方案")
    print(f"方案目录: {plans_dir}")
    print("\n请查看方案，选择一个后运行:")
    print("  python pipeline.py --config config.json --phase confirm --plan 1")
    
    return True


def _generate_plans(config, characters, relationships, ending_state, plot_lines):
    """生成续写方案"""
    source_book = config.get("source_book", "")
    
    prompt = f"""你是一个专业的小说策划。基于以下小说分析，设计3个续写方案（第二部）。

## 原著信息
- 书名：《{source_book}》

## 原著角色库
{characters[:1500]}

## 原著关系线
{relationships[:800]}

## 原著结局状态
{ending_state[:800]}

## 原著情节线（部分）
{plot_lines[:1000]}

## 续写设计原则

**第一步：分析原作**
从以上信息中提取：
- 原作的核心卖点是什么？
- 原作的情感基调是什么？（治愈/热血/虐心/搞笑...）
- 原作的主要冲突类型是什么？（家庭/职场/校园/奇幻...）
- 原作的读者群体是谁？

**第二步：设计方案**
基于分析结果，设计3个续写方案：
- 延续原作的核心卖点和情感基调
- 冲突类型与原作一致（不要擅自改变）
- 新角色符合原作的世界观
- 情感线发展方向与原作一致

**第三步：输出格式**

每个方案包含：
1. **书名**（5-10字，符合原作风格）
2. **核心卖点分析**（一句话，原作为什么好看）
3. **续写冲突**（一句话，延续原作的冲突类型）
4. **时间跳跃**（多久后？为什么？）
5. **新角色**（2-3个，符合原作世界观）
6. **情感线发展**（与原作基调一致）
7. **高潮设计**（至少3个高潮点）
8. **预期章数**（150-200章，总字数30-60万字）

请用以下格式输出：

---
## 方案一：《书名》

**核心卖点：** ...

**续写冲突：** ...

**时间跳跃：** ...

**新角色：**
- 角色A：...
- 角色B：...

**情感线：** ...

**高潮设计：**
1. ...
2. ...
3. ...

**预期章数：** ...

---
## 方案二：《书名》
...
---
"""
    
    try:
        result = call_llm(config, "plan", prompt, 
                         system_prompt="你是一个专业的小说策划。你必须基于原作的风格和卖点来设计续写，不要擅自改变原作的基调。输出简洁有力，不要废话。",
                         max_tokens=4096)
        
        # 解析方案
        plans = []
        current = []
        for line in result.split('\n'):
            if line.startswith('## 方案') or line.startswith('---'):
                if current:
                    plans.append('\n'.join(current))
                    current = []
                if not line.startswith('---'):
                    current.append(line)
            elif current:
                current.append(line)
        if current:
            plans.append('\n'.join(current))
        
        return plans[:3] if len(plans) >= 3 else [result]
    except Exception as e:
        print(f"    [FAIL] {e}")
        return [f"生成失败: {e}"]


# ─── Phase 3: 确认方案 ──────────────────────────────────────────────────────

def phase_confirm(config, plan_num=1):
    """用户确认方案，生成续写配置"""
    print("\n" + "=" * 50)
    print("Phase 3: 确认方案")
    print("=" * 50)
    
    dirs = get_dirs(config)
    plans_dir = dirs["plans_dir"]
    plan_path = plans_dir / f"plan_{plan_num}.md"
    
    if not plan_path.exists():
        print(f"[FAIL] 方案不存在: {plan_path}")
        return False
    
    plan_content = plan_path.read_text(encoding='utf-8')
    print(f"\n选择的方案:\n{plan_content[:500]}...\n")
    
    # 从方案中提取信息
    import re
    book_name_match = re.search(r'《(.+?)》', plan_content)
    book_name = book_name_match.group(1) if book_name_match else f"续写_{plan_num}"
    
    time_match = re.search(r'时间跳跃[：:]\s*(.+)', plan_content)
    time_jump = time_match.group(1).strip() if time_match else "多年后"
    
    # 生成续写配置（使用projects架构：projects/{作者}/{源书}/rewrites/{续写书名}/）
    source_dir = dirs["source_dir"]
    rewrites_dir = source_dir / "rewrites" / book_name
    rewrites_dir.mkdir(parents=True, exist_ok=True)
    
    continue_config = {
        "source_dir": str(source_dir),
        "rewrites_dir": str(rewrites_dir),
        "book_name": book_name,
        "time_jump": time_jump,
        "plan_file": str(plan_path),
        "api_key": config.get("api_key"),
        "api_base_url": config.get("api_base_url"),
        "model": config.get("model", "mimo-v2.5-pro"),
    }
    
    config_path = rewrites_dir / "continue_config.json"
    config_path.write_text(json.dumps(continue_config, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # 复制分析结果到rewrites_dir
    analysis_dir = dirs["analysis_dir"]
    import shutil
    shutil.copytree(analysis_dir, rewrites_dir / "analysis", dirs_exist_ok=True)
    
    # 复制characters.md到rewrites_dir根目录（供run_one读取）
    chars_src = analysis_dir / "characters.md"
    if chars_src.exists():
        shutil.copy2(chars_src, rewrites_dir / "characters.md")
        print(f"  [OK] 复制 characters.md 到 {rewrites_dir}")
    
    # 复制world.md到rewrites_dir根目录（供run_one读取）
    world_src = analysis_dir / "world.md"
    if world_src.exists():
        shutil.copy2(world_src, rewrites_dir / "world.md")
    
    # 复制plot.md到rewrites_dir根目录（供run_one读取）
    plot_src = analysis_dir / "plot.md"
    if plot_src.exists():
        shutil.copy2(plot_src, rewrites_dir / "plot.md")
    
    print(f"[OK] 确认完成")
    print(f"  书名: {book_name}")
    print(f"  时间跳跃: {time_jump}")
    print(f"  续写配置: {config_path}")
    print(f"\n下一步:")
    print(f"  python pipeline.py --config {config_path} --phase write --start 1 --end 20")
    
    return True


# ─── Phase 4: 逐章写作 ──────────────────────────────────────────────────────

def phase_write(config, start=1, end=20):
    """逐章写作"""
    print("\n" + "=" * 50)
    print("Phase 4: 逐章写作")
    print("=" * 50)
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.exists():
        print(f"[FAIL] 输出目录不存在: {rewrites_dir}")
        return False
    
    # 读取分析结果
    analysis_dir = rewrites_dir / "analysis"
    characters = (analysis_dir / "characters.md").read_text(encoding='utf-8')
    relationships = (analysis_dir / "relationships.md").read_text(encoding='utf-8')
    ending_state = (analysis_dir / "ending_state.md").read_text(encoding='utf-8')
    
    # 读取方案
    plan_file = config.get("plan_file", "")
    if plan_file and Path(plan_file).exists():
        plan_content = Path(plan_file).read_text(encoding='utf-8')
    else:
        plan_content = "（无方案）"
    
    # 创建章节目录
    chapters_dir = rewrites_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # 逐章写作
    print(f"  写第{start}章到第{end}章...")
    
    for ch_num in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch_num:03d}.txt"
        
        # 检查是否已存在
        if ch_file.exists():
            print(f"    [SKIP] 第{ch_num}章已存在")
            continue
        
        # 读取前文（最多3章）
        prev_context = _get_previous_context(chapters_dir, ch_num, max_chapters=3)
        
        # 生成章节
        print(f"    [WRITE] 第{ch_num}章...")
        chapter_content = _generate_chapter(config, ch_num, characters, relationships, 
                                           ending_state, plan_content, prev_context)
        
        if chapter_content:
            ch_file.write_text(chapter_content, encoding='utf-8')
            print(f"    [OK] 第{ch_num}章 ({len(chapter_content)}字)")
        else:
            print(f"    [FAIL] 第{ch_num}章")
    
    print(f"\n[OK] 写章完成 → {chapters_dir}")
    return True


def _get_previous_context(chapters_dir, current_ch, max_chapters=3):
    """获取前文内容"""
    context_parts = []
    for i in range(max(1, current_ch - max_chapters), current_ch):
        ch_file = chapters_dir / f"ch_{i:03d}.txt"
        if ch_file.exists():
            content = ch_file.read_text(encoding='utf-8')
            # 只取最后500字作为上下文
            if len(content) > 500:
                content = "..." + content[-500:]
            context_parts.append(f"【第{i}章】\n{content}")
    return "\n\n".join(context_parts)


def _generate_chapter(config, ch_num, characters, relationships, ending_state, plan_content, prev_context):
    """生成单章内容（调用 fangcun-write 续写模式）"""
    import sys
    writer_engine = Path(__file__).parent.parent.parent / "fangcun-write" / "tools"
    sys.path.insert(0, str(writer_engine))
    
    from writer import write_chapter
    
    # 构建续写上下文（注入到角色约束中）
    context = f"""## 角色名映射（必须使用这些名字，不可自编）
{characters[:2000]}

## 续写方案
{plan_content[:2000]}

## 原著关系线
{relationships[:1000]}
"""
    
    # 调用 fangcun-write 的续写模式
    result = write_chapter(config, ch_num, mode="continue", context=context, auto_fix=True)
    return result


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="fangcun-continue: 小说续写引擎")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--phase", required=True, 
                       choices=["analyze", "plan", "confirm", "outline", "write", "review"],
                       help="执行阶段")
    parser.add_argument("--plan", type=int, default=1, help="选择的方案编号")
    parser.add_argument("--start", type=int, default=1, help="开始章节")
    parser.add_argument("--end", type=int, default=20, help="结束章节")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.phase == "analyze":
        phase_analyze(config)
    elif args.phase == "plan":
        phase_plan(config)
    elif args.phase == "confirm":
        phase_confirm(config, args.plan)
    elif args.phase == "write":
        phase_write(config, args.start, args.end)
    else:
        print(f"[TODO] {args.phase} 阶段待实现")


if __name__ == "__main__":
    main()
