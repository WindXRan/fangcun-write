"""
源书级分析：事件提取 + 故事骨架 + 改编策略生成。

产物存放在 _cache/，供 story-engine 和 drama-engine 共用。
"""

import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from file_io import (
    get_cache_dir, get_source_chapters, get_source_text,
    load_events, save_events, get_events_text,
    load_skeleton, save_skeleton,
    load_adaptation, save_adaptation,
)


# ─── 事件提取 ──────────────────────────────────────────────────────────────

def extract_events(config, api_key, api_url, model, prompt_text, workers=5):
    """批量提取事件（带滑窗上下文 + 增量保存）。"""
    from lib.api_client import call_api

    chapters = get_source_chapters(config)
    if not chapters:
        print("[FAIL] 没有找到章节文件")
        return []

    existing = {e["id"]: e for e in load_events(config) if e.get("event")}
    chapters_to_do = [(n, f) for n, f in chapters if n not in existing]

    if len(chapters_to_do) < len(chapters):
        print(f"  已有 {len(chapters) - len(chapters_to_do)} 章事件，跳过")

    if not chapters_to_do:
        print(f"  全部 {len(chapters)} 章事件已有")
        return list(existing.values())

    print(f"  事件提取 | {len(chapters_to_do)} 章待处理 | 并行: {workers} | 模型: {model}")

    t0 = time.time()
    done = 0
    total = len(chapters_to_do)
    results = dict(existing)
    fail_count = 0

    def extract_one(ch_num, ch_file):
        chapter_text = ch_file.read_text(encoding="utf-8")
        prev_context = ""
        prev_ids = sorted([k for k in existing.keys() if k < ch_num], reverse=True)[:2]
        if prev_ids:
            prev_events = [existing[pid]["event"] for pid in prev_ids if existing[pid].get("event")]
            if prev_events:
                prev_context = "前几章事件摘要（供参考）：\n" + "\n".join(prev_events) + "\n\n"

        user_prompt = (
            f"{prev_context}"
            f"请根据以下小说章节数：{ch_num}"
            f"小说章节名称：{ch_file.stem}"
            f"、小说章节内容生成事件摘要：\n"
            f"{chapter_text[:4000]}"
        )
        try:
            result = call_api(api_key, model, user_prompt, system_prompt=prompt_text,
                              api_url=api_url, temperature=0.3, max_tokens=2048)
            result = result.strip()
            return {"id": ch_num, "chapter_index": ch_num, "chapter": ch_file.stem, "event": result}, "ok"
        except Exception as e:
            return None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_one, n, f): n for n, f in chapters_to_do}
        for future in as_completed(futures):
            ch_num = futures[future]
            result, status = future.result()
            done += 1
            if result:
                results[ch_num] = result
                existing[ch_num] = result
                print(f"    [{done}/{total}] ✓ 第{ch_num}章")
            else:
                fail_count += 1
                results[ch_num] = {"id": ch_num, "chapter_index": ch_num, "chapter": "", "event": ""}
                print(f"    [{done}/{total}] ✗ 第{ch_num}章 ({status})")
            save_events(config, [results[k] for k in sorted(results.keys())])

    elapsed = time.time() - t0
    ok = sum(1 for v in results.values() if v.get("event"))
    print(f"  完成 | {ok}章成功 / {fail_count}章失败 | {elapsed:.0f}s")
    return [results[k] for k in sorted(results.keys())]


# ─── 故事骨架 ──────────────────────────────────────────────────────────────

def build_skeleton(config, api_key, api_url, model, system_prompt, novel_name=""):
    """生成故事骨架。"""
    from lib.api_client import call_api

    events_text = get_events_text(config)
    if "不存在" in events_text or "为空" in events_text:
        print("[FAIL] 事件表不存在，请先提取事件")
        return None

    total_ch = len(get_source_chapters(config))
    valid_events = [e for e in load_events(config) if e.get("event")]

    incremental_note = ""
    if len(valid_events) < total_ch:
        incremental_note = f"""

⚠️ 增量模式：当前只有 {len(valid_events)}/{total_ch} 章事件数据。
只为有事件支撑的章节规划，未覆盖部分标注"待补充"。"""

    user_prompt = f"""## 作品名称
{novel_name or config.get('source_book', '未命名')}

## 事件表（{len(valid_events)}章有效）
{events_text}
{incremental_note}

请根据事件表搭建故事骨架。"""

    print(f"  故事骨架 | {len(valid_events)} 章事件 | 模型: {model}")
    t0 = time.time()

    try:
        result = call_api(api_key, model, user_prompt, system_prompt=system_prompt,
                          api_url=api_url, temperature=0.7, max_tokens=8192)
    except Exception as e:
        print(f"[FAIL] API 调用失败: {e}")
        return None

    m = re.search(r"<storySkeleton[^>]*>([\s\S]*?)</storySkeleton>", result)
    content = m.group(1).strip() if m else result.strip()

    save_skeleton(config, content)
    elapsed = time.time() - t0
    print(f"  完成 | {len(content)}字 | {elapsed:.0f}s")
    return content


# ─── 改编策略 ──────────────────────────────────────────────────────────────

def build_adaptation(config, api_key, api_url, model, system_prompt, novel_name=""):
    """生成改编策略。"""
    from lib.api_client import call_api

    events_text = get_events_text(config)
    skeleton = load_skeleton(config)
    if not skeleton:
        print("[FAIL] 故事骨架不存在，请先生成骨架")
        return None

    user_prompt = f"""## 作品名称
{novel_name or config.get('source_book', '未命名')}

## 事件表
{events_text}

## 故事骨架
{skeleton}

请根据事件表和故事骨架，制定改编策略。"""

    print(f"  改编策略 | 模型: {model}")
    t0 = time.time()

    try:
        result = call_api(api_key, model, user_prompt, system_prompt=system_prompt,
                          api_url=api_url, temperature=0.7, max_tokens=6144)
    except Exception as e:
        print(f"[FAIL] API 调用失败: {e}")
        return None

    m = re.search(r"<adaptationStrategy[^>]*>([\s\S]*?)</adaptationStrategy>", result)
    content = m.group(1).strip() if m else result.strip()

    save_adaptation(config, content)
    elapsed = time.time() - t0
    print(f"  完成 | {len(content)}字 | {elapsed:.0f}s")
    return content
