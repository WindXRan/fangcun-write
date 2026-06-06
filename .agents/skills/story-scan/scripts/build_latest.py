"""
构建 latest_ranks.json：
1. 加载最近两天的 JSON 快照
2. 按分类对比趋势（新上榜/掉榜/排名变化/阅读量变化）
3. 可选调用 OpenAI 兼容 API 生成 AI 总结
4. 输出 latest_ranks.json + trends/YYYY-MM-DD.json
"""
import os
import re
import json
import glob
import sys
import time
import argparse
from urllib.parse import quote
from pathlib import Path

# 加载 .env 文件（项目根目录）
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过，依赖系统环境变量

# Windows 终端 UTF-8 支持
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime


def parse_reads(reads_str: str) -> float:
    """将 '15.2万' 这样的字符串转为数值，用于比较。"""
    if not reads_str or reads_str == "未知":
        return 0
    s = reads_str.strip().replace(",", "")
    try:
        if "万" in s:
            return float(s.replace("万", "")) * 10000
        return float(s)
    except ValueError:
        return 0


def format_reads_change(diff: float) -> str:
    """格式化阅读量变化。"""
    if abs(diff) >= 10000:
        return f"{'+' if diff > 0 else ''}{diff / 10000:.1f}万"
    return f"{'+' if diff > 0 else ''}{int(diff)}"


def format_reads(value):
    """格式化阅读量数值。"""
    if value >= 10000:
        return f"{value / 10000:.1f}万"
    return str(int(value))


def load_snapshot(path: str) -> dict | None:
    """加载一个 JSON 快照文件。失败返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  快照文件损坏或无法读取 {path}: {e}")
        return None
    if not isinstance(data, dict) or "categories" not in data:
        print(f"⚠️  快照文件结构异常 {path}: 缺少 categories 字段")
        return None
    return data


def compare_categories(today_cats: list, prev_cats: list) -> dict:
    """
    对比两天的分类数据，返回每个分类的趋势信息。
    key = 分类名, value = trend dict
    """
    # 构建 prev 的索引: cat_name -> {url: (rank, reads_str, title)}
    prev_index = {}
    for cat in prev_cats:
        url_map = {}
        for i, book in enumerate(cat.get("books", [])):
            url_map[book["url"]] = {
                "rank": i + 1,
                "reads": book.get("reads", "未知"),
                "title": book.get("title", "未知"),
                "intro": book.get("intro", "暂无简介"),
            }
        prev_index[cat["name"]] = url_map

    trends = {}
    for cat in today_cats:
        cat_name = cat["name"]
        prev_urls = prev_index.get(cat_name, {})
        today_books = cat.get("books", [])

        new_books = []
        dropped_books = []
        risers = []
        fallers = []
        reads_growth = []

        today_urls = set()
        for i, book in enumerate(today_books):
            url = book["url"]
            today_urls.add(url)
            today_rank = i + 1
            title = book.get("title", "未知")

            if url in prev_urls:
                prev_info = prev_urls[url]
                prev_rank = prev_info["rank"]
                rank_change = prev_rank - today_rank  # 正数=上升

                if rank_change > 0:
                    risers.append({"title": title, "change": f"+{rank_change}"})
                elif rank_change < 0:
                    fallers.append({"title": title, "change": str(rank_change)})

                # 阅读量变化
                today_reads = parse_reads(book.get("reads", ""))
                prev_reads = parse_reads(prev_info["reads"])
                if today_reads > 0 and prev_reads > 0:
                    diff = today_reads - prev_reads
                    if diff != 0:
                        reads_growth.append(
                            {"title": title, "growth": format_reads_change(diff)}
                        )
            else:
                new_books.append(title)

        # 掉出榜单的书（含简介以便 AI 分析题材）
        for url, info in prev_urls.items():
            if url not in today_urls:
                dropped_books.append({
                    "title": info["title"],
                    "intro": info.get("intro", "暂无简介")[:100],
                })

        # 排序：涨幅最大的在前
        risers.sort(key=lambda x: int(x["change"].replace("+", "")), reverse=True)
        fallers.sort(key=lambda x: int(x["change"]))
        reads_growth.sort(
            key=lambda x: parse_reads(x["growth"].replace("+", "")), reverse=True
        )

        trends[cat_name] = {
            "new_count": len(new_books),
            "dropped_count": len(dropped_books),
            "new_books": new_books[:5],
            "dropped_books": dropped_books[:5],
            "top_risers": risers[:3],
            "top_fallers": fallers[:3],
            "reads_growth": reads_growth[:3],
            "summary": "",  # AI 总结，由 generate_ai_summaries 填充
        }

    return trends


def generate_trend_summary_text(cat_name: str, trend: dict) -> str:
    """生成基于规则的简短趋势文本（作为 AI 总结不可用时的 fallback）。"""
    parts = []
    if trend["new_count"] > 0:
        parts.append(f"新增{trend['new_count']}本上榜")
    if trend["dropped_count"] > 0:
        dropped_titles = [d["title"] if isinstance(d, dict) else d
                          for d in trend.get("dropped_books", [])]
        if dropped_titles:
            parts.append(f"{trend['dropped_count']}本掉出（{'、'.join('《' + t + '》' for t in dropped_titles)}）")
        else:
            parts.append(f"{trend['dropped_count']}本掉出")
    if trend["top_risers"]:
        r = trend["top_risers"][0]
        parts.append(f"《{r['title']}》排名上升{r['change']}位")
    if trend["reads_growth"]:
        g = trend["reads_growth"][0]
        parts.append(f"《{g['title']}》阅读量{g['growth']}")
    if not parts:
        parts.append("榜单无明显变动")
    return "；".join(parts) + "。"


def build_ai_prompt(cat_name: str, cat: dict, trend: dict) -> str:
    """构建 AI 总结的 prompt（统一模板）。"""
    # 当前榜单书籍
    intros = []
    for i, book in enumerate(cat.get("books", [])[:20]):
        intros.append(
            f"{i+1}. 《{book['title']}》- {book.get('author', '未知')}\n"
            f"   在读：{book.get('reads', '未知')}\n"
            f"   简介：{book.get('intro', '无')[:200]}"
        )
    intros_text = "\n".join(intros)

    # 新上榜书籍
    new_books = trend.get("new_books", [])
    new_text = "、".join(f"《{t}》" for t in new_books) if new_books else "无"

    # 掉出榜单书籍（含简介）
    dropped = trend.get("dropped_books", [])
    if dropped:
        dropped_lines = []
        for d in dropped:
            if isinstance(d, dict):
                dropped_lines.append(f"《{d['title']}》（{d.get('intro', '暂无简介')[:50]}）")
            else:
                dropped_lines.append(f"《{d}》")
        dropped_text = "、".join(dropped_lines)
    else:
        dropped_text = "无"

    # 排名变动
    risers = trend.get("top_risers", [])
    risers_text = "、".join(f"《{r['title']}》{r['change']}" for r in risers) if risers else "无"
    fallers = trend.get("top_fallers", [])
    fallers_text = "、".join(f"《{f['title']}》{f['change']}" for f in fallers) if fallers else "无"

    return f"""你是一位网文行业分析师。请根据以下数据，为番茄小说「{cat_name}」分类新书榜生成结构化分析。

## 当前榜单 Top 20
{intros_text}

## 榜单变动
- 新上榜：{new_text}
- 掉出榜单：{dropped_text}
- 排名上升：{risers_text}
- 排名下降：{fallers_text}

## 输出要求（请严格按以下格式输出，使用 Markdown）

**🔥 题材趋势**
用1-2句话总结当前分类的主流题材和高频元素（如穿书/重生/系统/种田等），点明哪些设定扎堆出现。

**📖 读者偏好**
用1句话概括读者口味方向（甜宠/虐/爽/日常/暗黑等），以及金手指类型偏好。

**🆕 新上榜作品**
列出新上榜书名，每本用一句话点评其题材亮点或差异化卖点。

**📉 掉出榜单**
列出掉出书名及其题材方向，简要分析可能掉出的原因（如题材饱和、同质化等）。

**💡 值得关注**
挑1-2本有差异化潜力的作品，说明理由。

要求：每个板块2-3句话，总字数250字以内。语言简洁专业，像行业快报。"""


BATCH_SIZE = 3  # 每批合并的分类数

MARKET_PERIODS = [("7", 7), ("14", 14), ("30", 30), ("all", None)]

MARKET_KEYWORDS = [
    # 通用
    "重生", "穿越", "系统", "空间", "异能", "末世", "废土", "天灾", "囤货",
    "修仙", "玄学", "无限流", "悬疑", "直播", "综艺", "娱乐圈", "基建",
    # 女频
    "穿书", "快穿", "团宠", "萌宝", "幼崽", "女配", "炮灰",
    "反派", "权臣", "宅斗", "宫斗", "和离", "替嫁", "逃荒", "种田", "美食", "经商",
    "年代", "七零", "八零", "军婚", "豪门", "总裁", "真假千金", "先婚后爱", "追妻",
    "甜宠", "双洁", "强制爱", "无CP", "国运",
    "校园", "暗恋", "青梅竹马", "民国", "兽世", "远古",
    # 男频
    "赘婿", "逆袭", "战神", "龙王", "神医", "兵王", "都市", "高武", "修真",
    "玄幻", "仙侠", "剑道", "丹药", "炼器", "阵法", "升级", "打怪", "副本",
    "历史", "三国", "明朝", "架空", "争霸", "谋略", "谍战", "抗战",
    "科幻", "星际", "机甲", "赛博朋克", "游戏", "电竞", "体育",
    "动漫", "衍生", "同人",
]


def build_batch_ai_prompt(batch: list) -> str:
    """构建批量 AI 总结的 prompt。

    batch: list of (cat_name, cat_data, trend_data) tuples
    """
    sections = []
    for cat_name, cat, trend in batch:
        intros = []
        for i, book in enumerate(cat.get("books", [])[:20]):
            intros.append(
                f"{i+1}. 《{book['title']}》- {book.get('author', '未知')}\n"
                f"   在读：{book.get('reads', '未知')}\n"
                f"   简介：{book.get('intro', '无')[:200]}"
            )
        intros_text = "\n".join(intros)

        new_books = trend.get("new_books", [])
        new_text = "、".join(f"《{t}》" for t in new_books) if new_books else "无"

        dropped = trend.get("dropped_books", [])
        if dropped:
            dropped_lines = []
            for d in dropped:
                if isinstance(d, dict):
                    dropped_lines.append(
                        f"《{d['title']}》（{d.get('intro', '暂无简介')[:50]}）"
                    )
                else:
                    dropped_lines.append(f"《{d}》")
            dropped_text = "、".join(dropped_lines)
        else:
            dropped_text = "无"

        risers = trend.get("top_risers", [])
        risers_text = (
            "、".join(f"《{r['title']}》{r['change']}" for r in risers)
            if risers else "无"
        )
        fallers = trend.get("top_fallers", [])
        fallers_text = (
            "、".join(f"《{f['title']}》{f['change']}" for f in fallers)
            if fallers else "无"
        )

        sections.append(
            f"### 分类：{cat_name}\n\n"
            f"**当前榜单 Top 20：**\n{intros_text}\n\n"
            f"**榜单变动：**\n"
            f"- 新上榜：{new_text}\n"
            f"- 掉出榜单：{dropped_text}\n"
            f"- 排名上升：{risers_text}\n"
            f"- 排名下降：{fallers_text}"
        )

    all_sections = "\n\n---\n\n".join(sections)
    cat_names = [b[0] for b in batch]

    output_examples = "\n\n".join(
        f"===BEGIN: {name}===\n"
        f"**🔥 题材趋势** ...\n"
        f"**📖 读者偏好** ...\n"
        f"**🆕 新上榜作品** ...\n"
        f"**📉 掉出榜单** ...\n"
        f"**💡 值得关注** ...\n"
        f"===END: {name}==="
        for name in cat_names
    )

    return (
        f"你是一位网文行业分析师。请根据以下数据，"
        f"为番茄小说的多个分类新书榜分别生成结构化分析。\n\n"
        f"{all_sections}\n\n"
        f"## 输出要求\n\n"
        f"请严格按照以下格式，为每个分类分别输出分析。"
        f"每个分类的分析必须包裹在对应的标记中：\n\n"
        f"{output_examples}\n\n"
        f"每个板块2-3句话，每个分类总字数250字以内。"
        f"语言简洁专业，像行业快报。\n"
        f"注意：必须为每个分类都输出完整分析，不可省略任何分类。"
    )


def parse_batch_response(response_text: str, cat_names: list) -> dict:
    """解析批量 AI 响应，返回 {cat_name: summary} 字典。"""
    results = {}
    for name in cat_names:
        pattern = rf"===BEGIN:\s*{re.escape(name)}\s*===(.*?)===END:\s*{re.escape(name)}\s*==="
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            summary = match.group(1).strip()
            if summary:
                results[name] = summary
    return results


def _save_trends_incremental(trend_path: str, date: str,
                             prev_date: str, trends: dict):
    """增量保存趋势数据到文件（每批成功后立即写入）。"""
    if not trend_path:
        return
    trend_output = {
        "date": date,
        "prev_date": prev_date,
        "trends": trends,
    }
    try:
        write_json(trend_path, trend_output)
    except Exception as e:
        print(f"⚠️  趋势文件写入失败: {e}")


def api_type_filename(type_name: str) -> str:
    """将类型名转成适合作为静态 JSON 文件名的名称。"""
    name = (type_name or "").strip()
    name = re.sub(r"[\\/]+", "_", name)
    name = re.sub(r"[^\w\u4e00-\u9fff\s-]", "_", name)
    name = re.sub(r"\s+", "_", name).strip("._")
    return name or "unknown"


def write_json(path: str, payload: dict):
    """统一写 JSON，确保中文可读。使用原子写入避免中断产生损坏文件。"""
    import tempfile
    # 写入临时文件
    tmp = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=os.path.dirname(path),
        suffix='.tmp', delete=False
    )
    try:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        # 原子替换目标文件
        os.replace(tmp.name, path)
    except Exception:
        # 清理临时文件
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def build_latest_api(output: dict, base_dir: str, rank_prefix: str = ""):
    """生成静态 latest 数据接口。

    GitHub Pages 不支持动态 query API，因此这里将 type 参数映射为静态文件：
    - api/latest/<rank_prefix>_all.json：全量数据
    - api/latest/<rank_prefix>_<type>.json：单个类型数据
    - api/latest/<rank_prefix>_index.json：类型索引
    """
    api_root = os.path.join(base_dir, "api")
    latest_dir = os.path.join(api_root, "latest")
    os.makedirs(latest_dir, exist_ok=True)

    # 记录旧文件，写完新文件后再删除（避免崩溃导致目录清空）
    prefix_pattern = f"{rank_prefix}_" if rank_prefix else ""
    old_files = set(glob.glob(os.path.join(latest_dir, f"{prefix_pattern}*.json")))

    date = output.get("date", "")
    prev_date = output.get("prev_date", "")
    rank_type = output.get("rank_type", "")
    categories = output.get("categories", [])

    all_payload = {
        "type": "all",
        "rank_type": rank_type,
        "date": date,
        "prev_date": prev_date,
        "categories": categories,
    }
    all_filename = f"{rank_prefix}_all.json" if rank_prefix else "all.json"
    write_json(os.path.join(latest_dir, all_filename), all_payload)

    types = [{
        "type": "all",
        "rank_type": rank_type,
        "url": f"api/latest/{all_filename}",
        "category_count": len(categories),
        "book_count": sum(len(cat.get("books", [])) for cat in categories),
    }]

    used_filenames = {"all"}
    for cat in categories:
        type_name = cat.get("name", "")
        filename = api_type_filename(type_name)
        base_filename = filename
        suffix = 2
        while filename in used_filenames:
            filename = f"{base_filename}_{suffix}"
            suffix += 1
        used_filenames.add(filename)

        # 添加排行榜类型前缀
        prefixed_filename = f"{rank_prefix}_{filename}" if rank_prefix else filename

        payload = {
            "type": type_name,
            "rank_type": rank_type,
            "date": date,
            "prev_date": prev_date,
            "category": cat,
            "categories": [cat],
        }
        write_json(os.path.join(latest_dir, f"{prefixed_filename}.json"), payload)

        url = f"api/latest/{quote(prefixed_filename)}.json"
        types.append({
            "type": type_name,
            "rank_type": rank_type,
            "url": url,
            "book_count": len(cat.get("books", [])),
        })

    index_filename = f"{rank_prefix}_index.json" if rank_prefix else "index.json"
    index_payload = {
        "date": date,
        "prev_date": prev_date,
        "rank_type": rank_type,
        "types": types,
    }
    write_json(os.path.join(latest_dir, index_filename), index_payload)

    # 更新主索引文件，包含所有排行榜类型
    main_index_path = os.path.join(api_root, "latest.json")
    if os.path.exists(main_index_path):
        try:
            with open(main_index_path, "r", encoding="utf-8") as f:
                main_index = json.load(f)
        except (json.JSONDecodeError, IOError):
            main_index = {"rank_types": []}
    else:
        main_index = {"rank_types": []}

    # 更新或添加当前排行榜类型的索引
    rank_types = main_index.get("rank_types", [])
    rank_type_entry = {
        "rank_type": rank_type,
        "prefix": rank_prefix,
        "date": date,
        "prev_date": prev_date,
        "types": types,
    }

    # 查找并更新已有的排行榜类型
    updated = False
    for i, rt in enumerate(rank_types):
        if rt.get("prefix") == rank_prefix:
            rank_types[i] = rank_type_entry
            updated = True
            break

    if not updated:
        rank_types.append(rank_type_entry)

    main_index["rank_types"] = rank_types
    write_json(main_index_path, main_index)

    # 清理不再需要的旧文件（新文件已全部写入成功）
    new_files = set(glob.glob(os.path.join(latest_dir, f"{prefix_pattern}*.json")))
    for stale_path in old_files - new_files:
        try:
            os.remove(stale_path)
        except OSError:
            pass

    return latest_dir


def parse_change(change: str) -> int:
    """解析 '+3' / '-2' 这类排名变化。"""
    try:
        return int(str(change or "0").replace("+", ""))
    except ValueError:
        return 0


def load_trend_rows(trends_dir: str) -> list:
    """加载全部趋势归档，按日期升序排列。"""
    rows = []
    for path in sorted(glob.glob(os.path.join(trends_dir, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  趋势文件读取失败: {path} ({e})")
            continue
        if not isinstance(data, dict) or "date" not in data:
            continue
        rows.append({
            "date": data.get("date", ""),
            "prev_date": data.get("prev_date", ""),
            "trends": data.get("trends", {}),
        })
    return sorted([r for r in rows if r["date"]], key=lambda x: x["date"])


def summarize_market_rows(rows: list) -> dict:
    """汇总某个分类在一组趋势行中的动能指标。"""
    totals = {
        "new_count": 0,
        "dropped_count": 0,
        "riser_count": 0,
        "faller_count": 0,
        "read_count": 0,
        "active_days": 0,
    }
    for row in rows:
        trend = row.get("trend") or {}
        riser_count = len(trend.get("top_risers", []))
        faller_count = len(trend.get("top_fallers", []))
        read_count = len(trend.get("reads_growth", []))
        totals["new_count"] += int(trend.get("new_count", 0) or 0)
        totals["dropped_count"] += int(trend.get("dropped_count", 0) or 0)
        totals["riser_count"] += riser_count
        totals["faller_count"] += faller_count
        totals["read_count"] += read_count
        if (
            trend.get("new_count", 0) or trend.get("dropped_count", 0)
            or riser_count or faller_count or read_count
        ):
            totals["active_days"] += 1
    return totals


def market_score(totals: dict) -> int:
    """计算全站热点动能分。"""
    return round(
        totals["new_count"] * 4 +
        totals["dropped_count"] * 2 +
        totals["riser_count"] * 2 +
        totals["faller_count"] * -1 +
        totals["read_count"] * 3 +
        totals["active_days"] * 1.5
    )


def collect_market_hot_types(categories: list, rows_window: list) -> list:
    """统计具体分类热度。"""
    result = []
    for name in categories:
        rows = [
            {"trend": row.get("trends", {}).get(name)}
            for row in rows_window
            if row.get("trends", {}).get(name)
        ]
        totals = summarize_market_rows(rows)
        score = market_score(totals)
        if score <= 0:
            continue
        result.append({
            "name": name,
            "score": score,
            "new_count": totals["new_count"],
            "dropped_count": totals["dropped_count"],
            "read_count": totals["read_count"],
            "active_days": totals["active_days"],
        })
    return sorted(result, key=lambda x: x["score"], reverse=True)


def collect_market_hot_genres(hot_types: list) -> list:
    """返回热门分类列表（直接使用原始分类，不再聚合）。"""
    return [
        {**item, "lead_category": item["name"]}
        for item in hot_types
        if item.get("score", 0) > 0
    ]


def add_theme_hits(score_map: dict, text: str, category_name: str, weight: int):
    """给命中的题材关键词加权。"""
    source = str(text or "")
    if not source:
        return
    for keyword in MARKET_KEYWORDS:
        if keyword not in source:
            continue
        item = score_map[keyword]
        item["count"] += weight
        item["categories"].add(category_name)


def collect_market_hot_themes(output: dict, rows_window: list,
                              categories: list) -> list:
    """统计最新榜单和近期趋势中的高频题材词。"""
    score_map = {
        name: {"name": name, "count": 0, "categories": set()}
        for name in MARKET_KEYWORDS
    }

    for cat in output.get("categories", []):
        cat_name = cat.get("name", "")
        for index, book in enumerate(cat.get("books", [])):
            weight = 2 if index < 10 else 1
            add_theme_hits(
                score_map,
                f"{book.get('title', '')} {book.get('intro', '')}",
                cat_name,
                weight
            )

    for row in rows_window:
        for cat_name in categories:
            trend = row.get("trends", {}).get(cat_name)
            if not trend:
                continue
            add_theme_hits(
                score_map,
                " ".join(trend.get("new_books", [])),
                cat_name,
                3
            )
            add_theme_hits(score_map, trend.get("summary", ""), cat_name, 1)

    themes = []
    for item in score_map.values():
        if item["count"] <= 0:
            continue
        themes.append({
            "name": item["name"],
            "count": item["count"],
            "category_count": len(item["categories"]),
        })
    return sorted(
        themes,
        key=lambda x: (x["count"], x["category_count"]),
        reverse=True
    )


def build_rule_market_summary(period_label: str, hot_genres: list,
                              hot_types: list, hot_themes: list) -> str:
    """基于统计结果生成全站热点兜底文案。"""
    top_genres = "、".join(item["name"] for item in hot_genres[:2])
    top_types = "、".join(item["name"] for item in hot_types[:3])
    top_themes = "、".join(item["name"] for item in hot_themes[:6])
    if not top_genres and not top_types and not top_themes:
        return f"{period_label}暂无足够数据判断全站热点。"
    if not top_genres and not top_types:
        return f"{period_label}，高频题材关键词：{top_themes}。数据量较少，建议持续积累后分析。"
    return (
        f"{period_label}里，{top_genres or top_types} 是更热的分类，"
        f"具体分类以 {top_types} 的榜单动能更强；题材上 {top_themes} "
        f"反复出现，说明读者仍偏好强设定、强情绪钩子和明确爽点。"
    )


def build_market_summary_payload(output: dict, trends_dir: str) -> dict:
    """生成全站热点统计和规则兜底总结。"""
    categories = [cat.get("name", "") for cat in output.get("categories", [])]
    trend_rows = load_trend_rows(trends_dir)
    periods = {}

    for key, days in MARKET_PERIODS:
        rows_window = trend_rows if days is None else trend_rows[-days:]
        period_label = "全部样本" if days is None else f"近 {days} 日"
        hot_types = collect_market_hot_types(categories, rows_window)
        hot_genres = collect_market_hot_genres(hot_types)
        hot_themes = collect_market_hot_themes(output, rows_window, categories)
        fallback_summary = build_rule_market_summary(
            period_label, hot_genres, hot_types, hot_themes
        )
        periods[key] = {
            "period": period_label,
            "source": "rule",
            "summary": fallback_summary,
            "fallback_summary": fallback_summary,
            "hot_genres": hot_genres[:5],
            "hot_types": hot_types[:6],
            "hot_themes": hot_themes[:14],
        }

    return {
        "date": output.get("date", ""),
        "prev_date": output.get("prev_date", ""),
        "periods": periods,
    }


def build_market_ai_prompt(payload: dict, rank_name: str = "番茄小说") -> str:
    """构建全站热点 AI 总结 prompt。"""
    sections = []
    for key, data in payload.get("periods", {}).items():
        genres = "、".join(
            f"{item['name']}({item['score']})"
            for item in data.get("hot_genres", [])[:5]
        )
        types = "、".join(
            f"{item['name']}({item['score']})"
            for item in data.get("hot_types", [])[:6]
        )
        themes = "、".join(
            f"{item['name']}({item['count']})"
            for item in data.get("hot_themes", [])[:10]
        )
        sections.append(
            f"周期 {key} / {data['period']}:\n"
            f"- 热门分类: {genres or '无'}\n"
            f"- 具体分类: {types or '无'}\n"
            f"- 高频题材: {themes or '无'}\n"
            f"- 规则兜底: {data['fallback_summary']}"
        )

    return f"""你是一位网文市场编辑，请根据番茄「{rank_name}」的统计结果，为每个周期生成一段全站热点判断。

{chr(10).join(sections)}

要求：
1. 只基于给定统计，不要编造未出现的类型或题材。
2. 每个周期输出 1 段中文，80-140 字。
3. 点明热门分类、具体分类、题材关键词，以及一句编辑判断。
4. 输出严格 JSON，不要 Markdown，不要解释，格式如下：
{{
  "7": "总结文本",
  "14": "总结文本",
  "30": "总结文本",
  "all": "总结文本"
}}"""


def parse_json_object(text: str):
    """尽量从模型响应中提取 JSON 对象或数组。"""
    text = (text or "").strip()
    # 剥离 Markdown 代码块包装（```json ... ``` 或 ``` ... ```）
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 JSON 对象 {...}
    start = text.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    # 尝试提取 JSON 数组 [...]
    start = text.find('[')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")


def enrich_market_summary_with_ai(payload: dict, api_key: str,
                                  base_url: str, model: str,
                                  rank_name: str = "番茄小说") -> dict:
    """使用 AI 改写全站热点总结；失败时保留规则兜底。"""
    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️  openai 库未安装，跳过全站热点 AI 总结。")
        return payload

    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
        prompt = build_market_ai_prompt(payload, rank_name)
        content = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=900,
                    temperature=0.5,
                )
                content = response.choices[0].message.content
                break
            except Exception as retry_e:
                if attempt < 2:
                    print(f"  ⚠️  全站热点 AI 调用失败（第{attempt+1}次），重试中... ({retry_e})")
                    time.sleep(2 ** attempt)
                else:
                    raise retry_e
        if content:
            parsed = parse_json_object(content)
            for key, summary in parsed.items():
                if key in payload["periods"] and isinstance(summary, str) and summary.strip():
                    payload["periods"][key]["summary"] = summary.strip()
                    payload["periods"][key]["source"] = "ai"
            print("✅ 全站热点 AI 总结已生成")
    except Exception as e:
        print(f"⚠️  全站热点 AI 总结失败，使用规则兜底: {e}")

    return payload



def is_rule_summary(summary: str) -> bool:
    """判断一个总结是否为规则模板生成的（非 AI）。
    规则摘要特征：短小、分号分隔、以句号结尾、无换行。
    AI 摘要通常更长、有换行或加粗标记。
    """
    if not summary:
        return True
    if summary == "首日数据，暂无趋势对比。":
        return True
    # AI 摘要的典型特征：有换行、有加粗、有结构化标题
    if "\n" in summary or "**" in summary:
        return False
    # AI 摘要通常较长，且有结构化标记（如 "🔥" 等 emoji 标题）
    if len(summary) >= 200 or "🔥" in summary or "📖" in summary or "💡" in summary:
        return False
    # 规则摘要特征：短文本、分号分隔、以句号结尾、无换行
    # 注意：规则摘要也会包含书名号《》，不能用书名号作为判断依据
    if len(summary) < 150 and "；" in summary:
        return True
    # 默认视为 AI 摘要（宁可跳过也不重复生成）
    return False


def generate_ai_summaries(categories: list, trends: dict,
                          api_key: str, base_url: str,
                          model: str, force: bool = False,
                          existing_trends: dict = None,
                          trend_path: str = None,
                          trend_date: str = "",
                          prev_date: str = "") -> dict:
    """通过 OpenAI 兼容 API 为每个分类生成 AI 总结。

    采用批量合并策略（每 BATCH_SIZE 个分类一次调用）减少 API 调用次数，
    并在每批成功后增量保存，避免中途失败丢失已完成的结果。
    批量失败的分类会自动降级为逐个重试。
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️  openai 库未安装，跳过 AI 总结。pip install openai")
        return trends

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
    existing_trends = existing_trends or {}

    # 1. 筛选需要生成总结的分类
    pending = []  # (cat_name, cat_data, trend_data)
    skipped = 0

    for cat in categories:
        cat_name = cat["name"]
        if cat_name not in trends:
            continue

        if not force:
            existing_summary = existing_trends.get(cat_name, {}).get("summary", "")
            if existing_summary and not is_rule_summary(existing_summary):
                trends[cat_name]["summary"] = existing_summary
                skipped += 1
                continue

        pending.append((cat_name, cat, trends[cat_name]))

    if skipped > 0:
        print(f"  ⏭️  跳过 {skipped} 个已有 AI 总结的分类")

    if not pending:
        print("  ✅ 所有分类已有 AI 总结，无需生成")
        return trends

    # 2. 分批处理
    batches = [
        pending[i:i + BATCH_SIZE]
        for i in range(0, len(pending), BATCH_SIZE)
    ]
    failed_cats = []  # 批量失败后需单独重试的分类

    print(f"  📦 共 {len(pending)} 个分类，分 {len(batches)} 批处理"
          f"（每批最多 {BATCH_SIZE} 个）")

    for batch_idx, batch in enumerate(batches):
        batch_names = [b[0] for b in batch]
        print(f"\n  📦 第 {batch_idx + 1}/{len(batches)} 批: "
              f"{', '.join(batch_names)}")

        prompt = build_batch_ai_prompt(batch)

        max_retries = 3
        batch_success = False
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500 * len(batch),
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("API 返回空内容")

                # 解析批量响应
                parsed = parse_batch_response(content, batch_names)

                if parsed:
                    for name, summary in parsed.items():
                        trends[name]["summary"] = summary
                        print(f"    ✅ {name}")

                    # 未解析出的分类加入失败队列
                    for name in batch_names:
                        if name not in parsed:
                            print(f"    ⚠️  未解析到: {name}（将单独重试）")
                            failed_cats.append(
                                next(b for b in batch if b[0] == name)
                            )

                    # 增量保存
                    _save_trends_incremental(
                        trend_path, trend_date, prev_date, trends
                    )
                    batch_success = True
                    break
                else:
                    raise ValueError("批量响应解析失败，未匹配到任何分类")

            except Exception as e:
                print(f"    ⚠️  第 {attempt} 次失败: {e}")
                if attempt < max_retries:
                    time.sleep(5 * attempt)

        if not batch_success:
            print(f"    ❌ 批量生成失败（已重试 {max_retries} 次），"
                  f"将逐个重试")
            failed_cats.extend(batch)

    # 3. 对失败的分类逐个重试（降级为单分类 prompt）
    if failed_cats:
        print(f"\n  🔄 逐个重试 {len(failed_cats)} 个失败分类...")
        for cat_name, cat, trend in failed_cats:
            prompt = build_ai_prompt(cat_name, cat, trend)
            max_retries = 3
            success = False
            for attempt in range(1, max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.7,
                    )
                    content = response.choices[0].message.content
                    if not content or not content.strip():
                        raise ValueError("API 返回空内容")
                    trends[cat_name]["summary"] = content.strip()
                    print(f"    ✅ {cat_name}")
                    _save_trends_incremental(
                        trend_path, trend_date, prev_date, trends
                    )
                    success = True
                    break
                except Exception as e:
                    print(f"    ⚠️  {cat_name} 第 {attempt} 次失败: {e}")
                    if attempt < max_retries:
                        time.sleep(5 * attempt)

            if not success:
                print(f"    ❌ {cat_name} 最终失败")
                old = existing_trends.get(cat_name, {}).get("summary", "")
                if old and not is_rule_summary(old):
                    trends[cat_name]["summary"] = old
                    print(f"    ↩️  保留旧 AI 总结: {cat_name}")
                else:
                    trends[cat_name]["summary"] = generate_trend_summary_text(
                        cat_name, trend
                    )

    return trends


# ========== 作者分析工具数据生成函数 ==========

# 情感偏好分类桶
EMOTION_BUCKETS = {
    "sweet": ["甜宠", "双洁", "团宠", "萌宝", "幼崽", "青梅竹马", "暗恋", "青春"],
    "angst": ["虐", "强制爱", "追妻", "替嫁", "先婚后爱"],
    "power_fantasy": ["重生", "穿书", "系统", "空间", "异能", "反派", "女配", "炮灰", "逆袭"],
    "daily_life": ["种田", "美食", "经商", "日常", "逃荒", "基建", "年代", "七零", "八零"],
}

# 金手指类型映射
GOLDEN_FINGER_MAP = {
    "重生": "重生记忆",
    "穿书": "穿书预知",
    "系统": "系统",
    "空间": "空间",
    "异能": "异能",
    "团宠": "团宠体质",
    "萌宝": "萌宝光环",
    "玄学": "玄学能力",
    "直播": "直播金手指",
}

# 简介钩子关键词
HOOK_KEYWORDS = ["复仇", "逆袭", "甜", "虐", "爽", "日常", "悬疑", "权谋", "经营", "养成", "抱大腿", "打脸"]

# 背景设定关键词
SETTING_KEYWORDS = {
    "架空古代": ["架空", "古代", "宫廷", "王府", "皇朝"],
    "真实朝代": ["唐朝", "宋朝", "明朝", "清朝", "汉朝", "秦朝", "三国"],
    "民国": ["民国", "军阀", "少帅"],
    "现代都市": ["都市", "豪门", "总裁", "校园", "职场"],
    "末世科幻": ["末世", "废土", "星际", "科幻", "天灾"],
    "修仙玄幻": ["修仙", "玄幻", "仙侠", "修真"],
}


def build_theme_trends(snapshots, data_dir, periods=None):
    """构建题材热度趋势数据。"""
    if periods is None:
        periods = MARKET_PERIODS

    # 按日期排序快照
    dated_snapshots = []
    for s in snapshots:
        m = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(s))
        if m:
            dated_snapshots.append({
                "path": s,
                "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
                "date_compact": f"{m.group(1)}{m.group(2)}{m.group(3)}"
            })
    dated_snapshots.sort(key=lambda x: x["date"])

    # 计算每个关键词在每天的命中数
    daily_keyword_counts = {}  # {date: {keyword: count}}
    daily_keyword_categories = {}  # {keyword: set of categories}

    for snap in dated_snapshots:
        try:
            with open(snap["path"], "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        day_counts = {kw: 0 for kw in MARKET_KEYWORDS}
        day_cat_map = {kw: set() for kw in MARKET_KEYWORDS}

        for cat in data.get("categories", []):
            cat_name = cat.get("name", "")
            for book in cat.get("books", []):
                text = f"{book.get('title', '')} {book.get('intro', '')}"
                for kw in MARKET_KEYWORDS:
                    if kw in text:
                        day_counts[kw] += 1
                        day_cat_map[kw].add(cat_name)

        daily_keyword_counts[snap["date"]] = day_counts
        for kw in MARKET_KEYWORDS:
            if kw not in daily_keyword_categories:
                daily_keyword_categories[kw] = set()
            daily_keyword_categories[kw].update(day_cat_map[kw])

    # 计算关键词共现（在同一本书中同时出现的关键词对）
    co_occurrence = {}  # {(kw1, kw2): count}
    latest_snap = dated_snapshots[-1] if dated_snapshots else None
    if latest_snap:
        try:
            with open(latest_snap["path"], "r", encoding="utf-8") as f:
                data = json.load(f)
            for cat in data.get("categories", []):
                for book in cat.get("books", []):
                    text = f"{book.get('title', '')} {book.get('intro', '')}"
                    found_kws = [kw for kw in MARKET_KEYWORDS if kw in text]
                    for i in range(len(found_kws)):
                        for j in range(i + 1, len(found_kws)):
                            pair = tuple(sorted([found_kws[i], found_kws[j]]))
                            co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
        except Exception:
            pass

    # 按时间窗口生成结果
    result_periods = {}
    for key, days in periods:
        if days is None:
            window_dates = [s["date"] for s in dated_snapshots]
        else:
            window_dates = [s["date"] for s in dated_snapshots[-days:]]

        if not window_dates:
            continue

        # 统计每个关键词在窗口内的总命中数
        themes = []
        for kw in MARKET_KEYWORDS:
            total = sum(daily_keyword_counts.get(d, {}).get(kw, 0) for d in window_dates)
            if total == 0:
                continue

            daily_counts = [
                {"date": d, "count": daily_keyword_counts.get(d, {}).get(kw, 0)}
                for d in window_dates
            ]

            # 计算趋势方向（比较前后两半）
            mid = len(daily_counts) // 2
            first_half = sum(d["count"] for d in daily_counts[:mid]) if mid > 0 else 0
            second_half = sum(d["count"] for d in daily_counts[mid:]) if mid > 0 else 0

            if second_half > first_half * 1.1:
                direction = "rising"
            elif second_half < first_half * 0.9:
                direction = "falling"
            else:
                direction = "stable"

            trend_pct = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

            themes.append({
                "name": kw,
                "total_count": total,
                "category_count": len(daily_keyword_categories.get(kw, set())),
                "categories": list(daily_keyword_categories.get(kw, set())),
                "daily_counts": daily_counts,
                "trend_direction": direction,
                "trend_pct": round(trend_pct, 1),
            })

        themes.sort(key=lambda x: x["total_count"], reverse=True)

        # 筛选共现 Top 10
        top_combos = []
        for (kw1, kw2), count in sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)[:10]:
            # 找到这两个关键词共同出现的分类
            cats = daily_keyword_categories.get(kw1, set()) & daily_keyword_categories.get(kw2, set())
            top_combos.append({
                "themes": [kw1, kw2],
                "co_count": count,
                "categories": list(cats)[:5],
            })

        result_periods[key] = {
            "period": "全部样本" if days is None else f"近 {days} 日",
            "themes": themes,
            "top_combinations": top_combos,
        }

    return {
        "date": dated_snapshots[-1]["date"] if dated_snapshots else "",
        "generated_at": datetime.now().isoformat(),
        "periods": result_periods,
    }


def build_competitive_analysis(latest_data):
    """构建竞品对标分析数据。"""
    result = {}

    for cat in latest_data.get("categories", []):
        cat_name = cat.get("name", "")
        books = cat.get("books", [])[:10]  # Top 10

        if not books:
            continue

        # 统计关键词出现比例
        keyword_counts = {}
        for kw in MARKET_KEYWORDS:
            count = sum(1 for b in books if kw in f"{b.get('title', '')} {b.get('intro', '')}")
            if count > 0:
                keyword_counts[kw] = {"keyword": kw, "count": count, "presence": round(count / len(books), 2)}

        shared_keywords = sorted(keyword_counts.values(), key=lambda x: x["presence"], reverse=True)[:15]

        # 标题模式分析
        title_lengths = [len(b.get("title", "")) for b in books]
        has_punctuation = sum(1 for b in books if any(p in b.get("title", "") for p in "：，！？、·"))
        avg_title_length = sum(title_lengths) / len(title_lengths) if title_lengths else 0

        # 检测常见标题结构
        title_structures = []
        for b in books:
            title = b.get("title", "")
            parts = []
            if any(kw in title for kw in ["重生", "穿越", "穿书"]):
                parts.append("穿越/重生")
            if any(kw in title for kw in ["夫人", "小姐", "王爷", "将军", "总裁"]):
                parts.append("身份")
            if any(kw in title for kw in ["归来", "复仇", "逆袭", "崛起"]):
                parts.append("动作")
            if parts:
                title_structures.append("+".join(parts))

        # 统计常见结构
        structure_counts = {}
        for s in title_structures:
            structure_counts[s] = structure_counts.get(s, 0) + 1
        common_structures = [s for s, c in sorted(structure_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        # 简介钩子分析
        hook_counts = {}
        for b in books:
            intro = b.get("intro", "")[:200]
            for hook in HOOK_KEYWORDS:
                if hook in intro:
                    hook_counts[hook] = hook_counts.get(hook, 0) + 1
        common_hooks = [h for h, c in sorted(hook_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        # 背景设定检测
        setting_counts = {}
        for b in books:
            text = f"{b.get('title', '')} {b.get('intro', '')}"
            for setting, keywords in SETTING_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    setting_counts[setting] = setting_counts.get(setting, 0) + 1
        common_settings = [s for s, c in sorted(setting_counts.items(), key=lambda x: x[1], reverse=True)[:3]]

        # 阅读量分布
        reads_values = []
        for b in books:
            r = parse_reads(b.get("reads", ""))
            if r > 0:
                reads_values.append(r)

        reads_values.sort(reverse=True)
        reads_dist = {}
        if reads_values:
            reads_dist = {
                "min": format_reads(reads_values[-1]),
                "max": format_reads(reads_values[0]),
                "median": format_reads(reads_values[len(reads_values) // 2]),
                "top1_avg": format_reads(reads_values[0]),
                "top10_avg": format_reads(sum(reads_values) / len(reads_values)),
            }

        result[cat_name] = {
            "top10_books": [
                {"rank": i + 1, "title": b.get("title", ""), "reads": b.get("reads", ""), "author": b.get("author", "")}
                for i, b in enumerate(books)
            ],
            "shared_keywords": shared_keywords,
            "title_patterns": {
                "avg_length": round(avg_title_length, 1),
                "has_punctuation": round(has_punctuation / len(books), 2) if books else 0,
                "common_structures": common_structures,
            },
            "intro_patterns": {
                "avg_length": round(sum(len(b.get("intro", "")) for b in books) / len(books)) if books else 0,
                "common_hooks": common_hooks,
                "common_settings": common_settings,
            },
            "reads_distribution": reads_dist,
        }

    return {
        "date": latest_data.get("date", ""),
        "categories": result,
    }


def build_reader_profile(latest_data):
    """构建读者偏好画像数据（按原始分类）。"""
    genre_profiles = {}

    for cat in latest_data.get("categories", []):
        cat_name = cat.get("name", "")
        all_books = cat.get("books", [])[:20]

        if not all_books or not cat_name:
            continue

        # 热门元素统计
        element_counts = {}
        for kw in MARKET_KEYWORDS:
            count = sum(1 for b in all_books if kw in f"{b.get('title', '')} {b.get('intro', '')}")
            if count > 0:
                element_counts[kw] = count

        top_elements = [
            {"keyword": kw, "weight": count}
            for kw, count in sorted(element_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]

        # 情感偏好计算
        emotion_scores = {bucket: 0 for bucket in EMOTION_BUCKETS}
        for b in all_books:
            text = f"{b.get('title', '')} {b.get('intro', '')}"
            for bucket, keywords in EMOTION_BUCKETS.items():
                for kw in keywords:
                    if kw in text:
                        emotion_scores[bucket] += 1

        total_emotion = sum(emotion_scores.values()) or 1
        emotional_preference = {
            bucket: round(score / total_emotion, 2)
            for bucket, score in emotion_scores.items()
        }

        # 金手指偏好
        golden_counts = {}
        for b in all_books:
            text = f"{b.get('title', '')} {b.get('intro', '')}"
            for kw, gf_type in GOLDEN_FINGER_MAP.items():
                if kw in text:
                    golden_counts[gf_type] = golden_counts.get(gf_type, 0) + 1

        total_golden = sum(golden_counts.values()) or 1
        golden_preference = [
            {"type": gf, "frequency": round(count / total_golden, 2)}
            for gf, count in sorted(golden_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # 背景设定偏好
        setting_counts = {}
        for b in all_books:
            text = f"{b.get('title', '')} {b.get('intro', '')}"
            for setting, keywords in SETTING_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    setting_counts[setting] = setting_counts.get(setting, 0) + 1

        total_setting = sum(setting_counts.values()) or 1
        setting_preference = {
            setting: round(count / total_setting, 2)
            for setting, count in sorted(setting_counts.items(), key=lambda x: x[1], reverse=True)
        }

        genre_profiles[cat_name] = {
            "top_elements": top_elements,
            "emotional_preference": emotional_preference,
            "golden_finger_preference": golden_preference,
            "setting_preference": setting_preference,
        }

    # 全局金手指偏好
    all_golden = {}
    for profile in genre_profiles.values():
        for gf in profile.get("golden_finger_preference", []):
            all_golden[gf["type"]] = all_golden.get(gf["type"], 0) + gf["frequency"]

    total_all_golden = sum(all_golden.values()) or 1
    overall_golden = [
        {"type": gf, "frequency": round(freq / total_all_golden, 2)}
        for gf, freq in sorted(all_golden.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "date": latest_data.get("date", ""),
        "period": "all",
        "genre_profiles": genre_profiles,
        "overall_top3_golden_fingers": overall_golden,
    }


def build_creation_suggestions(theme_trends, competitive_analysis, reader_profile,
                                api_key, base_url, model):
    """使用 AI 生成创作建议。"""
    try:
        from openai import OpenAI
    except ImportError:
        print("⚠️  openai 库未安装，跳过创作建议生成。")
        return None

    if not api_key or not base_url or not model:
        print("⚠️  未配置 AI 服务，跳过创作建议生成。")
        return None

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

    result = {
        "date": theme_trends.get("date", ""),
        "periods": {},
    }

    # 所有原始分类列表（从 reader_profile 的 key 获取）
    all_categories = list(reader_profile.get("genre_profiles", {}).keys())
    if not all_categories:
        print("⚠️  无分类数据，跳过创作建议生成。")
        return None

    # 对每个时间窗口生成建议
    for period_key in ["7", "14", "30", "all"]:
        period_themes = theme_trends.get("periods", {}).get(period_key, {})
        if not period_themes:
            continue

        genre_suggestions = {}
        cross_genre_opportunities = []

        # 为每个分类收集数据
        categories_data = []
        for cat_name in all_categories:
            cat_themes = []
            for theme in period_themes.get("themes", [])[:20]:
                if cat_name in theme.get("categories", []):
                    cat_themes.append(theme)

            cat_competitive = competitive_analysis.get("categories", {}).get(cat_name, {})
            cat_profile = reader_profile.get("genre_profiles", {}).get(cat_name, {})

            if not cat_themes:
                continue

            themes_text = "\n".join([
                f"  - {t['name']}: 命中{t['total_count']}次, 覆盖{t['category_count']}个分类, 趋势{t['trend_direction']}"
                for t in cat_themes[:8]
            ])

            competitive_text = ""
            if cat_competitive:
                top_books = cat_competitive.get("top10_books", [])[:3]
                competitive_text = f"  Top3: " + ", ".join([f"{b['title']}({b['reads']})" for b in top_books]) + "\n"

            profile_text = ""
            if cat_profile:
                top_elements = cat_profile.get("top_elements", [])[:3]
                profile_text = "热门元素: " + ", ".join([f"{e['keyword']}" for e in top_elements])

            categories_data.append((cat_name, themes_text, competitive_text, profile_text))

        if not categories_data:
            continue

        # 分批调用 AI（每批最多 9 个分类）
        batch_size = 9
        for batch_start in range(0, len(categories_data), batch_size):
            batch = categories_data[batch_start:batch_start + batch_size]

            sections = []
            for cname, cthemes, ccomp, cprof in batch:
                section = f"### {cname}\n热门题材:\n{cthemes}\n{ccomp}{cprof}"
                sections.append(section)

            batch_json = ", ".join([f'"{b[0]}": {{...}}' for b in batch])

            batch_prompt = f"""你是一位网文创作顾问。请根据以下各分类的市场数据，为每个分类提供创作方向建议。

{chr(10).join(sections)}

请输出严格JSON格式，每个分类一个key（共{len(batch)}个分类）：
{{{batch_json}}}

每个分类的值为：
{{
  "market_position": "一句话竞争格局",
  "recommended_themes": ["题材1", "题材2", "题材3"],
  "gap_opportunities": ["机会1", "机会2"],
  "title_suggestions": ["书名1", "书名2", "书名3"],
  "avoid_themes": ["饱和题材1", "饱和题材2"],
  "summary": "150字以内综合建议"
}}"""

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": batch_prompt}],
                    max_tokens=4000,
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                if content:
                    try:
                        parsed = parse_json_object(content)
                        for cname, _, _, _ in batch:
                            if cname in parsed:
                                genre_suggestions[cname] = parsed[cname]
                                print(f"    ✅ {cname} 创作建议")
                            else:
                                print(f"    ⚠️ {cname} 未在批量响应中找到")
                    except Exception:
                        print(f"    ⚠️ 批量创作建议响应解析失败，尝试逐个回退")
                        for cname, cthemes, ccomp, cprof in batch:
                            single_prompt = f"你是网文创作顾问。{cname}分类数据:\n{cthemes}\n{ccomp}{cprof}\n输出JSON: {{\"market_position\":\"...\",\"recommended_themes\":[],\"gap_opportunities\":[],\"title_suggestions\":[],\"avoid_themes\":[],\"summary\":\"...\"}}"
                            try:
                                resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": single_prompt}], max_tokens=800, temperature=0.7)
                                c = resp.choices[0].message.content
                                if c:
                                    genre_suggestions[cname] = parse_json_object(c)
                                    print(f"    ✅ {cname} 创作建议（回退）")
                            except Exception as fallback_e:
                                print(f"    ❌ {cname} 创作建议失败: {fallback_e}")
            except Exception as e:
                print(f"    ❌ 批量创作建议 AI调用失败: {e}")

        # 生成跨分类机会
        if len(genre_suggestions) >= 2:
            cross_prompt = f"""基于以下各分类的热门题材，请推荐3个跨分类的题材组合机会：

{chr(10).join([f'{name}: {", ".join(s.get("recommended_themes", [])[:2])}' for name, s in genre_suggestions.items()])}

请输出严格JSON数组格式：
[
  {{"combination": "题材1+题材2+题材3", "reasoning": "推荐理由", "example_hook": "示例钩子"}},
  ...
]"""
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": cross_prompt}],
                    max_tokens=600,
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                if content:
                    try:
                        cross_genre_opportunities = parse_json_object(content)
                    except Exception:
                        pass
            except Exception:
                pass

        result["periods"][period_key] = {
            "genre_suggestions": genre_suggestions,
            "cross_genre_opportunities": cross_genre_opportunities,
        }

    return result


def build_author_analysis(output, trends_dir, data_dir, snapshots,
                          api_key, api_base_url, api_model, prefix):
    """构建作者分析工具的全部数据。"""
    print("\n📊 开始生成作者分析工具数据...")

    author_dir = os.path.join(data_dir, "author")
    os.makedirs(author_dir, exist_ok=True)

    # 1. 题材热度趋势
    print("  📈 生成题材热度趋势...")
    theme_trends = build_theme_trends(snapshots, data_dir)
    write_json(os.path.join(author_dir, f"theme_trends_{prefix}.json"), theme_trends)
    print(f"    ✅ 题材热度: {len(theme_trends.get('periods', {}).get('all', {}).get('themes', []))} 个关键词")

    # 2. 竞品对标分析
    print("  🏆 生成竞品对标分析...")
    competitive = build_competitive_analysis(output)
    write_json(os.path.join(author_dir, f"competitive_analysis_{prefix}.json"), competitive)
    print(f"    ✅ 竞品分析: {len(competitive.get('categories', {}))} 个分类")

    # 3. 读者偏好画像
    print("  👤 生成读者偏好画像...")
    reader_profile = build_reader_profile(output)
    write_json(os.path.join(author_dir, f"reader_profile_{prefix}.json"), reader_profile)
    print(f"    ✅ 读者画像: {len(reader_profile.get('genre_profiles', {}))} 个分类")

    # 4. AI 创作建议
    print("  💡 生成 AI 创作建议...")
    suggestions = build_creation_suggestions(
        theme_trends, competitive, reader_profile,
        api_key, api_base_url, api_model
    )
    if suggestions:
        write_json(os.path.join(author_dir, f"creation_suggestions_{prefix}.json"), suggestions)
        print(f"    ✅ 创作建议: {len(suggestions.get('periods', {}))} 个周期")
    else:
        print("    ⚠️ 跳过创作建议（AI 服务未配置或调用失败）")

    print("  ✅ 作者分析数据生成完成！")


def main():
    parser = argparse.ArgumentParser(description="构建 latest_ranks.json")
    parser.add_argument("--force", action="store_true",
                        help="强制重新生成所有 AI 总结，忽略已有总结")
    parser.add_argument("--date", type=str, default="",
                        help="指定目标日期 (YYYY-MM-DD)，默认使用最新快照")
    parser.add_argument("--rank-type", type=str, default="all",
                        choices=["all", "male_new", "male_read", "female_new", "female_read"],
                        help="指定排行榜类型，默认处理所有类型")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    trends_dir = os.path.join(data_dir, "trends")
    os.makedirs(trends_dir, exist_ok=True)

    # 排行榜类型配置
    rank_types = {
        "male_new": {"name": "男频新书榜", "prefix": "male_new"},
        "male_read": {"name": "男频阅读榜", "prefix": "male_read"},
        "female_new": {"name": "女频新书榜", "prefix": "female_new"},
        "female_read": {"name": "女频阅读榜", "prefix": "female_read"},
    }

    # 确定要处理的排行榜类型
    if args.rank_type == "all":
        types_to_process = list(rank_types.keys())
    else:
        types_to_process = [args.rank_type]

    # 处理每种排行榜类型
    for rank_type_key in types_to_process:
        rank_config = rank_types[rank_type_key]
        prefix = rank_config["prefix"]
        rank_name = rank_config["name"]

        print(f"\n{'='*60}")
        print(f"📊 处理{rank_name}")
        print(f"{'='*60}")

        # 查找该类型的 JSON 快照文件
        snapshots = sorted(
            glob.glob(os.path.join(data_dir, f"fanqie_{prefix}_ranks_*.json"))
        )

        if not snapshots:
            print(f"⚠️  未找到{rank_name}的快照文件，跳过")
            continue

        # 根据 --date 参数选择目标快照
        if args.date:
            target_date_compact = args.date.replace("-", "")
            target_path = os.path.join(
                data_dir, f"fanqie_{prefix}_ranks_{target_date_compact}.json"
            )
            if not os.path.exists(target_path):
                print(f"⚠️  未找到 {args.date} 的{rank_name}快照文件: {target_path}")
                continue
            latest_path = target_path
            target_idx = snapshots.index(target_path) if target_path in snapshots else -1
            if target_idx == -1:
                print(f"⚠️  快照文件存在但未在日期索引中找到，将无法生成趋势对比: {target_path}")
        else:
            latest_path = snapshots[-1]
            target_idx = len(snapshots) - 1

        latest_data = load_snapshot(latest_path)
        if latest_data is None:
            print(f"❌ 跳过 {prefix}: 目标快照加载失败")
            continue
        print(f"目标快照: {os.path.basename(latest_path)} ({latest_data['date']})")

        # 加载前一天的快照（如果有）
        prev_data = None
        prev_date = ""
        if target_idx > 0:
            prev_path = snapshots[target_idx - 1]
            prev_data = load_snapshot(prev_path)
            if prev_data is not None:
                prev_date = prev_data.get("date", "")
            else:
                print(f"⚠️  对比快照加载失败，将仅生成当日数据")
            print(f"对比快照: {os.path.basename(prev_path)} ({prev_date})")

        # 加载已有的趋势数据（用于保留已有 AI 总结）
        existing_trends = {}
        trend_path = os.path.join(trends_dir, f"{prefix}_{latest_data['date']}.json")
        if os.path.exists(trend_path) and not args.force:
            try:
                with open(trend_path, "r", encoding="utf-8") as f:
                    existing_trend_data = json.load(f)
                    existing_trends = existing_trend_data.get("trends", {})
                ai_count = sum(1 for t in existing_trends.values()
                              if not is_rule_summary(t.get("summary", "")))
                rule_count = len(existing_trends) - ai_count
                print(f"已有趋势数据: {ai_count} 个 AI 总结, {rule_count} 个待补充")
            except Exception as e:
                print(f"⚠️  已有趋势数据加载失败，将重新生成: {e}")

        if args.force:
            print(f"\n🔄 强制模式：将重新生成{rank_name}的所有 AI 总结")

        # 对比趋势
        if prev_data:
            trends = compare_categories(
                latest_data["categories"], prev_data["categories"]
            )
        else:
            print("仅有一天数据，无法生成趋势对比。")
            trends = {
                cat["name"]: {
                    "new_count": 0,
                    "dropped_count": 0,
                    "new_books": [],
                    "dropped_books": [],
                    "top_risers": [],
                    "top_fallers": [],
                    "reads_growth": [],
                    "summary": "首日数据，暂无趋势对比。",
                }
                for cat in latest_data["categories"]
            }

        # ========== AI 总结：通过 API_BASE_URL / API_KEY / API_MODEL 配置 ==========
        api_base_url = os.environ.get("API_BASE_URL", "")
        api_key = os.environ.get("API_KEY", "")
        api_model = os.environ.get("API_MODEL", "")

        if api_base_url and api_key and api_model:
            print(f"\n正在使用 {api_model} 生成 AI 总结...")
            print(f"  API: {api_base_url}")
            trends = generate_ai_summaries(
                latest_data["categories"], trends,
                api_key, api_base_url, api_model,
                force=args.force,
                existing_trends=existing_trends,
                trend_path=trend_path,
                trend_date=latest_data["date"],
                prev_date=prev_date
            )
        else:
            missing = [k for k, v in {"API_BASE_URL": api_base_url, "API_KEY": api_key, "API_MODEL": api_model}.items() if not v]
            print(f"\n未配置 AI 服务（缺少: {', '.join(missing)}），使用规则摘要替代。")
            for cat_name, trend in trends.items():
                # 保留已有 AI 总结
                old = existing_trends.get(cat_name, {}).get("summary", "")
                if old and not is_rule_summary(old):
                    trend["summary"] = old
                elif not trend.get("summary"):
                    trend["summary"] = generate_trend_summary_text(cat_name, trend)

        # 组装输出
        output = {
            "date": latest_data["date"],
            "prev_date": prev_date,
            "rank_type": rank_name,
            "categories": [],
        }

        for cat in latest_data["categories"]:
            cat_name = cat["name"]
            cat_output = {
                "name": cat_name,
                "trend": trends.get(cat_name, {}),
                "books": cat.get("books", []),
            }
            output["categories"].append(cat_output)

        # 写入该排行榜类型的 latest_ranks.json
        out_path = os.path.join(data_dir, f"latest_{prefix}_ranks.json")
        write_json(out_path, output)
        print(f"\n✅ 已生成: {out_path}")

        # 生成静态 API 文件：api/latest/<prefix>.json
        api_dir = build_latest_api(output, base_dir, prefix)
        print(f"✅ Lastest API: {api_dir}")

        # 写入 trends/<prefix>_YYYY-MM-DD.json
        trend_output = {
            "date": latest_data["date"],
            "prev_date": prev_date,
            "rank_type": rank_name,
            "trends": trends,
        }
        write_json(trend_path, trend_output)
        print(f"✅ 趋势存档: {trend_path}")

        # 生成全站热点总结：AI 优先，规则文案兜底
        market_payload = build_market_summary_payload(output, trends_dir)
        if api_base_url and api_key and api_model:
            market_payload = enrich_market_summary_with_ai(
                market_payload, api_key, api_base_url, api_model, rank_name
            )
        market_path = os.path.join(data_dir, f"market_summary_{prefix}.json")
        write_json(market_path, market_payload)
        print(f"✅ 全站热点总结: {market_path}")

        # 生成 dates.json 索引（供前端历史日期选择器使用）
        date_list = []
        for s in snapshots:
            fname = os.path.basename(s)
            # fanqie_<prefix>_ranks_YYYYMMDD.json -> YYYY-MM-DD
            m = re.search(r"(\d{4})(\d{2})(\d{2})", fname)
            if m:
                date_list.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        dates_path = os.path.join(data_dir, f"dates_{prefix}.json")
        write_json(dates_path, {"dates": sorted(date_list)})
        print(f"✅ 日期索引: {dates_path} ({len(date_list)} 个日期)")

        # ========== 作者分析工具数据生成 ==========
        build_author_analysis(output, trends_dir, data_dir, snapshots,
                              api_key, api_base_url, api_model, prefix)


if __name__ == "__main__":
    main()
