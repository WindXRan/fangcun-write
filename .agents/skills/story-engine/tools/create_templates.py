# -*- coding: utf-8 -*-
"""
批量创建模板文件，从 analysis-modes.json 驱动。
用法：
  python create_templates.py <模式> <章节数> <输出目录>
  python create_templates.py all <章节数> <输出目录>
   python create_templates.py setup <章节数> <设定目录>

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

## 写章时叙事声音

（填入：用XX语气，注意XX特征）

## 写章时对话写法

（填入：句子长短、口语化程度、角色区分方式）

## 写章时场景描写

（填入：详略程度、环境与情绪的关联方式）

## 写章时转折手法

（填入：场景切换方式、切换节奏）

## 写章时节奏控制

（填入：段落长度偏好、高潮/舒缓段处理方式）

## 写章时用词偏好

（填入：口语化程度、修辞偏好、特色高频词）

## 写章时情绪表达

（填入：情绪外化方式，如"写到XX情绪时用XX方式"）

## 值得模仿的写法

1. （写法 + 示例，仿写时保留技法换内容）
2.
""",
    "plot": """# 情节指南：第{N}章

> 来源：{源书名} 第{N}章

## 写章目标

（填入：本章在全书中完成什么功能）

## 写章节奏骨架

（填入：情绪曲线、场景切换、段落节奏）

## 写章钩子布局

（填入：章首/章中/章末钩子写法）

## 保留功能，换血肉

| 保留的功能 | 新书必须换掉的内容 |
|-----------|-----------------|
| | |

## 写章时必须避开的特征（至少2条）

1.
2.

## 写章可套用的公式

- 爽点公式：
- 虐点公式：
- 悬念公式：

## 写章时用的叙事技巧

（填入：信息差设计、情绪操控方式）
""",
    "hook": """# 钩子指南：第{N}章

> 来源：{源书名} 第{N}章

## 写章时章首钩子

（填入：技法、具体写法、示例）

## 写章时章中钩子

| 位置 | 钩子类型 | 技法 | 仿写时换什么 |
|------|---------|------|-------------|
| | | | |

## 写章时章末钩子

（填入：技法、具体写法、示例）

## 写章时情绪钩子

（填入：共情点、仿写建议）

## 写章时信息钩子

（填入：信息缺口模式、仿写建议）

## 写章时反预期钩子

（填入：反转模式、仿写建议）
""",
    "character": """# 角色指南：第{N}章

> 来源：{源书名} 第{N}章

## 写章时让角色有立体感

（填入：手法、示例、可套用方式）

## 写章时性格外化

（填入：技法、示例、可套用方式）

## 写章时区分角色

| 角色 | 说话特点 | 行为特点 | 区别 |
|------|---------|---------|------|
| | | | |

## 写章时配角写法

（填入：功能、存在感方式、仿写建议）

## 写章时角色关系张力

（填入：张力模式、示例、仿写建议）

## 写章时埋角色成长线

（填入：技法、示例、仿写建议）
"""
}

# 设定/大纲模板
SETUP_TEMPLATES = {
    "setting": """# 新书设定

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

## 人物设定

### 女主
- 身份/背景/性格/目标

### 男主
- 身份/背景/性格/关键人设标签

### 关键配角
- XXX：身份，作用

## NPC 命名映射表

| 源文角色 | 新书角色 | 身份 | 性格差异 |
|---------|---------|------|---------|

## 世界观设定

### 时代背景

### 主要势力

### 核心设定
（根据题材填写：穿书规则/修炼体系/科技设定/社会规则等）

### 与源文的差异化

## 人设差异化检查

| 检查项 | 源文 | 新书（必须不同） |
|--------|------|-----------------|
| CP互动模式 | | |
| 女主独特身份 | | |
| 相识方式 | | |
""",
    "arc": """# 全书弧线

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


def create_setup_templates(count, setting_dir):
    """创建设定模板"""
    os.makedirs(setting_dir, exist_ok=True)
    
    # 新书概念模板
    act1 = max(10, count // 6)
    act2 = act1 + 1
    act3 = act1 + count // 3
    act4 = act3 + 1
    content = SETUP_TEMPLATES["setting"].replace("{章节数}", str(count))
    path = os.path.join(setting_dir, "新书设定.md")
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"Created setting template in {setting_dir}")
    
    # 弧线模板
    seg = count // 4
    content = SETUP_TEMPLATES["arc"].replace("{章节数}", str(count))
    content = content.replace("{seg1}", str(seg))
    content = content.replace("{seg2}", str(seg + 1))
    content = content.replace("{seg3}", str(seg * 2))
    content = content.replace("{seg4}", str(seg * 2 + 1))
    content = content.replace("{seg5}", str(seg * 3))
    content = content.replace("{seg6}", str(seg * 3 + 1))
    path = os.path.join(setting_dir, "全书弧线.md")
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
        print("  python create_templates.py setup <章节数> <设定目录>")
        print("  python create_templates.py list")
        print("")
        list_modes()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'list':
        list_modes()
    elif command == 'setup':
        if len(sys.argv) < 4:
            print("用法: python create_templates.py setup <章节数> <设定目录>")
            sys.exit(1)
        count = int(sys.argv[2])
        setting_dir = sys.argv[3]
        create_setup_templates(count, setting_dir)
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
