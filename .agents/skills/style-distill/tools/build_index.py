"""构建场景索引：从 knowledge_base/chapters/ 提取标签，生成 index.json。"""

import os
import re
import json
from pathlib import Path


def extract_metadata(text):
    """从场景片段的元数据区域提取结构化信息。"""
    meta = {}
    # 找到 --- 后面的元数据区域
    if "---" in text:
        meta_text = text.split("---")[-1]
    else:
        meta_text = text[-500:]  # fallback: 最后500字

    for line in meta_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        m = re.match(r'[-•]\s*(.+?)[:：]\s*(.+)', line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            meta[key] = val

    return meta


def extract_tags_from_content(text, meta):
    """从内容和元数据中提取标签。"""
    tags = set()

    # 从"情节类型"提取
    scene_type = meta.get("情节类型", "")
    if scene_type:
        for t in re.split(r'[/、,，]', scene_type):
            t = t.strip()
            if t:
                tags.add(t)

    # 从"关键词"提取
    keywords = meta.get("关键词", "")
    if keywords:
        for kw in re.findall(r'[\u4e00-\u9fff]+', keywords):
            if len(kw) >= 2:
                tags.add(kw)

    # 从内容特征推断标签
    content_lower = text.lower()

    # 情绪标签
    emotion_patterns = {
        "搞笑": ["哈哈", "笑死", "噗", "搞笑", "逗", "乐"],
        "愤怒": ["骂", "怒", "吼", "摔", "打", "揍"],
        "温情": ["暖", "感动", "泪", "心疼", "温柔"],
        "紧张": ["慌", "怕", "紧张", "心跳", "发抖"],
        "打脸": ["打脸", "啪", "嚣张", "嘲笑", "反击"],
        "吵架": ["骂", "怼", "吵", "互怼", "毒舌"],
        "撒娇": ["撒娇", "妈妈", "求", "哄"],
    }
    for tag, patterns in emotion_patterns.items():
        if any(p in text for p in patterns):
            tags.add(tag)

    # 场景类型标签
    scene_patterns = {
        "家庭": ["家", "妈", "爸", "奶奶", "姥姥"],
        "校园": ["学校", "老师", "同学", "教室", "上课"],
        "日常": ["吃饭", "逛街", "睡觉", "做饭"],
        "冲突": ["冲突", "对峙", "打架", "争吵"],
        "对话": ["说", "问", "答", "喊"],
    }
    for tag, patterns in scene_patterns.items():
        if any(p in text for p in patterns):
            tags.add(tag)

    return sorted(tags)


def build_index(styles_dir):
    """构建场景索引。"""
    styles_dir = Path(styles_dir)
    scenes_dir = styles_dir / "knowledge_base" / "chapters"

    if not scenes_dir.exists():
        print(f"  [FAIL] scenes 目录不存在: {scenes_dir}")
        return None

    # 从目录名提取作者和书名
    # 结构: .agents/styles/{作者}/{书名}/ 或 .agents/skills/style-{作者}/
    parts = styles_dir.parts
    author = ""
    book = ""
    for i, p in enumerate(parts):
        if p.startswith("style-"):
            author = p.replace("style-", "")
        elif p == "styles" and i + 2 < len(parts):
            author = parts[i + 1]
            book = parts[i + 2]

    scenes = []
    for f in sorted(scenes_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        meta = extract_metadata(text)
        tags = extract_tags_from_content(text, meta)

        # 解析章节号和场景号
        m = re.match(r'ch(\d+)_scene(\d+)', f.stem)
        ch_num = int(m.group(1)) if m else 0
        scene_num = int(m.group(2)) if m else 0

        scenes.append({
            "id": f"{author}/{book}/{f.stem}" if author and book else f.stem,
            "author": author,
            "book": book,
            "chapter": ch_num,
            "scene": scene_num,
            "file": str(f.relative_to(styles_dir)),
            "tags": tags,
            "keywords": meta.get("关键词", ""),
            "scene_desc": meta.get("场景描述", ""),
            "chars": len(re.sub(r'\s', '', text)),
        })

    # 构建索引
    index = {
        "author": author,
        "book": book,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }

    # 写入 index.json
    index_path = styles_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [OK] index.json: {len(scenes)} scenes")

    # 统计标签
    tag_counts = {}
    for s in scenes:
        for t in s["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:20]
    print(f"  Top tags: {', '.join(f'{t}({c})' for t, c in top_tags)}")

    return index


def main():
    import argparse
    parser = argparse.ArgumentParser(description="构建场景索引")
    parser.add_argument("styles_dir", help="风格数据目录")
    args = parser.parse_args()

    build_index(args.styles_dir)


if __name__ == "__main__":
    main()
