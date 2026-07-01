"""
quality_checker.py — 方寸仿写代码级质量检查。
与 prompt 级 quality-gate 不同，这个脚本是真正的可执行检查：
- 返回 exit code 0=通过 / 1=阻塞
- 不依赖 LLM，纯代码执行
- 可被 pipeline_runner 调用，实际阻断流程

用法:
    python quality_checker.py check <project_dir> [--chapter N]
    python quality_checker.py audit <project_dir>
    python quality_checker.py scan-names <project_dir> <源文角色名列表>

退出码:
    0 = 全部通过
    1 = 有 P0 阻塞项
"""

import os, sys, re, json, glob, pathlib

EXIT_PASS = 0
EXIT_BLOCK = 1
SOURCE_NAMES = ["乔娇娇", "乔忠国", "乔夫人", "乔天经", "乔地义", "孟谷雪",
                "华大", "刘嬷嬷", "乔府", "乔家", "大雍", "雍帝",
                "左和静", "左夫人", "韩雅弦", "韩明哲", "兖国公",
                "二皇子", "四皇子", "太子沈元湛", "百里承佑", "静王", "镇北军"]

REPORT = {"pass": 0, "warn": 0, "block": 0, "items": []}


def log(level, msg, detail=""):
    REPORT["items"].append({"level": level, "msg": msg, "detail": detail})
    REPORT[level] += 1
    prefix = {"pass": "  ✅", "warn": "  ⚠️", "block": "  🔴"}[level]
    print(f"{prefix} {msg}")
    if detail:
        for line in detail.split("\n"):
            print(f"     {line}")


def get_xml_text(filepath, tag):
    """从 XML 文件中提取指定标签的文本（简单版，不依赖lxml）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 提取第一个匹配标签的内容（支持多行）
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", content, re.DOTALL)
        return m.group(1).strip() if m else ""
    except:
        return ""


def get_character_names(project_dir):
    """读取仿写项目的所有角色卡文件名（不含扩展名）"""
    chars_dir = os.path.join(project_dir, "作品信息", "设定", "角色")
    if not os.path.isdir(chars_dir):
        return set()
    return {os.path.splitext(f)[0] for f in os.listdir(chars_dir) if f.endswith(".xml")}


def check_chapter_source_names(project_dir, chapter_n=None):
    """检查正文和章纲中是否有源文角色名泄露"""
    print("\n── 检查源文角色名泄露 ──")

    if chapter_n:
        patterns = [
            f"正文/章纲/第{chapter_n}章.xml",
            f"正文/正文/第{chapter_n}章.xml",
        ]
    else:
        # 扫描全部已写章节
        patterns = ["正文/章纲/第*.xml", "正文/正文/第*.xml"]

    found_any = False
    for pattern in patterns:
        full_pattern = os.path.join(project_dir, pattern)
        for fpath in glob.glob(full_pattern):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for name in SOURCE_NAMES:
                if name in content:
                    found_any = True
                    fname = os.path.relpath(fpath, project_dir)
                    log("block", f"源文角色名「{name}」出现在 {fname}",
                        f"应替换为仿写对应角色名")

    if not found_any:
        log("pass", "未发现源文角色名泄露" + (f"（第{chapter_n}章）" if chapter_n else "（全部章节）"))
    return not found_any


def check_character_cards(project_dir):
    """检查角色卡完整性：章纲角色都有对应角色卡"""
    print("\n── 检查角色卡完整性 ──")

    char_names = get_character_names(project_dir)
    log("pass", f"共 {len(char_names)} 个角色卡文件")

    # 检查所有章纲的角色引用
    outline_pattern = os.path.join(project_dir, "正文/章纲/第*.xml")
    missing_all = set()
    checked_chapters = 0

    for fpath in glob.glob(outline_pattern):
        content = open(fpath, "r", encoding="utf-8").read()
        # 从 <character> 标签提取角色名
        chars_in_outline = re.findall(r'<character\s+name="([^"]+)"', content)
        if not chars_in_outline:
            continue
        checked_chapters += 1
        for cname in chars_in_outline:
            if cname not in char_names:
                missing_all.add(cname)

    if checked_chapters == 0:
        log("warn", "未找到章纲文件")
        return False

    log("pass", f"扫描了 {checked_chapters} 个章纲")

    if missing_all:
        for name in sorted(missing_all):
            log("block", f"角色卡缺失：{name}",
                f"需在 作品信息/设定/角色/{name}.xml 创建角色卡")
        return False
    else:
        log("pass", "所有出场角色都有角色卡")
        return True


def check_source_mapping(project_dir):
    """检查配角角色卡是否有 source_mapping"""
    print("\n── 检查 source_mapping 完整性 ──")

    chars_dir = os.path.join(project_dir, "作品信息", "设定", "角色")
    if not os.path.isdir(chars_dir):
        log("warn", "角色目录不存在")
        return False

    # 主角名单（可以不需 source_mapping）
    main_chars = {"苏棠", "沈婉", "苏正清", "苏长渊", "苏长泽", "顾北辰"}

    missing = []
    has_mapping = []
    for fname in sorted(os.listdir(chars_dir)):
        if not fname.endswith(".xml"):
            continue
        name = os.path.splitext(fname)[0]
        fpath = os.path.join(chars_dir, fname)
        content = open(fpath, "r", encoding="utf-8").read()
        if "<source_mapping>" in content:
            has_mapping.append(name)
        elif name not in main_chars:
            missing.append(name)

    log("pass", f"{len(has_mapping)} 个角色卡有 source_mapping")

    if missing:
        for name in missing:
            log("warn", f"角色「{name}」缺 source_mapping", "建议添加以保管线映射完整")
        return True  # 不阻塞，只是警告
    else:
        log("pass", "全部必要角色卡都有 source_mapping")
        return True


def check_title_depth(project_dir, chapter_n=None):
    """检查称谓换皮深度：防止'太子/二皇子/四皇子'等源文称谓直接使用"""
    print("\n── 检查称谓换皮深度 ──")

    shallow_titles = {"太子", "二皇子", "四皇子", "三皇子"}

    if chapter_n:
        patterns = [f"正文/正文/第{chapter_n}章.xml", f"正文/章纲/第{chapter_n}章.xml"]
    else:
        patterns = ["正文/正文/第*.xml", "正文/章纲/第*.xml"]

    found = set()
    for pattern in patterns:
        full_pattern = os.path.join(project_dir, pattern)
        for fpath in glob.glob(full_pattern):
            content = open(fpath, "r", encoding="utf-8").read()
            for title in shallow_titles:
                # 检查是否作为独立称谓出现（而非姓名的一部分）
                # "太子"出现但"乾王/宸王/嘉王"没出现 → 浅层换皮
                if re.search(rf'(?<!["\']){title}(?!["\'])', content):
                    found.add(title)

    if found:
        for title in sorted(found):
            log("warn", f"称谓「{title}」与源文相同", "建议换为封号（如太子→乾王/储君）")
        return True  # warning only
    else:
        log("pass", "称谓与源文有区分" + (f"（第{chapter_n}章）" if chapter_n else ""))
        return True


def check_character_consistency(project_dir):
    """检查跨章角色名一致性"""
    print("\n── 检查跨章角色名一致性 ──")

    # 读取各章节正文中的角色称呼
    char_names = get_character_names(project_dir)
    body_pattern = os.path.join(project_dir, "正文/正文/第*.xml")

    name_variants = {}  # 角色名 -> 各章出现的称呼变体
    found_any = False

    for fpath in sorted(glob.glob(body_pattern)):
        fname = os.path.basename(fpath)
        ch_num = re.search(r'第(\d+)章', fname)
        if not ch_num:
            continue
        ch = ch_num.group(1)
        content = open(fpath, "r", encoding="utf-8").read()

        # 检查仿写主角色名是否都在正文中一致使用
        for cname in sorted(char_names):
            # 跳过太短的名字（如单字）避免误报
            if len(cname) <= 1:
                continue
            if cname in content:
                if cname not in name_variants:
                    name_variants[cname] = set()
                name_variants[cname].add(ch)

    # 检查是否有角色在5章以上没出现（针对主角色）
    main_chars = {"苏棠", "沈婉", "苏正清", "苏长渊", "苏长泽"}
    for cname in main_chars:
        if cname in name_variants:
            chapters = sorted(name_variants[cname], key=int)
            log("pass", f"{cname}: 出现在第{','.join(chapters[:5])}...章" if len(chapters) > 5
                else f"{cname}: 出现在第{','.join(chapters)}章")

    return True


def audit(project_dir):
    """全量审计"""
    print("\n" + "=" * 60)
    print("  方寸质量检查 — 全量审计")
    print("=" * 60)

    check_chapter_source_names(project_dir)
    check_character_cards(project_dir)
    check_source_mapping(project_dir)
    check_title_depth(project_dir)
    check_character_consistency(project_dir)

    print_report()


def check(project_dir, chapter_n=None):
    """指定章节检查"""
    mode = f"第{chapter_n}章" if chapter_n else "全部章节"
    print("\n" + "=" * 60)
    print(f"  方寸质量检查 — {mode}")
    print("=" * 60)

    check_chapter_source_names(project_dir, chapter_n)
    if not chapter_n:
        check_character_cards(project_dir)
        check_source_mapping(project_dir)
        check_title_depth(project_dir)
        check_character_consistency(project_dir)
    else:
        check_title_depth(project_dir, chapter_n)

    print_report()


def print_report():
    """输出汇总"""
    total = REPORT["pass"] + REPORT["warn"] + REPORT["block"]
    print(f"\n  ──── 汇总 ────")
    print(f"  ✅ 通过: {REPORT['pass']}  ⚠️ 警告: {REPORT['warn']}  🔴 阻塞: {REPORT['block']}")

    if REPORT["block"] > 0:
        print(f"\n  ❌ 有 {REPORT['block']} 项阻塞，必须先修复")
    elif REPORT["warn"] > 0:
        print(f"\n  ⚠️ 有 {REPORT['warn']} 项警告，建议修复")
    else:
        print(f"\n  ✅ 全部通过")


def scan_names(project_dir, source_names_str):
    """扫描正文中是否包含指定的源文角色名（自定义列表）"""
    names = [n.strip() for n in source_names_str.split(",") if n.strip()]
    if not names:
        print("请提供源文角色名列表，逗号分隔")
        return

    print(f"\n扫描源文角色名: {', '.join(names)}")
    found_any = False

    for pattern in ["正文/正文/第*.xml", "正文/章纲/第*.xml"]:
        full_pattern = os.path.join(project_dir, pattern)
        for fpath in sorted(glob.glob(full_pattern)):
            content = open(fpath, "r", encoding="utf-8").read()
            for name in names:
                if name in content:
                    found_any = True
                    fname = os.path.relpath(fpath, project_dir)
                    print(f"  🔴 {fname}: 发现「{name}」")

    if not found_any:
        print("  ✅ 未发现源文角色名")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法:")
        print("  python quality_checker.py check <project_dir> [--chapter N]")
        print("  python quality_checker.py audit <project_dir>")
        print("  python quality_checker.py scan-names <project_dir> <源文角色名,逗号分隔>")
        sys.exit(EXIT_PASS)

    mode = sys.argv[1]
    project_dir = sys.argv[2]

    if not os.path.isdir(project_dir):
        print(f"项目目录不存在: {project_dir}")
        sys.exit(EXIT_BLOCK)

    if mode == "check":
        chapter_n = None
        if "--chapter" in sys.argv:
            idx = sys.argv.index("--chapter")
            if idx + 1 < len(sys.argv):
                chapter_n = sys.argv[idx + 1]
        check(project_dir, chapter_n)
    elif mode == "audit":
        audit(project_dir)
    elif mode == "scan-names":
        names_str = sys.argv[3] if len(sys.argv) > 3 else ""
        scan_names(project_dir, names_str)
    else:
        print(f"未知模式: {mode}")
        sys.exit(EXIT_BLOCK)

    sys.exit(EXIT_BLOCK if REPORT["block"] > 0 else EXIT_PASS)
