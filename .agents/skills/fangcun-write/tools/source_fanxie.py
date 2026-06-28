"""
仿写换皮引擎：基于 mapping.xml 做纯文本替换。
LLM 不参与此步骤，0% 出错率。

用法:
    from source_fanxie import fanxie_replace, verify_no_leak
    replaced = fanxie_replace(source_text, project_dir)
    leaks = verify_no_leak(replaced, project_dir)
"""

import re, xml.etree.ElementTree as ET
from pathlib import Path


def load_all_mappings(project_dir: str) -> dict:
    """加载 mapping.xml 全部映射类别，返回 {cat: {source: target}}"""
    mapping_file = Path(project_dir) / "作品信息" / "mapping.xml"
    if not mapping_file.exists():
        return {}

    tree = ET.parse(mapping_file)
    root = tree.getroot()
    result = {}

    for cat_elem in root:
        cat = cat_elem.tag  # characters, scenes, items, concepts
        if cat_elem.tag in ("description",):
            continue
        mapping = {}
        for pair in cat_elem.findall("pair"):
            s = pair.get("source", "").strip()
            t = pair.get("target", "").strip()
            if s and t:
                mapping[s] = t
        if mapping:
            result[cat] = mapping

    return result


def fanxie_replace(text: str, project_dir: str) -> str:
    """对源文做换皮替换，返回替换后的文本。

    替换顺序:
    1. 先角色名（长名字先替换，避免子串匹配）
    2. 再场景名
    3. 再物品名
    4. 再通用概念
    """
    mappings = load_all_mappings(project_dir)
    if not mappings:
        return text

    result = text

    # 优先级顺序：角色 > 场景 > 物品 > 概念
    for cat in ["characters", "scenes", "items", "concepts"]:
        mapping = mappings.get(cat, {})
        for s in sorted(mapping.keys(), key=len, reverse=True):
            result = result.replace(s, mapping[s])

    return result


def verify_no_leak(text: str, project_dir: str) -> list:
    """检查替换后的文本是否还有源文角色名/场景名。返回泄漏列表。"""
    mappings = load_all_mappings(project_dir)
    source_terms = []
    for cat, mapping in mappings.items():
        source_terms.extend(mapping.keys())

    leaks = []
    for s in sorted(source_terms, key=len, reverse=True):
        if s in text:
            leaks.append(s)
    return leaks


def audit_source_entities(project_dir: str, source_dir: str, max_chapters: int = 30):
    """扫描源文找出所有未映射的实体。"""
    import glob
    mappings = load_all_mappings(project_dir)
    all_mapped_sources = set()
    for m in mappings.values():
        all_mapped_sources.update(m.keys())

    text = ''
    for ch in range(1, max_chapters + 1):
        files = glob.glob(f"{source_dir}/正文/正文/第{ch}章*.txt")
        if files:
            text += open(files[0], encoding='utf-8').read()

    # 找已知实体但未映射的
    known = {
        '角色': ['林哲', '杨雪', '许欣', '武喆', '田龙', '吴义气', '萧红玉', '许富发', '田雯', '马丽霞', '韦德胜', '王忆苦', '何建', '李一'],
        '场景': ['帝都', '北京', '朝阳', '百子湾', '十八里店', '雁北', '面馆', '拉面馆', '望京', '工体', '羊城', '龙洞村', '路边摊', '酒吧', '饭店', '酒店', '医院', '出租屋'],
        '物品': ['北冰洋', '黑金卡', '百达翡丽', '路易十三'],
    }

    missing = {}
    for cat, items in known.items():
        not_mapped = [i for i in items if i in text and i not in all_mapped_sources]
        if not_mapped:
            missing[cat] = not_mapped

    return missing


if __name__ == "__main__":
    import sys, glob
    cmd = sys.argv[1] if len(sys.argv) > 1 else "replace"

    if cmd == "replace":
        project_dir = sys.argv[2] if len(sys.argv) > 2 else "projects/提笔忘章节/我真是海鲜大亨？身份都是自己给的"
        src = sys.argv[3] if len(sys.argv) > 3 else "projects/提笔忘章节/我冒充富二代？身份都是自己给的"
        ch = int(sys.argv[4]) if len(sys.argv) > 4 else 1

        files = glob.glob(f"{src}/正文/正文/第{ch}章*.txt")
        if not files:
            print(f"第{ch}章不存在")
            exit(1)

        text = open(files[0], encoding="utf-8").read()
        replaced = fanxie_replace(text, project_dir)
        leaks = verify_no_leak(replaced, project_dir)

        print(f"替换完成 | 输入{len(text)}字 → 输出{len(replaced)}字")
        if leaks:
            print(f"⚠️ 泄漏({len(leaks)}处): {leaks}")
        else:
            print("✅ 换皮完整，无泄漏")

        out_dir = Path(project_dir) / "_fanxie"
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"第{ch}章.md").write_text(replaced, encoding="utf-8")
        print(f"保存到: {out_dir / f'第{ch}章.md'}")

    elif cmd == "audit":
        project_dir = sys.argv[2] if len(sys.argv) > 2 else "projects/提笔忘章节/我真是海鲜大亨？身份都是自己给的"
        source_dir = sys.argv[3] if len(sys.argv) > 3 else "projects/提笔忘章节/我冒充富二代？身份都是自己给的"
        missing = audit_source_entities(project_dir, source_dir)
        if missing:
            print("未映射的实体:")
            for cat, items in missing.items():
                print(f"  {cat}: {items}")
        else:
            print("✅ 全部实体已映射")
