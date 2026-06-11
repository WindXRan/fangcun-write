"""
B站搜索工具（基于 bilibili-api-python SDK）。
支持搜索视频 + 获取评论（需SESSDATA cookie获取更多评论）。

用法:
    python bilibili_sdk_search.py "嘎子带货" --limit 10 --comments 10
    python bilibili_sdk_search.py "潘嘎之交" --limit 10 --comments 10 --sessdata "你的SESSDATA"
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from bilibili_api import search, comment, video, Credential


async def search_videos(keyword, page=1, count=20, order_type="totalrank"):
    """搜索视频。"""
    order = search.OrderVideo.TOTALRANK
    if order_type == "click":
        order = search.OrderVideo.CLICK
    elif order_type == "pubdate":
        order = search.OrderVideo.PUBDATE
    elif order_type == "dm":
        order = search.OrderVideo.DM
    elif order_type == "stow":
        order = search.OrderVideo.STOW

    result = await search.search_by_type(
        keyword=keyword,
        search_type=search.SearchObjectType.VIDEO,
        page=page,
        order_type=order,
    )
    return result.get("result", [])


async def get_comments(oid, credential=None, max_count=10):
    """获取视频评论（按热度排序）。"""
    comments_list = []
    page = 1

    while len(comments_list) < max_count and page <= 5:
        try:
            result = await comment.get_comments(
                oid=oid,
                type_=comment.CommentResourceType.VIDEO,
                order=comment.OrderType.LIKE,
                page_index=page,
                credential=credential,
            )
            replies = result.get("replies") or []
            if not replies:
                break
            for r in replies:
                content = r.get("content", {}).get("message", "")
                member = r.get("member", {})
                comments_list.append({
                    "user": member.get("uname", ""),
                    "content": content,
                    "like": r.get("like", 0),
                })
                if len(comments_list) >= max_count:
                    break
            page += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  [WARN] 评论获取失败: {e}", file=sys.stderr)
            break

    return comments_list[:max_count]


def format_number(n):
    if not n:
        return "0"
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)


def clean_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()


async def do_search(keyword, limit=20, order="totalrank", include_comments=10, credential=None):
    """执行搜索并收集信息。"""
    print(f'\n🔍 搜索B站: "{keyword}" (排序:{order}, 数量:{limit})')

    results = await search_videos(keyword, page=1, count=limit, order_type=order)
    if not results:
        print("  [WARN] 无搜索结果")
        return []

    videos = []
    for i, v in enumerate(results[:limit]):
        bvid = v.get("bvid", "")
        aid = v.get("aid", 0)
        vid = {
            "title": clean_html(v.get("title", "")),
            "bvid": bvid,
            "aid": aid,
            "author": v.get("author", ""),
            "play": v.get("play", 0),
            "danmaku": v.get("video_review", 0),
            "favorites": v.get("favorites", 0),
            "duration": v.get("duration", ""),
            "description": clean_html(v.get("description", ""))[:300],
            "tag": v.get("tag", ""),
            "url": f"https://www.bilibili.com/video/{bvid}",
            "comments": [],
        }

        if include_comments > 0 and aid:
            await asyncio.sleep(0.5)
            vid["comments"] = await get_comments(aid, credential=credential, max_count=include_comments)

        videos.append(vid)

    print(f"  ✅ 找到 {len(videos)} 个视频")
    return videos


def format_markdown(videos, keyword):
    lines = [f"# B站搜索: {keyword}\n", f"共 {len(videos)} 个视频\n"]
    for i, v in enumerate(videos, 1):
        lines.append(f"## {i}. {v['title']}")
        lines.append(f"- UP主: {v['author']}")
        lines.append(f"- 播放: {format_number(v['play'])} | 弹幕: {format_number(v['danmaku'])} | 收藏: {format_number(v['favorites'])}")
        lines.append(f"- 时长: {v['duration']}")
        lines.append(f"- 链接: {v['url']}")
        if v['tag']:
            lines.append(f"- 标签: {v['tag']}")
        if v['description']:
            lines.append(f"- 简介: {v['description'][:200]}")
        if v['comments']:
            lines.append(f"\n### 评论 ({len(v['comments'])}条)")
            for c in v['comments']:
                lines.append(f"- 👍{c['like']} @{c['user']}: {c['content']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="B站视频搜索工具（SDK版）")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=20, help="返回视频数量")
    parser.add_argument("--order", default="totalrank",
                       choices=["totalrank", "click", "pubdate", "dm", "stow"])
    parser.add_argument("--comments", type=int, default=10, help="每个视频取几条评论")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--sessdata", help="B站 SESSDATA cookie")
    parser.add_argument("--cookie-file", help="cookie文件路径（存放SESSDATA）")
    args = parser.parse_args()

    # 构建 Credential
    credential = None
    sessdata = args.sessdata
    if not sessdata and args.cookie_file:
        cf = Path(args.cookie_file)
        if cf.exists():
            sessdata = cf.read_text(encoding='utf-8').strip()

    if sessdata:
        credential = Credential(sessdata=sessdata)
        print(f"✅ 已使用SESSDATA认证")

    videos = asyncio.run(do_search(args.keyword, args.limit, args.order, args.comments, credential))

    if not videos:
        print("无结果")
        sys.exit(1)

    output = json.dumps(videos, ensure_ascii=False, indent=2) if args.json else format_markdown(videos, args.keyword)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\n📄 已保存到: {args.output}")
    else:
        print("\n" + output)


if __name__ == "__main__":
    main()
