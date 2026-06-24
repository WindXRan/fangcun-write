"""Phase: 章纲映射——LLM 读源文 events.json × 新书设定 → 生成新书章纲（换皮不换骨）。"""
import json, re, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import _path_setup  # noqa: F401
from lib.api_client import call_llm
from source_io import load_events


def phase_chapter_map(config, state_mgr=None):
    """LLM 并行生成新书章纲（换皮不换骨）。

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

    source_events = load_events(config)
    if not source_events:
        print("  [FAIL] 源文 events.json 不存在")
        if state_mgr: state_mgr.phase_failed("chapter-map", error="源文 events.json 不存在")
        return False

    concept_text = ""
    for fname in ["concept.md", "book_info.md", "world.md"]:
        fp = rewrites_dir / fname
        if fp.exists():
            concept_text += f"\n--- {fname} ---\n" + fp.read_text(encoding="utf-8")

    chars_text = ""
    chars_path = rewrites_dir / "characters.md"
    if chars_path.exists():
        chars_text = chars_path.read_text(encoding="utf-8")

    if not concept_text:
        print("  [WARN] 新书设定文件不存在，使用 name_map 机械替换")
        return _fallback_name_swap(config, source_events, rewrites_dir, state_mgr)

    batch_size = 10
    total = len(source_events)
    batches = []
    for i in range(0, total, batch_size):
        batches.append((i + 1, min(i + batch_size, total)))

    workers = config.get("workers", 200)
    print(f"  章纲生成 | {total}章 / {len(batches)}批 | 并行: {workers}")

    t0 = time.time()
    results = {}
    fail_count = 0

    prompts_dir = str(Path(__file__).resolve().parent.parent.parent / "prompts")
    base_dir = config.get("base_dir", ".")
    rewrites_str = config.get("rewrites_dir", "")

    def gen_batch(batch_start, batch_end):
        batch_events = source_events[batch_start - 1:batch_end]
        source_summary = _format_source_events(batch_events)

        from prompt_loader import load_prompt
        replacements = {
            "start": str(batch_start), "end": str(batch_end),
            "新书名": Path(rewrites_str).name,
            "贯穿目标": concept_text,
            "source_events": source_summary,
            "name_map": chars_text,
            "concept": concept_text,
            "characters_context": chars_text,
        }
        user_prompt = load_prompt(
            f"{prompts_dir}/chapter-map.md", base_dir, replacements,
            mode="api", rewrites_dir=rewrites_str,
        )
        # System prompt: 优先拆文库文风，回退 agent.md
        analyze_dir = config.get("analyze_dir", "")
        system_prompt = ""
        if analyze_dir:
            for fname in ["文风分析.md", "文风.md"]:
                sp = Path(analyze_dir) / fname
                if sp.exists():
                    system_prompt = sp.read_text(encoding="utf-8")[:4000]
                    break
        if not system_prompt:
            from prompt_meta import load_system_prompt
            system_prompt = load_system_prompt("agent.md") or ""
        system_prompt += "\n\n你必须输出一个 JSON 数组。不要输出其他内容。"

        try:
            result = call_llm(config, "chapter-map", user_prompt, system_prompt)
            m = re.search(r"\[[\s\S]*\]", result)
            if m:
                batch_data = json.loads(m.group(0))
                return batch_data, "ok"
            return None, "no_json"
        except Exception as e:
            return None, str(e)

    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as executor:
        futures = {}
        for b_start, b_end in batches:
            futures[executor.submit(gen_batch, b_start, b_end)] = (b_start, b_end)
        for future in as_completed(futures):
            b_start, b_end = futures[future]
            data, status = future.result()
            done = len(results) + len(batches) - len(futures) + 1
            if data:
                for e in data:
                    results[e.get("id", "")] = e
                print(f"    [{done}/{len(batches)}] V ch{b_start}-{b_end} ({len(data)}条)")
            else:
                fail_count += 1
                print(f"    [{done}/{len(batches)}] X ch{b_start}-{b_end} ({status})")
                for e in source_events[b_start - 1:b_end]:
                    results[e.get("id", "")] = _swap_names(e, chars_text)

    new_events = [results[str(i)] for i in range(1, total + 1) if str(i) in results]
    out_path = rewrites_dir / "events.json"
    out_path.write_text(json.dumps(new_events, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t0
    ok = sum(1 for _ in new_events)
    print(f"  完成 | {ok}章成功 / {fail_count}批失败 | {elapsed:.0f}s")
    print(f"  [OK] 章纲 → {out_path}")

    if state_mgr: state_mgr.phase_done("chapter-map")
    return True


def _format_source_events(events) -> str:
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
    ne = dict(event)
    name_map = {}
    for m in re.finditer(r'<item\s+old="([^"]+)"\s+new="([^"]+)"', chars_text):
        name_map[m.group(1)] = m.group(2)
    for old, new in sorted(name_map.items(), key=lambda x: -len(x[0])):
        for k in ne:
            if isinstance(ne[k], str):
                ne[k] = ne[k].replace(old, new)
    return ne


def _fallback_name_swap(config, source_events, rewrites_dir, state_mgr):
    chars_path = rewrites_dir / "characters.md"
    chars_text = chars_path.read_text(encoding="utf-8") if chars_path.exists() else ""
    new_events = [_swap_names(e, chars_text) for e in source_events]
    out_path = rewrites_dir / "events.json"
    out_path.write_text(json.dumps(new_events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] 章纲（name_map替换） → {out_path} ({len(new_events)}章)")
    if state_mgr: state_mgr.phase_done("chapter-map")
    return True
