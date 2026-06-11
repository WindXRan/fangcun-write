"""源文脱敏：剥离数字/编号/人名，保留结构。

喂给 LLM 写 guide 时，不再给全章源文，给脱敏版。
"""

import re
import json
from pathlib import Path

from lib.source_locator import get_source_text, find_source_file


def _load_characters(config):
    """从 settings/characters.md 读取角色名→角色类型映射。"""
    rewrites_dir = config.get("rewrites_dir", "")
    chars_path = Path(rewrites_dir) / "settings" / "characters.md"
    if not chars_path.exists():
        return {}

    text = chars_path.read_text(encoding="utf-8")
    mapping = {}

    current_role = "角色"
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue

        # 匹配 "**名字**（年龄）" 或 "**名字**" 格式
        m = re.match(r'^\*\*(.+?)\*\*(?:（(.+?)）)?', line)
        if m:
            name = m.group(1).strip()
            if re.match(r'^[\u4e00-\u9fff]{2,4}$', name):
                # 从上下文推断角色类型
                if "男主" in line or "男一" in line or "男主角" in line:
                    current_role = "男主"
                elif "女一" in line or "女主角" in line:
                    current_role = "女主角"
                elif "女二" in line:
                    current_role = "女配"
                elif "女三" in line:
                    current_role = "女配"
                elif "配角" in line or "龙套" in line:
                    current_role = "配角"
                else:
                    # 看前文有什么角色标题
                    pass
                mapping[name] = current_role
            continue

        # 匹配 "### 女X：" 或 "### 角色类别" 标题来更新 current_role
        m = re.match(r'^###?\s*(.+)$', line)
        if m:
            header = m.group(1)
            if "男主角" in header:
                current_role = "男主"
            elif "女主角" in header or ("女主" in header):
                current_role = "女主角"
            elif "女二" in header or "女三" in header or "女配" in header:
                current_role = "女配"
            elif "配角" in header:
                current_role = "配角"
            elif "龙套" in header:
                current_role = "龙套"

        # 匹配 "- 名字：类型" 格式（备用）
        m = re.match(r'^[-*]\s*(.+?)[：:]\s*(.+?)$', line)
        if m:
            name = m.group(1).strip()
            role = m.group(2).strip()
            if re.match(r'^[\u4e00-\u9fff]{2,4}$', name):
                role_label = re.sub(r'[，,、].*$', '', role)
                mapping[name] = role_label

    return mapping


def strip_source_text(text, name_map=None):
    """脱敏：数字→【N】，角色名→【角色类型】。

    Args:
        text: 源文文本
        name_map: {原名: 角色标签} 字典，如 {"李命": "男主", "林希": "女配"}

    Returns:
        脱敏后的文本
    """
    if not text:
        return text

    # 1. 替换数字序列
    text = re.sub(r'\d+', '【N】', text)

    # 2. 替换中文数字词（如"二""三"等单独出现时可能表示数量）
    # 注意：中文数字作为词语一部分时不能替换（如"十分""一切"）
    # 这里是简版，只替换明确的数量表示
    # （完整方案需要词法分析，暂时不做激进替换）
    pass

    # 3. 替换场景设定词，防止设定泄漏（如"监狱"→新书写成"监狱"）
    # 这些词是源文特有的场景标识，新书场景不同，不应出现
    setting_replacements = [
        # 长词优先（避免"监狱长"被"监狱"先替换）
        ("女子监狱长", "【全女场所负责人】"),
        ("女子监狱", "【全女场所】"),
        ("女监狱长", "【女负责人】"),
        ("监狱长", "【负责人】"),
        ("女监区", "【女场所区域】"),
        ("男监狱", "【男封闭场所】"),
        ("女监狱", "【女封闭场所】"),
        ("女监", "【全女场所】"),
        ("监狱", "【封闭场所】"),
        ("狱警", "【工作人员】"),
        ("犯人", "【被管理者】"),
        ("监区", "【区域】"),
        ("囚犯", "【被管理者】"),
        ("管教", "【管理者】"),
        ("禁闭室", "【处罚室】"),
        ("禁闭", "【处罚】"),
        ("女犯", "【被管理者】"),
        ("食堂", "【就餐区】"),
        ("牢房", "【房间】"),
    ]
    for src_word, tgt in setting_replacements:
        text = text.replace(src_word, tgt)

    # 5. 替换角色名
    if name_map:
        # 按名字长度降序排列，避免部分匹配
        for name in sorted(name_map.keys(), key=len, reverse=True):
            role_label = name_map[name]
            text = text.replace(name, f'【{role_label}】')

    return text


def strip_source_chapter(config, chapter_num, name_map=None):
    """读取并脱敏源文章节。

    Args:
        config: 配置字典
        chapter_num: 章节号
        name_map: 角色名映射（可选，不传则从 characters.md 自动读取）

    Returns:
        脱敏后的文本，或 None（文件不存在）
    """
    text = get_source_text(config, chapter_num)
    if text is None:
        return None

    if name_map is None:
        name_map = _load_characters(config)

    return strip_source_text(text, name_map)


def make_structure_summary(config, chapter_num, name_map=None):
    """生成结构摘要（比完整脱敏版更精简，只保留骨架信息）。

    返回格式：
        【源文结构】
        字数: {N}
        场景数: {N}
        场景列表:
        - 场景1: 角色【男主】+ 【女配A】，地点【场景1】，冲突：{冲突类型}
        ...
        情绪曲线: {起点} → {中点} → {终点}
        冲突类型: {冲突类型1} / {冲突类型2}
    """
    text = get_source_text(config, chapter_num)
    if text is None:
        return None

    # 字数
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 段落数
    paras = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    # 对话行数（含引号的行）
    dialogue_lines = len([l for l in text.split('\n') if '「' in l or '"' in l or '"' in l or '“' in l])

    summary_parts = [
        f"字数：{cn_chars}",
        f"段落数：{len(paras)}",
        f"对话行数：{dialogue_lines}",
    ]

    return '\n'.join(summary_parts)
