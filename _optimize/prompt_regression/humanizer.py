#!/usr/bin/env python3
"""
Humanizer — 去AI写作"精致感"，打回粗糙真实的人类写法。
只做删除和简化，不做润色。目标是打破LLM输出的统计规律。

用法:
    python humanizer.py --input 正文/第N章.xml --output 正文/第N章_humanized.xml
"""

import re, sys, argparse
from pathlib import Path


def load_text(filepath):
    text = Path(filepath).read_text(encoding="utf-8")
    m = re.search(r"<content>(.*?)</content>", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def save_text(filepath, content, original):
    """保存时保留原始XML结构，只替换content内容。"""
    text = Path(original).read_text(encoding="utf-8")
    new = re.sub(r"<content>.*?</content>", f"<content>\n{content}\n  </content>", text, flags=re.DOTALL)
    Path(filepath).write_text(new, encoding="utf-8")


def humanize(text):
    """核心：破坏LLM写作的统计规律，制造人类的"粗糙感"."""

    lines = text.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # ---- 1. 删除段首的"精致过渡词" ----
        stripped = re.sub(r"^(然而|不过|但是|可是|却|就在这时|突然间|忽然|与此同时|不出所料|果然)", "", stripped)

        # ---- 2. 删除万能状语 ----
        stripped = re.sub(r"猛地|蓦地|倏地|陡然|骤然", "", stripped)
        stripped = re.sub(r"轻轻地|轻轻地|缓缓地|微微地|淡淡地|默默地|悄悄地|静静地|渐渐地", "", stripped)
        stripped = re.sub(r"不禁|不由|忍不住|下意识", "", stripped)

        # ---- 3. 删除"像/如/仿佛/如同"打头的比喻 ----
        stripped = re.sub(r"，?像[^。，！？]{2,20}(一样|一般|似的)?[，。]", "。", stripped)
        stripped = re.sub(r"，?仿佛[^。，！？]{2,20}[，。]", "。", stripped)
        stripped = re.sub(r"，?如[^。，！？]{2,15}般[，。]", "。", stripped)

        # ---- 4. 删除"心中/心里/心底"的情绪描述 ----
        stripped = re.sub(r"心中[一动一紧一沉一酸一暖一痛]", "", stripped)
        stripped = re.sub(r"心里[一]", "", stripped)
        stripped = re.sub(r"心头[一震一紧一暖一酸]", "", stripped)
        stripped = re.sub(r"鼻头一酸|鼻子一酸|眼眶一热|眼睛一酸", "", stripped)

        # ---- 5. 删除"XX感"类抽象名词 ----
        stripped = re.sub(r"一种[^。，！？]{1,10}感", "", stripped)
        stripped = re.sub(r"[了]?某种[^。，！？]{1,10}", "。", stripped)

        # ---- 6. 简化复杂句式 ----
        # "XX是XXX的" -> "XXX了"
        stripped = re.sub(r"是[^。，！？]{3,15}的", "了", stripped)

        # "她/他意识到/发现/感觉/觉得" -> 直接写内容
        stripped = re.sub(r"[她他它]意识到[，：]", "", stripped)
        stripped = re.sub(r"[她他它]发现[，：]", "", stripped)
        stripped = re.sub(r"[她他它][感觉]觉[得到][，：]", "", stripped)

        # ---- 7. 制造"粗糙感"：把长句从中间切开 ----
        if len(stripped) > 30 and "，" in stripped:
            # 50%概率在第一个逗号后切断
            parts = stripped.split("，", 1)
            if len(parts[0]) > 5 and len(parts[0]) < 15:
                stripped = parts[0] + "。" + parts[1]

        # ---- 8. 删除重复的"精致描写" ----
        # "像被冻住一样"类
        stripped = re.sub(r"像被[^。，]{2,10}一样", "", stripped)
        # "仿佛整个世界"类
        stripped = re.sub(r"仿佛[^。，]{2,15}[，。]", "。", stripped)

        result.append(stripped)

    # 合并太短的段落（单句<10字且不是对话/OS）
    merged = []
    for i, line in enumerate(result):
        if i > 0 and len(line) < 15 and not line.startswith(("“", "【", "‘")) and not line.startswith(("她", "他", "乔")):
            merged[-1] += "，" + line
        else:
            merged.append(line)

    return "\n\n".join(merged)


def main():
    parser = argparse.ArgumentParser(description="去AI精致感")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    content = load_text(args.input)
    humanized = humanize(content)
    save_text(args.output, humanized, args.input)

    print(f"原文 {len(content)} 字 → 去精后 {len(humanized)} 字")


if __name__ == "__main__":
    main()
