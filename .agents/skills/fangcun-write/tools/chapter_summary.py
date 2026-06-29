"""
章节摘要提取器 — 逐章并行提取核心事件/角色/情绪/冲突。
一次提取，总纲/卷纲/套路分析全部共用。
"""
import os, sys, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
# lib/api_client.py 在 .agents/tools/lib/
_SHARED = _HERE.parent.parent.parent / "tools"
if _SHARED.exists():
    sys.path.insert(0, str(_SHARED))

# 每章提取的字段
FIELDS = ["核心事件", "关键转折", "出场角色", "情绪基调", "冲突类型"]

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  章节摘要格式:
#  {
#    "ch": 1,
#    "核心事件": "主角林渊选择洪荒世界，全班震惊",
#    "出场角色": "林渊, 陆辰, 苏青",
#    "情绪基调": "压抑→震惊→期待",
#    "冲突类型": "身份冲突, 生存冲突"
#  }
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def _extract_xml_content(text: str) -> str:
    """从XML中提取<content>文本。"""
    import re
    m = re.search(r'<content>(.*?)</content>', text, re.DOTALL)
    return m.group(1) if m else text


def get_chapter_text(chapter_file: str) -> str:
    """安全读一章，支持 txt 和 xml，截断到6000字。"""
    text = Path(chapter_file).read_text(encoding="utf-8", errors="replace")
    if chapter_file.endswith('.xml'):
        text = _extract_xml_content(text)
    return text[:6000]


def extract_one(ch_num: int, chapter_text: str, api_key: str,
                api_url: str, model: str) -> dict:
    """单章摘要提取。"""
    from lib.api_client import call_api

    sys_prompt = """你是有经验的网文编辑。读一章正文，提取5个字段：
- 核心事件：用2-3句话概括本章最重要的剧情推进。写清楚谁做了什么、结果如何。
- 关键转折：本章从开头到结尾发生了什么转变（情绪/局势/认知/关系）
- 出场角色：本章实际出场的主要角色名，逗号分隔
- 情绪基调：读者读完本章的情绪变化，如"压抑→爽→期待"
- 冲突类型：本章核心冲突类型，如"身份冲突/生存冲突/信息差冲突/打脸"

只输出这5个字段，每行一个。不要多余内容。"""

    user_prompt = f"第{ch_num}章正文（6000字内）：\n\n{chapter_text}"

    try:
        resp = call_api(api_key, model, user_prompt, system_prompt=sys_prompt,
                        api_url=api_url, temperature=0.1, max_tokens=500)
    except Exception as e:
        return {"ch": ch_num, "error": str(e)}

    # 解析输出
    result = {"ch": ch_num}
    lines = resp.strip().split("\n")
    for line in lines:
        for field in FIELDS:
            if line.startswith(field + "：") or line.startswith(field + ":"):
                result[field] = line[len(field)+1:].strip()
                break
    return result


def extract_all(project_dir: str, chapter_range: list[int] = None,
                workers: int = 20, force: bool = False) -> list[dict]:
    """提取全书摘要，增量保存。"""
    chap_dir = Path(project_dir) / "正文" / "正文"
    out_file = Path(project_dir) / "作品信息" / "章节摘要.json"

    # 已提取的
    existing = {}
    if out_file.exists() and not force:
        try:
            for item in json.loads(out_file.read_text(encoding="utf-8")):
                if "核心事件" in item:
                    existing[item["ch"]] = item
        except: pass

    # 找章节文件
    all_chs = sorted(chap_dir.glob("第*.txt")) + sorted(chap_dir.glob("第*.xml"))
    if not all_chs:
        print("  W 无章节文件")
        return []

    # 确定要处理的章节
    todo = []
    for f in all_chs:
        # 解析章节号
        stem = f.stem
        for prefix in ["第"]:
            if stem.startswith(prefix):
                try:
                    num_str = stem[len(prefix):].split("章")[0]
                    ch_num = int(num_str)
                    break
                except: continue
        else:
            continue
        if chapter_range and ch_num not in chapter_range:
            continue
        if ch_num in existing and not force:
            continue
        todo.append((ch_num, str(f)))

    if not todo:
        print(f"  全部 {len(existing)} 章已有摘要，跳过")
        return list(existing.values())

    # API 配置
    api_key = os.environ.get("API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        print("  W 未设置 API_KEY")
        return []

    _base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not _base.endswith("/v1"):
        _base += "/v1"
    api_url = _base + "/chat/completions"
    model = os.environ.get("FANGCUN_MODEL", "deepseek-chat")

    # 并行提取
    print(f"  摘要提取 | {len(todo)} 章待处理 | 并行 {workers} | 模型 {model}")
    results = dict(existing)
    t0 = time.time()
    done = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        fut_map = {}
        for ch_num, fpath in todo:
            text = get_chapter_text(fpath)
            fut = pool.submit(extract_one, ch_num, text, api_key, api_url, model)
            fut_map[fut] = ch_num

        for fut in as_completed(fut_map):
            ch_num = fut_map[fut]
            try:
                r = fut.result()
                if "error" in r:
                    fail += 1
                    print(f"    X 第{ch_num}章: {r['error'][:50]}")
                else:
                    results[ch_num] = r
                    done += 1
                    if done % 20 == 0:
                        print(f"    {done}/{len(todo)}")
            except Exception as e:
                fail += 1
                print(f"    X 第{ch_num}章: {e}")

        # 增量保存
        ordered = [results[k] for k in sorted(results.keys())]
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t0
    print(f"  完成 | {done} 章成功 / {fail} 章失败 | {elapsed:.0f}s")
    return ordered


def format_summaries(data: list[dict]) -> str:
    """格式化摘要列表为LLM易读文本。"""
    lines = []
    for item in data:
        ch = item.get("ch", "?")
        event = item.get("核心事件", "")
        turn = item.get("关键转折", "")
        chars = item.get("出场角色", "")
        emotion = item.get("情绪基调", "")
        conflict = item.get("冲突类型", "")
        parts = [f"第{ch}章"]
        if event: parts.append(f"事件: {event}")
        if turn: parts.append(f"转折: {turn}")
        if chars: parts.append(f"角色: {chars}")
        if emotion: parts.append(f"情绪: {emotion}")
        if conflict: parts.append(f"冲突: {conflict}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
