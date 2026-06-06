# -*- coding: utf-8 -*-
"""
校验 guide 文件是否符合"指导手册"格式。

用法：
  python verify_guide_format.py <蒸馏目录>
  python verify_guide_format.py <蒸馏目录> --strict  # 严格模式，禁止"原文"等词
"""

import sys
import os
import re

BANNED_WORDS = ['源文', '原文']
REQUIRED_PREFIX = ['写章时', '仿写时', '写章可', '写章必须', '写章目标', '保留功能']


def check_file(path, strict=False):
    """检查单个 guide 文件，返回问题列表"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []
    basename = os.path.basename(path)

    # 跳过不含 guide 字段的文件（如 style_profile_1.json）
    lines = content.split('\n')

    # 1. 检查敏感词
    if strict:
        for word in BANNED_WORDS:
            for i, line in enumerate(lines, 1):
                if word in line and not line.strip().startswith('> 来源'):
                    issues.append(f'  {basename}:{i} 出现禁止词"{word}" → {line.strip()[:60]}')

    # 2. 统计"写章时/仿写时"出现次数
    instruction_count = sum(1 for line in lines if any(line.startswith(p) for p in REQUIRED_PREFIX))
    if instruction_count < 3:
        issues.append(f'  {basename}: 只有{instruction_count}条指令（至少需要3条"写章时/仿写时"）')

    # 3. 检查排除项
    if 'plot_' in basename and '排除项' not in content:
        issues.append(f'  {basename}: missing排除项')

    return issues


def main():
    if len(sys.argv) < 2:
        print("用法: python verify_guide_format.py <蒸馏目录> [--strict]")
        sys.exit(1)

    distill_dir = sys.argv[1]
    strict = '--strict' in sys.argv

    if not os.path.isdir(distill_dir):
        print(f"Error: 目录不存在: {distill_dir}")
        sys.exit(1)

    total_issues = 0
    checked = 0
    for fname in sorted(os.listdir(distill_dir)):
        if not fname.endswith('.md') or not any(g in fname for g in ['guide']):
            continue
        path = os.path.join(distill_dir, fname)
        issues = check_file(path, strict)
        checked += 1
        for issue in issues:
            print(issue)
            total_issues += 1

    print(f"\n检查 {checked} 个文件，发现 {total_issues} 个问题")


if __name__ == '__main__':
    main()
