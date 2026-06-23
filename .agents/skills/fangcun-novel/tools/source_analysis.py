"""
源书级分析模块：事件提取 + 故事骨架 + 改编策略。

产物存放在 projects/{作者}/{源书名}/_cache/ 下，供 fangcun-novel 和 fangcun-drama 共用。
"""

import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_cache_dir(config):
    """获取源书 _cache 目录。优先从 config.source_dir 读取。"""
    # 优先从 config 读取 source_dir
    if config.get("source_dir"):
        source_dir = Path(config["source_dir"])
        if source_dir.exists():
            return source_dir
    
    # 兼容旧路径
    base_dir = Path(config.get("base_dir", "."))
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    return Path(base_dir) / "projects" / author / source_book / "_cache"


def get_chapters_dir(config):
    """获取章节目录。"""
    cache = get_cache_dir(config)
    chapters = cache / "chapters"
    if chapters.exists():
        return chapters
    # 兼容 fangcun-drama 的 source_dir
    if config.get("source_dir"):
        sd = Path(config["source_dir"])
        if sd.exists():
            return sd
    return chapters


# ─── 事件提取 ───────────────────────────────────────────────────────────

def load_events(config):
    """读取事件表。"""
    events_file = get_cache_dir(config) / "events.json"
    if not events_file.exists():
        return []
    return json.loads(events_file.read_text(encoding="utf-8"))


def save_events(config, events):
    """保存事件表。"""
    events_file = get_cache_dir(config) / "events.json"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def get_events_text(config, chapter_ids=None):
    """读取事件表，返回格式化文本。"""
    events = load_events(config)
    if chapter_ids:
        events = [e for e in events if e.get("id") in chapter_ids]
    valid = [e for e in events if e.get("event")]
    if not valid:
        return "事件表不存在或为空"
    lines = []
    for e in valid:
        lines.append(f"第{e.get('chapter_index', e.get('id', '?'))}章，标题:{e.get('chapter', '?')}，事件:{e.get('event', '?')}")
    return "\n".join(lines)


def get_novel_chapters(config):
    """获取章节文件列表。"""
    chapters_dir = get_chapters_dir(config)
    chapters = []
    for f in sorted(chapters_dir.glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m:
            chapters.append((int(m.group(1)), f))
    return chapters


def get_novel_text(config, chapter_index):
    """读取单章原文。"""
    chapters_dir = get_chapters_dir(config)
    for f in sorted(chapters_dir.glob("第*章*.txt")):
        m = re.search(r"(\d+)", f.name)
        if m and int(m.group(1)) == chapter_index:
            return f.read_text(encoding="utf-8")
    return ""


def extract_events(config, api_key, api_url, model, prompt_text, workers=5):
    """批量提取事件（带滑窗上下文 + 增量保存）。"""
    from lib.api_client import call_api

    chapters = get_novel_chapters(config)
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
                print(f"    [{done}/{total}] V 第{ch_num}章")
            else:
                fail_count += 1
                results[ch_num] = {"id": ch_num, "chapter_index": ch_num, "chapter": "", "event": ""}
                print(f"    [{done}/{total}] X 第{ch_num}章 ({status})")
            save_events(config, [results[k] for k in sorted(results.keys())])

    elapsed = time.time() - t0
    ok = sum(1 for v in results.values() if v.get("event"))
    print(f"  完成 | {ok}章成功 / {fail_count}章失败 | {elapsed:.0f}s")
    return [results[k] for k in sorted(results.keys())]


# ─── 故事骨架 ───────────────────────────────────────────────────────────

def load_skeleton(config):
    """读取故事骨架。"""
    f = get_cache_dir(config) / "story_skeleton.md"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def save_skeleton(config, content):
    """保存故事骨架。"""
    f = get_cache_dir(config) / "story_skeleton.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


def build_skeleton(config, api_key, api_url, model, system_prompt, novel_name=""):
    """生成故事骨架。"""
    from lib.api_client import call_api

    events_text = get_events_text(config)
    if "不存在" in events_text or "为空" in events_text:
        print("[FAIL] 事件表不存在，请先提取事件")
        return None

    total_ch = len(get_novel_chapters(config))
    valid_events = [e for e in load_events(config) if e.get("event")]

    incremental_note = ""
    if len(valid_events) < total_ch:
        incremental_note = f"""

[注意] 增量模式：当前只有 {len(valid_events)}/{total_ch} 章事件数据。
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

    # 提取 <storySkeleton> 标签内容
    m = re.search(r"<storySkeleton[^>]*>([\s\S]*?)</storySkeleton>", result)
    content = m.group(1).strip() if m else result.strip()

    save_skeleton(config, content)
    elapsed = time.time() - t0
    print(f"  完成 | {len(content)}字 | {elapsed:.0f}s")
    return content


# ─── 改编策略 ───────────────────────────────────────────────────────────

def load_adaptation(config):
    """读取改编策略。"""
    f = get_cache_dir(config) / "adaptation_strategy.md"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8")


def save_adaptation(config, content):
    """保存改编策略。"""
    f = get_cache_dir(config) / "adaptation_strategy.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")


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
