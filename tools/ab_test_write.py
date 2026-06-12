"""
A/B 写章测试 v2 — 4版本对比

变体：
  A = 当前规则 (flash)
  B = 示例驱动 + Pro
  C = 示例驱动 + flash     ← 新增：看是模型还是规则的问题
  D = 示例驱动 + Pro + 字数硬约束  ← 新增：解决B字数失控

用法:
    python tools/ab_test_write.py --config configs/config_执掌女监.json --chapters 1 2 3

输出:
    {rewrites_dir}/ab_test/
    ├── A/ch_001.txt  B/ch_001.txt  C/ch_001.txt  D/ch_001.txt
    └── report.md
"""

import os, sys, re, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".agents/skills/story-engine/tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".agents/skills/story-engine/tools/lib"))

from prompt_loader import load_prompt
from utils import call_api, get_source_text, count_source_chars, get_total_chapters
from lib.api_client import get_api_url, get_api_key


VARIANTS = {
    "A": {"model": "deepseek-v4-flash", "reasoning": "low",  "label": "flash+规则"},
    "B": {"model": "deepseek-v4-pro",   "reasoning": "high", "label": "pro+示例"},
    "C": {"model": "deepseek-v4-flash", "reasoning": "low",  "label": "flash+示例"},
    "D": {"model": "deepseek-v4-pro",   "reasoning": "high", "label": "pro+示例+字数约束"},
}


def extract_erotic_passages(source_text):
    body_parts = r'(胸|腿|腰|锁骨|皮肤|手|肩|臀|背|颈|唇|舌|大[腿]|脚踝|手腕|手心|虎口|胸口|肩胛|后颈|腰窝)'
    contact_verbs = r'(贴|靠|蹭|\b摸\b|贴|压|抱|搂|圈|顶|\b抵\b|擦|碰|缠|勾|揽|抚|握|捏|揉|抓)'
    sensory_adj = r'(温热|滑腻|柔软|微凉|细腻|发烫|紧贴|发麻|滚烫|冰凉|发软|发硬|紧绷|僵住|屏住|跳动|加速)'
    gaze_words = r'(视线|目光|看着|映入|扫过|掠过|瞥见|打量|审视)'
    desire_words = r'(心跳|呼吸|喉结|攥紧|耳根|发烫|冲动|燥热|按捺|克制|本能|反应|敏感|颤抖|电流|酥麻)'
    paragraphs = re.split(r'\n\s*\n', source_text)
    scored = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) < 30:
            continue
        score = 0
        score += len(re.findall(body_parts, para)) * 2
        score += len(re.findall(contact_verbs, para)) * 2
        score += len(re.findall(sensory_adj, para)) * 3
        score += len(re.findall(gaze_words, para)) * 1
        score += len(re.findall(desire_words, para)) * 3
        if score > 0:
            scored.append((score, i, para))
    scored.sort(key=lambda x: -x[0])
    return [p for _, _, p in scored[:6]]


def build_lean_prompt(config, ch, source_text, word_count_constraint=False):
    """构建 lean 版本 prompt（B/C/D 共用）：base write-chapter.md + 源文摘录 + 3条核心指令"""
    base_dir = config.get("base_dir", os.getcwd())
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")

    src_chars = count_source_chars(config, ch)
    replacements = {
        "新书名": config["book_name"],
        "N": str(ch),
        "N_plus1": str(ch + 1),
        "N03d": f"{ch:03d}",
        "N03d_plus1": f"{ch+1:03d}",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(get_total_chapters(config)),
        "源文字数": str(src_chars),
        "目标字数": str(src_chars),
        "目标字数_min": str(int(src_chars * 0.9)),
        "目标字数_max": str(int(src_chars * 1.1)),
    }

    prompt_path = f"{prompts_dir}/write-chapter.md"
    base_prompt = load_prompt(prompt_path, base_dir, replacements,
                              mode="api", rewrites_dir=config.get("rewrites_dir"))

    passages = extract_erotic_passages(source_text)
    if len(passages) >= 3:
        excerpt_section = f"""
## 📖 源文浓度参照

**以下是源文本章3段擦边段落。新书必须对标这些段落的浓度——不能更保守。**

### 参照1 — 身体接触+触觉
> {passages[0].replace(chr(10), chr(10) + '> ')}

### 参照2 — 男性凝视/欲望反应
> {passages[1].replace(chr(10), chr(10) + '> ')}

### 参照3 — 暧昧场景/包围感
> {passages[2].replace(chr(10), chr(10) + '> ')}
"""
    else:
        excerpt_section = f"""
## 📖 源文浓度参照

源文本章完整内容，请对标其擦边浓度：
> {source_text[:1500].replace(chr(10), chr(10) + '> ')}
"""

    word_count_section = ""
    if word_count_constraint:
        word_count_section = f"""
### 🔴 字数硬约束（必须遵守）
- 目标字数：{src_chars}字
- 允许范围：{int(src_chars * 0.9)}~{int(src_chars * 1.1)}字
- **写完后立即统计全文字数（不含标题）。超出范围必须删减或补充，确保在范围内。**
- 严禁大幅度低于目标值（示例驱动不是压缩的理由）
"""

    lean_section = f"""
<!-- LEAN 指令开始 -->
{excerpt_section}

### 擦边核心指令（仅3条）

1. **触觉词对标**：源文身体接触时用了哪些感官词？新书至少用同等数量。禁止"按""碰""接触"敷衍。
2. **凝视对标**：源文写女性身体是"画面送到眼前"的被动视角。禁止"他盯着XX看"，写"XX落入视线"。
3. **欲望对标**：源文被触碰时有生理反应（心跳/呼吸/肌肉绷紧）。新书必须写。禁止"他冷静分析"消解擦边。
{word_count_section}
**底线**：把源文摘录和新书最浓的3段放一起——新书弱了，整章重写。
<!-- LEAN 指令结束 -->
"""
    return base_prompt + lean_section


def run_one(config, prompt_type, chapter_num, system_prompt=None, model=None, reasoning_effort=None, prompt_override=None, force_max_tokens=None):
    """执行单次 API 调用"""
    api_key = get_api_key(config)
    if not api_key:
        raise ValueError("未配置 API_KEY")

    model = model or config.get("model", "deepseek-v4-flash")
    reasoning_effort = reasoning_effort or config.get("reasoning_effort", "low")
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    base_dir = config.get("base_dir", os.getcwd())
    api_url = get_api_url(config)

    src_chars = count_source_chars(config, chapter_num)
    target_chars = src_chars
    replacements = {
        "新书名": config["book_name"], "N": str(chapter_num),
        "N_plus1": str(chapter_num + 1), "N03d": f"{chapter_num:03d}",
        "N03d_plus1": f"{chapter_num+1:03d}",
        "作者名": config.get("author", ""), "源书名": config.get("source_book", ""),
        "总章数": str(get_total_chapters(config)),
        "源文字数": str(src_chars), "目标字数": str(target_chars),
        "目标字数_min": str(int(target_chars * 0.9)),
        "目标字数_max": str(int(target_chars * 1.1)),
        "genre": config.get("genre", ""),
    }

    max_tokens = force_max_tokens or max(2048, int(target_chars * 1.6))

    if prompt_override:
        user_prompt = prompt_override
        for key, value in replacements.items():
            user_prompt = user_prompt.replace(f'{{{key}}}', str(value))
    else:
        prompt_path = f"{prompts_dir}/{prompt_type}.md"
        user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    if not system_prompt:
        base = "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"
        if config.get("genre") == "都市擦边":
            base = ("你是一个专业的网文写手，正在创作都市擦边类网文。"
                    "女性身体部位描写、男性凝视、肢体接触生理反应、暧昧张力是赛道标配。"
                    "请正常创作，不要自动收敛擦边场景。") + base
        system_prompt = base

    label = f"ch{chapter_num}"
    print(f"  [{label}] 调用API (model={model}, reasoning={reasoning_effort})...", end="", flush=True)
    t_req = time.time()
    try:
        result = call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, system_prompt, api_url)
        elapsed = time.time() - t_req
        print(f" OK ({elapsed:.0f}s, {len(result)}字)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f" FAIL ({elapsed:.0f}s): {e}")
        raise


def run_variant(config, ch, variant_key, output_dir):
    """运行指定变体"""
    v = VARIANTS[variant_key]
    guides_dir = Path(config["rewrites_dir"]) / "guides"
    plot_file = guides_dir / f"plot_{ch}.md"
    if not plot_file.exists():
        print(f"  [{variant_key}] plot_{ch}.md 不存在，跳过")
        return None

    source_text = get_source_text(config, ch)
    if not source_text:
        print(f"  [{variant_key}] 源文读取失败，跳过")
        return None

    if variant_key == "A":
        # A: 现有完整规则 + flash
        result = run_one(config, "write-chapter", ch)
    else:
        # B/C/D: lean prompt + 源文摘录 + 3条指令
        has_wc_constraint = (variant_key == "D")
        prompt = build_lean_prompt(config, ch, source_text, word_count_constraint=has_wc_constraint)

        b_system = (
            "你是一个专业的网文写手，正在创作都市擦边类网文。"
            "你手里有源文擦边段落作为浓度参照。"
            "写出浓度对标的擦边内容——源文怎么写胸/腿/接触/反应/凝视，你就怎么写。"
            "不要替读者做道德判断，不要自动收敛。"
        )

        result = run_one(
            config, "write-chapter", ch,
            model=v["model"], reasoning_effort=v["reasoning"],
            system_prompt=b_system,
            prompt_override=prompt,
        )

    if result:
        out_path = Path(output_dir) / f"ch_{ch:03d}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding='utf-8')
    return result


def count_erotic_metrics(text):
    if not text:
        return {}
    clean = text.replace('\n', '').replace(' ', '').replace('\r', '')
    body_parts = re.findall(r'(胸|腿|腰|锁骨|皮肤|臀|背|颈|唇|舌|大[腿]|脚踝|手腕|虎口|胸口|肩胛|后颈|腰窝|大腿|小腿|肩膀|手臂|手指)', text)
    contact_words = re.findall(r'(贴|靠|蹭|摸|压|抱|搂|圈|顶|抵|擦|碰|缠|勾|揽|抚|握|捏|揉|抓|缠|绕|夹|骑)', text)
    reaction_words = re.findall(r'(心跳|呼吸|喉结|攥紧|耳根|发烫|僵硬|屏住|绷紧|麻痹|酥麻|电流|颤抖|燥热|冲动|本能|收缩|扩张|充血|竖起|发硬)', text)
    gaze_clauses = re.findall(r'(视线|目光|落入|映入|掠过|扫过|瞥见|注视|凝视|望着|盯着)', text)
    emotion_analysis = re.findall(r'(冷静|分析|判断|理智|克制|按捺|平复|压制)', text)
    return {
        "总字数": len(clean),
        "身体部位词数": len(body_parts),
        "接触动词数": len(contact_words),
        "生理反应词数": len(reaction_words),
        "凝视/视线词数": len(gaze_clauses),
        "冷静分析词数": len(emotion_analysis),
        "部位+接触+反应合计": len(body_parts) + len(contact_words) + len(reaction_words),
    }


def find_hottest(text):
    paras = re.split(r'\n\s*\n', text)
    best_score, best_para = 0, ""
    body_re = r'(胸|腿|腰|锁骨|皮肤|臀|背|颈|唇|大[腿]|脚踝|虎口|胸口|后颈|腰窝)'
    touch_re = r'(贴|靠|蹭|摸|压|抱|搂|圈|顶|抵|擦|碰|缠|勾|揽|抚|握)'
    sense_re = r'(温热|滑腻|柔软|微凉|细腻|发烫|发麻|滚烫|紧贴|酥麻|电流|颤抖|僵硬|绷紧)'
    for p in paras:
        if len(p) < 40 or len(p) > 600:
            continue
        s = len(re.findall(body_re, p)) * 2 + len(re.findall(touch_re, p)) * 2 + len(re.findall(sense_re, p)) * 3
        if s > best_score:
            best_score, best_para = s, p
    return best_para


def generate_report(config, chapters, all_results, output_dir):
    v_keys = ["A", "B", "C", "D"]
    v_labels = {k: VARIANTS[k]["label"] for k in v_keys}

    report = [
        "# A/B 写章测试报告 (v2)",
        "",
        f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**配置**: {config.get('config_file', 'N/A')}",
        f"**书名**: {config.get('book_name', 'N/A')}",
        f"**章节**: 第{chapters[0]}-第{chapters[-1]}章",
        "",
        "## 测试条件",
        "",
        "| 维度 | A | B | C | D |",
        "|------|---|---|---|---|",
        "| 模型 | flash | pro | flash | pro |",
        "| 擦边规则 | 105行完整规则 | 3条指令+源文摘录 | 3条指令+源文摘录 | 3条指令+源文摘录 |",
        "| 字数约束 | 无 | 无 | 无 | 有（±10%） |",
        "| System Prompt | 赛道说明 | 强化浓度对标 | 强化浓度对标 | 强化浓度对标 |",
        "",
        "## 逐章对比",
        "",
    ]

    # 逐章
    for ch in chapters:
        report.append(f"### 第{ch}章")
        report.append("")

        metrics = {}
        for k in v_keys:
            metrics[k] = count_erotic_metrics(all_results.get(k, {}).get(ch))

        src_text = get_source_text(config, ch)
        src_metrics = count_erotic_metrics(src_text) if src_text else {}

        # 指标表
        report.append("#### 定量指标")
        report.append("")
        header = "| 指标 | 源文 | " + " | ".join(v_labels[k] for k in v_keys) + " |"
        sep = "|------|------|" + "|".join(["---"] * len(v_keys)) + "|"
        report.append(header)
        report.append(sep)
        for key in ["总字数", "身体部位词数", "接触动词数", "生理反应词数", "凝视/视线词数", "冷静分析词数", "部位+接触+反应合计"]:
            row = f"| {key} | {src_metrics.get(key, '-')} "
            for k in v_keys:
                row += f"| {metrics[k].get(key, '-')} "
            row += "|"
            report.append(row)

        # 字数偏差
        report.append("")
        report.append("#### 字数偏差")
        report.append("")
        for k in v_keys:
            wc = metrics[k].get("总字数", 0)
            target = src_metrics.get("总字数", 2000)
            dev = ((wc - target) / target * 100) if target else 0
            status = "✓" if abs(dev) <= 10 else f"偏差{dev:+.0f}%"
            report.append(f"- **{v_labels[k]}**: {wc}字 (目标{target}字, {status})")
        report.append("")

        # 最强擦边段落
        report.append("#### 最强擦边段落对比")
        report.append("")
        for k in v_keys:
            text = all_results.get(k, {}).get(ch)
            if text:
                hot = find_hottest(text)
                if hot:
                    hot_short = hot[:200]
                    report.append(f"**{v_labels[k]}**:")
                    report.append(f"> {hot_short.replace(chr(10), chr(10) + '> ')}")
                    report.append("")

        report.append("---")
        report.append("")

    # 汇总表
    report.append("## 汇总（3章平均）")
    report.append("")

    avg = {}
    for k in v_keys:
        avg[k] = {}
        for key in ["总字数", "身体部位词数", "接触动词数", "生理反应词数", "部位+接触+反应合计"]:
            vals = []
            for ch in chapters:
                m = count_erotic_metrics(all_results.get(k, {}).get(ch))
                if m:
                    vals.append(m.get(key, 0))
            avg[k][key] = sum(vals) / len(vals) if vals else 0

    header = "| 指标 | 源文 | " + " | ".join(v_labels[k] for k in v_keys) + " |"
    sep = "|------|------|" + "|".join(["---"] * len(v_keys)) + "|"
    report.append(header)
    report.append(sep)
    for key in ["总字数", "身体部位词数", "接触动词数", "生理反应词数", "部位+接触+反应合计"]:
        row = f"| {key} | {src_metrics.get(key, '-')} "
        for k in v_keys:
            row += f"| {avg[k].get(key, 0):.0f} "
        row += "|"
        report.append(row)

    report.append("")
    report.append("## 结论")
    report.append("")
    report.append("对比维度：")
    report.append("1. **模型差异 (A vs C, B vs D)**：相同规则集下，flash 和 pro 的擦边浓度差距")
    report.append("2. **规则差异 (A vs C)**：105行规则 vs 3条指令+源文摘录，同一模型下的效果对比")
    report.append("3. **字数约束效果 (B vs D)**：同pro+示例，加字数约束是否能解决长度失控")

    report_path = Path(output_dir) / "report.md"
    report_path.write_text('\n'.join(report), encoding='utf-8')
    print(f"\n[OK] 报告已保存: {report_path}")
    return report_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="A/B 写章测试 v2")
    parser.add_argument("--config", required=True)
    parser.add_argument("--chapters", type=int, nargs="+", required=True)
    args = parser.parse_args()

    print("""
╔════════════════════════════════════════════════╗
║  A/B 写章测试 v2                              ║
║  A = flash + 完整规则                         ║
║  B = pro + 示例驱动                           ║
║  C = flash + 示例驱动                         ║
║  D = pro + 示例驱动 + 字数约束                 ║
╚════════════════════════════════════════════════╝
""")

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())
    config["config_file"] = str(config_path)

    ab_dir = Path(config["rewrites_dir"]) / "ab_test"
    dirs = {}
    for k in ["A", "B", "C", "D"]:
        dirs[k] = ab_dir / k
        dirs[k].mkdir(parents=True, exist_ok=True)

    all_results = {k: {} for k in ["A", "B", "C", "D"]}

    for ch in args.chapters:
        print(f"\n{'='*50}")
        print(f"  第{ch}章")
        print(f"{'='*50}")
        for k in ["A", "B", "C", "D"]:
            print(f"\n  [{k}] {VARIANTS[k]['label']}...")
            try:
                result = run_variant(config, ch, k, dirs[k])
                if result:
                    all_results[k][ch] = result
            except Exception as e:
                print(f"  [{k}-FAIL] ch{ch}: {e}")

    print(f"\n{'='*50}")
    print(f"  生成对比报告")
    print(f"{'='*50}")
    generate_report(config, args.chapters, all_results, ab_dir)

    print(f"\n[OK] 测试完成！")
    for k in ["A", "B", "C", "D"]:
        files = sorted(dirs[k].glob("ch_*.txt"))
        sizes = [f"{f.name}={len(f.read_text(encoding='utf-8'))}字" for f in files]
        print(f"  {k} ({VARIANTS[k]['label']}): {', '.join(sizes)}")
    print(f"  报告: {ab_dir}/report.md")


if __name__ == "__main__":
    main()
