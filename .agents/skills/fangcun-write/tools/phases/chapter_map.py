"""Phase: 章纲映射——LLM 读源文 events.json × 新书设定 → 生成新书章纲（换皮不换骨）。"""
import json, re
from pathlib import Path

import _path_setup  # noqa: F401
from lib.api_client import call_llm
from source_io import load_events


def phase_chapter_map(config, state_mgr=None):
    """LLM 生成新书章纲（换皮不换骨）。

    放在 open-book 之后、guides 之前。
    输出：{rewrites_dir}/events.json
    """
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.exists():
        rewrites_dir.mkdir(parents=True, exist_ok=True)

    if state_mgr:
        if state_mgr.is_phase_done("chapter-map"):
            print("章纲已有，跳过")
            return True
        state_mgr.phase_start("chapter-map")

    # 1. 读源文 events.json
    source_events = load_events(config)
    if not source_events:
        print("  [FAIL] 源文 events.json 不存在")
        if state_mgr:
            state_mgr.phase_failed("chapter-map", error="源文 events.json 不存在")
        return False

    # 2. 读新书设定
    concept_text = ""
    for fname in ["concept.md", "book_info.md", "world.md"]:
        fp = rewrites_dir / fname
        if fp.exists():
            concept_text += f"\n--- {fname} ---\n" + fp.read_text(encoding="utf-8")[:3000]

    chars_text = ""
    chars_path = rewrites_dir / "characters.md"
    if chars_path.exists():
        chars_text = chars_path.read_text(encoding="utf-8")[:2000]

    if not concept_text:
        print("  [WARN] 新书设定文件不存在，使用 name_map 机械替换")
        return _fallback_name_swap(config, source_events, rewrites_dir, state_mgr)

    # 3. 分批生成（每批 20 章）
    batch_size = 20
    new_events = []
    total_chapters = len(source_events)

    print(f"  源文 {total_chapters} 章，每批 {batch_size} 章生成章纲...")

    for batch_start in range(0, total_chapters, batch_size):
        batch_end = min(batch_start + batch_size, total_chapters)
        batch = source_events[batch_start:batch_end]

        # Build source events summary for this batch
        source_summary = _format_source_events(batch)

        # Build prompt replacements
        from prompt_loader import load_prompt
        prompts_dir = str(Path(__file__).resolve().parent.parent.parent / "prompts")
        replacements = {
            "start": str(batch_start + 1),
            "end": str(batch_end),
            "新书名": Path(config.get("rewrites_dir", "")).name,
            "贯穿目标": concept_text[:500],
            "source_events": source_summary,
            "name_map": chars_text[:1000],
            "concept": concept_text,
            "characters_context": chars_text,
        }

        user_prompt = load_prompt(
            f"{prompts_dir}/chapter-map.md",
            config.get("base_dir", "."), replacements, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )

        from prompt_meta import load_system_prompt
        system_prompt = load_system_prompt("agent.md") or ""
        system_prompt += "\n\n你必须输出一个 JSON 数组，包含该批次所有章节的章纲条目。不要输出其他内容。"

        try:
            result = call_llm(config, "chapter-map", user_prompt, system_prompt)
            # Extract JSON array
            json_match = re.search(r"\[[\s\S]*\]", result)
            if json_match:
                batch_events = json.loads(json_match.group(0))
                new_events.extend(batch_events)
                print(f"    {batch_start+1}-{batch_end}章 OK ({len(batch_events)}条)")
            else:
                print(f"    {batch_start+1}-{batch_end}章 FAIL: 未找到 JSON，使用 name_map 回退")
                for e in batch:
                    new_events.append(_swap_names(e, chars_text))
        except Exception as ex:
            print(f"    {batch_start+1}-{batch_end}章 FAIL: {ex}")
            for e in batch:
                new_events.append(_swap_names(e, chars_text))

    # 4. 写入
    out_path = rewrites_dir / "events.json"
    out_path.write_text(json.dumps(new_events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] 章纲 → {out_path} ({len(new_events)}章)")

    if state_mgr:
        state_mgr.phase_done("chapter-map")
    return True


def _format_source_events(events) -> str:
    """将源文 events 格式化为简洁文本供 prompt 使用。"""
    lines = []
    for e in events:
        lines.append(
            f"第{e.get('id','?')}章: {e.get('核心事件','')} | "
            f"开头:{e.get('开头承接','')[:30]} | "
            f"结尾:{e.get('结尾状态','')[:30]} | "
            f"弧线:{e.get('情绪弧线','')}"
        )
    return "\n".join(lines)


def _swap_names(event: dict, chars_text: str) -> dict:
    """机械替换角色名（LLM 失败时的回退）。"""
    ne = dict(event)
    # Extract name_map from chars_text
    name_map = {}
    for m in re.finditer(r'<item\s+old="([^"]+)"\s+new="([^"]+)"', chars_text):
        name_map[m.group(1)] = m.group(2)
    for old, new in sorted(name_map.items(), key=lambda x: -len(x[0])):
        for k in ne:
            if isinstance(ne[k], str):
                ne[k] = ne[k].replace(old, new)
    return ne


def _fallback_name_swap(config, source_events, rewrites_dir, state_mgr):
    """纯 name_map 替换（无 LLM，无新书设定时使用）。"""
    chars_path = rewrites_dir / "characters.md"
    chars_text = chars_path.read_text(encoding="utf-8") if chars_path.exists() else ""
    new_events = [_swap_names(e, chars_text) for e in source_events]
    out_path = rewrites_dir / "events.json"
    out_path.write_text(json.dumps(new_events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] 章纲（name_map替换） → {out_path} ({len(new_events)}章)")
    if state_mgr:
        state_mgr.phase_done("chapter-map")
    return True
