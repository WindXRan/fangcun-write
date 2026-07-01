"""
P0 规则检查器 — 结构化回归测试第一关。

用法:
    python checker.py --output 正文/正文/第1章.xml --report _optimize/round1/check_report.json

输出:
    JSON 格式的 pass/fail 报告，每项含：名称、状态、详情、违规次数。
    无 API 调用，纯正则 + 统计。
"""

import re, json, sys, argparse
from pathlib import Path


def extract_content(xml_text: str) -> str:
    """从 <content> 标签中提取正文。"""
    m = re.search(r'<content>(.*?)</content>', xml_text, re.DOTALL)
    return m.group(1).strip() if m else xml_text.strip()


def check_closing_summary(text: str) -> dict:
    """章尾最后100字是否包含总结升华句。"""
    tail = text[-100:] if len(text) > 100 else text
    patterns = [
        r'终于明白',
        r'一切都[^。]*$',
        r'[他她它]终于',
        r'这一刻[^。]*$',
        r'此刻[，,].*$',
        r'所有的一切',
        r'终于知道',
        r'他终于[^。]*$',
        r'似乎一切都',
        r'一切[，,].*都[^。]*$',
        r'阳光洒进来[^。]*$',
        r'暖洋洋的[^。]*$',
    ]
    found = []
    for p in patterns:
        ms = re.findall(p, tail)
        found.extend(ms)
    return {
        "name": "章尾总结升华",
        "status": "fail" if found else "pass",
        "detail": f"发现 {len(found)} 处总结句: {found[:3]}" if found else "OK",
        "count": len(found),
    }


def check_opening_hook(text: str) -> dict:
    """章首前100字是否有钩子(事件/对话/动作)，而非天气/风景/日常。"""
    head = text[:100] if len(text) > 100 else text
    # 禁止开场模式
    opener = text[:50].strip()
    bad_openers = [
        r'^[这那]一天[，,]',
        r'^[这那]天[，,]',
        r'^[这那]个[，,]',
        r'^[今明后]天[，,]',
        r'^[春夏秋冬]天[，,]',
        r'^[一三]年后[，,]',
        r'^[一三]个月前[，,]',
        r'^清晨[，,]',
        r'^天[气空][^。]{0,20}',
        r'^[^。]{0,10}的风[^。]{0,20}',
        r'^[^。]{0,10}的阳光[^。]{0,20}',
    ]
    for p in bad_openers:
        if re.search(p, opener):
            return {
                "name": "章首钩子",
                "status": "fail",
                "detail": f"以天气/时间/日常开场: {opener[:30]}...",
                "count": 1,
            }
    # 检测是否有事件/对话: 首100字出现引号、动作词
    has_dialogue = '"' in head or '"' in head or '“' in head
    if not has_dialogue and len(head) < 80:
        # 前80字无引号，可能没有钩子
        return {
            "name": "章首钩子",
            "status": "warn",
            "detail": "前80字无对话开场，确认是否有动作事件",
            "count": 1,
        }
    return {"name": "章首钩子", "status": "pass", "detail": "OK", "count": 0}


def check_banned_words(text: str) -> dict:
    """一级禁用词检测。"""
    patterns = {
        "情态":  [r'仿佛', r'犹如', r'宛若', r'如同', r'好像[^。]{0,10}一般'],
        "表情":  [r'眼中闪过', r'嘴角勾起', r'嘴角扬起', r'心中涌起', r'心头一震', r'心中一动'],
        "动作":  [r'深吸一口气', r'不禁', r'不由自主', r'情不自禁'],
        "弱化":  [r'微微[一笑动摇]', r'缓缓', r'轻轻', r'淡淡', r'一丝', r'一抹'],
        "判断":  [r'不容置疑', r'显而易见', r'毫无疑问'],
    }
    found = {}
    total = 0
    for category, pats in patterns.items():
        hits = []
        for p in pats:
            hits.extend(re.findall(p, text))
        if hits:
            found[category] = hits[:5]  # 最多报5个
            total += len(hits)
    return {
        "name": "禁用词检测",
        "status": "pass" if total == 0 else ("warn" if total <= 3 else "fail"),
        "detail": f"共 {total} 处: {json.dumps(found, ensure_ascii=False)}" if found else "OK",
        "count": total,
    }


def check_emotion_telling(text: str) -> dict:
    """直述情绪检测: 他感到、他意识到 等。"""
    patterns = [
        r'[他她它][感觉]到[^。]{0,15}',
        r'[他她它]意识到[^。]{0,15}',
        r'[他她它]察觉[^。]{0,10}',
        r'[他她它][心]?底[^。]{0,15}[一阵股]',
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    unique = list(set(found))[:5]
    return {
        "name": "情绪直述",
        "status": "pass" if not found else ("warn" if len(found) <= 2 else "fail"),
        "detail": f"发现 {len(found)} 处: {unique}" if found else "OK",
        "count": len(found),
    }


def check_meta_words(text: str) -> dict:
    """元信息词检测。"""
    patterns = [r'上一章', r'本章', r'前文', r'后文', r'伏笔', r'细纲',
                r'第[一二三四五六七八九十百千万两\d]+章',
                r'读者[^的]']
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    return {
        "name": "元信息词",
        "status": "fail" if found else "pass",
        "detail": f"发现: {found[:5]}" if found else "OK",
        "count": len(found),
    }


def check_format(text: str) -> dict:
    """格式规则检查。"""
    issues = []
    # 破折号
    dashes = len(re.findall(r'——|--', text))
    if dashes > 0:
        issues.append(f"破折号 {dashes} 处")
    # 省略号
    ellipsis_count = len(re.findall(r'\.{3,}|…{2,}', text))
    if ellipsis_count > 0:
        issues.append(f"省略号 {ellipsis_count} 处")
    # 他说/她道 对话标签（独立出现时）
    said = len(re.findall(r'[他她][说道喊叫]道[，,：:]', text))
    if said > 0:
        issues.append(f"「他说/她道」标签 {said} 处")
    # 感叹号密度
    exclaim = len(re.findall(r'！', text))
    exclaim_density = exclaim / max(len(text) / 1000, 1)
    if exclaim_density > 15:
        issues.append(f"感叹号密度 {exclaim_density:.1f}/千字（阈值15）")
    status = "pass"
    if len(issues) > 2:
        status = "fail"
    elif issues:
        status = "warn"
    return {
        "name": "格式规则",
        "status": status,
        "detail": "; ".join(issues) if issues else "OK",
        "count": len(issues),
    }


def check_weak_adverb_density(text: str) -> dict:
    """弱化副词密度: 微微/淡淡/缓缓/轻轻 每千字不超过3次。"""
    words = re.findall(r'微微|淡淡|缓缓|轻轻', text)
    density = len(words) / max(len(text) / 1000, 1)
    return {
        "name": "弱化副词密度",
        "status": "pass" if density <= 3 else "fail",
        "detail": f"{len(words)} 次，{density:.1f}/千字{'（<=3，通过）' if density <=3 else '（>3，超标）'}",
        "count": len(words),
    }


def check_paragraph_length(text: str) -> dict:
    """段落长度监控：平均句数、过长段落。"""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return {"name": "段落长度", "status": "pass", "detail": "无段落", "count": 0}
    # 段落的句数（按。？！结尾分割）
    sent_counts = []
    for p in paragraphs:
        sents = len(re.findall(r'[。？！]', p))
        sent_counts.append(sents)
    avg = sum(sent_counts) / len(sent_counts) if sent_counts else 0
    long_paras = sum(1 for s in sent_counts if s > 5)
    return {
        "name": "段落长度",
        "status": "warn" if long_paras > 0 else "pass",
        "detail": f"平均 {avg:.1f} 句/段，{long_paras} 段超过5句",
        "count": long_paras,
    }


def check_metaphors(text: str) -> dict:
    """万能比喻检测。"""
    patterns = [
        r'像[^。]{0,10}般',
        r'如[^。]{0,10}般',
        r'像[^。]{0,10}一样',
        r'如[^。]{0,10}一样',
        r'仿佛[^。]{0,10}一般',
        r'潮水般|闪电般|狂风般|洪水般',
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    return {
        "name": "万能比喻",
        "status": "fail" if found else "pass",
        "detail": f"发现 {len(found)} 处: {found[:3]}" if found else "OK",
        "count": len(found),
    }


def check_word_count(text: str) -> dict:
    """字数统计。不加判断，仅输出。"""
    # 去空格去标点
    clean = re.sub(r'\s+', '', text)
    chars = len(clean)
    return {
        "name": "字数统计",
        "status": "info",
        "detail": f"{chars} 字（去空白）",
        "count": chars,
    }


ALL_CHECKS = [
    check_closing_summary,
    check_opening_hook,
    check_banned_words,
    check_emotion_telling,
    check_meta_words,
    check_format,
    check_weak_adverb_density,
    check_paragraph_length,
    check_metaphors,
    check_word_count,
]


def run_checks(text: str) -> list:
    return [check(text) for check in ALL_CHECKS]


def summary(results: list) -> dict:
    """生成汇总。"""
    counts = {"pass": 0, "warn": 0, "fail": 0, "info": 0}
    for r in results:
        if r["status"] in counts:
            counts[r["status"]] += 1
        if r["status"] == "fail":
            counts.setdefault("fail_items", []).append(r["name"])
    return counts


def main():
    parser = argparse.ArgumentParser(description="P0 规则检查器")
    parser.add_argument("--output", required=True, help="输出 XML 文件路径")
    parser.add_argument("--report", help="输出 JSON 报告路径（可选）")
    args = parser.parse_args()

    content = Path(args.output).read_text(encoding='utf-8')
    text = extract_content(content)
    if not text:
        print("错误: 未能从 XML 提取正文")
        sys.exit(1)

    results = run_checks(text)
    s = summary(results)

    # 打印报告
    print(f"\n{'='*50}")
    print(f"检查报告: {args.output}")
    print(f"状态: {"✅ 通过" if s['fail'] == 0 else f"❌ {s['fail']} 项未通过"}")
    print(f"  {s['pass']} 通过  {s.get('warn', 0)} 警告  {s['fail']} 未通过  {s.get('info', 0)} 信息")
    print(f"{'='*50}")
    for r in results:
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "info": "ℹ️"}.get(r["status"], "?")
        print(f"  {icon} {r['name']}: {r['detail']}")
    print()

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        report = {
            "file": args.output,
            "summary": s,
            "checks": results,
        }
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"报告已保存: {args.report}")


if __name__ == "__main__":
    main()
