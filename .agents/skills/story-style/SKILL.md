---
name: story-style
description: |
  源文分析：拆章+风格指纹+多模式插件分析。
  当前模式：style（inkos 8维度）、hook（钩子工程学）。
  触发条件：用户说「分析风格」「跑风格分析」「提取风格」，或直接传源文文件路径。
  加新模式只需在 analysis-modes.json 加配置+创建prompt文件。
argument-hint: <源文.txt路径>
allowed-tools: Bash(python *) Bash(ls *) Bash(mkdir *)
shell: powershell
---

# story-style

> 源文分析，插件式，可缓存。所有工具和prompt引用 story-engine。

## 启动时询问

运行前先问用户两个问题：

**1. 分析范围**：
- 前10章（快速预览）
- 前30章（标准）
- 全本（完整）

**2. 分析模式**（读取 `analysis-modes.json` 中 enabled 的模式，列出选项）：
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
    └── hook_guide_N.md            # hook 插件输出
```

## 流程

### 0.1 拆章
```bash
python .agents/skills/story-engine/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
```

### 0.2 风格指纹（脚本）
```bash
mkdir -Force novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
```

### 0.3 创建分析模板（脚本）

读取 `analysis-modes.json`，为每个 enabled 的模式创建模板：

```bash
python .agents/skills/story-engine/tools/create_templates.py style <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/create_templates.py hook <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
```

### 0.4 分析（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。**

每个 agent 读1个源文，输出该章所有模式的 guide 文件。

Task prompt 见 `.agents/skills/story-engine/prompts/` 下各模式的 prompt 文件。

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
