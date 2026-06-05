# -*- coding: utf-8 -*-
"""
批量创建模板文件，从 analysis-modes.json 驱动。
用法：
  python create_templates.py <模式> <章节数> <输出目录>
  python create_templates.py all <章节数> <输出目录>
  python create_templates.py setup <章节数> <设定目录> <大纲目录>

模式自动从 analysis-modes.json 发现，新增模式只需：
1. 在 analysis-modes.json 加配置
2. 在 templates/ 目录加模板文件（可选，有默认模板）
"""

import sys
import os
import json

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "analysis-modes.json")
TEMPLATES_DIR = os.path.join(SKILL_DIR, "templates")

# 默认模板（当 templates/ 目录下没有对应文件时使用）
DEFAULT_TEMPLATES = {
    "style": """# 风格指南：第{N}章

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
""",
    "plot": """# 情节指南：第{N}章

> 来源：{源书名} 第{N}章

## 一、骨架：情节结构

### 本章功能

（填入：本章在全书中的功能是什么？如：开局铺垫/关系推进/冲突升级/高潮爆发/转折收尾）

### 情绪曲线

- 起始情绪：（填入，如：平淡/紧张/甜蜜）
- 情绪强度变化：（填入具体数值，如 5→7→8→6）
- 峰值位置：（填入，如：中段/结尾）
- 结束情绪：（填入，如：悬念/满足/心酸）

### 节奏模式

- 段落节奏：（填入，如：慢热开场→快速冲突→爆发→余韵）
- 场景切换次数：（填入数字）
- 场景切换节奏：（填入，如：快切/慢推/渐进）

### 钩子设计

- 章首钩子：（填入类型，如：悬念/冲突/反常）
- 章中钩子：（填入位置和类型）
- 章末钩子：（填入类型，如：反转/信息缺口/情感悬念/甜点）

---

## 二、血肉：情节桥段

### 核心桥段清单

| 序号 | 情节功能 | 具体描述 | 触发方式 | 情感效果 |
|------|---------|---------|---------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

⚠️ **情节功能**用抽象词：告白/秘密揭露/惊艳亮相/亲吻触发/情敌挑衅/男主救场/误会澄清/身份反转/打脸/撒糖/...
⚠️ **触发方式**写具体：直接台词/回忆杀/意外撞见/第三方揭露/物品触发/环境催化/...

### 关键场景细节

（填入：本章有哪些让读者印象深刻的场景细节？这些是"血肉"，写新书时必须原创）

1.
2.
3.

### 关键台词/对话模式

（填入：本章有哪些标志性对话？说话方式有什么特点？）

1.
2.

---

## 三、排除项

（填入：模仿了会暴露抄源文的特征，至少2个。写新书时必须避开）

1.
2.

---

## 四、可复用的抽象模式

（填入：可以借鉴的"公式"，但必须换具体实现）

- 爽点公式：（如"弱者展示实力→强者震惊"）
- 甜点公式：（如"无意间的亲密→双方心虚"）
- 虐点公式：（如"误解→伤害→真相大白→后悔"）
- 悬念公式：（如"信息缺口→读者好奇→延迟揭露"）

---

## 五、叙事技巧

### 信息差设计

（填入：谁知道什么、谁知道谁不知道、读者知道什么？）

### 悬念机制

（填入：用什么制造好奇心？在哪里留钩子？）

### 情绪操控

（填入：用什么手法让读者笑/紧张/心动？）
""",
    "hook": """# 钩子工程分析：第{N}章

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
""",
    "character": """# 角色塑造分析：第{N}章

> 来源：{源书名} 第{N}章

## 1. 角色立体感

（填入：作者怎么让角色感觉像真人？用了什么细节？引用原文例句）

## 2. 性格外化技法

（填入：作者怎么通过动作/对话/反应展示性格，而不是直说「她很XX」？）

## 3. 角色差异化

（填入：不同角色的说话方式、行为模式有什么区别？怎么一眼分出谁是谁？）

## 4. 配角塑造

（填入：配角怎么做到有存在感但不抢戏？用了什么技法？）

## 5. 角色关系张力

（填入：角色之间的关系怎么制造有趣/紧张/甜蜜的动态？）

## 6. 角色成长暗示

（填入：作者怎么暗示角色在变化？用了什么伏笔或细节？）
"""
}

# 设定/大纲模板
SETUP_TEMPLATES = {
    "outline": """# 章纲：第{N}章

## 第{N}章 [章名]

- 核心事件：（填入：2-3句话，原创事件）
- 因果逻辑：（填入：A→B→C→D，每个环节一句话）
- 触发逻辑：（填入：为什么发生，必须和源文不同）
- 节奏模式：（填入：情绪强度变化，如 低→高→低）
- 钩子：（填入：章末钩子，1句话）
- 爽点来源：（填入：爽感公式，如"身份反转""装逼打脸"）
- 原创元素：（填入：至少1个源文完全没有的元素）
""",
    "concept": """# 新书概念

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

## 具体场景设计（至少5个）

| 场景 | 章节范围 | 具体内容 | 对应源文场景 |
|------|---------|---------|-------------|
| | | | |

## 故事弧线

### 第一幕（1-{act1}章）

### 第二幕（{act2}-{act3}章）

### 第三幕（{act4}-{章节数}章）
""",
    "bible": """# 世界观设定

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
""",
    "arc": """# 全书弧线骨架

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
""",
    "mapping": """# 章节顺序映射

| 新书章号 | 源文章号 | 功能 | 匹配理由 |
|---------|---------|------|---------|
"""
}


def load_modes_config():
    """从 analysis-modes.json 加载配置"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_template(mode_name):
    """获取模板内容：优先从 templates/ 目录读取，否则用默认模板"""
    # 尝试从 templates/ 目录读取
    template_path = os.path.join(TEMPLATES_DIR, f"{mode_name}.md")
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # 使用默认模板
    if mode_name in DEFAULT_TEMPLATES:
        return DEFAULT_TEMPLATES[mode_name]
    
    return None


def create_guide_templates(mode_name, count, output_dir, use_config_dir=False):
    """为指定模式创建指南模板"""
    config = load_modes_config()
    modes = config.get("modes", {})
    
    if mode_name not in modes:
        print(f"Error: Mode '{mode_name}' not defined in analysis-modes.json")
        print(f"Available modes: {', '.join(modes.keys())}")
        return False
    
    mode_config = modes[mode_name]
    if not mode_config.get("enabled", True):
        print(f"Warning: Mode '{mode_name}' is disabled")
        return False
    
    output_pattern = mode_config.get("output_pattern", f"{mode_name}_guide_{{N}}.md")
    
    # 只在 use_config_dir=True 时使用 json 中的 output_dir
    if use_config_dir:
        output_dir = mode_config.get("output_dir", output_dir)
    
    template = get_template(mode_name)
    if template is None:
        print(f"Error: Template not found for mode '{mode_name}'")
        return False
    
    os.makedirs(output_dir, exist_ok=True)
    created = 0
    for i in range(1, count + 1):
        filename = output_pattern.replace("{N}", str(i))
        path = os.path.join(output_dir, filename)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(template.replace("{N}", str(i)))
            created += 1
    
    print(f"Created {created} {mode_name} guide templates in {output_dir}")
    return True


def create_setup_templates(count, setting_dir, outline_dir):
    """创建设定/大纲模板"""
    os.makedirs(setting_dir, exist_ok=True)
    os.makedirs(outline_dir, exist_ok=True)
    
    # 章纲模板
    for i in range(1, count + 1):
        path = os.path.join(outline_dir, f"章纲_{i}.md")
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(SETUP_TEMPLATES["outline"].replace("{N}", str(i)))
    print(f"Created {count} outline templates in {outline_dir}")
    
    # 新书概念模板
    act1 = max(10, count // 6)
    act2 = act1 + 1
    act3 = act1 + count // 3
    act4 = act3 + 1
    content = SETUP_TEMPLATES["concept"].replace("{章节数}", str(count))
    content = content.replace("{act1}", str(act1))
    content = content.replace("{act2}", str(act2))
    content = content.replace("{act3}", str(act3))
    content = content.replace("{act4}", str(act4))
    path = os.path.join(setting_dir, "新书概念.md")
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"Created concept template in {setting_dir}")
    
    # 世界观模板
    path = os.path.join(setting_dir, "story_bible.md")
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(SETUP_TEMPLATES["bible"])
    print(f"Created story bible template in {setting_dir}")
    
    # 弧线骨架模板
    seg = count // 4
    content = SETUP_TEMPLATES["arc"].replace("{章节数}", str(count))
    content = content.replace("{seg1}", str(seg))
    content = content.replace("{seg2}", str(seg + 1))
    content = content.replace("{seg3}", str(seg * 2))
    content = content.replace("{seg4}", str(seg * 2 + 1))
    content = content.replace("{seg5}", str(seg * 3))
    content = content.replace("{seg6}", str(seg * 3 + 1))
    path = os.path.join(setting_dir, "全书弧线骨架.md")
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"Created arc skeleton template in {setting_dir}")
    
    # 章节映射模板
    path = os.path.join(setting_dir, "章节顺序.md")
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(SETUP_TEMPLATES["mapping"])
    print(f"Created chapter mapping template in {setting_dir}")


def list_modes():
    """列出所有可用模式"""
    config = load_modes_config()
    modes = config.get("modes", {})
    
    print("Available modes:")
    for name, mode in sorted(modes.items(), key=lambda x: x[1].get("order", 99)):
        status = "ON" if mode.get("enabled", True) else "OFF"
        priority = mode.get("priority", "-")
        description = mode.get("description", "")
        print(f"  [{status}] {name} (priority:{priority}) - {description}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  python create_templates.py <模式> <章节数> <输出目录>")
        print("  python create_templates.py all <章节数> <输出目录>")
        print("  python create_templates.py setup <章节数> <设定目录> <大纲目录>")
        print("  python create_templates.py list")
        print("")
        list_modes()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        list_modes()
    elif command == 'setup':
        if len(sys.argv) < 5:
            print("用法: python create_templates.py setup <章节数> <设定目录> <大纲目录>")
            sys.exit(1)
        count = int(sys.argv[2])
        setting_dir = sys.argv[3]
        outline_dir = sys.argv[4]
        create_setup_templates(count, setting_dir, outline_dir)
    elif command == 'all':
        if len(sys.argv) < 4:
            print("用法: python create_templates.py all <章节数> <输出目录>")
            sys.exit(1)
        count = int(sys.argv[2])
        output_dir = sys.argv[3]
        config = load_modes_config()
        modes = config.get("modes", {})
        for mode_name in sorted(modes.keys(), key=lambda x: modes[x].get("order", 99)):
            if modes[mode_name].get("enabled", True):
                create_guide_templates(mode_name, count, output_dir)
    else:
        # 单个模式
        if len(sys.argv) < 4:
            print(f"用法: python create_templates.py {command} <章节数> <输出目录>")
            sys.exit(1)
        count = int(sys.argv[2])
        output_dir = sys.argv[3]
        create_guide_templates(command, count, output_dir)
