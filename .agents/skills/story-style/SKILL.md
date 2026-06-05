---
name: story-style
description: |
  源文分析：拆章+风格指纹+多模式插件分析。
  当前模式：plot（情节结构）、style（inkos 8维度）、hook（钩子工程学）、character（角色塑造）。
  触发条件：用户说「分析风格」「跑风格分析」「提取风格」，或直接传源文文件路径。
  加新模式只需在 analysis-modes.json 加配置+创建prompt文件。
argument-hint: <源文.txt路径>
allowed-tools: Bash(python *) Bash(ls *) Bash(mkdir *)
shell: powershell
---

# story-style

> 源文分析，插件式，可缓存。所有工具和prompt引用 story-engine。

## ⚠️ 核心规则

1. **每个 agent 只分析1章，禁止合并多章到同一个 agent**
2. **plot 模式优先级最高**（章纲生成的必需前置），必须先于 hook/character 完成
3. 批次大小固定为 10 agents 并行

## 启动时询问

运行前先问用户两个问题：

**1. 分析范围**：
- 前10章（快速预览）
- 前30章（标准）
- 全本（完整）

**2. 分析模式**（读取 `analysis-modes.json` 中 enabled 的模式，列出选项）：
- plot（情节结构）⚠️ 优先级最高
- style（inkos 8维度）
- hook（钩子工程学）
- character（角色塑造）
- 全部

## 共享文件

- 工具：`.agents/skills/story-engine/tools/`
- 配置：`.agents/skills/story-engine/analysis-modes.json`
- prompt：`.agents/skills/story-engine/prompts/`

## 输出

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/                          # 拆章后章节
└── 蒸馏/mode-b/
    ├── style_profile_N.json       # 脚本指纹
    ├── style_guide_N.md           # style 插件输出
    ├── hook_guide_N.md            # hook 插件输出
    ├── character_guide_N.md       # character 插件输出
    └── plot_guide_N.md            # plot 插件输出（优先级最高，章纲必需）
```

## 执行顺序

⚠️ **plot 必须先完成**，因为章纲生成依赖 plot_guide_N.md。

```
plot（第1批）→ plot（第2批）→ ... → plot（全部完成）
                                    ↓
                    style + hook + character（并行）
```

## 流程

⚠️ **时间统计**：每步操作前后调用计时工具，记录耗时到会话 `style-{作者名}-{书名}`。

### 0.1 拆章
```bash
python .agents/skills/story-engine/tools/timer.py start "拆章" --session "style-{作者名}-{书名}"
python .agents/skills/story-engine/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
python .agents/skills/story-engine/tools/timer.py stop "拆章" --session "style-{作者名}-{书名}"
```

### 0.2 风格指纹（脚本）
```bash
python .agents/skills/story-engine/tools/timer.py start "风格指纹" --session "style-{作者名}-{书名}"
mkdir -Force novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
python .agents/skills/story-engine/tools/timer.py stop "风格指纹" --session "style-{作者名}-{书名}"
```

### 0.3 创建分析模板（脚本）

读取 `analysis-modes.json`，为每个 enabled 的模式创建模板。**plot 优先创建**：

```bash
python .agents/skills/story-engine/tools/timer.py start "创建模板" --session "style-{作者名}-{书名}"
python .agents/skills/story-engine/tools/create_templates.py plot <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/create_templates.py style <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/create_templates.py hook <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/create_templates.py character <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/timer.py stop "创建模板" --session "style-{作者名}-{书名}"
```

### 0.4 分析（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。** 每批启动10个独立 Task。

每个 agent 读1个源文，输出该章所有模式的 guide 文件。

**执行顺序**：plot 必须先全部完成，再启动 hook/character/style。

```bash
python .agents/skills/story-engine/tools/timer.py start "LLM分析" --session "style-{作者名}-{书名}"
# 第1批：10 agents 并行，每 agent 处理1章 plot
# 第2批：10 agents 并行，每 agent 处理1章 plot
# ... 直到 plot 全部完成
# 然后：hook/character/style 并行（每 agent 处理1章的所有模式）
python .agents/skills/story-engine/tools/timer.py stop "LLM分析" --session "style-{作者名}-{书名}"
```

Task prompt 见 `.agents/skills/story-engine/prompts/` 下各模式的 prompt 文件。

### 0.5 生成时间报告

```bash
python .agents/skills/story-engine/tools/timer.py report --session "style-{作者名}-{书名}" --output "novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/timing_report.md"
```

## 插件扩展

加新模式只需：
1. 创建 `.agents/skills/story-engine/prompts/{mode}-analysis-task.md`
2. 在 `.agents/skills/story-engine/analysis-modes.json` 加一行配置
3. 在 `create_templates.py` 加一个 template 函数

## 缓存策略

- 所有模式的 guide 文件齐全 → 跳过
- 全量扫描所有 guide 文件字符数，低于600字的视为未完成，需重新分析
- 空模板（仍含占位文字）= 未完成，需重新分析
- 手动刷新 → 删除 `蒸馏/mode-b/` 下对应文件
