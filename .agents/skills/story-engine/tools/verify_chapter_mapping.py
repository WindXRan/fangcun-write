# -*- coding: utf-8 -*-
"""
校验章节顺序映射的正确性。

检查：
1. 映射不能重复（两个新书章映射到同一个源文章）
2. 映射的源文章号在蒸馏目录中有对应的 plot_guide
3. 所有新书章都有映射
4. 源文章号按顺序递增（允许跳号，不允许倒序）

用法：
  python verify_chapter_mapping.py <章节顺序.md> <蒸馏目录>
"""

import sys
import os
import re


def parse_mapping(mapping_path):
    """解析章节顺序.md，返回映射列表"""
    mappings = []
    with open(mapping_path, 'r', encoding='utf-8') as f:
        text = f.read()

    in_table = False
    for line in text.split('\n'):
        if '|' not in line:
            in_table = False
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) < 3:
            continue
        if cells[0] == '新书章号' or line.strip().startswith('|---'):
            in_table = True
            continue
        if not in_table:
            continue

        new_ch = cells[0]
        src_ch = cells[1]
        func = cells[2] if len(cells) > 2 else ''

        # 解析章号（支持"1"和"第1章"格式）
        new_num = None
        m = re.search(r'\d+', new_ch)
        if m:
            new_num = int(m.group())

        src_num = None
        m = re.search(r'\d+', src_ch)
        if m:
            src_num = int(m.group())

        if new_num and src_num:
            mappings.append((new_num, src_num, func))

    return mappings


def main():
    if len(sys.argv) < 3:
        print("用法: python verify_chapter_mapping.py <章节顺序.md> <蒸馏目录>")
        sys.exit(1)

    mapping_path = sys.argv[1]
    distill_dir = sys.argv[2]

    if not os.path.isfile(mapping_path):
        print(f"Error: 章节顺序文件不存在: {mapping_path}")
        sys.exit(1)
    if not os.path.isdir(distill_dir):
        print(f"Error: 蒸馏目录不存在: {distill_dir}")
        sys.exit(1)

    mappings = parse_mapping(mapping_path)
    if not mappings:
        print("Error: 没解析到任何映射")
        sys.exit(1)

    print(f"解析到 {len(mappings)} 个映射")

    issues = []

    # 1. 检查重复源文映射
    src_to_new = {}
    for new_n, src_n, func in mappings:
        if src_n in src_to_new:
            issues.append(f"[ERROR] 源文第{src_n}章映射到多个新书章: 第{src_to_new[src_n]}章 和 第{new_n}章")
        src_to_new[src_n] = new_n

    # 2. 检查 plot_guide 是否存在
    for new_n, src_n, func in mappings:
        guide_path = os.path.join(distill_dir, f'plot_guide_{src_n}.md')
        if not os.path.isfile(guide_path):
            issues.append(f"[WARN] 新书第{new_n}章→源文第{src_n}章，但 plot_guide_{src_n}.md 不存在")

    # 3. 检查序列完整性
    new_nums = sorted([m[0] for m in mappings])
    for i in range(1, len(new_nums)):
        if new_nums[i] - new_nums[i-1] != 1:
            issues.append(f"[WARN] 新书章号不连续: 第{new_nums[i-1]}章→第{new_nums[i]}章（跳过{new_nums[i] - new_nums[i-1] - 1}章）")

    # 4. 检查是否按源文章号顺序（允许跳号）
    last_src = 0
    for new_n, src_n, func in sorted(mappings, key=lambda x: x[0]):
        if src_n < last_src:
            issues.append(f"[WARN] 源文章号倒序: 新书第{new_n}章→源文第{src_n}章，但上一章源文第{last_src}章")
        last_src = src_n

    if not issues:
        print("\n全部通过，无问题")
    else:
        print(f"\n发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  {issue}")


if __name__ == '__main__':
    main()
