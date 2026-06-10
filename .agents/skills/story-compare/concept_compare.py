#!/usr/bin/env python3
"""
concept_compare.py - 开书设定对比清单

在正式写章节前，对比源文设定与新书设定的完整清单。
从 concept.md 提取设定模块，结合源书信息，输出结构化对比报告。

用法:
  python concept_compare.py <书名>
  python concept_compare.py <书名> --source <作者/源书名>
  python concept_compare.py <书名> --llm

示例:
  python concept_compare.py "傅总的全能助理"
  python concept_compare.py "傅总的全能助理" --source "闻栖/林助理颠颠的，总裁他超爱"

输出: rewrites/{书名}/compare/开书设定对比清单.md
"""

import os, re, sys, glob
from collections import Counter
from datetime import datetime

NOVEL_DB = 'projects'


# ═══════════════════════════════════════════
# 基础工具函数
# ═══════════════════════════════════════════

def read_file(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def find_rewrite_dir(book_name):
    """查找新书 rewrite 目录"""
    # 搜索 projects/*/*/rewrites/{book_name}/
    pattern = os.path.join(NOVEL_DB, '*', '*', 'rewrites', book_name)
    matches = sorted(glob.glob(pattern))
    return matches[0] if matches else None


def find_source_book_dir(rewrite_dir):
    """从 rewrite 目录反推源书目录"""
    parts = rewrite_dir.replace('\\', '/').split('/')
    if 'rewrites' in parts:
        idx = parts.index('rewrites')
        source = '/'.join(parts[:idx])
        if os.path.isdir(source):
            return source
    return None


# ═══════════════════════════════════════════
# concept.md + settings/*.md 解析
# ═══════════════════════════════════════════

SETTINGS_FILE_MAP = {
    'book_info.md': '书名信息',
    'characters.md': '角色设定',
    'plot.md': '剧情设定',
    'world.md': '世界观',
    'source_analysis.md': '源文模式分析',
}

def parse_concept(content):
    """按 ## 标题拆分 concept.md 为字典"""
    sections = {}
    current_section = None
    current_lines = []

    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections[current_section] = '\n'.join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_lines).strip()

    return sections

def load_settings_files(rewrite_dir, sections):
    """加载 settings/*.md 文件并合并到 sections 字典"""
    settings_dir = os.path.join(rewrite_dir, 'settings')
    if not os.path.isdir(settings_dir):
        return sections

    for filename, section_key in SETTINGS_FILE_MAP.items():
        filepath = os.path.join(settings_dir, filename)
        if os.path.exists(filepath):
            content = read_file(filepath)
            # 用 section_key 标记来源，不覆盖已存在的同名 key
            merged = False
            for existing_key in list(sections.keys()):
                if section_key in existing_key:
                    # 追加内容
                    sections[existing_key] += '\n\n' + content
                    merged = True
                    break
            if not merged:
                sections[f'{section_key}（settings/{filename}）'] = content

    return sections


def extract_book_name(content):
    """从 # 标题提取书名"""
    m = re.search(r'^#\s+[《]?(.+?)[》]?(?:设定)', content)
    if m:
        return m.group(1).strip()
    return None


def extract_title_candidates(sections):
    """提取书名候选"""
    for key in ['书名候选（3个）', '书名候选', '书名']:
        section = sections.get(key, '')
        candidates = []
        for line in section.split('\n'):
            m = re.match(r'\d+[\.\、]\s*(.+?)(?:—|$)', line)
            if m:
                candidates.append(m.group(1).strip())
        if candidates:
            return candidates
    return []


def extract_blurb_candidates(sections):
    """提取简介候选"""
    blurb_key = next((k for k in sections if '简介' in k), None)
    if not blurb_key:
        return {}

    section = sections[blurb_key]
    blurbs = {}
    current_version = None
    current_lines = []

    for line in section.split('\n'):
        m = re.match(r'###\s*(.+?)$', line)
        if m:
            if current_version:
                blurbs[current_version] = '\n'.join(current_lines).strip()
            current_version = m.group(1).strip()
            current_lines = []
        elif current_version:
            current_lines.append(line)

    if current_version:
        blurbs[current_version] = '\n'.join(current_lines).strip()

    return blurbs


def extract_characters(sections):
    """提取角色设定列表（兼容 concept.md 和 settings/characters.md 格式）"""
    char_key = next((k for k in sections if '角色' in k), None)
    if not char_key:
        return []

    section = sections[char_key]
    chars = []
    current_char = None  # 用于追踪 characters.md 的多行表格

    for line in section.split('\n'):
        line_s = line.strip()
        if not line_s:
            continue  # 空行不打断表格行追踪

        # === 格式1: settings/characters.md 的 ### 男主角：陆昭白 ===
        m = re.match(r'#{1,4}\s*(?:男主角|女主角|主要配角|配角\d*)\s*[：:]\s*(.+)$', line_s)
        if m:
            full = m.group(1).strip()
            name = re.sub(r'\s*\(.*?\)\s*', '', full).split('，')[0].split('（')[0].strip()
            if '男主角' in line_s:
                role_type = '男主'
            elif '女主角' in line_s:
                role_type = '女主'
            else:
                role_type = re.search(r'(?:主要配角|配角\d*)', line_s)
                role_type = role_type.group(0) if role_type else '配角'
            current_char = {'role': role_type, 'name': name, 'info': full, 'age': '', 'traits': []}
            chars.append(current_char)
            continue

        # === 追踪 characters.md 表格行（在 ### 行之后出现） ===
        if current_char:
            # | **年龄** | 19岁 |  → 提取年龄
            m = re.match(r'\|\s*\*{0,2}年龄\*{0,2}\s*\|\s*(.+?)\s*\|', line_s)
            if m:
                current_char['age'] = m.group(1).strip()
            # | **身份** | xxx | 或 | **性格** | xxx | → 追加到 info
            m = re.match(r'\|\s*\*{0,2}(?:身份|性格|身份与性格|核心设定)\*{0,2}\s*\|\s*(.+?)\s*\|', line_s)
            if m and current_char['info']:
                val = m.group(1).strip()
                current_char['info'] += f' | {val}'
            continue

        # === 格式2: concept.md 的 **女主**：xxx 或 - **男主**：xxx ===
        m = re.match(r'[-*\s]*\*{2}([^*]+?)\*{2}[:：]\s*(.+)$', line_s)
        if m:
            role_name = m.group(1).strip()
            info = m.group(2).strip()
            age = re.search(r'(\d+)岁', info).group(1) if re.search(r'(\d+)岁', info) else ''
            name_m = re.match(r'([\u4e00-\u9fff]{2,3})', info)
            name = name_m.group(1) if name_m else role_name
            if '男' in role_name or '男主' in role_name:
                role_type = '男主'
            elif '女' in role_name or '女主' in role_name:
                role_type = '女主'
            else:
                role_type = role_name
            chars.append({'role': role_type, 'name': name, 'age': age, 'info': info})
            continue

        # === 格式3: - 角色名：xxx ===
        m = re.match(r'[-]\s*([\u4e00-\u9fff]{2,4})[:：]\s*(.+)$', line_s)
        if m and '角色' not in line_s and '设定' not in line_s:
            name = m.group(1).strip()
            info = m.group(2).strip()
            chars.append({
                'role': name, 'name': name,
                'age': re.search(r'(\d+)岁', info).group(1) if re.search(r'(\d+)岁', info) else '',
                'info': info,
            })

    return chars


def extract_source_analysis(sections):
    """提取源文模式分析（兼容 concept.md 和 settings/source_analysis.md）"""
    for key in sections:
        if '源文' in key:
            return sections[key]
    # 也尝试从 settings/plot.md 中提取
    for key in sections:
        if '剧情设定' in key or 'plot' in key:
            return sections[key]
    return ''


def extract_world(sections):
    """提取世界观（兼容 concept.md 和 settings/world.md）"""
    for key in sections:
        if '世界观' in key:
            return sections[key]
    return ''


def extract_main_arc(sections):
    """提取主线弧线（兼容 concept.md 和 settings/plot.md）"""
    for key in sections:
        if '主线' in key or '弧线' in key:
            return sections[key]
    # 从剧情设定中提取
    for key in sections:
        if '剧情设定' in key:
            # 格式: ## 主线弧线（一句话）\n内容...
            text = sections[key]
            m = re.search(r'##?\s*主线弧线.*?\n\s*(.+?)(?:\n##|\Z)', text, re.DOTALL)
            if m:
                return m.group(1).strip()
    return ''


def parse_conflict(content):
    """从核心冲突段落提取源文vs新书（兼容 concept.md 和 settings/plot.md 格式）"""
    src_conflict = ''
    new_conflict = ''

    # 格式1: concept.md 的 **源文核心冲突**：xxx
    m = re.search(r'\*{0,2}源文核心冲突\*{0,2}[：:]\s*(.+?)$', content, re.M)
    if m:
        src_conflict = m.group(1).strip()

    m = re.search(r'\*{0,2}新书核心冲突\*{0,2}[：:]\s*(.+?)$', content, re.M)
    if m:
        new_conflict = m.group(1).strip()

    # 格式2: settings/plot.md 的 *   **冲突类型**：列表
    if not src_conflict and not new_conflict:
        m = re.search(r'\*{0,2}冲突类型\*{0,2}[：:]\s*', content)
        if m:
            # 提取列表项作为冲突描述
            after = content[m.end():]
            items = re.findall(r'\d+\.\s*\*{0,2}(.+?)\*{0,2}\s*（(.+?)）', after)
            if items:
                src_conflict = '源文冲突：' + '；'.join([f'{t}({d})' for t, d in items])
                new_conflict = src_conflict  # 相同冲突类型但具体事件不同
        # 从情感内核段落找源文vs新书区别
        em_m = re.search(r'\*{0,2}源文\*{0,2}[：:]\s*(.+?)(?:\n|$)', content[content.find('情感内核'):] if '情感内核' in content else content)
        new_em_m = re.search(r'\*{0,2}新书\*{0,2}[：:]\s*(.+?)(?:\n|$)', content[content.find('情感内核'):] if '情感内核' in content else content)
        if not src_conflict and em_m:
            src_conflict = em_m.group(1).strip()[:100]
        if not new_conflict and new_em_m:
            new_conflict = new_em_m.group(1).strip()[:100]

    # 换皮要点
    peel_points = []
    in_peel = False
    for line in content.split('\n'):
        stripped = line.strip()
        if '换皮要点' in stripped:
            in_peel = True
            continue
        if in_peel:
            m = re.match(r'[-–]\s*(.+)$', stripped)
            if m:
                peel_points.append(m.group(1).strip())
            elif stripped == '':
                pass
            elif stripped.startswith('-'):
                peel_points.append(stripped.lstrip('- '))

    return src_conflict, new_conflict, peel_points


# ═══════════════════════════════════════════
# 源书信息读取
# ═══════════════════════════════════════════

def read_source_book_info(source_path):
    """读取源书元信息：_header.txt → 原始 txt → 首章角色名"""
    info = {}
    content = ''
    header_path = os.path.join(source_path, '_cache', '_header.txt')
    if os.path.exists(header_path):
        content = read_file(header_path)
    else:
        # 没有 _header.txt 就尝试找原始 txt 文件
        txt_files = glob.glob(os.path.join(source_path, '_cache', '*.txt'))
        txt_files = [f for f in txt_files if '_header' not in f and '_toc' not in f]
        if txt_files:
            raw = read_file(txt_files[0])
            lines = raw.split('\n')
            content = '\n'.join(lines[:80])  # 前 80 行通常包含头部信息

    if content:
        m = re.search(r'书名[：:]\s*(.+)', content)
        if m: info['name'] = m.group(1).strip()
        m = re.search(r'作者[：:]\s*(.+)', content)
        if m: info['author'] = m.group(1).strip()
        m = re.search(r'分类[：:]\s*(.+)', content)
        if m: info['category'] = m.group(1).strip()
        m = re.search(r'标签[：:]\s*(.+)', content)
        if m: info['tags'] = m.group(1).strip()
        m = re.search(r'字数[：:]\s*(\d+)', content)
        if m: info['word_count'] = m.group(1)
        m = re.search(r'章节[：:]\s*(\d+)', content)
        if m: info['chapter_count'] = m.group(1)

        # 简介
        in_intro = False
        intro_lines = []
        for line in content.split('\n'):
            if '简介' in line and ':' in line:
                in_intro = True
                continue
            if in_intro:
                if line.strip().startswith('=====') or line.strip().startswith('【'):
                    break
                intro_lines.append(line)
        if intro_lines:
            info['blurb'] = '\n'.join(intro_lines).strip()

    # 首章角色名提取
    ch1_path = os.path.join(source_path, '_cache', 'chapters', '第1章.txt')
    if not os.path.exists(ch1_path):
        ch_files = glob.glob(os.path.join(source_path, '_cache', 'chapters', '第1章*.txt'))
        if ch_files:
            ch1_path = ch_files[0]

    if os.path.exists(ch1_path):
        ch1_text = read_file(ch1_path)
        info['chapter1'] = ch1_text[:2000]
        info['characters_from_ch1'] = extract_names_from_chapter(ch1_text)

    return info


def extract_names_from_chapter(text):
    """从章节文本提取高频人名（2-3字）"""
    candidates = re.findall(r'[\u4e00-\u9fff]{2,3}(?=[，。！？、：；""''（）\u3000\s])', text)
    counter = Counter(candidates)

    skip_words = {
        '一个', '没有', '什么', '可以', '知道', '已经', '说道', '这样', '那个',
        '自己', '就是', '不是', '这个', '起来', '他们', '时候', '过来', '你们',
        '我们', '看着', '怎么', '如果', '因为', '所以', '然后', '觉得', '以后',
        '现在', '心里', '突然', '眼睛', '还是', '一声', '一下', '出来', '之后',
        '面前', '一样', '一阵', '一点', '之间', '身上', '直接', '刚才', '真的',
        '当时', '难道', '所有', '最后', '好像', '一直', '根本', '完全', '不过',
        '而且', '或者', '虽然', '但是', '只是', '还是', '因为', '所以', '如果',
        '的话', '说道', '开口', '开口', '面前', '身后', '抬头', '低头', '点头',
        '摇头', '回头', '转身', '看见', '听见', '觉得', '以为', '开始', '终于',
        '突然', '然后', '接着', '跟着', '只见', '只见', '只见', '哪知', '谁知',
        '不料', '不想', '不禁', '不由', '忍不住', '不由得', '只见他', '只见她',
        '见他', '见她', '对他', '对她', '向他', '向她', '把她', '把他', '被她',
        '被他', '给她', '给他', '让她', '让他', '令人', '让人', '有人', '没人',
        '每个人', '所有人', '任何人', '这时', '那时', '此前', '此前', '此刻',
        '瞬间', '片刻', '一时', '一直', '一阵', '一笑', '一看', '一听', '一想',
        '一开口', '一转', '一转', '一回', '一回头', '一转身',
    }

    result = [(n, c) for n, c in counter.most_common(30)
              if n not in skip_words and c >= 3]
    return result


# ═══════════════════════════════════════════
# 分析逻辑
# ═══════════════════════════════════════════

def get_new_book_chars(concept_content, rewrite_dir=None):
    """从 concept.md + settings/characters.md 提取新书角色名列表"""
    names = []

    # 优先从 settings/characters.md 提取（格式规整）
    if rewrite_dir:
        char_path = os.path.join(rewrite_dir, 'settings', 'characters.md')
        if os.path.exists(char_path):
            char_text = read_file(char_path)
            # ### 男主角：陆昭白
            for m in re.finditer(r'#+\s*(?:男主角|女主角)\s*[：:]\s*([\u4e00-\u9fff]{2,4})', char_text):
                names.append(m.group(1))
            # ### 主要配角 / ### 配角N 表格中的名字
            for m in re.finditer(r'(?<=\|\s)\*\*([\u4e00-\u9fff]{2,4})\*\*', char_text):
                names.append(m.group(1))

    # 也从 concept.md 提取
    for m in re.finditer(r'\*{2}([^*]+?)\*{2}[:：]', concept_content):
        role = m.group(1).strip()
        if role in ('角色', '设定', '角色设定'):
            continue
        rest = concept_content[m.end():m.end() + 60]
        name_m = re.match(r'([\u4e00-\u9fff]{2,3})', rest)
        if name_m:
            names.append(name_m.group(1))

    for m in re.finditer(r'-\s*([\u4e00-\u9fff]{2,4})[:：]', concept_content):
        name = m.group(1).strip()
        if len(name) >= 2 and name not in names and '角色' not in name and '设定' not in name:
            names.append(name)

    return list(set(names))


def analyze_name_overlap(new_names, source_chars):
    """新书角色名 vs 源文高频名 重叠检测"""
    src_names = [n for n, c in source_chars]
    overlaps = []

    for new_name in new_names:
        for src_name in src_names:
            if len(src_name) <= 1:
                continue
            if new_name == src_name:
                overlaps.append((new_name, src_name, '完全匹配'))
            elif len(new_name) >= 2 and len(src_name) >= 2:
                new_suffix = new_name[-1] if len(new_name) <= 2 else new_name[-2:]
                src_suffix = src_name[-1] if len(src_name) <= 2 else src_name[-2:]
                if new_suffix == src_suffix and len(new_suffix) >= 1:
                    tag = '单字重叠'
                    if (new_name, src_name, tag) not in overlaps:
                        overlaps.append((new_name, src_name, tag))

    return overlaps


CONFLICT_TYPES = {
    '身份': ['身份', '阶层', '地位', '出身', '门第', '血统'],
    '利益': ['利益', '资源', '竞争', '权力', '商业', '事业', '金钱', '财产'],
    '信息差': ['信息', '秘密', '隐瞒', '误会', '误解', '错位', '伪装', '假冒'],
    '道德': ['道德', '伦理', '良心', '原则', '正义', '良知'],
    '情感': ['情感', '爱情', '感情', '暗恋', '单恋', '三角', '虐恋'],
    '生存': ['生存', '活着', '保命', '求生', '危机', '死亡', '生死'],
    '系统': ['系统', '任务', '剧情', '穿书', '穿越', '系统强制'],
    '自由意志': ['自由', '意志', '反抗', '掌控', '控制', '压迫'],
}


def detect_conflict_type(text):
    """检测冲突类型"""
    found = []
    for tname, keywords in CONFLICT_TYPES.items():
        if any(k in text for k in keywords):
            found.append(tname)
    return found if found else ['其他']


def analyze_conflict_change(src_conflict, new_conflict, full_content):
    """分析冲突类型变更"""
    if new_conflict:
        new_section = full_content[full_content.find('新书'):] if '新书' in full_content else new_conflict
    else:
        new_section = ''

    src_types = detect_conflict_type(src_conflict)
    new_types = detect_conflict_type(new_conflict or new_section)

    has_overlap = bool(set(src_types) & set(new_types))
    return src_types, new_types, not has_overlap


def analyze_world_change(src_world, new_world):
    """分析世界观场景重叠"""
    src_places = re.findall(r'[\u4e00-\u9fff]{2,6}(?:市|城|区|镇|街|路|大厦|楼|别墅|小区|公馆|山庄|园|岛|港)', src_world)
    new_places = re.findall(r'[\u4e00-\u9fff]{2,6}(?:市|城|区|镇|街|路|大厦|楼|别墅|小区|公馆|山庄|园|岛|港)', new_world)

    common_places = list(set(src_places) & set(new_places))

    src_era = re.findall(r'(古代|现代|民国|未来|架空|都市|修仙|玄幻|奇幻|科幻|年代|穿越|重生|古风|现代言情|豪门|总裁)', src_world)
    new_era = re.findall(r'(古代|现代|民国|未来|架空|都市|修仙|玄幻|奇幻|科幻|年代|穿越|重生|古风|现代言情|豪门|总裁)', new_world)

    same_era = bool(set(src_era) & set(new_era)) if src_era and new_era else None

    return {
        'src_places': src_places,
        'new_places': new_places,
        'common_places': common_places,
        'src_era': list(set(src_era)),
        'new_era': list(set(new_era)),
        'same_era': same_era,
    }


def check_ai_naming(names):
    """检测 AI 命名通病"""
    violations = []
    ai_chars = set('知念涵熙曦辞汐瑶瑾萱珞卿岚鸢')
    common_surnames = {'沈', '林', '顾', '陆', '傅', '苏', '江', '容', '秦', '裴', '霍', '薄', '祁'}

    for name in names:
        risky_chars = [c for c in name if c in ai_chars]
        if risky_chars:
            violations.append(f'"{name}" 含诗意字: {", ".join(risky_chars)}')
        if name[0] in common_surnames:
            pass  # 常见姓不算违规，只记录
        if len(name) == 2 and name[0] in common_surnames:
            pass  # 正常

    return violations


def extract_source_archetype(sections):
    """从源文分析提取人设模式"""
    src = extract_source_analysis(sections)
    m = re.search(r'人设模式[：:]\s*(.+?)(?:\n|$)', src)
    return m.group(1).strip() if m else ''


# ═══════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════

def generate_report(book_name, sections, source_info, new_chars,
                    peel_points, name_overlaps, conflict_analysis,
                    world_analysis, ai_violations, source_archetype):
    lines = []
    def L(s=''): lines.append(s)

    L(f'# 开书设定对比清单：{book_name}')
    L(f'> 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}')
    L('> 用途：正式写章前审阅设定对比，确认"换皮"充分后再推进 guides → write 阶段')
    L('')
    L('---')
    L('')

    # ── 元信息 ──
    L('## 一、元信息对比')
    L('')
    src_name = source_info.get('name', '（未知）')
    src_author = source_info.get('author', '（未知）')

    L('| 维度 | 源文 | 新书 | 判定 |')
    L('|------|------|------|------|')
    name_similar = book_name and any(c in book_name for c in src_name if len(c) >= 2)
    L(f'| 书名 | {src_name} | {book_name} | {"⚠️ 含源文字" if name_similar else "✅ 已区分"} |')
    L(f'| 作者 | {src_author} | （仿写） | — |')
    L(f'| 分类 | {source_info.get("category", "—")} | 一致（题材锁定） | 📋 |')
    L(f'| 标签 | {source_info.get("tags", "—")} | 一致 | 📋 |')
    src_wc = source_info.get('word_count', '')
    src_cc = source_info.get('chapter_count', '')
    if src_wc:
        L(f'| 源文字数 | {src_wc} | {"—"} | — |')
    if src_cc:
        L(f'| 源文章节 | {src_cc} 章 | — | — |')
    L('')

    # ── 书名候选 ──
    titles = extract_title_candidates(sections)
    if titles:
        L('### 书名候选')
        L('')
        for t in titles:
            L(f'- {t}')
        L('')

    # ── 角色对比 ──
    L('## 二、角色设定对比')
    L('')
    L('### 2.1 角色设定表')
    L('')
    L('| 角色 | 年龄 | 设定概要 | 源文人设模式 | 换皮判定 |')
    L('|------|------|----------|-------------|----------|')

    chars = extract_characters(sections)
    if chars:
        for c in chars:
            display_name = c.get('name', c['role'])
            summary = c['info'][:70]
            L(f'| {display_name} ({c["role"]}) | {c["age"] or "—"} | {summary} | {source_archetype or "—"} | ⏳ |')
    else:
        L('| — | — | 未解析到角色设定 | — | ⏳ |')
    L('')

    # 角色名重叠
    L('### 2.2 角色名重叠检测')
    L('')
    if name_overlaps:
        L('| 新书角色 | 源文角色 | 匹配类型 |')
        L('|----------|----------|----------|')
        for new_n, src_n, mtype in name_overlaps:
            tag = '❌' if mtype == '完全匹配' else '⚠️'
            L(f'| {new_n} | {src_n} | {tag} {mtype} |')
        L('')
        L('> ❌ 完全匹配=角色名相同，必须改名。⚠️ 单字重叠=末字相同，建议调整。')
    else:
        L('✅ 未检测到角色名重叠。')
    L('')

    # AI 命名检测
    L('### 2.3 AI命名通病检测')
    L('')
    if ai_violations:
        for v in ai_violations:
            L(f'- ⚠️ {v}')
        L('')
        L('> 建议改用通俗名字，参考规则：混搭单名双名、配角用王李张刘陈等常见姓。')
    else:
        L('✅ 未检测到AI命名通病。')
    L('')

    # ── 核心冲突 ──
    L('## 三、核心冲突对比')
    L('')
    src_type = conflict_analysis['src_types']
    new_type = conflict_analysis['new_types']
    type_changed = conflict_analysis['type_changed']
    src_conflict_raw = conflict_analysis['src_raw']
    new_conflict_raw = conflict_analysis['new_raw']

    L('| 维度 | 源文 | 新书 | 判定 |')
    L('|------|------|------|------|')
    L(f'| 冲突类型 | {", ".join(src_type)} | {", ".join(new_type)} | {"✅ 已换" if type_changed else "❌ 未变更"} |')
    if src_conflict_raw or new_conflict_raw:
        L(f'| 源文冲突 | {src_conflict_raw[:80] or "—"} | — | — |')
        L(f'| 新书冲突 | — | {new_conflict_raw[:80] or "—"} | — |')
    L('')

    if not type_changed:
        L('> 🔴 **核心冲突类型未变更！** 源文和新书共享冲突类型，违反"冲突类型强制换"原则。必须重新设计。')
        L('')
        # 建议从可用类型池中推荐不同方向
        all_types = list(CONFLICT_TYPES.keys())
        src_set = set(src_type)
        new_set = set(new_type)
        used = src_set | new_set
        unused = [t for t in all_types if t not in used]
        if unused:
            L(f'> 建议方向：{", ".join(unused[:3])} 等（当前类型 {", ".join(used)} 已用）')
        L('')

    # 换皮要点
    L('### 换皮要点清单')
    L('')
    if peel_points:
        L('| # | 换皮项 | 状态 |')
        L('|---|--------|------|')
        for i, pt in enumerate(peel_points, 1):
            L(f'| {i} | {pt} | ⏳ |')
    else:
        L('⚠️ concept.md 中未找到"换皮要点"列表。建议在核心冲突章节补充。')
    L('')

    # ── 世界观 ──
    L('## 四、世界观对比')
    L('')
    world_section = extract_world(sections)
    era_same = world_analysis['same_era']

    L('| 维度 | 源文 | 新书 | 判定 |')
    L('|------|------|------|------|')
    L(f'| 时代背景 | {", ".join(world_analysis["src_era"]) or "—"} | {", ".join(world_analysis["new_era"]) or "—"} | {"✅ 一致" if era_same else "⚠️ 需确认"} |')
    common = world_analysis['common_places']
    if common:
        L(f'| 场景重叠 | {", ".join(common[:5])} | ⚠️ {len(common)} 处重叠 |')
    else:
        L(f'| 场景重叠 | — | ✅ 无重叠 |')
    L('')

    L('### 世界观摘要')
    L('')
    if world_section:
        for line in world_section.strip().split('\n')[:15]:
            line = line.strip()
            if line:
                L(f'> {line}')
    else:
        L('> 未找到世界观设定。')
    L('')

    # ── 主线弧线 ──
    L('## 五、主线弧线')
    L('')
    arc = extract_main_arc(sections)
    if arc:
        L(f'> {arc}')
    else:
        L('> 未找到主线弧线。')
    L('')

    # ── 换皮检验 ──
    L('## 六、换皮检验清单')
    L('')
    L('| 检查项 | 判定 | 说明 |')
    L('|--------|------|------|')
    L(f'| 角色名完全不同 | {"❌ 有重叠" if name_overlaps else "✅ 无重叠"} | 排除音近/形近 |')
    L(f'| 核心冲突类型不同 | {"✅ 已更换" if type_changed else "❌ 未变更"} | 不可同类型 |')
    L(f'| 场景名已替换 | {"⚠️ 部分重叠" if common else "✅ 已替换"} | 核心场景全换 |')
    L(f'| 题材不变 | ✅ | 题材锁定规则 |')
    L(f'| 情感内核原创 | ⏳ | 需人工确认 |')
    L(f'| 情节驱动逻辑不同 | ⏳ | 需人工确认 |')
    L(f'| 剥名后无法辨认源文 | ⏳ | 换皮终极检验 |')
    L('')

    # ── 风险 ──
    L('## 七、风险点汇总')
    L('')
    risks = []

    if not type_changed:
        risks.append(('🔴 高', f'冲突类型未变更（源文{",".join(src_type)} vs 新书{",".join(new_type)}），必须重新设计'))

    exact_overlaps = [n for n, s, t in name_overlaps if t == '完全匹配']
    if exact_overlaps:
        risks.append(('🔴 高', f'角色名完全重叠：{", ".join(exact_overlaps)}，必须改名'))

    if ai_violations:
        risks.append(('🟡 中', f'AI命名通病 {len(ai_violations)} 处'))

    if common:
        risks.append(('🟡 中', f'场景名重叠 {len(common)} 处：{", ".join(common[:3])}'))

    if not peel_points:
        risks.append(('🟡 中', '缺少明确的换皮要点列表'))

    if name_similar:
        risks.append(('🟢 低', f'新书名含源文字：建议确认不构成混淆'))

    L('| 级别 | 风险项 |')
    L('|------|--------|')
    if risks:
        for level, desc in risks:
            L(f'| {level} | {desc} |')
    else:
        L('| ✅ | **未发现明显风险** |')
    L('')

    # ── 结论 ──
    L('## 八、比对结论')
    L('')
    high = sum(1 for l, d in risks if '🔴' in l)
    mid = sum(1 for l, d in risks if '🟡' in l)
    low = sum(1 for l, d in risks if '🟢' in l)

    if high > 0:
        L(f'> 🔴 **存在 {high} 项高风险、{mid} 项中风险。修正后再推进写章。**')
        L('>')
        L('> 修复方案：')
        L('> 1. 手动编辑 rewrites/目录下的 plot_guide.md 或重新调整 concept.md')
        L('> 2. 修复后重新运行此检查')
        L('> 3. 确认无高风险后再推进 guides → write')
    elif mid > 0:
        L(f'> 🟡 **存在 {mid} 项中风险。建议确认后推进，写章时注意规避。**')
        L('>')
        L('> 确认无误后，可继续运行：')
        L('>')
        L('>     python tools/rewrite_chapters.py --config configs/xxx.json --phase guides')
    else:
        L('> ✅ **设定检查全部通过，可以推进写章。**')
        L('>')
        L('> 建议下一步：')
        L('> 1. 运行 guides 阶段生成 plot_N.md 和 style_N.md')
        L('> 2. 运行 write 阶段写章')
        L('> 3. 写完后 trim → continuity → compare → unified')
    L('')

    # ── 附录 ──
    L('---')
    L('')
    L('## 附录：源书信息')
    L('')
    src_blurb = source_info.get('blurb', '')
    if src_blurb:
        L('### 源书简介')
        L('')
        L(f'> {src_blurb}')
        L('')

    src_chars = source_info.get('characters_from_ch1', [])
    if src_chars:
        L('### 源书高频角色名（首章提取）')
        L('')
        L('| 名字 | 出现次数 |')
        L('|------|----------|')
        for name, count in src_chars[:12]:
            L(f'| {name} | {count} |')
        L('')

    ch1_text = source_info.get('chapter1', '')
    if ch1_text:
        L('### 源书开篇（前500字）')
        L('')
        L(f'> {ch1_text[:500].replace(chr(10), chr(10) + "> ")}')
        L('')

    return '\n'.join(lines)


# ═══════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════

def main():
    # 确保控制台输出支持 UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    import argparse
    parser = argparse.ArgumentParser(description='开书设定对比清单')
    parser.add_argument('book_name', help='新书名')
    parser.add_argument('--source', help='源书路径 (作者/源书名)')
    parser.add_argument('--llm', action='store_true', help='启用 LLM 定性分析（需 API_KEY）')
    parser.add_argument('--output', help='输出路径（默认 compare/开书设定对比清单.md）')
    args = parser.parse_args()

    book_name = args.book_name

    # 查找 rewrite 目录
    rewrite_dir = find_rewrite_dir(book_name)
    if not rewrite_dir:
        print(f'[错误] 未找到新书目录: {book_name}')
        print(f'   搜索路径: {NOVEL_DB}/*/*/rewrites/{book_name}/')
        sys.exit(1)

    concept_path = os.path.join(rewrite_dir, 'concept.md')
    if not os.path.exists(concept_path):
        print(f'[错误] 未找到 concept.md: {concept_path}')
        print(f'   请先完成开书阶段（open-book）')
        sys.exit(1)

    print(f'[读取] {concept_path}')
    concept_content = read_file(concept_path)
    sections = parse_concept(concept_content)

    # 加载 settings/*.md（多文件开书模式）
    sections = load_settings_files(rewrite_dir, sections)
    settings_dir = os.path.join(rewrite_dir, 'settings')
    if os.path.isdir(settings_dir):
        print(f'[合并] settings/*.md 已合并')
    print(f'[解析] {len(sections)} 个设定模块: {", ".join(sections.keys())}')

    # 源书
    source_book_dir = find_source_book_dir(rewrite_dir)
    if args.source:
        source_book_dir = os.path.join(NOVEL_DB, args.source)

    source_info = {}
    if source_book_dir and os.path.isdir(source_book_dir):
        print(f'[源书] {source_book_dir}')
        source_info = read_source_book_info(source_book_dir)
        if source_info:
            print(f'   书名: {source_info.get("name", "?")}  作者: {source_info.get("author", "?")}')
    else:
        print('[注意] 未找到源书目录，角色名重叠检测跳过')

    # 提取数据（优先从 settings/characters.md 提取）
    new_chars = get_new_book_chars(concept_content, rewrite_dir)

    # 冲突：优先从 settings/plot.md 取（更详细），再回退 concept.md
    conflict_section = sections.get('剧情设定（settings/plot.md）', '') or ''
    if not conflict_section:
        conflict_section = sections.get('核心冲突', '') or ''
        if not conflict_section:
            plot_path = os.path.join(rewrite_dir, 'settings', 'plot.md')
            if os.path.exists(plot_path):
                conflict_section = read_file(plot_path)
    src_conflict, new_conflict, peel_points = parse_conflict(conflict_section)

    print(f'[数据] 角色: {len(new_chars)} 个  换皮要点: {len(peel_points)} 条')

    # 分析
    name_overlaps = []
    if 'characters_from_ch1' in source_info:
        name_overlaps = analyze_name_overlap(new_chars, source_info['characters_from_ch1'])
        if name_overlaps:
            print(f'[重叠] 角色名重叠: {len(name_overlaps)} 处')

    src_types, new_types, type_changed = ['—'], ['—'], True
    if src_conflict or new_conflict:
        src_types, new_types, type_changed = analyze_conflict_change(
            src_conflict, new_conflict, conflict_section
        )
    conflict_analysis = {
        'src_types': src_types,
        'new_types': new_types,
        'type_changed': type_changed,
        'src_raw': src_conflict,
        'new_raw': new_conflict,
    }
    if not type_changed:
        print(f'[风险] 冲突类型未变更: {",".join(src_types)}')

    world_section = extract_world(sections)
    src_world = extract_source_analysis(sections)
    world_analysis = analyze_world_change(src_world, world_section)
    if world_analysis['common_places']:
        print(f'[重叠] 场景重叠: {len(world_analysis["common_places"])} 处')

    ai_violations = check_ai_naming(new_chars)
    source_archetype = extract_source_archetype(sections)

    # LLM mode
    if args.llm:
        api_key = os.environ.get('API_KEY')
        if api_key:
            print('[LLM] 分析...')
            # TODO: LLM analysis stub
            print('   （--llm 模式待实现，当前仅算法检查）')

    # 写报告
    report = generate_report(
        book_name, sections, source_info, new_chars,
        peel_points, name_overlaps, conflict_analysis,
        world_analysis, ai_violations, source_archetype,
    )

    out_dir = os.path.join(rewrite_dir, 'compare')
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.output or os.path.join(out_dir, '开书设定对比清单.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f'[完成] 报告已生成: {out_path}')
    print()

    # 摘要
    high = sum(1 for l in report.split('\n') if '🔴' in l and '|' in l)
    mid = sum(1 for l in report.split('\n') if '🟡' in l and '|' in l)
    if high:
        print(f'[结果] 高风险 {high} 项 -- 修正后再推进写章')
    elif mid:
        print(f'[结果] 中风险 {mid} 项 -- 确认后可推进')
    else:
        print(f'[结果] 全部通过 -- 可以推进写章')


if __name__ == '__main__':
    main()
