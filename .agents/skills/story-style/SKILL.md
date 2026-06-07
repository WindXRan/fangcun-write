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
2. **plot 单独一批，style+hook+character 合并一批**（共2批，不是4批）
3. **模板结构嵌入 prompt**，agent 直接生成文件，不读取模板文件
4. **style_profile 必须读取**，提供定量锚点，禁止跳过
5. 批次大小固定为 10 agents 并行

## 启动时询问

运行前先问用户两个问题：

**1. 分析范围**：
- 前10章（快速预览）
- 前30章（标准）
- 全本（完整）

**2. 分析模式**（读取 `analysis-modes.json` 中 enabled 的模式，列出选项）：
- plot（情节结构）
- style（inkos 8维度）
- hook（钩子工程学）
- character（角色塑造）
- 全部

## 共享文件

- 工具：`.agents/skills/story-engine/tools/`
- 配置：`.agents/skills/story-engine/analysis-modes.json`
- prompt：`.agents/skills/story-engine/prompts/`（模板结构已嵌入，agent 不读取这些文件）

## 输出

```
projects/{作者名}/{源书名}/
├── _cache/chapters/               # 拆章后章节
│   └── ch_001.txt
└── _cache/analysis/               # 源文分析缓存
    ├── style_profile_001.json     # 脚本指纹（定量锚点）
    ├── plot_001.md                # plot 输出
    ├── style_001.md               # style 输出
    ├── hook_001.md                # hook 输出
    └── character_001.md           # character 输出
```

## 执行顺序

两批完成，plot 先行（质量要求最高），style+hook+character 合并（省 agent）：

```
第1批：plot（10 agents 并行，每 agent 1章）→ 完成后启动第2批
第2批：style+hook+character（10 agents 并行，每 agent 1章3模式）
```

## 流程

⚠️ **时间统计**：每步操作前后调用计时工具，记录耗时到会话 `style-{作者名}-{书名}`。

### 0.1 拆章
```bash
python .agents/skills/story-engine/tools/timer.py start "拆章" --session "style-{作者名}-{书名}"
python .agents/skills/story-engine/tools/split_chapters_generic.py <源文.txt> projects/{作者名}/{源书名}/_cache/chapters/
python .agents/skills/story-engine/tools/timer.py stop "拆章" --session "style-{作者名}-{书名}"
```

### 0.2 风格指纹（脚本）
```bash
python .agents/skills/story-engine/tools/timer.py start "风格指纹" --session "style-{作者名}-{书名}"
mkdir -Force projects/{作者名}/{源书名}/_cache/analysis/
python .agents/skills/story-engine/tools/calc_style_profile.py projects/{作者名}/{源书名}/_cache/chapters/第N章.txt -o projects/{作者名}/{源书名}/_cache/analysis/style_profile_N.json
python .agents/skills/story-engine/tools/timer.py stop "风格指纹" --session "style-{作者名}-{书名}"
```

### 0.3 创建分析模板（脚本）

创建模板文件用于缓存检查（未完成章节检测），但 **agent 不读取模板文件**，模板结构已嵌入 prompt。

```bash
python .agents/skills/story-engine/tools/timer.py start "创建模板" --session "style-{作者名}-{书名}"
python .agents/skills/story-engine/tools/create_templates.py plot <章节数> projects/{作者名}/{源书名}/_cache/analysis/
python .agents/skills/story-engine/tools/create_templates.py style <章节数> projects/{作者名}/{源书名}/_cache/analysis/
python .agents/skills/story-engine/tools/create_templates.py hook <章节数> projects/{作者名}/{源书名}/_cache/analysis/
python .agents/skills/story-engine/tools/create_templates.py character <章节数> projects/{作者名}/{源书名}/_cache/analysis/
python .agents/skills/story-engine/tools/timer.py stop "创建模板" --session "style-{作者名}-{书名}"
```

### 0.4 分析（2批，10 agents × N批，并行）

⚠️ **每个 agent 只分析1章。** 每批启动10个独立 Task。

**两批结构**：
- **第1批 plot**：每 agent 读源文+style_profile，输出 plot_guide_N.md
- **第2批 style+hook+character**：每 agent 读源文+style_profile，输出3个 guide 文件

**Token 优化要点**：
- plot 单独一批，agent 专注度最高（质量要求最高）
- style+hook+character 合并一批，共享源文上下文，省 agent 数量
- agent 只读源文+style_profile（2个文件），不读取模板文件
- 模板结构嵌入在 prompt 中，agent 直接按结构生成输出

```bash
python .agents/skills/story-engine/tools/timer.py start "LLM分析" --session "style-{作者名}-{书名}"
# 第1批：10 agents 并行，每 agent 处理1章 plot
# 等待第1批全部完成
# 第2批：10 agents 并行，每 agent 处理1章的 style+hook+character
python .agents/skills/story-engine/tools/timer.py stop "LLM分析" --session "style-{作者名}-{书名}"
```

#### Agent Prompt 构造

每个 agent 的 prompt 包含：
1. 角色设定（从对应 prompt 文件提取）
2. 源文路径（agent 读取）
3. style_profile 路径（agent 读取，定量锚点）
4. 输出结构（嵌入在 prompt 中，从对应 prompt 文件提取）
5. 质量要求
6. 输出路径

prompt 文件位于 `.agents/skills/story-engine/prompts/`：
- `plot-guide-task.md` — plot 模板结构
- `style-analysis-task.md` — style 模板结构
- `hook-analysis-task.md` — hook 模板结构
- `character-analysis-task.md` — character 模板结构

构造时将 prompt 文件中的【输出结构】部分嵌入 agent prompt，替换 `{源书名}` 和 `{作者名}`。

**第1批（plot）prompt**：从 `plot-guide-task.md` 提取，1 agent 输出1个文件。
**第2批（style+hook+character）prompt**：合并3个 prompt 文件的输出结构到同一个 agent prompt，1 agent 输出3个文件。

### 0.5 生成时间报告

```bash
python .agents/skills/story-engine/tools/timer.py report --session "style-{作者名}-{书名}" --output "projects/{作者名}/{源书名}/_cache/analysis/timing_report.md"
```

## 插件扩展

加新模式只需 2 步：
1. 在 `.agents/skills/story-engine/analysis-modes.json` 加一行配置
2. 创建 `.agents/skills/story-engine/prompts/{mode}-analysis-task.md`（包含【输出结构】）

模板会自动从 `templates/` 目录读取，或使用内置默认模板。无需改代码。

## 缓存策略

- 所有模式的 guide 文件齐全 → 跳过
- 空模板（仍含占位文字）= 未完成，需重新分析
- 手动刷新 → 删除 `_cache/analysis/` 下对应文件

### 检查未完成章节的正确方式

**错误方式**（按文件大小判断）：文件大小不可靠，模板和已完成分析可能大小相近。

**正确方式**（检查模板占位符）：

```powershell
# 列出未完成的章节（仍含模板占位符）
Get-ChildItem "projects/{作者名}/{源书名}/_cache/analysis/{mode}_*.md" | Where-Object { (Get-Content $_.FullName -Raw) -match '（填入：' } | Select-Object -ExpandProperty Name

# 统计未完成数量
Get-ChildItem "projects/{作者名}/{源书名}/_cache/analysis/{mode}_*.md" | Where-Object { (Get-Content $_.FullName -Raw) -match '（填入：' } | Measure-Object | Select-Object -ExpandProperty Count

# 列出已完成的章节
Get-ChildItem "projects/{作者名}/{源书名}/_cache/analysis/{mode}_*.md" | Where-Object { (Get-Content $_.FullName -Raw) -notmatch '（填入：' } | Select-Object -ExpandProperty Name
```

其中 `{mode}` 替换为 `style`、`hook`、`character`、`plot`。

## Token 优化说明

相比旧版（每模式一个 agent），优化后：
- **文件读取减少**：每章从 12 次 Read（4模式×3文件）降到 2 次（源文+style_profile）
- **agent 数量减少**：从 40 个（10章×4模式）降到 20 个（10章×2批）
- **plot 独立一批**：保证最高质量（章纲必需前置）
- **style+hook+character 合并一批**：共享上下文，省 agent 开销
- **模板文件仍由脚本创建**：用于缓存检测，但 agent 不读取
- **style_profile 保留**：提供定量锚点，保证分析质量
