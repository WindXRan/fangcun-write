"""从蒸馏目录的 plot_guide_*.md 提取全书情节概览。

用法: python extract_plot_overview.py <蒸馏目录> <输出文件>

示例: python extract_plot_overview.py novel-download-authors/闻栖/分手了？秦少火速领证上位/蒸馏/mode-b/ 仿写/分手当天，我嫁给了前任的死对头/设定/plot_overview.md
"""

import sys, os, re, glob


def read_file(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def extract_field(text, header):
    """提取某个 ## 标题下的内容，直到下一个 ## 或文件结束。"""
    pattern = rf'^##\s*{re.escape(header)}\s*$'
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        return ''
    start = m.end()
    # 找下一个 ## 标题
    m2 = re.search(r'^##\s+', text[start:], re.MULTILINE)
    end = start + m2.start() if m2 else len(text)
    return text[start:end].strip()


def extract_table(text, header):
    """提取某个 ## 标题下的表格内容。"""
    content = extract_field(text, header)
    # 只保留表格行
    lines = [l for l in content.split('\n') if l.strip().startswith('|')]
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 3:
        print('用法: python extract_plot_overview.py <蒸馏目录> <输出文件>')
        sys.exit(1)

    distill_dir = sys.argv[1]
    output_path = sys.argv[2]

    # 找所有 plot_guide_*.md
    pattern = os.path.join(distill_dir, 'plot_guide_*.md')
    files = sorted(glob.glob(pattern), key=lambda f: int(re.search(r'(\d+)', os.path.basename(f)).group(1)))

    if not files:
        print(f'未找到 plot_guide_*.md: {pattern}')
        sys.exit(1)

    print(f'找到 {len(files)} 个 plot_guide 文件')

    chapters = []
    all_exclusions = []
    all_formulas = {'爽点': [], '虐点': [], '悬念': [], '情绪操控': []}

    for f in files:
        ch_num = int(re.search(r'(\d+)', os.path.basename(f)).group(1))
        text = read_file(f)

        # 提取本章功能
        func = extract_field(text, '本章功能')
        if not func:
            # 尝试从 "### 本章功能" 提取
            m = re.search(r'###\s*本章功能\s*\n(.+?)(?=\n###|\n---|\Z)', text, re.DOTALL)
            func = m.group(1).strip() if m else ''

        # 提取情绪曲线
        emotion = ''
        m = re.search(r'###\s*情绪曲线\s*\n(.+?)(?=\n###|\n---|\Z)', text, re.DOTALL)
        if m:
            emotion = m.group(1).strip()

        # 提取排除项
        exclusions = extract_field(text, '排除项')
        if exclusions:
            for line in exclusions.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('*') or re.match(r'^\d+\.', line)):
                    all_exclusions.append(f'第{ch_num}章: {line}')

        # 提取可复用的抽象模式
        formulas = extract_field(text, '可复用的抽象模式')
        if formulas:
            for key in all_formulas:
                m = re.search(rf'{key}公式[：:]\s*(.+)', formulas)
                if m:
                    all_formulas[key].append(f'第{ch_num}章: {m.group(1).strip()}')

        chapters.append({
            'num': ch_num,
            'func': func[:200] if func else '（未提取到）',
            'emotion': emotion[:300] if emotion else '（未提取到）',
        })

    # 生成输出
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    out = []
    out.append('# 情节概览')
    out.append(f'> 共 {len(chapters)} 章')
    out.append('')

    # 一、情节主线
    out.append('## 一、情节主线')
    out.append('')
    for ch in chapters:
        out.append(f'- 第{ch["num"]}章 - {ch["func"]}')
    out.append('')

    # 二、情绪曲线摘要
    out.append('## 二、情绪曲线摘要')
    out.append('')
    for ch in chapters:
        out.append(f'### 第{ch["num"]}章')
        out.append(ch['emotion'])
        out.append('')

    # 三、排除项汇总
    out.append('## 三、排除项汇总')
    out.append('')
    if all_exclusions:
        for ex in all_exclusions:
            out.append(f'- {ex}')
    else:
        out.append('（无）')
    out.append('')

    # 四、可复用的抽象模式
    out.append('## 四、可复用的抽象模式')
    out.append('')
    for key, items in all_formulas.items():
        out.append(f'### {key}公式')
        out.append('')
        if items:
            for item in items:
                out.append(f'- {item}')
        else:
            out.append('（无）')
        out.append('')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    print(f'已生成: {output_path} ({len(chapters)} 章)')


if __name__ == '__main__':
    main()
