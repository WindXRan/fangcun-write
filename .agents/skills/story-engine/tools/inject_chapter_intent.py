# -*- coding: utf-8 -*-
"""
为 plot_guide_N.md 注入章节意图字段。
从全书弧线.md 解析弧线分段+伏笔数据，逐章映射到 plot_guide。

用法：
  python inject_chapter_intent.py <全书弧线.md> <蒸馏目录>
"""

import sys
import os
import re

def parse_arc_sections(text):
    """解析弧线各段落的章节范围"""
    sections = []
    in_table = False
    headers = []
    for line in text.split('\n'):
        if line.startswith('| 章范围') or line.startswith('|---'):
            continue
        if line.startswith('|') and not in_table:
            in_table = True
        if in_table and line.startswith('|') and '|' in line[1:]:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) >= 4:
                sections.append(cells)
        elif in_table and not line.startswith('|'):
            in_table = False
    return sections

def parse_table_rows(text, table_headers):
    """解析 markdown 表格的行"""
    rows = []
    in_table = False
    found_header = False
    for line in text.split('\n'):
        if '|' not in line:
            in_table = False
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) < 2:
            continue
        # 跳过表头
        if any(h in cells[0] for h in table_headers):
            found_header = True
            continue
        if line.strip().startswith('|---'):
            continue
        if found_header and cells[0] and not cells[0].startswith('（'):
            rows.append(cells)
    return rows

def parse_chapter_range(range_str):
    """解析章范围如 '1-10' 或 '1'"""
    m = re.match(r'(\d+)\s*-\s*(\d+)', range_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r'(\d+)', range_str)
    if m:
        return int(m.group(1)), int(m.group(1))
    return None, None

def _extract_table_rows(text, start_marker, end_markers, skip_header, min_cols):
    """从 markdown 文本中提取表格行，支持任意列数"""
    rows = []
    in_section = False
    for line in text.split('\n'):
        if start_marker in line:
            in_section = True
            continue
        if in_section and any(e in line for e in end_markers):
            break
        if not in_section:
            continue
        if '|' not in line or line.strip().startswith('|---'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) < min_cols:
            continue
        if any(h in cells[0] for h in skip_header):
            continue
        rows.append(cells)
    return rows


def parse_arc(arc_path):
    """解析全书弧线.md, 返回结构化数据"""
    with open(arc_path, 'r', encoding='utf-8') as f:
        text = f.read()

    data = {
        'segments': [],
        'char_male': [],
        'char_female': [],
        'foreshadows': [],
        'turning_points': [],
    }

    # 情感曲线
    emotion_rows = _extract_table_rows(text, '全书情感曲线',
        ['角色成长主线', '核心伏笔清单', '关键转折点', '##'], ['章范围'], 4)
    for cells in emotion_rows:
        start, end = parse_chapter_range(cells[0])
        if start:
            data['segments'].append({
                'start': start, 'end': end or start,
                'emotion': cells[1] if len(cells) > 1 else '',
                'intensity': cells[2] if len(cells) > 2 else '',
                'function': cells[3] if len(cells) > 3 else '',
                'reason': cells[4] if len(cells) > 4 else cells[3] if len(cells) > 3 else ''
            })

    # 角色成长主线（按子表解析：男女主分开）
    char_sections = re.split(r'(?=###\s*(?:男主|女主))', text)
    for sec in char_sections:
        if '男主' in sec[:20]:
            rows = _extract_table_rows(sec, '男主', ['###', '##'], ['阶段', '男主'], 2)
            for cells in rows:
                start, end = parse_chapter_range(cells[0])
                if start:
                    data['char_male'].append({
                        'start': start, 'end': end or start,
                        'state': cells[1] if len(cells) > 1 else '',
                        'turning': cells[2] if len(cells) > 2 else ''
                    })
        elif '女主' in sec[:20]:
            rows = _extract_table_rows(sec, '女主', ['###', '##'], ['阶段', '女主'], 2)
            for cells in rows:
                start, end = parse_chapter_range(cells[0])
                if start:
                    data['char_female'].append({
                        'start': start, 'end': end or start,
                        'state': cells[1] if len(cells) > 1 else '',
                        'turning': cells[2] if len(cells) > 2 else ''
                    })

    # 伏笔清单
    fb_rows = _extract_table_rows(text, '核心伏笔清单',
        ['关键转折点', '##'], ['伏笔'], 2)
    for cells in fb_rows:
        data['foreshadows'].append({
            'content': cells[0],
            'bury': cells[1] if len(cells) > 1 else '',
            'retrieve': cells[2] if len(cells) > 2 else '',
            'priority': cells[3] if len(cells) > 3 else ''
        })

    # 关键转折点
    tp_rows = _extract_table_rows(text, '关键转折点',
        ['##'], ['章节'], 2)
    for cells in tp_rows:
        ch, _ = parse_chapter_range(cells[0])
        if ch:
            data['turning_points'].append({
                'chapter': ch,
                'event': cells[1] if len(cells) > 1 else '',
                'function': cells[2] if len(cells) > 2 else ''
            })

    return data

def find_segment(chapter, segments):
    """找到章节所属的弧线段"""
    for seg in segments:
        if seg['start'] <= chapter <= seg['end']:
            return seg
    print(f"  [WARN] 第{chapter}章未找到匹配的弧线段，使用最后一段")
    return segments[-1] if segments else None

def find_foreshadows(chapter, foreshadows):
    """找到该章节应该埋设和回收的伏笔"""
    bury = []
    retrieve = []
    for f in foreshadows:
        if f['bury'] and chapter in parse_stages(f['bury']):
            bury.append(f['content'])
        if f['retrieve'] and chapter in parse_stages(f['retrieve']):
            retrieve.append(f['content'])
    return bury, retrieve

def parse_stages(stage_str):
    """解析阶段描述如 '第1-5章', '1-5', '第3章', '第1、3、5章' 返回章节号列表"""
    chapters = set()
    # 移除"章"字和各种分隔符
    cleaned = stage_str.replace('章', '').replace(' ', '').replace('、', ',').replace('，', ',')
    parts = cleaned.split(',')
    for part in parts:
        if not part:
            continue
        # 1-5 或 第1-5
        m = re.match(r'第?\s*(\d+)\s*[-~–]\s*(\d+)', part)
        if m:
            for i in range(int(m.group(1)), int(m.group(2)) + 1):
                chapters.add(i)
            continue
        # 第3 或 3
        m = re.match(r'第?\s*(\d+)', part)
        if m:
            chapters.add(int(m.group(1)))
    return chapters

def inject_intent(plot_path, chapter, arc_data):
    """为 plot_guide 注入章节意图，合并已有的写章目标"""
    with open(plot_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '## 章节意图' in content:
        return False

    seg = find_segment(chapter, arc_data['segments'])
    bury, retrieve = find_foreshadows(chapter, arc_data['foreshadows'])
    is_turning = any(tp['chapter'] == chapter for tp in arc_data['turning_points'])

    # 提取并移除旧的"写章目标"内容
    goal_text = ''
    goal_match = re.search(r'## 写章目标\s*\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
    if goal_match:
        goal_text = goal_match.group(1).strip().replace('\n', ' ')
        # 移除旧的写章目标段落
        content = content[:goal_match.start()] + content[goal_match.end():]

    lines = ['', '## 章节意图', '']

    if goal_text:
        lines.append(f"- **本章在全书中**：{goal_text}")

    if seg:
        lines.append(f"- **全书中位置**：{seg['function']}（第{seg['start']}-{seg['end']}章）")
        lines.append(f"- **本章情绪目标**：{seg['emotion']}（强度{seg['intensity']}）")
        lines.append(f"- **主线推进**：{seg['reason'] or seg['function']}")

    char_advance = []
    for cl in arc_data['char_male']:
        if cl['start'] <= chapter <= cl['end']:
            char_advance.append(f"男主→{cl['state']}")
    for cl in arc_data['char_female']:
        if cl['start'] <= chapter <= cl['end']:
            char_advance.append(f"女主→{cl['state']}")
    if char_advance:
        lines.append(f"- **情感/成长线推进**：{'，'.join(char_advance)}")

    if is_turning:
        tp = next(tp for tp in arc_data['turning_points'] if tp['chapter'] == chapter)
        lines.append(f"- **关键转折点**：{tp['event']}（{tp['function']}）")

    if bury:
        lines.append(f"- **新埋伏笔**：{'；'.join(bury)}")
    if retrieve:
        lines.append(f"- **可回收伏笔**：{'；'.join(retrieve)}")

    stale = [f['content'] for f in arc_data['foreshadows']
             if parse_stages(f['bury']) and all(ch < chapter for ch in parse_stages(f['bury']))
             and not (f['retrieve'] and chapter in parse_stages(f['retrieve']))]
    if stale:
        lines.append(f"- **过期债务**（之前埋的该还了）：{'；'.join(stale)}")

    # 追加到文件末尾
    content += '\n'.join(lines) + '\n'

    with open(plot_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def main():
    if len(sys.argv) < 3:
        print("用法: python inject_chapter_intent.py <全书弧线.md> <蒸馏目录>")
        sys.exit(1)

    arc_path = sys.argv[1]
    distill_dir = sys.argv[2]

    if not os.path.isfile(arc_path):
        print(f"Error: 全书弧线文件不存在: {arc_path}")
        sys.exit(1)
    if not os.path.isdir(distill_dir):
        print(f"Error: 蒸馏目录不存在: {distill_dir}")
        sys.exit(1)

    arc_data = parse_arc(arc_path)
    print(f"解析到 {len(arc_data['segments'])} 个弧线段")
    print(f"解析到 {len(arc_data['char_male'])+len(arc_data['char_female'])} 个角色成长阶段")
    print(f"解析到 {len(arc_data['foreshadows'])} 个伏笔")
    print(f"解析到 {len(arc_data['turning_points'])} 个转折点")

    # 找到所有 plot_guide 文件
    injected = 0
    for fname in sorted(os.listdir(distill_dir)):
        m = re.match(r'plot_guide_(\d+)\.md', fname)
        if m:
            chapter = int(m.group(1))
            path = os.path.join(distill_dir, fname)
            if inject_intent(path, chapter, arc_data):
                print(f"  ✅ 注入章节意图: {fname}")
                injected += 1
            else:
                print(f"  ⏭️  已有章节意图: {fname}")

    print(f"\n完成：{injected} 个文件已注入")


if __name__ == '__main__':
    main()
