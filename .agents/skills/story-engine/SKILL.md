---
name: story-engine
description: |
  仿写引擎 vPlan：全书规划先行，一次出稿。
  触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
  全书规划（弧线+章纲+映射）在写作前完成，写作阶段纯并行无后处理。
  不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-engine

> 全书规划先行，纯写作出稿。

## 文件结构

⚠️ **章节命名格式**：`第N章`（N 为阿拉伯数字），如 `第1章`、`第2章`、`第101章`。
- ❌ 禁止：第一章、第二章、第０１章
- ✅ 正确：第1章、第2章、第101章
- 文件名、章节标题、引用全部统一用此格式

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/
│   ├── 第1章.txt
│   ├── 第2章.txt
│   └── ...
├── 蒸馏/mode-b/
│   ├── style_profile_1.json     # 脚本指纹
│   ├── style_guide_1.md         # LLM inkos 8维度风格指南
│   ├── plot_guide_1.md          # LLM 情节指南（骨架+血肉+排除项）
│   └── ...

仿写/{新书名}/                    ⚠️ 用新书名，不是源文名
├── 设定/
│   ├── 新书概念.md（3候选书名+卖点+人设+故事弧线+NPC映射）
│   ├── 简介.md（3种风格：标准版/悬念版/甜宠版）
│   ├── story_bible.md
│   ├── 全书弧线骨架.md
│   ├── plot_overview.md
│   ├── 章节顺序.md
│   └── 支线大纲.md
├── 大纲/章纲_N.md
└── 正文/第N章.txt
```

⚠️ 产出目录：`仿写/{新书名}/`（不是根目录，不是 `仿写/仿写/`）
⚠️ `{新书名}` 由 A1 agent 在新书概念中生成（3选1），目录在 A1 完成后确定

## 去重等级

默认 Lv1+Lv2。Lv2 触发逻辑标准（至少满足2条）：起因不同、动机不同、后果不同、参与人不同。

---

## Phase 0：源文分析（并行，插件式）

⚠️ Phase 0 与 Phase 1.1 可并行启动，不阻塞弧线骨架。
⚠️ 具体编排步骤见「开书编排」。
⚠️ **每个 agent 只分析1章，禁止合并多章到同一个 agent。**

### 分析范围（自动决策，无需询问用户）

- 前10章（快速预览，~5分钟）
- 前30章（标准，~15分钟）
- 全本（完整，~40分钟）

默认：全本。

### 分析模式（读取 `analysis-modes.json`）

当前启用的模式（按 order 排序）：

| 模式 | 输出文件 | 说明 | 优先级 | 执行顺序 |
|------|---------|------|--------|---------|
| plot | plot_guide_N.md | 情节结构（章纲必需前置） | 1 | 1 |
| style | style_guide_N.md | inkos 8维度文风分析 | 2 | 2 |
| hook | hook_guide_N.md | 钩子工程学 | 3 | 3 |
| character | character_guide_N.md | 角色塑造 | 3 | 4 |

**执行顺序**：按 order 排序，同 priority 可并行。plot 必须先全部完成。

### 流程

1. 检查 `蒸馏/mode-b/` 下是否已有各模式的 guide 文件 → 已有则跳过
2. 拆章（如源文章节已存在则跳过）
3. 创建蒸馏模板（`python create_templates.py all <章节数> <输出目录>`）
4. 按 order 分批分析：
   - order=1（plot）：10 agents 并行
   - order=2（style）：10 agents 并行
   - order=3（hook/character）：可并行，10 agents 并行
   - 每个 agent 只处理1章

### 插件架构

分析模式定义在 `analysis-modes.json`，按 `priority` 和 `order` 排序执行。

**加新模式只需 2 步**：
1. 在 `analysis-modes.json` 加一行配置
2. 创建 `prompts/{mode}-analysis-task.md`

模板自动从 `templates/` 目录读取，或使用内置默认模板。无需改代码。

写章 agent 自动读取蒸馏目录下所有 `*_guide_*.md` 文件，无需改 write-chapter.md。

---

## Phase 1：全书规划（每本新书都要做）

字数约束：2000-2500字，硬上限3000字。
⚠️ 具体编排步骤见「开书编排」。

### 依赖关系

```
Phase 1.0 设定/大纲模板 ──→ Phase 1.1 弧线骨架（无依赖，立即启动）
                          └── Phase 0 蒸馏（并行）
                              ├── plot 蒸馏（必需，优先完成）
                              ├── style/hook/character 蒸馏（可选，增强质量）
                              └── Phase 1.2 章纲（逐章，等 plot 完成）
                                  └── Phase 1.3 章节映射（等全部章纲完成）
```

### 1.0 创建设定/大纲模板（脚本，一次性，无依赖）

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录> <大纲目录>
```

示例（148章）：
```bash
python .agents/skills/story-engine/tools/create_templates.py setup 148 仿写/新书名/设定 仿写/新书名/大纲
```

⚠️ 已存在的文件不会被覆盖。可安全重复运行。
⚠️ 此命令只创建设定+大纲模板，不依赖蒸馏目录。

### 1.1 新书概念 + 全书弧线骨架（1 agent，无依赖，立即启动）

- 新书概念.md：**3个候选书名**（标推荐）、核心卖点、NPC命名映射表（必填）、故事弧线（三幕结构）、差异化
- 简介.md：**3种风格**（标准版/悬念版/甜宠版），每种150-250字完整简介
- story_bible.md
- 题材识别：应用 [prompts/genre-management.md](prompts/genre-management.md) 中的 fatigue 词表

Task prompt 见 [prompts/arc-skeleton.md](prompts/arc-skeleton.md)。输出保存到 `设定/全书弧线骨架.md`。

⚠️ 弧线骨架不依赖蒸馏，可与 Phase 0 并行。
⚠️ 新书概念必须包含 3 个候选书名（标推荐）。简介单独生成为 `简介.md`，包含 3 种风格。

### 1.2 章纲生成（10 agents × N批，并行，逐章启动）

⚠️ **每个 agent 只生成1章章纲，禁止合并多章到同一个 agent。** 每批启动10个独立 Task。

前置条件：该章的 `plot_guide_X.md`（必需）已在蒸馏目录中。
可选读取：蒸馏目录下所有其他 `*_guide_X.md` 文件（自动发现，无需逐个指定）。
可逐章启动，不必等全部蒸馏完成。

Task prompt 见 [prompts/chapter-outline.md](prompts/chapter-outline.md)。每章输出保存到 `大纲/章纲_N.md`。

### 1.3 全书章节顺序映射（1 agent，依赖全部章纲完成）

Task prompt 见 [prompts/chapter-mapping.md](prompts/chapter-mapping.md)。输出保存到 `设定/章节顺序.md`。

---

## 开书编排（端到端，agent 自动执行）

用户说「仿写」「用vPlan写」「帮我仿写这本书」时，按以下步骤自动执行，不需要用户输任何命令。

⚠️ **时间统计**：每步操作前后调用计时工具，记录耗时到会话 `vplan-{新书名}`。

### Step 0：定位源文

1. 检查用户是否提供了源文路径（.txt 文件或目录）
2. 如果是目录，查找目录下的 .txt 文件
3. 如果没有提供，扫描 `novel-download-authors/` 下所有作者目录，列出可选源文
4. 确定 `{作者名}` 和 `{源书名}`

⚠️ **目录命名**：项目目录使用新书名，不是源文名。即 `仿写/{新书名}/`，新书名由 A1 agent 在新书概念中生成。
⚠️ 在 A1 完成前，可用临时目录名（如 `仿写/temp-{timestamp}/`），A1 完成后重命名为正式书名。

### Step 1：创建项目目录 + 设定/大纲模板

```bash
python .agents/skills/story-engine/tools/timer.py start "创建模板" --session "vplan-{新书名}"
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录> <大纲目录>
python .agents/skills/story-engine/tools/timer.py stop "创建模板" --session "vplan-{新书名}"
```

- 章节数：先用拆章脚本得到源文章节数，或用户提供
- 设定目录：`仿写/{新书名}/设定/`
- 大纲目录：`仿写/{新书名}/大纲/`

⚠️ **全本蒸馏必须完成后再进入 Step 3**，确保弧线骨架有完整的情节参考。

### Step 2：全本蒸馏

```bash
python .agents/skills/story-engine/tools/timer.py start "全本蒸馏" --session "vplan-{新书名}"
```
- 加载 story-style skill，执行 Phase 0 完整流程
- **⚠️ plot 优先**：先完成全部 plot 蒸馏，再启动 hook/character/style
- 10 agents 并行分析，逐批完成
- 每个 agent 只处理1章

```bash
python .agents/skills/story-engine/tools/timer.py stop "全本蒸馏" --session "vplan-{新书名}"
```

### Step 2.5：生成情节概览

```bash
python .agents/skills/story-engine/tools/extract_plot_overview.py <蒸馏目录> <设定目录>/plot_overview.md
```

- 蒸馏目录：`novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/`
- 设定目录：`仿写/{新书名}/设定/`
- 生成 plot_overview.md，供后续 agents 读取

### Step 3：弧线骨架（3 agents 并行）

全本蒸馏完成后，**同时启动 3 个 agent**：

| Agent | 任务 | 输出文件 |
|-------|------|---------|
| A1 | 新书概念（人设、NPC映射） | 设定/新书概念.md |
| A2 | 世界观设定 | 设定/story_bible.md |
| A3 | 全书弧线骨架（情感曲线、角色成长、伏笔） | 设定/全书弧线骨架.md |

```bash
python .agents/skills/story-engine/tools/timer.py start "弧线骨架" --session "vplan-{新书名}"
# 3 agents 并行，每个读取 plot_guide_*.md
python .agents/skills/story-engine/tools/timer.py stop "弧线骨架" --session "vplan-{新书名}"
```

Task prompt 见 prompts/arc-skeleton.md。

### Step 4：章纲生成（流水线）

弧线骨架完成后，**分批启动章纲生成**：
- 第1批：第1-10章章纲（10 agents 并行）
- 第2批：第11-20章章纲（10 agents 并行）
- ... 逐批进行

```bash
python .agents/skills/story-engine/tools/timer.py start "章纲生成" --session "vplan-{新书名}"
# 10 agents 并行，逐批完成
python .agents/skills/story-engine/tools/timer.py stop "章纲生成" --session "vplan-{新书名}"
```

Task prompt 见 prompts/chapter-outline.md。

### Step 5：写章（流水线，与章纲并行）

**流水线优化**：章纲第1批完成后，立即开始写章第1批，同时继续章纲第2批。

```
章纲：  [第1批] [第2批] [第3批] ...
             ↓      ↓      ↓
写章：  [第1批] [第2批] [第3批] ...
```

```bash
python .agents/skills/story-engine/tools/timer.py start "写章" --session "vplan-{新书名}"
# 10 agents 并行，逐批完成
python .agents/skills/story-engine/tools/timer.py stop "写章" --session "vplan-{新书名}"
```

Task prompt 见 prompts/write-chapter.md。

### Step 7：导出

```bash
python .agents/skills/story-engine/tools/timer.py start "导出" --session "vplan-{新书名}"
cat 仿写/{新书名}/正文/*.txt > 仿写/{新书名}/{新书名}.txt
python .agents/skills/story-engine/tools/timer.py stop "导出" --session "vplan-{新书名}"
```

### Step 8：生成时间报告

```bash
python .agents/skills/story-engine/tools/timer.py report --session "vplan-{新书名}" --output "仿写/{新书名}/timing_report.md"
```

---

## Phase 2：纯写作（每批循环）

⚠️ 具体编排步骤见「开书编排」Step 5。

### B4 写章（10 agents 并行，`context: fork`）

⚠️ **每个 agent 只写1章，禁止合并多章到同一个 agent。** 每批启动10个独立 Task。

Task prompt 见 [prompts/write-chapter.md](prompts/write-chapter.md)。每章输出保存到 `正文/第N章.txt`。

### B5 循环
1. 检查是否还有未写章节
2. 有 → 启动下一批
3. 无 → 导出

---

## Phase 3：导出
```bash
cat 仿写/{新书名}/正文/*.txt > 仿写/{新书名}/{新书名}.txt
```

---

## 断点续传

使用 `timer.py` 的检查点功能，支持中断后继续。

### 会话命名

```
vplan-{新书名}          # 全流程会话
style-{作者名}-{书名}   # 蒸馏会话
```

### 蒸馏阶段（逐章检查点）

```bash
# 开始蒸馏第1章
python timer.py start "蒸馏-第1章" --session "vplan-{新书名}"

# 蒸馏完成，记录检查点
python timer.py mark-completed "蒸馏-第1章" --session "vplan-{新书名}"

# 查看哪些章节待处理
python timer.py pending --session "vplan-{新书名}"
```

### 章纲阶段（逐章检查点）

```bash
python timer.py mark-completed "章纲-第1章" --session "vplan-{新书名}"
```

### 写章阶段（逐章检查点）

```bash
python timer.py mark-completed "写章-第1章" --session "vplan-{新书名}"
```

### 断点续传流程

```bash
# 1. 检查会话状态
python timer.py status --session "vplan-{新书名}"

# 2. 查看待完成任务
python timer.py pending --session "vplan-{新书名}"

# 3. 检查特定任务是否完成
python timer.py is-completed "蒸馏-第1章" --session "vplan-{新书名}"

# 4. 继续未完成的任务
# ... 只运行 pending 的任务
```

### 命令参考

| 命令 | 说明 |
|------|------|
| `start <任务>` | 开始计时 |
| `stop <任务>` | 结束计时 |
| `checkpoint <任务> --status <状态>` | 记录检查点 |
| `mark-completed <任务>` | 标记完成 |
| `mark-failed <任务>` | 标记失败 |
| `is-completed <任务>` | 检查是否完成（返回 true/false） |
| `status` | 显示会话状态 |
| `pending` | 显示待完成任务 |
| `report` | 生成时间报告 |
