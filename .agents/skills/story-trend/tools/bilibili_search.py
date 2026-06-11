"""
B站搜索工具：搜索视频、提取标题/描述/评论。
用于热梗调研，收集第一手网络素材。

用法:
    python bilibili_search.py "嘎子带货" --limit 20 --comments 5
    python bilibili_search.py "潘嘎之交" --limit 10 --sort click --output trends/嘎子带货/bilibili.md
"""

import argparse
import hashlib
import functools
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("需要 requests 库: pip install requests", file=sys.stderr)
    sys.exit(1)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"
COMMENTS_API = "https://api.bilibili.com/x/v2/reply"
NAV_API = "https://api.bilibili.com/x/web-interface/nav"

# WBI 签名混淆表
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

_session = None
_wbi_keys = None
_user_cookie = None


def set_cookie(cookie_str):
    """设置用户cookie（从浏览器复制）。"""
    global _user_cookie, _session
    _user_cookie = cookie_str
    _session = None  # 重置session以使用新cookie


def _get_mixin_key(orig):
    return functools.reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, '')[:32]


def _enc_wbi(params, img_key, sub_key):
    """WBI 签名。"""
    mixin_key = _get_mixin_key(img_key + sub_key)
    params['wts'] = round(time.time())
    params = dict(sorted(params.items()))
    params = {
        k: ''.join(ch for ch in str(v) if ch not in "!*'()")
        for k, v in params.items()
    }
    query = urlencode(params)
    params['w_rid'] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def _get_session():
    """获取带cookie的session。"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        if _user_cookie:
            _session.headers['Cookie'] = _user_cookie
        try:
            _session.get("https://www.bilibili.com", timeout=10)
        except Exception:
            pass
    return _session


def _get_wbi_keys():
    """获取 WBI 签名密钥。"""
    global _wbi_keys
    if _wbi_keys:
        return _wbi_keys
    s = _get_session()
    try:
        nav = s.get(NAV_API, timeout=10).json()
        wbi = nav.get('data', {}).get('wbi_img', {})
        img_url = wbi.get('img_url', '')
        sub_url = wbi.get('sub_url', '')
        _wbi_keys = (
            img_url.split('/')[-1].split('.')[0] if img_url else '',
            sub_url.split('/')[-1].split('.')[0] if sub_url else '',
        )
    except Exception:
        _wbi_keys = ('', '')
    return _wbi_keys


def api_get(url, params=None, retries=3):
    """带WBI签名+重试的API请求。"""
    s = _get_session()
    img_key, sub_key = _get_wbi_keys()

    for attempt in range(retries):
        try:
            signed_params = _enc_wbi(dict(params), img_key, sub_key) if params else {}
            resp = s.get(url, params=signed_params, timeout=15)
            data = resp.json()
            code = data.get("code")
            if code == 0:
                return data.get("data", {})
            if code == -412:
                print(f"  [WARN] 被风控(-412)，等待{5*(attempt+1)}s...", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
                global _session, _wbi_keys
                _session = None
                _wbi_keys = None
                continue
            print(f"  [WARN] API错误: code={code}, msg={data.get('message','')}", file=sys.stderr)
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"  [FAIL] {e}", file=sys.stderr)
                return None
    return None


def search_videos(keyword, page=1, page_size=20, order="totalrank"):
    """搜索B站视频。"""
    return api_get(SEARCH_API, {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "order": order,
    })


def get_comments(oid, sort=2, pn=1, ps=20):
    """获取视频评论（sort: 0时间/1回复数/2热度）。"""
    return api_get(COMMENTS_API, {
        "type": 1, "oid": oid, "sort": sort, "pn": pn, "ps": ps,
    })


def get_top_comments(oid, limit=10):
    """获取视频热评，自动合并热度+时间排序凑够数量。"""
    seen = set()
    comments = []

    # 先取热评（sort=2，通常返回3条）
    data = get_comments(oid, sort=2, ps=limit)
    if data:
        for r in (data.get("replies") or []):
            rpid = r.get("rpid")
            if rpid and rpid not in seen:
                seen.add(rpid)
                comments.append({
                    "user": r.get("member", {}).get("uname", ""),
                    "content": clean_html(r.get("content", {}).get("message", "")),
                    "like": r.get("like", 0),
                })
            if len(comments) >= limit:
                return comments

    # 不够再取按点赞排序的（sort=1）
    if len(comments) < limit:
        data = get_comments(oid, sort=1, ps=limit * 2)
        if data:
            for r in (data.get("replies") or []):
                rpid = r.get("rpid")
                if rpid and rpid not in seen:
                    seen.add(rpid)
                    comments.append({
                        "user": r.get("member", {}).get("uname", ""),
                        "content": clean_html(r.get("content", {}).get("message", "")),
                        "like": r.get("like", 0),
                    })
                if len(comments) >= limit:
                    break

    # 还不够取按时间排序的（sort=0）
    if len(comments) < limit:
        data = get_comments(oid, sort=0, ps=limit * 2)
        if data:
            for r in (data.get("replies") or []):
                rpid = r.get("rpid")
                if rpid and rpid not in seen:
                    seen.add(rpid)
                    comments.append({
                        "user": r.get("member", {}).get("uname", ""),
                        "content": clean_html(r.get("content", {}).get("message", "")),
                        "like": r.get("like", 0),
                    })
                if len(comments) >= limit:
                    break

    return comments[:limit]


def clean_html(text):
    return re.sub(r'<[^>]+>', '', text or '').strip()


def format_number(n):
    if not n:
        return "0"
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)


def search_and_collect(keyword, limit=20, order="totalrank", include_comments=3):
    """搜索视频并收集信息。"""
    print(f'\n🔍 搜索B站: "{keyword}" (排序:{order}, 数量:{limit})')

    data = search_videos(keyword, page_size=min(limit, 50), order=order)
    if not data:
        print("  [WARN] 搜索无结果")
        return []

    results = data.get("result", [])
    if not results:
        print("  [WARN] 无搜索结果")
        return []

    videos = []
    for v in results[:limit]:
        vid = {
            "title": clean_html(v.get("title", "")),
            "bvid": v.get("bvid", ""),
            "aid": v.get("aid", 0),
            "author": v.get("author", ""),
            "play": v.get("play", 0),
            "danmaku": v.get("danmaku", 0),
            "favorites": v.get("favorites", 0),
            "duration": v.get("duration", ""),
            "pubdate": v.get("pubdate", 0),
            "description": clean_html(v.get("description", ""))[:300],
            "tag": v.get("tag", ""),
            "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
            "comments": [],
        }
        if include_comments > 0 and vid["aid"]:
            time.sleep(0.5)
            vid["comments"] = get_top_comments(vid["aid"], limit=include_comments)
        videos.append(vid)

    print(f"  ✅ 找到 {len(videos)} 个视频")
    return videos


def format_videos_markdown(videos, keyword):
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
            lines.append("\n### 热评")
            for c in v['comments']:
                lines.append(f"- 👍{c['like']} @{c['user']}: {c['content']}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="B站视频搜索工具（热梗调研用）")
    parser.add_argument("keyword", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=20, help="返回视频数量")
    parser.add_argument("--order", default="totalrank",
                       choices=["totalrank", "click", "pubdate", "dm", "stow"])
    parser.add_argument("--comments", type=int, default=3, help="每个视频取几条评论")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--cookie", help="B站cookie字符串（从浏览器复制）")
    parser.add_argument("--cookie-file", help="cookie文件路径")
    args = parser.parse_args()

    if args.cookie:
        set_cookie(args.cookie)
    elif args.cookie_file:
        from pathlib import Path as _P
        cf = _P(args.cookie_file)
        if cf.exists():
            set_cookie(cf.read_text(encoding='utf-8').strip())
        else:
            print(f"cookie文件不存在: {args.cookie_file}", file=sys.stderr)

    videos = search_and_collect(args.keyword, args.limit, args.order, args.comments)
    if not videos:
        print("无结果")
        sys.exit(1)

    output = json.dumps(videos, ensure_ascii=False, indent=2) if args.json else format_videos_markdown(videos, args.keyword)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\n📄 已保存到: {args.output}")
    else:
        print("\n" + output)


if __name__ == "__main__":
    main()
