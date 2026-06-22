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
    replacements = {
        "新书名": book_name if book_name != "auto" else "（待生成）",
        "源书名": source_book,
        "events_text": events_text[:15000],  # 限制长度
        "skeleton": (skeleton or "（未生成）")[:5000],
        "concept": concept[:5000],
    }

    # 调用 LLM
    print("  调用 LLM 分析骨架...")
    try:
        user_prompt = load_prompt(
            str(Path(config.get("prompts_dir", "")) / "skeleton-map.md"),
            str(base_dir),
            replacements,
            mode="api",
            rewrites_dir=str(rewrites_dir),
        )
        content = call_llm(config, "skeleton-map", user_prompt, "")

        # 提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)```', content)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # 尝试直接解析
            json_match = re.search(r'\{[\s\S]*"chapters"[\s\S]*\}', content)
            if json_match:
                json_str = json_match.group(0)
            else:
                print("  [FAIL] 无法从 LLM 输出中提取 JSON")
                if state_mgr:
                    state_mgr.phase_failed("skeleton-map", error="JSON 提取失败")
                return False

        skeleton_map = json.loads(json_str)

        # 验证结构
        if "chapters" not in skeleton_map:
            print("  [FAIL] JSON 缺少 chapters 字段")
            if state_mgr:
                state_mgr.phase_failed("skeleton-map", error="JSON 结构错误")
            return False

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
        print(f"  源文 {source_chapters} 章 → 新书 {new_chapters} 章")
        for a, count in sorted(actions.items()):
            print(f"    {a}: {count} 章")

        if state_mgr:
            state_mgr.phase_done("skeleton-map")
        return True

    except json.JSONDecodeError as e:
        print(f"  [FAIL] JSON 解析失败: {e}")
        if state_mgr:
            state_mgr.phase_failed("skeleton-map", error=f"JSON 解析失败: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] skeleton-map 失败: {e}")
        if state_mgr:
            state_mgr.phase_failed("skeleton-map", error=str(e))
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    cfg.setdefault("base_dir", os.getcwd())
    phase_skeleton_map(cfg)
