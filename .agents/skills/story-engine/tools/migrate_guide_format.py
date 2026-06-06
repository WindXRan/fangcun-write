# -*- coding: utf-8 -*-
"""
将旧格式的 guide 文件（分析报告）转换为新格式（指导手册）。

用法：
  python migrate_guide_format.py <蒸馏目录>
  python migrate_guide_format.py <蒸馏目录> --dry-run  # 只显示改动不执行
"""

import sys
import os
import re


def needs_conversion(content):
    """检查是否还是旧格式"""
    old_patterns = [
        '## 一、骨架', '## 二、血肉', '## 三、排除项',
        '## 四、可复用的抽象模式', '## 五、叙事技巧',
        '## 1. 叙事声音与语气', '## 1. 段落钩子',
        '## 1. 角色立体感',
    ]
    for p in old_patterns:
        if p in content:
            return True
    return False


def convert_plot(content):
    """转换 plot_guide 旧格式→新格式"""
    replaces = [
        (r'^## 本章功能\s*\n', '## 写章目标\n'),
        (r'^### 本章功能\s*\n', '## 写章目标\n'),
        (r'^## 一、骨架：情节结构\s*\n', ''),
        (r'^## 二、血肉：情节桥段\s*\n', ''),
        (r'^## 三、排除项\s*\n', '## 写章时必须避开的特征\n'),
        (r'^## 四、可复用的抽象模式\s*\n', '## 写章可套用的公式\n'),
        (r'^## 五、叙事技巧\s*\n', '## 写章时用的叙事技巧\n'),
        (r'^### 情绪曲线\s*\n', '## 写章节奏骨架\n'),
        (r'^### 节奏模式\s*\n', ''),
        (r'^### 钩子设计\s*\n', '## 写章钩子布局\n'),
        (r'^### 核心桥段清单\s*\n', '## 保留功能，换血肉\n'),
        (r'^### 关键场景细节\s*\n', ''),
        (r'^### 关键台词/对话模式\s*\n', ''),
        (r'^### 信息差设计\s*\n', ''),
        (r'^### 悬念机制\s*\n', ''),
        (r'^### 情绪操控\s*\n', ''),
        # 排除项前缀调整
        (r'(模仿了会暴露抄源文的特征)', ''),
        (r'(写新书时必须避开)', ''),
    ]
    for old, new in replaces:
        content = re.sub(old, new, content, flags=re.MULTILINE)

    # 移除空的 --- 分隔线
    content = re.sub(r'\n---\n', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content


def convert_style(content):
    """转换 style_guide 旧格式→新格式"""
    replaces = [
        (r'^## 1. 叙事声音与语气\s*\n', '## 写章时叙事声音\n'),
        (r'^## 2. 对话风格\s*\n', '## 写章时对话写法\n'),
        (r'^## 3. 场景描写特征\s*\n', '## 写章时场景描写\n'),
        (r'^## 4. 转折与衔接手法\s*\n', '## 写章时转折手法\n'),
        (r'^## 5. 节奏特征\s*\n', '## 写章时节奏控制\n'),
        (r'^## 6. 词汇偏好\s*\n', '## 写章时用词偏好\n'),
        (r'^## 7. 情绪表达方式\s*\n', '## 写章时情绪表达\n'),
        (r'^## 8. 独特习惯\s*\n', '## 值得模仿的写法\n'),
    ]
    for old, new in replaces:
        content = re.sub(old, new, content, flags=re.MULTILINE)
    return content


def convert_hook(content):
    """转换 hook_guide 旧格式→新格式"""
    replaces = [
        (r'^## 1. 段落钩子\s*\n', ''),
        (r'^## 2. 章首钩子\s*\n', '## 写章时章首钩子\n'),
        (r'^## 3. 章末钩子\s*\n', '## 写章时章末钩子\n'),
        (r'^## 4. 情绪钩子\s*\n', '## 写章时情绪钩子\n'),
        (r'^## 5. 信息钩子\s*\n', '## 写章时信息钩子\n'),
        (r'^## 6. 反预期钩子\s*\n', '## 写章时反预期钩子\n'),
    ]
    for old, new in replaces:
        content = re.sub(old, new, content, flags=re.MULTILINE)
    return content


def convert_character(content):
    """转换 character_guide 旧格式→新格式"""
    replaces = [
        (r'^## 1. 角色立体感\s*\n', '## 写章时让角色有立体感\n'),
        (r'^## 2. 性格外化技法\s*\n', '## 写章时性格外化\n'),
        (r'^## 3. 角色差异化\s*\n', '## 写章时区分角色\n'),
        (r'^## 4. 配角塑造\s*\n', '## 写章时配角写法\n'),
        (r'^## 5. 角色关系张力\s*\n', '## 写章时角色关系张力\n'),
        (r'^## 6. 角色成长暗示\s*\n', '## 写章时埋角色成长线\n'),
    ]
    for old, new in replaces:
        content = re.sub(old, new, content, flags=re.MULTILINE)
    return content


def convert_file(path):
    """根据文件名判断类型并转换"""
    basename = os.path.basename(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if not needs_conversion(content):
        return None

    old_hash = hash(content)

    if basename.startswith('plot_'):
        content = convert_plot(content)
    elif basename.startswith('style_'):
        content = convert_style(content)
    elif basename.startswith('hook_'):
        content = convert_hook(content)
    elif basename.startswith('character_'):
        content = convert_character(content)
    else:
        return None

    if hash(content) == old_hash:
        return None

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return basename


def main():
    if len(sys.argv) < 2:
        print("用法: python migrate_guide_format.py <蒸馏目录> [--dry-run]")
        sys.exit(1)

    distill_dir = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    if not os.path.isdir(distill_dir):
        print(f"Error: 目录不存在: {distill_dir}")
        sys.exit(1)

    converted = []
    for fname in sorted(os.listdir(distill_dir)):
        if not fname.endswith('.md'):
            continue
        path = os.path.join(distill_dir, fname)
        result = convert_file(path)
        if result:
            converted.append(result)

    if dry_run:
        print(f"[DRY RUN] Files to convert:")
    else:
        print(f"Converted:")

    for f in converted:
        print(f"  [OK] {f}")

    print(f"\nTotal: {len(converted)} files {'(dry-run)' if dry_run else ''}")


if __name__ == '__main__':
    main()
