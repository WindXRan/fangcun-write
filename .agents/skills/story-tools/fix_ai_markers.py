"""批量删除AI路标词"""
import os
import re
import sys
import json
import argparse
from pathlib import Path

# AI路标词列表
AI_MARKERS = [
    '首先', '其次', '然后', '最后',
    '与此同时', '值得注意的是', '此外',
    '不仅', '而且', '虽然', '但是',
    '然而', '因此', '所以', '总之',
    '综上所述', '换句话说', '也就是说',
    '具体来说', '事实上', '实际上',
    '显然', '毫无疑问', '不可否认',
    '从某种意义上', '从某种程度上',
]


def remove_ai_markers(text):
    """删除AI路标词，返回(修改后文本, 删除数量)。"""
    count = 0
    
    for marker in AI_MARKERS:
        # 匹配句首的路标词（前面是换行或句号等标点）
        pattern = r'(?:^|[\n。！？])\s*' + re.escape(marker)
        matches = re.findall(pattern, text)
        if matches:
            count += len(matches)
            # 替换：保留标点，删除路标词
            text = re.sub(pattern, lambda m: m.group()[:1] if m.group() else '', text)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text, count


def process_chapter(ch_file):
    """处理单个章节文件。"""
    text = ch_file.read_text(encoding='utf-8')
    new_text, count = remove_ai_markers(text)
    
    if count > 0:
        ch_file.write_text(new_text, encoding='utf-8')
    
    return count


def main():
    parser = argparse.ArgumentParser(description="批量删除AI路标词")
    parser.add_argument("--config", required=True, help="配置文件")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=101, help="结束章")
    
    args = parser.parse_args()
    
    # 读取配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding='utf-8'))
    chapters_dir = Path(config['rewrites_dir']) / 'chapters'
    
    if not chapters_dir.exists():
        print(f"章节目录不存在: {chapters_dir}")
        sys.exit(1)
    
    print(f"\n{'=' * 50}")
    print(f"批量删除AI路标词 (ch{args.start}-{args.end})")
    print("=" * 50)
    
    total_fixed = 0
    total_markers = 0
    
    for ch in range(args.start, args.end + 1):
        ch_file = chapters_dir / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue
        
        count = process_chapter(ch_file)
        
        if count > 0:
            total_fixed += 1
            total_markers += count
            print(f"  ch{ch:03d}: 删除{count}处AI路标词")
    
    print(f"\n完成：{total_fixed}章被修改，共删除{total_markers}处AI路标词")


if __name__ == "__main__":
    main()
