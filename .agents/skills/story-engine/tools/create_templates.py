# -*- coding: utf-8 -*-
"""
批量创建模板文件，让 agent 只填内容不写格式。
用法：python create_templates.py <类型> <章节数> <输出目录>

类型：
  style       - 风格指南模板（inkos 8维度）
  strategy    - 叙事策略模板
  outline     - 章纲模板
  concept     - 新书概念模板
  bible       - 世界观模板
  arc         - 全书弧线骨架模板
  mapping     - 章节顺序映射模板
"""

import sys
import os

STYLE_TEMPLATE = """# 风格指南：第{N}章

> 来源：{源书名} 第{N}章
> 基于 style_profile_{N}.json 定量数据

## 1. 叙事声音与语气

（填入：冷峻/热烈/讽刺/温情/...，附原文例句）

## 2. 对话风格

（填入：句子长短、口头禅、方言痕迹、对话节奏）

## 3. 场景描写特征

（填入：五感偏好、意象选择、描写密度、环境与情绪的关联）

## 4. 转折与衔接手法

（填入：场景切换、时间跳跃、段落过渡）

## 5. 节奏特征

（填入：长短句分布、段落长度、高潮/舒缓交替）

## 6. 词汇偏好

（填入：高频特色用词、比喻倾向、口语化程度）

## 7. 情绪表达方式

（填入：直白抒情 vs 动作外化、内心独白频率）

## 8. 独特习惯

（填入：值得模仿的个人写作习惯）
"""

STRATEGY_TEMPLATE = """# 叙事策略：第{N}章

> 来源：{源书名} 第{N}章

## 排除项

（填入：模仿了会暴露抄源文的特征，至少2个）

1.
2.

## 节奏骨架

- 情绪强度变化：（填入具体数值，如 5→7→8→6）
- 钩子位置和类型：（填入：章末钩子是悬念/反转/甜/虐？）
- 爽点公式：（填入：抽象描述，如"弱者展示实力→强者震惊"）
- 节奏模式：（填入：几段日常+几段冲突+几段甜？）
- 场景切换频率：（填入：快/中/慢）

## 叙事策略

### 信息差设计

（填入：谁知道什么、谁知道谁不知道、读者知道什么？）

### 悬念机制

（填入：用什么制造好奇心？在哪里留钩子？）

### 情绪操控

（填入：用什么手法让读者笑/紧张/心动？）

### 视角策略

（填入：为什么选这个视角？限制了什么信息？）

### 节奏意图

（填入：为什么这里快？为什么这里慢？）
"""

OUTLINE_TEMPLATE = """# 章纲：第{N}章

## 第{N}章 [章名]

- 核心事件：（填入：2-3句话，原创事件）
- 因果逻辑：（填入：A→B→C→D，每个环节一句话）
- 触发逻辑：（填入：为什么发生，必须和源文不同）
- 节奏模式：（填入：情绪强度变化，如 低→高→低）
- 钩子：（填入：章末钩子，1句话）
- 爽点来源：（填入：爽感公式，如"身份反转""装逼打脸"）
- 原创元素：（填入：至少1个源文完全没有的元素）
"""

CONCEPT_TEMPLATE = """# 新书概念

## 基本信息
- **书名**：
- **类型**：
- **标签**：
- **体量**：{章节数}章
- **一句话梗概**：

## 核心卖点

1.
2.
3.

## 人设差异化检查

| 检查项 | 源文 | 新书（必须不同） |
|--------|------|-----------------|
| CP互动模式 | | |
| 女主独特身份 | | |
| 相识方式 | | |

## NPC 命名映射表

| 源文角色 | 新书角色 | 身份 | 性格差异 |
|---------|---------|------|---------|
| | | | |

## 故事弧线

### 第一幕（1-{act1}章）

### 第二幕（{act2}-{act3}章）

### 第三幕（{act4}-{章节数}章）

## 差异化

1.
2.
3.
"""

BIBLE_TEMPLATE = """# 世界观设定

## 时代背景

## 主要势力

### 势力A

### 势力B

## 核心设定

（根据题材填写：穿书规则/修炼体系/科技设定/社会规则等）

## 关键道具

1.
2.
3.
"""

ARC_TEMPLATE = """# 全书弧线骨架

## 全书情感曲线

| 章范围 | 情绪类型 | 强度(1-10) | 功能 | 设计理由 |
|--------|---------|-----------|------|---------|
| 1-{seg1} | | | 开局 | |
| {seg2}-{seg3} | | | 推进 | |
| {seg4}-{seg5} | | | 高潮 | |
| {seg6}-{章节数} | | | 收尾 | |
（根据实际章节数调整段落划分）

## 角色成长主线

### 男主：从[A]到[B]

| 阶段 | 章范围 | 状态 | 关键转折 |
|------|--------|------|---------|

### 女主：从[C]到[D]

| 阶段 | 章范围 | 状态 | 关键转折 |
|------|--------|------|---------|

## 核心伏笔清单

| 伏笔 | 埋设阶段 | 预计回收阶段 | 优先级 |
|------|---------|-------------|--------|
"""

MAPPING_TEMPLATE = """# 章节顺序映射

| 新书章号 | 源文章号 | 功能 | 匹配理由 |
|---------|---------|------|---------|
"""

HOOK_TEMPLATE = """# 钩子工程分析：第{N}章

> 来源：{源书名} 第{N}章

## 1. 段落钩子

（填入：作者怎么在段落结尾勾住读者往下读？用了什么技法？引用原文例句）

## 2. 章首钩子

（填入：开头几段怎么抓住注意力？第一句话是什么类型的钩子？）

## 3. 章末钩子

（填入：结尾怎么让读者必须翻页？是悬念、反转、情感、还是信息缺口？）

## 4. 情绪钩子

（填入：作者怎么让读者在意角色？用了什么情感绑定技法？）

## 5. 信息钩子

（填入：作者怎么制造「想知道答案」的欲望？藏了什么信息？）

## 6. 反预期钩子

（填入：作者怎么打破读者预期？在哪里做了反转？效果是什么？）
"""


def create_style_templates(count, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(1, count + 1):
        path = os.path.join(output_dir, f"style_guide_{i}.md")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(STYLE_TEMPLATE.replace("{N}", str(i)))
    print(f"Created {count} style guide templates in {output_dir}")


def create_strategy_templates(count, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(1, count + 1):
        path = os.path.join(output_dir, f"strategy_guide_{i}.md")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(STRATEGY_TEMPLATE.replace("{N}", str(i)))
    print(f"Created {count} strategy guide templates in {output_dir}")


def create_hook_templates(count, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(1, count + 1):
        path = os.path.join(output_dir, f"hook_guide_{i}.md")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(HOOK_TEMPLATE.replace("{N}", str(i)))
    print(f"Created {count} hook guide templates in {output_dir}")


def create_outline_templates(count, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(1, count + 1):
        path = os.path.join(output_dir, f"章纲_{i}.md")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(OUTLINE_TEMPLATE.replace("{N}", str(i)))
    print(f"Created {count} chapter outline templates in {output_dir}")


def create_concept_template(output_dir, chapter_count=188):
    os.makedirs(output_dir, exist_ok=True)
    act1 = max(10, chapter_count // 6)
    act2 = act1 + 1
    act3 = act1 + chapter_count // 3
    act4 = act3 + 1
    content = CONCEPT_TEMPLATE.replace("{章节数}", str(chapter_count))
    content = content.replace("{act1}", str(act1))
    content = content.replace("{act2}", str(act2))
    content = content.replace("{act3}", str(act3))
    content = content.replace("{act4}", str(act4))
    path = os.path.join(output_dir, "新书概念.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created concept template in {output_dir}")


def create_bible_template(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "story_bible.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(BIBLE_TEMPLATE)
    print(f"Created story bible template in {output_dir}")


def create_arc_template(output_dir, chapter_count=188):
    os.makedirs(output_dir, exist_ok=True)
    seg = chapter_count // 4
    content = ARC_TEMPLATE.replace("{章节数}", str(chapter_count))
    content = content.replace("{seg1}", str(seg))
    content = content.replace("{seg2}", str(seg + 1))
    content = content.replace("{seg3}", str(seg * 2))
    content = content.replace("{seg4}", str(seg * 2 + 1))
    content = content.replace("{seg5}", str(seg * 3))
    content = content.replace("{seg6}", str(seg * 3 + 1))
    path = os.path.join(output_dir, "全书弧线骨架.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created arc skeleton template in {output_dir}")


def create_mapping_template(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "章节顺序.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(MAPPING_TEMPLATE)
    print(f"Created chapter mapping template in {output_dir}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法:")
        print("  python create_templates.py style <章节数> <输出目录>")
        print("  python create_templates.py hook <章节数> <输出目录>")
        print("  python create_templates.py outline <章节数> <输出目录>")
        print("  python create_templates.py concept <输出目录> [章节数]")
        print("  python create_templates.py bible <输出目录>")
        print("  python create_templates.py arc <输出目录>")
        print("  python create_templates.py mapping <输出目录>")
        print("  python create_templates.py all <章节数> <蒸馏目录> <设定目录> <大纲目录>")
        sys.exit(1)

    template_type = sys.argv[1]

    if template_type == 'style':
        count = int(sys.argv[2])
        output_dir = sys.argv[3] if len(sys.argv) > 3 else '.'
        create_style_templates(count, output_dir)
    elif template_type == 'hook':
        count = int(sys.argv[2])
        output_dir = sys.argv[3] if len(sys.argv) > 3 else '.'
        create_hook_templates(count, output_dir)
    elif template_type == 'outline':
        count = int(sys.argv[2])
        output_dir = sys.argv[3] if len(sys.argv) > 3 else '.'
        create_outline_templates(count, output_dir)
    elif template_type == 'concept':
        output_dir = sys.argv[2]
        chapter_count = int(sys.argv[3]) if len(sys.argv) > 3 else 188
        create_concept_template(output_dir, chapter_count)
    elif template_type == 'bible':
        create_bible_template(sys.argv[2])
    elif template_type == 'arc':
        create_arc_template(sys.argv[2])
    elif template_type == 'mapping':
        create_mapping_template(sys.argv[2])
    elif template_type == 'all':
        count = int(sys.argv[2])
        distill_dir = sys.argv[3]
        setting_dir = sys.argv[4]
        outline_dir = sys.argv[5]
        create_style_templates(count, distill_dir)
        create_hook_templates(count, distill_dir)
        create_outline_templates(count, outline_dir)
        create_concept_template(setting_dir, count)
        create_bible_template(setting_dir)
        create_arc_template(setting_dir, count)
        create_mapping_template(setting_dir)
    else:
        print(f"未知类型: {template_type}")
        sys.exit(1)
