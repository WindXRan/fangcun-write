"""Agent 模式写章：任务生成器，不调 API。

Agent 模式 ≠ Python 调 API 套皮。
真正的 agent 模式是 opencode agent（我）做编排，子 agent 做写章。

这个 phase 只做一件事：生成 _agent_tasks.json → 我读这个文件 → 派生子 agent → 完成。

流程：
    1. phase_write_agent 扫描待写章节，生成 _agent_tasks.json
    2. opencode agent 读取 _agent_tasks.json
    3. 每个章节派生子 agent（Task tool）
    4. 子 agent 自主：读概念 → 读 plot_guide → 读源文 → 写章 → 完成
    5. phase_postfix 做机械修正（通过 pipeline 后续阶段）
"""

import json
import os
from pathlib import Path

from prompt_loader import load_prompt
from utils import get_total_chapters, count_source_chars


def phase_write_agent(config, start, end, workers=5, state_mgr=None):
    """生成 agent 写章任务清单，不调用任何 API。"""
    base_dir = config.get("base_dir", os.getcwd())
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    rewrites_dir = config.get("rewrites_dir", "")

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章（Agent 模式, ch{start}-{end}, 生成任务清单）")
    print(f"{'=' * 50}")

    if state_mgr:
        state_mgr.phase_start("write")

    # 扫描待写章节
    chapters_dir = Path(rewrites_dir) / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    # 收集每个章节的变量
    total_ch = get_total_chapters(config)
    tasks = []

    for ch in range(start, end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if ch_file.exists() and ch_file.stat().st_size > 500:
            print(f"  [SKIP] ch{ch} 已存在")
            if state_mgr:
                state_mgr.chapter_completed(ch)
            continue

        n = str(ch)
        n_plus1 = str(ch + 1)
        src_chars = count_source_chars(config, ch)
        target = src_chars if src_chars > 0 else 1500

        replacements = {
            "新书名": config["book_name"],
            "N": n,
            "N03d": f"{ch:03d}",
            "N_plus1": n_plus1,
            "N03d_plus1": f"{ch+1:03d}",
            "作者名": config.get("author", ""),
            "源书名": config.get("source_book", ""),
            "总章数": str(total_ch),
            "源文字数": str(src_chars),
            "目标字数": str(target),
            "目标字数_min": str(int(target * 0.9)),
            "目标字数_max": str(int(target * 1.1)),
        }

        # 读角色变量
        book_data_path = Path(rewrites_dir) / "book_data.json"
        if book_data_path.exists():
            try:
                bd = json.loads(book_data_path.read_text(encoding="utf-8"))
                char_vars = bd.get("meta", {}).get("character_variables", {})
                replacements.update(char_vars)
            except Exception:
                pass

        # 加载 prompt（agent mode：不嵌入文件内容）
        try:
            prompt_text = load_prompt(
                f"{prompts_dir}/write-chapter.md",
                base_dir, replacements, mode="agent",
                rewrites_dir=rewrites_dir,
            )
        except FileNotFoundError as e:
            print(f"  [FAIL] ch{ch}: {e}")
            if state_mgr:
                state_mgr.chapter_failed(ch, error=str(e))
            continue

        # 提取文件引用列表，方便子 agent 知道要读哪些文件
        from prompt_loader import extract_file_refs, PASS_THROUGH_TAGS
        file_refs = extract_file_refs(prompt_text)
        read_files = [
            {"tag": tag, "path": path}
            for tag, path, _, _ in file_refs
            if tag not in PASS_THROUGH_TAGS
        ]

        task = {
            "chapter": ch,
            "output": str(ch_file),
            "target_chars": target,
            "target_min": int(target * 0.9),
            "target_max": int(target * 1.1),
            "replacements": replacements,
            "read_files": read_files,
            "prompt": prompt_text,
        }
        tasks.append(task)
        print(f"  [TASK] ch{ch}: 目标{target}字 → {ch_file}")

    if not tasks:
        print("  无需生成任务")
        if state_mgr:
            state_mgr.phase_done("write")
        return {}, {}

    # 写入任务清单
    manifest = {
        "project": config.get("book_name", ""),
        "author": config.get("author", ""),
        "source_book": config.get("source_book", ""),
        "base_dir": base_dir,
        "rewrites_dir": rewrites_dir,
        "prompts_dir": prompts_dir,
        "system_prompt": "prompts/system-agent.md",
        "tasks": tasks,
    }

    manifest_path = Path(rewrites_dir) / "_agent_tasks" / "write_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] 任务清单已生成: {manifest_path}")
    print(f"    共 {len(tasks)} 章待写")
    print(f"\n    使用 opencode agent 消费任务：")
    print(f"    读取 {manifest_path} 并按章节派生子 agent")

    if state_mgr:
        state_mgr.phase_done("write", extra={
            "manifest": str(manifest_path),
            "pending": len(tasks),
            "note": "任务已生成",
        })

    return {t["chapter"]: t["output"] for t in tasks}, {}
