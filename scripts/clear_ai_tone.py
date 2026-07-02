#!/usr/bin/env python3
"""
AI腔自动清除脚本 — 批量修复仿写正文中的AI生成特征。
用法: python3 clear_ai_tone.py <项目目录> [起始章] [结束章]
"""

import sys, re, os
from pathlib import Path

PROJ = sys.argv[1] if len(sys.argv) > 1 else "projects/仿写新书"
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
END = int(sys.argv[3]) if len(sys.argv) > 3 else 999

BASE = Path(PROJ) / "正文" / "正文"

# ─── 修复规则（按优先级）──────────────────────────────────────────────

RULES = [

    # P0: 系统游戏化表达 → 内心感知
    (
        r"她低头瞄了一眼——[^。]{0,60}系统[^。]{0,60}一闪而过[^。]{0,30}",
        lambda m: "她心里忽然一紧" + re.search(r"命运|不对|问题|不安", m.group(0)).group(0) if re.search(r"命运|不对|问题|不安", m.group(0)) else "她心里忽然觉得不对",
        "系统游戏化 → 内心感知"
    ),
    (
        r"系统界面在视野边缘闪了一下",
        "她心里忽然一紧",
        "系统游戏化 → 内心感知"
    ),
    (
        r"屏幕上只剩[^。]{0,40}波纹在闪烁",
        "脑子里那点灵力已经见底了",
        "系统游戏化 → 自然叙述"
    ),

    # P1: "不是A，而是B" 对比句式
    (
        r"不是(\S{1,8})，而是(\S{1,12})",
        lambda m: m.group(1) + "？" + m.group(2) + "。",
        "对比句式 → 直接叙述"
    ),
    (
        r"不是(\S{1,8})是(\S{1,12})",
        lambda m: m.group(1) + "？" + m.group(2) + "。",
        "对比句式 → 直接叙述"
    ),

    # P2: "带着……的……" 啰嗦表达
    (
        r"带着(\S{1,6})的(\S{1,8})",
        lambda m: m.group(1) + "的" + m.group(2),
        "带着…的… → 直接定语"
    ),
    (
        r"带着(\S{1,10})",
        lambda m: m.group(1),
        "带着 → 删掉"
    ),

    # P3: "这种方法……" "这个办法……" 解释性废话
    (
        r"这种方法\S{0,10}",
        "",
        "解释性废话 → 删除"
    ),
    (
        r"这个办法\S{0,10}",
        "",
        "解释性废话 → 删除"
    ),

    # P4: 过于工整的排比句（3个以上并列"容易…更容易…最…"）
    (
        r"容易(\S{1,8})，容易(\S{1,8})，更(\S{1,8})",
        lambda m: m.group(1) + "，" + m.group(2) + "，还会" + m.group(3),
        "工整排比 → 打乱"
    ),

    # P5: 书面语副词
    (
        r"缓缓地",
        "慢慢",
        "书面副词 → 口语"
    ),
    (
        r"轻轻地",
        "轻轻",
        "书面副词 → 口语"
    ),
    (
        r"默默地",
        "",
        "书面副词 → 删除"
    ),

    # P6: 经典AI cliché
    (
        r"嘴角扯出一个不像笑的笑",
        "嘴角动了一下",
        "AI cliché → 自然表达"
    ),
    (
        r"嘴角扯了扯，算不上笑",
        "嘴角动了一下",
        "AI cliché → 自然表达"
    ),
    (
        r"孤零零的影子",
        "影子拖得老长",
        "AI cliché → 自然表达"
    ),
    (
        r"佝偻着，\S{1,4}着",
        lambda m: "背弓着" + ("，" + m.group(0).split("，")[-1] if "，" in m.group(0) else ""),
        "语法错误 → 修正"
    ),

    # P7: 章末总结体（"她在心里快速比较——" 之类的过渡）
    (
        r"\n\n她在心里快速比较[^\n]{0,50}\n\n",
        "\n\n",
        "章末总结 → 切场景"
    ),

    # P8: 过度使用破折号（——）连接解释，AI特别爱用
    (
        r"(\S{1,15})——(\S{1,20})——",
        lambda m: m.group(1) + "，" + m.group(2),
        "破折号过度 → 改逗号"
    ),

    # P9: "分明…" 确定性过度表达
    (
        r"分明(\S{1,3})",
        lambda m: "明明" + m.group(1),
        "分明 → 明明（更口语）"
    ),

    # P10: 游戏数值表达（"见底""只剩X点"）
    (
        r"灵力已经见底",
        "那点灵力已经用完了",
        "游戏表达 → 自然叙述"
    ),
    (
        r"屏幕上只剩[^。]{0,40}",
        "脑子里一阵空",
        "游戏界面 → 内心感知"
    ),

    # P11: 多余的"方才""刚刚"重复
    (
        r"方才\S{0,5}刚刚",
        "方才",
        "重复时间词 → 精简"
    ),

    # P12: "一字不差" "分毫不差" 等AI爱用的精确描述
    (
        r"一字不差",
        "一模一样",
        "AI精确词 → 口语"
    ),
    (
        r"分毫不差",
        "一点不差",
        "AI精确词 → 口语"
    ),

    # P13: "她在原著中太清楚…" 过于书面
    (
        r"她在原著中太清楚",
        "她太清楚原著里",
        "书面语序 → 口语语序"
    ),

    # P14: 修复"瘦削着"这类语法错误
    (
        r"瘦削着",
        "瘦得很",
        "语法错误 → 修正"
    ),
    (
        r"发白着",
        "发白",
        "语法错误 → 修正"
    ),

    # P15: "转瞬" → "转眼"
    (
        r"转瞬",
        "转眼",
        "书面词 → 口语词"
    ),

    # P16: 删除多余的"恰好""正好"堆砌
    (
        r"恰好\S{0,3}正好",
        "正好",
        "副词堆砌 → 精简"
    ),

    # P17: "不由得" → "忍不住"
    (
        r"不由得",
        "忍不住",
        "书面词 → 口语词"
    ),

    # P18: 修复"找不出" → "看不出"
    (
        r"找不出一丝",
        "看不出一丝",
        "动词误用 → 修正"
    ),

    # P19: "故作娇羞" → 更自然的表达
    (
        r"故作娇羞",
        "装出一副害羞的样子",
        "书面语 → 口语"
    ),

    # P20: 修复"悄无声息"等AI高频词
    (
        r"悄无声息",
        "一点声音都没有",
        "AI高频词 → 口语"
    ),
]

# ─── 执行修复 ─────────────────────────────────────────────────────────────────

def fix_chapter(path: Path, ch_num: int):
    text = path.read_text(encoding="utf-8")
    original_len = len(text)
    fixes_applied = []

    content_start = text.find("<content>")
    content_end = text.find("</content>")
    if content_start == -1 or content_end == -1:
        return 0, []

    pre = text[:content_start + len("<content>")]
    content = text[content_start + len("<content>"):content_end]
    post = text[content_end:]

    for pattern, replacement, desc in RULES:
        if callable(replacement):
            matches = list(re.finditer(pattern, content))
            for m in matches:
                try:
                    new_text = replacement(m)
                    content = content[:m.start()] + new_text + content[m.end():]
                    fixes_applied.append(desc)
                except:
                    pass
        else:
            count = 0
            while pattern in content:
                content = content.replace(pattern, replacement, 1)
                count += 1
            if count > 0:
                fixes_applied.extend([desc] * count)

    new_text = pre + content + post
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")

    return len(fixes_applied), fixes_applied


def main():
    print(f"AI腔清除脚本 — {PROJ}")
    print(f"章节范围: {START} ~ {END}\n")

    total_fixes = 0
    chapters_fixed = 0

    for ch in range(START, END + 1):
        for ext in ("", ".xml"):
            p = BASE / f"第{ch}章{ext}"
            if p.exists():
                n, fixes = fix_chapter(p, ch)
                if n > 0:
                    chapters_fixed += 1
                    total_fixes += n
                    print(f"  第{ch}章: {n}处修复")
                    for f in set(fixes):
                        print(f"    - {f}")
                break
        else:
            if ch <= 99:
                print(f"  第{ch}章: 未找到文件")

    print(f"\n完成: {chapters_fixed}章, 共{total_fixes}处修复")


if __name__ == "__main__":
    main()
