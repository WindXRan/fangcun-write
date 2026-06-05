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

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/
├── 蒸馏/mode-b/
│   ├── style_profile_N.json     # 脚本指纹
│   ├── style_guide_N.md         # LLM inkos 8维度风格指南
│   └── strategy_guide_N.md      # LLM 排除项+节奏骨架+叙事策略

仿写/仿写/{新书名}/
├── 设定/
│   ├── 新书概念.md
│   ├── story_bible.md
│   ├── 全书弧线骨架.md
│   ├── 章节顺序.md
│   └── 支线大纲.md
├── 大纲/章纲_N.md
└── 正文/第N章.txt
```

⚠️ 产出目录：`仿写/仿写/{新书名}/`（不是根目录）

## 去重等级

默认 Lv1+Lv2。Lv2 触发逻辑标准（至少满足2条）：起因不同、动机不同、后果不同、参与人不同。

---

## Phase 0：源文分析（并行，插件式）

⚠️ Phase 0 与 Phase 1.1 可并行启动，不阻塞弧线骨架。
⚠️ 具体编排步骤见「开书编排」。

### 分析范围（自动决策，无需询问用户）

- 前10章（快速预览，~5分钟）
- 前30章（标准，~15分钟）
- 全本（完整，~40分钟）

默认：全本。

### 分析模式（读取 `analysis-modes.json`）

当前启用的模式：

| 模式 | 输出文件 | 说明 |
|------|---------|------|
| style | style_guide_N.md | inkos 8维度文风分析 |
| hook | hook_guide_N.md | 钩子工程学 |
| character | character_guide_N.md | 角色塑造 |

默认：全部。

### 流程

1. 检查 `蒸馏/mode-b/` 下是否已有各模式的 guide 文件 → 已有则跳过
2. 拆章（如源文章节已存在则跳过）
3. 创建蒸馏模板（story-style 创建所有 enabled 模式的模板）
4. 10 agents 并行分析

### 插件架构

分析模式定义在 `analysis-modes.json`。

**加新模式只需**：
1. 创建 `prompts/{mode}-analysis-task.md`
2. 在 `analysis-modes.json` 加一行配置
3. `create_templates.py` 加一个 template 函数

写章 agent 自动读取所有 `*_guide_*.md` 文件，无需改 write-chapter.md。

---

## Phase 1：全书规划（每本新书都要做）

字数约束：2000-2500字，硬上限3000字。
⚠️ 具体编排步骤见「开书编排」。

### 依赖关系

```
Phase 1.0 设定/大纲模板 ──→ Phase 1.1 弧线骨架（无依赖，立即启动）
                          └── Phase 0 蒸馏（并行）
                              └── Phase 1.2 章纲（逐章，等对应章蒸馏完成）
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

- 新书概念.md：书名、类型、核心卖点、NPC命名映射表（必填）、故事弧线、差异化
- story_bible.md
- 题材识别：应用 [prompts/genre-management.md](prompts/genre-management.md) 中的 fatigue 词表

Task prompt 见 [prompts/arc-skeleton.md](prompts/arc-skeleton.md)。输出保存到 `设定/全书弧线骨架.md`。

⚠️ 弧线骨架不依赖蒸馏，可与 Phase 0 并行。

### 1.2 章纲生成（10 agents × N批，并行，逐章启动）

⚠️ **每个 agent 只生成1章章纲，禁止合并多章到同一个 agent。**

前置条件：该章的 `strategy_guide_X.md` 和 `style_guide_X.md` 已在蒸馏目录中。
可逐章启动，不必等全部蒸馏完成。

Task prompt 见 [prompts/chapter-outline.md](prompts/chapter-outline.md)。每章输出保存到 `大纲/章纲_N.md`。

### 1.3 全书章节顺序映射（1 agent，依赖全部章纲完成）

Task prompt 见 [prompts/chapter-mapping.md](prompts/chapter-mapping.md)。输出保存到 `设定/章节顺序.md`。

---

## 开书编排（端到端，agent 自动执行）

用户说「仿写」「用vPlan写」「帮我仿写这本书」时，按以下步骤自动执行，不需要用户输任何命令。

### Step 0：定位源文

1. 检查用户是否提供了源文路径（.txt 文件或目录）
2. 如果是目录，查找目录下的 .txt 文件
3. 如果没有提供，扫描 `novel-download-authors/` 下所有作者目录，列出可选源文
4. 确定 `{作者名}` 和 `{源书名}`

### Step 1：创建项目目录 + 设定/大纲模板

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录> <大纲目录>
```

- 章节数：先用拆章脚本得到源文章节数，或用户提供
- 设定目录：`仿写/仿写/{新书名}/设定/`
- 大纲目录：`仿写/仿写/{新书名}/大纲/`

### Step 2：并行启动 Phase 0 + Phase 1.1

**同时启动两个 agent：**

**Agent A：弧线骨架**（无依赖，立即启动）
- 读取 prompts/arc-skeleton.md
- 填写新书概念.md、story_bible.md、全书弧线骨架.md
- 应用 genre-management.md 中的题材识别和 fatigue 词表

**Agent B：源文蒸馏**（并行）
- 加载 story-style skill，执行 Phase 0 完整流程（所有 enabled 模式）
- 10 agents 并行分析，逐批完成

### Step 3：逐章生成章纲

等 Agent A（弧线骨架）完成后，检查 Agent B 的进度：
- 每完成一章的蒸馏（style_guide_N.md 存在），立即启动该章的章纲生成
- 10 agents 并行，不必等全部蒸馏完成

```python
# 伪代码：检查哪些章可以启动章纲
for i in range(1, 章节数+1):
    if exists(f"蒸馏/mode-b/strategy_guide_{i}.md") and exists(f"蒸馏/mode-b/style_guide_{i}.md"):
        # 启动该章的章纲 agent
```

Task prompt 见 prompts/chapter-outline.md。

### Step 4：章节顺序映射

等全部章纲完成后，启动映射 agent。

Task prompt 见 prompts/chapter-mapping.md。

### Step 5：写章

10 agents 并行，每批10章。每章读取：
- 章纲_N.md
- 章节顺序.md 中对应的源文章号
- 蒸馏/mode-b/ 下对应的 *_guide_X.md

Task prompt 见 prompts/write-chapter.md。

### Step 6：导出

```bash
cat 仿写/仿写/{新书名}/正文/*.txt > 仿写/仿写/{新书名}/{新书名}.txt
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
cat 仿写/仿写/{新书名}/正文/*.txt > 仿写/仿写/{新书名}/{新书名}.txt
```
