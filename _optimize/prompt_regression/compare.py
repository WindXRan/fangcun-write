"""
维度对比器 — 两段式：结构对齐 + 读者体验对比。

用法:
    python compare.py --original 源文/第1章.txt --output _optimize/round1/output_ch1.xml --guide 章纲/第1章.xml --report _optimize/round1/compare.json

输出:
    两段制 JSON:
    - alignment:   原文 vs 输出，各结构维度是否一致
    - reader_experience: 原文 vs 输出，读者视角哪个更好（严格 A/B 比较）
"""

import json, sys, argparse, os, re
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / ".agents" / "skills" / "fangcun-write" / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
try:
    from llm_provider import call_llm
except ImportError:
    call_llm = None


def _call_llm_fallback(messages: list):
    import urllib.request
    api_key = os.environ.get("API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", api_key)
    if not api_key:
        return None
    base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    url = base + "/chat/completions"
    model = os.environ.get("FANGCUN_MODEL", "deepseek-v4-pro")
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.1}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def extract_content(xml_text: str) -> str:
    m = re.search(r'<content>(.*?)</content>', xml_text, re.DOTALL)
    return m.group(1).strip() if m else xml_text.strip()


SYSTEM_PROMPT = """
你是一名对照分析助手。对比原文和仿写输出，输出两部分 JSON。

## 第一部分：结构对齐（structure alignment）

判断输出在技术维度上是否和原文一致。

| 维度 | 判断方法 | 取值 |
|------|---------|------|
| 开篇手法 | 原文第1-200字怎么开篇的？输出呢？ | action/dialogue/suspense/emotion/exposition |
| 章尾钩子 | 原文最后3行是什么收束？输出呢？ | crisis/sudden_reveal/cliffhanger/summary/emotional/countdown |
| 情绪弧线 | 原文本章情绪起点→终点是什么？输出呢？ | 自由文本 |
| 信息释放节奏 | 原文前25%释放了什么信息？输出呢？ | 自由文本 |
| 调性 | 原文的叙事基调（口语/吐槽/严肃/文艺）？输出呢？ | 自由文本 |

## 第二部分：读者体验对比（reader experience comparison）

这是核心。从读者视角出发，逐项对比原文和输出。**每项只能用"A>B"、"A≈B"、"A<B"来回答，禁止含糊。**

A = 原文，B = 输出。A>B 表示原文更好，A<B 表示输出更好。

| 维度 | 判断方法 |
|------|---------|
| 代入感强度 | 哪个让你更快进入故事、更在意角色？看前300字就能判断 |
| 主角辨识度 | 哪个的主角更像"一个具体的人"——有口癖、有态度、有脾气？ |
| 对话自然度 | 哪个的对话听起来像真人说话，而不是"解释剧情用的工具对话"？ |
| 爽感密度 | 哪一章的爽点更多、更密集？不是指数量，而是"读完觉得爽了"的感觉 |
| 钩子力度 | 哪个的结尾更让你想看下一章？ |
| 信息紧凑度 | 哪个更有"每句话都在推进"的感觉？哪个更注水？ |
| 情感共鸣 | 哪个让你更有情绪波动（生气/开心/紧张/感动）？ |

## 输出格式

严格遵守以下 JSON 格式，不要输出其他文字：

{
  "alignment": {
    "开篇手法": {"原文": "动作开场", "输出": "动作开场", "一致": true, "说明": "均以动作切入"},
    "章尾钩子": {"原文": "危机", "输出": "危机", "一致": true, "说明": ""},
    "情绪弧线": {"原文": "好奇→震惊→温暖→紧张→期待", "输出": "好奇→震惊→紧张→期待", "一致": false, "说明": "输出缺了温暖环节"},
    "信息释放节奏": {"原文": "前25%只写出生感知", "输出": "前25%揭了穿书+系统", "一致": false, "说明": "输出信息释放比原文快"},
    "调性": {"原文": "口语吐槽", "输出": "口语吐槽", "一致": true, "说明": ""}
  },
  "reader_experience": {
    "代入感强度": {"比较": "A>B", "理由": "原文前100字就让读者感受到主角的处境和性格，输出节奏偏慢"},
    "主角辨识度": {"比较": "A>B", "理由": "原文主角口癖鲜明（完了完了、特么的），输出主角内心OS偏书面"},
    "对话自然度": {"比较": "A>B", "理由": "原文对话有生活感，输出对话偏功能化"},
    "爽感密度": {"比较": "A≈B", "理由": "两者爽点分布接近"},
    "钩子力度": {"比较": "A≈B", "理由": "两者均以悬念收尾"},
    "信息紧凑度": {"比较": "A>B", "理由": "原文每段都有推进，输出有几段内心的无信息增量"},
    "情感共鸣": {"比较": "A>B", "理由": "原文有母亲初为人母的细腻描写引发共情，输出偏事件推进忽略情感"}
  }
}
"""


def run_compare(original: str, output: str, guide: str = "") -> str:
    guide_block = f"# 章纲\n{guide[:2000]}\n\n" if guide else ""
    user = f"""{guide_block}# 原文
{original[:4000]}

# 仿写输出
{output[:4000]}

输出 JSON。"""

    resp = None
    if call_llm:
        resp, err = call_llm([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
        if err:
            resp = _call_llm_fallback([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
    else:
        resp = _call_llm_fallback([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
    if not resp:
        return json.dumps({"error": "LLM 调用失败"}, ensure_ascii=False)
    m = re.search(r'\{.*\}', resp, re.DOTALL)
    if m:
        try:
            json.loads(m.group())
            return m.group()
        except json.JSONDecodeError:
            pass
    return resp


def main():
    parser = argparse.ArgumentParser(description="维度对比器（含读者体验）")
    parser.add_argument("--original", required=True, help="原文文件路径")
    parser.add_argument("--output", required=True, help="输出 XML 文件路径")
    parser.add_argument("--guide", help="章纲文件路径（可选）")
    parser.add_argument("--report", help="输出 JSON 报告路径（可选）")
    args = parser.parse_args()

    if not Path(args.original).exists():
        print(f"错误: 原文文件不存在: {args.original}")
        sys.exit(1)
    if not Path(args.output).exists():
        print(f"错误: 输出文件不存在: {args.output}")
        sys.exit(1)

    original_text = Path(args.original).read_text(encoding='utf-8')
    output_text = extract_content(Path(args.output).read_text(encoding='utf-8'))
    guide_text = ""
    if args.guide and Path(args.guide).exists():
        guide_text = Path(args.guide).read_text(encoding='utf-8')

    print("正在对比（含读者体验分析）...")
    result = run_compare(original_text, output_text, guide_text)

    try:
        data = json.loads(result)
        print(f"\n{'='*55}")
        print("结构对齐")
        print(f"{'='*55}")
        if "alignment" in data:
            a_match = 0
            a_total = 0
            for dim, info in data["alignment"].items():
                if isinstance(info, dict) and "一致" in info:
                    a_total += 1
                    icon = "✅" if info["一致"] else "❌"
                    print(f"  {icon} {dim}: {info.get('说明', '')}")
                    if info["一致"]:
                        a_match += 1
            if a_total:
                print(f"  对齐: {a_match}/{a_total}")
        print()

        print(f"{'='*55}")
        print("读者体验对比（A=原文, B=输出）")
        print(f"{'='*55}")
        if "reader_experience" in data:
            a_better = 0
            b_better = 0
            tie = 0
            total = 0
            for dim, info in data["reader_experience"].items():
                if isinstance(info, dict) and "比较" in info:
                    total += 1
                    cmp = info["比较"]
                    icon = {"A>B": "🔴", "A≈B": "⚪", "A<B": "🟢"}.get(cmp, "❓")
                    print(f"  {icon} {dim}: {cmp} — {info.get('理由', '')}")
                    if cmp == "A>B":
                        a_better += 1
                    elif cmp == "A<B":
                        b_better += 1
                    else:
                        tie += 1
            if total:
                print(f"\n  原文胜出: {a_better}  持平: {tie}  输出胜出: {b_better}")
        print()
    except (json.JSONDecodeError, TypeError) as e:
        print(f"JSON 解析失败: {e}")
        print(result)

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        # 如果是解析失败的 fallback，可能不是 JSON
        try:
            json.loads(result)
            Path(args.report).write_text(result, encoding='utf-8')
        except (json.JSONDecodeError, TypeError):
            Path(args.report).write_text(
                json.dumps({"raw_output": result}, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        print(f"对比报告已保存: {args.report}")


if __name__ == "__main__":
    main()
