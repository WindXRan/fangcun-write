"""Phase 1.5: 骨架映射（源文章节→新书章节）

分析源文骨架结构，设计新书的章节骨架。
输出 skeleton_map.json，供 plot-guide 阶段使用。
"""

import os
import re
import json
from pathlib import Path

import _path_setup  # noqa: F401
from state_manager import atomic_write_text
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from prompt_loader import load_prompt
from lib.api_client import call_llm


def _try_parse_json(text):
    """尝试解析 JSON，失败时自动修复常见问题。"""
    # 直接尝试
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 修复尾部逗号
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 修复截断的 JSON（补缺失的括号）
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    if open_braces > 0 or open_brackets > 0:
        fixed = text.rstrip().rstrip(',')
        if fixed.endswith('"'):
            fixed += '"'
        fixed += ']' * open_brackets + '}' * open_braces
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # 提取最后一个完整的 chapters 数组
    m = re.search(r'"chapters"\s*:\s*\[([\s\S]*?)\](?=\s*[,}])', text)
    if m:
        chapters_str = m.group(1)
        # 逐个提取 chapter 对象
        chapters = []
        for cm in re.finditer(r'\{[^{}]*"ch"\s*:\s*\d+[^{}]*\}', chapters_str):
            try:
                chapters.append(json.loads(cm.group(0)))
            except json.JSONDecodeError:
                continue
        if chapters:
            return {"chapters": chapters}

    return None


def phase_skeleton_map(config, state_mgr=None):
    """骨架映射：分析源文骨架，设计新书章节结构。"""
    print("\n" + "=" * 50)
    print("Phase 1.5: 骨架映射")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("skeleton-map"):
            print("skeleton_map.json 已完成，跳过")
            return True
        state_mgr.phase_start("skeleton-map")

    rewrites_dir = Path(config.get("rewrites_dir", ""))
    base_dir = Path(config.get("base_dir", os.getcwd()))
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    # 加载源文产物
    from file_io import load_events, load_skeleton, get_events_text

    events = load_events(config)
    skeleton = load_skeleton(config)
    events_text = get_events_text(config)

    if not events:
        print("  [FAIL] events.json 不存在，请先运行 fangcun-analyze")
        if state_mgr:
            state_mgr.phase_failed("skeleton-map", error="events.json 不存在")
        return False

    # 加载 concept.md
    concept_path = rewrites_dir / "concept.md"
    if not concept_path.exists():
        print("  [FAIL] concept.md 不存在，请先运行 open-book")
        if state_mgr:
            state_mgr.phase_failed("skeleton-map", error="concept.md 不存在")
        return False
    concept = concept_path.read_text(encoding="utf-8")

    # 构建替换变量
    book_name = config.get("book_name", "auto")
    base_replacements = {
        "新书名": book_name if book_name != "auto" else "（待生成）",
        "源书名": source_book,
        "skeleton": (skeleton or "（未生成）")[:3000],
        "concept": concept[:3000],
    }

    prompts_dir = config.get("prompts_dir", str(Path(__file__).resolve().parent.parent.parent / "prompts"))
    tasks_dir = str(Path(__file__).resolve().parent.parent.parent / "tasks")

    # 分批处理 events（避免单次 prompt 过长导致超时）
    events_lines = events_text.split("\n")
    total_lines = len(events_lines)
    batch_size = max(20, total_lines // 2)  # 每批至少20行
    batches = []
    for i in range(0, total_lines, batch_size):
        batch_text = "\n".join(events_lines[i:i + batch_size])
        batches.append(batch_text)

    all_chapters = []
    all_trim = []
    analysis = {}

    for batch_idx, batch_events in enumerate(batches):
        print(f"  批次 {batch_idx + 1}/{len(batches)}...")
        replacements = {**base_replacements, "events_text": batch_events[:8000]}

        try:
            # 优先从 tasks/ 加载
            task_file = Path(tasks_dir) / "skeleton-map.md"
            if not task_file.exists():
                task_file = Path(prompts_dir) / "skeleton-map.md"
            user_prompt = load_prompt(
                str(task_file),
                str(base_dir),
                replacements,
                mode="api",
                rewrites_dir=str(rewrites_dir),
            )
            content = call_llm(config, "skeleton-map", user_prompt, "")

            # 提取并修复 JSON
            json_match = re.search(r'```json\s*([\s\S]*?)```', content)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_match = re.search(r'\{[\s\S]*"chapters"[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    print(f"  [WARN] 批次 {batch_idx + 1} JSON 提取失败，跳过")
                    continue

            batch_result = _try_parse_json(json_str)
            if not batch_result:
                print(f"  [WARN] 批次 {batch_idx + 1} JSON 解析失败，跳过")
                continue
            batch_chapters = batch_result.get("chapters", [])
            batch_trim = batch_result.get("trim_reasons", [])

            # 合并结果
            ch_offset = len(all_chapters)
            for ch in batch_chapters:
                ch["ch"] = ch_offset + 1 + len([c for c in all_chapters])
                all_chapters.append(ch)
            all_trim.extend(batch_trim)

            # 合并分析
            if not analysis:
                analysis = batch_result.get("analysis", {})
            else:
                # 合并核心章、过渡章、水章列表
                for key in ("core_chapters", "transition_chapters", "filler_chapters"):
                    existing = set(analysis.get(key, []))
                    new_items = batch_result.get("analysis", {}).get(key, [])
                    existing.update(new_items)
                    analysis[key] = sorted(existing)

        except json.JSONDecodeError as e:
            print(f"  [WARN] 批次 {batch_idx + 1} JSON 解析失败: {e}")
            continue
        except Exception as e:
            print(f"  [WARN] 批次 {batch_idx + 1} 失败: {e}")
            continue

    if not all_chapters:
        print("  [FAIL] 所有批次均失败")
        if state_mgr:
            state_mgr.phase_failed("skeleton-map", error="所有批次均失败")
        return False

    # 重新编号
    for i, ch in enumerate(all_chapters):
        ch["ch"] = i + 1

    # 构建最终结果
    skeleton_map = {
        "analysis": analysis,
        "new_structure": _build_acts(all_chapters),
        "chapters": all_chapters,
        "trim_reasons": all_trim,
    }

    # 验证源文章节覆盖率
    covered = set()
    for entry in skeleton_map.get("chapters", []):
        for s in entry.get("source", []):
            covered.add(s)
    for trim in skeleton_map.get("trim_reasons", []):
        for s in trim.get("source", []):
            covered.add(s)
    total_source = len(events)
    all_source = set(range(1, total_source + 1))
    missing = all_source - covered
    if missing and len(missing) > 10:
        print(f"  [WARN] {len(missing)} 个源文章节未覆盖: {sorted(missing)[:20]}...")

    # 保存
    output_path = rewrites_dir / "skeleton_map.json"
    atomic_write_text(output_path, json.dumps(skeleton_map, ensure_ascii=False, indent=2))
    print(f"  [OK] skeleton_map.json")

    # 打印摘要
    new_chapters = len(skeleton_map.get("chapters", []))
    source_chapters = skeleton_map.get("analysis", {}).get("source_chapters", "?")
    actions = {}
    for ch in skeleton_map.get("chapters", []):
        a = ch.get("action", "unknown")
        actions[a] = actions.get(a, 0) + 1
    print(f"  源文 {total_source} 章 → 新书 {new_chapters} 章")
    for a, count in sorted(actions.items()):
        print(f"    {a}: {count} 章")

    if state_mgr:
        state_mgr.phase_done("skeleton-map")
    return True


def _build_acts(chapters):
    """根据章节列表自动划分幕次。"""
    total = len(chapters)
    if total <= 10:
        return {"total_chapters": total, "acts": [
            {"act": 1, "name": "全书", "chapters": list(range(1, total + 1)), "function": "完整故事"}
        ]}

    # 按三分之一划分
    act1_end = total // 3
    act2_end = act1_end * 2

    return {"total_chapters": total, "acts": [
        {"act": 1, "name": "开篇", "chapters": list(range(1, act1_end + 1)), "function": "建立人物与核心矛盾"},
        {"act": 2, "name": "发展", "chapters": list(range(act1_end + 1, act2_end + 1)), "function": "矛盾升级与解决"},
        {"act": 3, "name": "收尾", "chapters": list(range(act2_end + 1, total + 1)), "function": "高潮与结局"},
    ]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    cfg.setdefault("base_dir", os.getcwd())
    phase_skeleton_map(cfg)
