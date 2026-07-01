"""
仿写格式测试 — 自动对比不同章纲格式的生成效果

用法:
    python 仿写格式测试.py <源文正文路径> [--output <输出目录>]

流程:
    1. 读源文 → 提取结构特征
    2. 用N种章纲格式分别生成正文
    3. 对比字数/段落数/信息点等指标
    4. 输出最优格式

返回: 结构化JSON报告
"""
import sys, os, re, json, time

# 添加工具路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from llm_provider import call_llm


def extract_structure(text: str) -> dict:
    """从源文正文提取结构特征"""
    clean = re.sub(r'^第\d+章.*?\n', '', text).strip()
    paras = [p for p in clean.split('\n\n') if p.strip()]

    # 信息释放点检测
    info_points = []
    markers = {
        "穿越/穿书": ['穿书', '穿越', '小说', '原著', '书里'],
        "灭门/危机": ['灭门', '炮灰', '死', '夭折', '抄家'],
        "金手指/商城": ['商城', '功德', '系统', '金手指', '面板'],
        "心声暴露": ['心声', '听到', '在说话', '脑海'],
        "钩子/危机": ['爬床', '丫鬟', '今晚', '内鬼'],
    }

    for i, p in enumerate(paras):
        pos_pct = (i / len(paras)) * 100
        for key, kws in markers.items():
            if any(kw in p for kw in kws):
                info_points.append({
                    "position": f"段{i+1}({pos_pct:.0f}%)",
                    "type": key,
                    "preview": p[:40]
                })
                break

    return {
        "total_chars": len(clean),
        "total_paras": len(paras),
        "avg_chars_per_para": round(len(clean) / len(paras), 1),
        "first_10_paras": [{"chars": len(p), "preview": p[:50]} for p in paras[:10]],
        "last_3_paras": [{"chars": len(p), "preview": p[:50]} for p in paras[-3:]],
        "info_release_points": info_points,
        "para_lengths": [len(p) for p in paras],
    }


def generate_chapter(guide_format: str, source_structure: dict, temperature: float = 0.5) -> tuple[str, dict]:
    """用指定章纲格式生成一章"""
    # 构建prompt
    example_paras = source_structure["first_10_paras"]
    para_lines = "\n".join([f"({p['chars']}字) {p['preview']}" for p in example_paras])

    last3 = source_structure["last_3_paras"]
    last3_lines = "\n".join([f"({p['chars']}字) {p['preview']}" for p in last3])

    target_chars = source_structure["total_chars"]
    target_paras = source_structure["total_paras"]
    target_avg = source_structure["avg_chars_per_para"]

    prompts = {
        "E-示例+章纲": f"""你的任务：写一章正文。先看源文段落风格，严格模仿。

源文段落样本（前10段，每段字数+开头）：
{para_lines}

源文最后3段（钩子风格参考）：
{last3_lines}

分析特征：
- 每段{target_avg}字，1-2句
- 总段落数约{target_paras}段
- 总字数约{target_chars}字

章纲：
[Beat1] 主角穿越/出生/好奇打量（约{int(target_paras*0.19)}段）
[Beat2] 发现世界观+危机（约{int(target_paras*0.20)}段）
[Beat3] 金手指上线（约{int(target_paras*0.18)}段）
[Beat4] 家庭互动+能力暴露（约{int(target_paras*0.25)}段）
[Beat5] 危机预警+钩子（约{int(target_paras*0.18)}段）

要求：
- 每段{int(target_avg-5)}-{int(target_avg+5)}字，1-2句
- 总字数{target_chars}字左右，总段数{target_paras}段左右
- 口语吐槽风，自然不要硬
- 模仿源文的信息释放顺序
- 章尾钩子功能与源文一致（突然揭示/倒计时）
- 不写章节标题，不写分析，直接写正文""",

        "D-严格字数": f"""写一章正文。每段{int(target_avg-5)}-{int(target_avg+5)}字，每段1-2句。

总字数{target_chars}字，总段数{target_paras}段。

章纲：
[1]投胎+好奇+古代环境（{int(target_paras*0.19)}段）
[2]穿书发现+灭门预警（{int(target_paras*0.20)}段）
[3]金手指上线（{int(target_paras*0.18)}段）
[4]母亲互动+心声暴露（{int(target_paras*0.25)}段）
[5]危机预警钩子（{int(target_paras*0.18)}段）

写完必须统计字数。超了砍到达标。
不写标题，不分析。""",

        "C-短句80段": f"""写一章正文，共{target_paras}段，每段{int(target_avg-5)}-{int(target_avg+5)}字。

总字数{target_chars}字左右。

分段：
段1-15：穿越出生，好奇打量，内心吐槽
段16-30：发现穿书，灭门危机
段31-45：金手指上线，浏览价格
段46-70：母亲互动，心声暴露，温暖接纳
段71-{target_paras}：危机预警，钩子

每段1-2句，口语吐槽风。直接写正文。""",
    }

    prompt = prompts.get(guide_format, list(prompts.values())[0])
    resp, err = call_llm([{"role": "user", "content": prompt}], temperature=temperature)

    if err:
        return "", {"error": err}

    # 统计
    body = re.sub(r'^#.*?\n', '', resp, flags=re.MULTILINE).strip()
    paras = [p for p in body.split('\n\n') if p.strip() and len(p.strip()) > 3]
    chars = len(body)

    metrics = {
        "chars": chars,
        "paras": len(paras),
        "avg": round(chars/len(paras), 1) if paras else 0,
        "chars_diff": abs(chars - source_structure["total_chars"]),
        "paras_diff": abs(len(paras) - source_structure["total_paras"]),
        "has_chuanshu": any(kw in body for kw in ['穿书','小说','原著','书里']),
        "has_weiji": any(kw in body for kw in ['灭门','炮灰','死','夭折']),
        "has_jinzhi": any(kw in body for kw in ['商城','功德','系统','金手指']),
        "has_xinsheng": any(kw in body for kw in ['心声','听到','脑海']),
        "has_hook": any(kw in body for kw in ['爬床','今晚','内鬼','丫鬟']),
    }
    # 读者视角自评：LLM自己读一遍，给体验评分
    _reader_prompt = f"""你刚读完一章网文。请从读者角度回答：

1. 读第1段时，你什么感觉？（好奇/无聊/困惑/好笑？）""" + chr(10) + f"""2. 读中间部分，信息释放节奏舒服吗？（太快/太慢/刚好？）
3. 读最后几段，你想点下一章吗？
4. 和原文比（如果有），读者体验差距在哪？
5. 总分1-10分

全文：{body[:800]}...（总{chars}字）"""
    _rr, _re = call_llm([{"role": "user", "content": _reader_prompt}], temperature=0.3)
    metrics["reader_review"] = _rr[:300] if _rr else "无"
    # 从评分提取数字
    _score_match = re.search(r'总分[：:]\s*(\d+)', _rr or "")
    metrics["score"] = int(_score_match.group(1)) if _score_match else 5

    return resp, metrics


def main():
    if len(sys.argv) < 2:
        print("用法: python 仿写格式测试.py <源文正文路径> [--output <目录>]")
        sys.exit(1)

    src_path = sys.argv[1]
    if not os.path.exists(src_path):
        print(f"文件不存在: {src_path}")
        sys.exit(1)

    text = open(src_path, encoding='utf-8').read()
    text = re.sub(r'<[^>]+>', '', text).strip()

    print(f"📖 读取源文: {os.path.basename(src_path)}")

    # Step 1: 提取结构
    struct = extract_structure(text)
    print(f"📊 结构: {struct['total_chars']}字, {struct['total_paras']}段, 平均{struct['avg_chars_per_para']}字/段")
    print(f"   信息释放点: {len(struct['info_release_points'])}个")

    # Step 2: 多格式测试
    formats = ["E-示例+章纲", "D-严格字数", "C-短句80段"]
    results = {}

    for fmt in formats:
        print(f"\n🧪 测试[{fmt}]...", end=" ", flush=True)
        resp, metrics = generate_chapter(fmt, struct)
        if not resp:
            print(f"❌ {metrics.get('error', 'unknown')}")
            continue
        print(f"✅ {metrics['chars']}字/{metrics['paras']}段 评分:{metrics['score']}")
        results[fmt] = metrics

        # 保存输出
        out_dir = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--output" else "/tmp"
        if len(sys.argv) > 3:
            out_dir = sys.argv[3]
        elif len(sys.argv) > 2 and sys.argv[2] == "--output":
            out_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp"
        else:
            out_dir = "/tmp"

        safe_name = fmt.replace(" ", "_").replace("-", "_")
        with open(f"{out_dir}/ch_{safe_name}.txt", 'w', encoding='utf-8') as f:
            f.write(resp)

    # Step 3: 对比报告
    print(f"\n{'='*60}")
    print(f"{'格式':20s} {'字数':>6s} {'段落':>6s} {'均长':>5s} {'字数差':>6s} {'段差':>5s} {'要素':>5s} {'评分':>6s}")
    print(f"{'-'*60}")

    best = None
    for fmt, m in sorted(results.items(), key=lambda x: x[1].get("score", 0), reverse=True):
        score = m.get("score", 0)
        print(f"{fmt[:20]:20s} {m['chars']:6d} {m['paras']:6d} {m['avg']:5.1f} {m['chars_diff']:6d} {m['paras_diff']:5d} {m.get('score',0):6.1f}")
        if best is None or score > best[1].get("score", 0):
            best = (fmt, m)

    print(f"\n{'='*60}")
    if best:
        print(f"🏆 最佳格式: {best[0]}")
        print(f"   字数: {best[1]['chars']}(目标{struct['total_chars']},差{best[1]['chars_diff']})")
        print(f"   段落: {best[1]['paras']}(目标{struct['total_paras']},差{best[1]['paras_diff']})")
        print(f"   评分: {best[1]['score']}")

    # 输出JSON报告
    report = {
        "source": os.path.basename(src_path),
        "structure": {k: v for k, v in struct.items() if k != "para_lengths"},
        "results": results,
        "best": best[0] if best else None
    }

    report_path = f"{out_dir}/test_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 报告保存: {report_path}")


if __name__ == "__main__":
    main()
