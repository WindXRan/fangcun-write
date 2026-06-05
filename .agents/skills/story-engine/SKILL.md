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

⚠️ 产出目录：`仿写/仿写/仿写/{新书名}/`（不是根目录）

## 去重等级

默认 Lv1+Lv2。Lv2 触发逻辑标准（至少满足2条）：起因不同、动机不同、后果不同、参与人不同。

---

## Phase 0：源文分析（前置依赖）

⚠️ 运行前检查 `蒸馏/mode-b/` 下是否有 `style_guide_*.md` + `strategy_guide_*.md`。
- 已有 → 跳过
- 没有 → 先运行 `/story-style` 和 `/story-strategy`（可并行开两个 agent 会话同时跑）

---

## Phase 1：全书规划（每本新书都要做）

字数约束：2000-2500字，硬上限3000字。

### 1.0 创建模板（脚本，一次性）

先用脚本批量创建模板文件，agent 只填内容不写格式：

```bash
python .agents/skills/story-engine/tools/create_templates.py all <章节数> <蒸馏目录> <设定目录> <大纲目录>
```

示例（188章）：
```bash
python .agents/skills/story-engine/tools/create_templates.py all 188 novel-download-authors/闻栖/女配一睁眼/蒸馏/mode-b 仿写/新书名/设定 仿写/新书名/大纲
```

⚠️ 已存在的文件不会被覆盖。可安全重复运行。

### 1.1 新书概念 + 世界观 + 题材识别

- 新书概念.md：书名、类型、核心卖点、NPC命名映射表（必填）、故事弧线、差异化
- story_bible.md
- 题材识别：应用 [prompts/genre-management.md](prompts/genre-management.md) 中的 fatigue 词表

### 1.1 全书弧线骨架（1 agent，`context: fork`）

Task prompt 见 [prompts/arc-skeleton.md](prompts/arc-skeleton.md)。输出保存到 `设定/全书弧线骨架.md`。

### 1.2 章纲生成（10 agents × N批，并行，`context: fork`）

⚠️ **每个 agent 只生成1章章纲，禁止合并多章到同一个 agent。** 每批启动10个独立 Task。

Task prompt 见 [prompts/chapter-outline.md](prompts/chapter-outline.md)。每章输出保存到 `大纲/章纲_N.md`。

### 1.3 全书章节顺序映射（1 agent，`context: fork`）

Task prompt 见 [prompts/chapter-mapping.md](prompts/chapter-mapping.md)。输出保存到 `设定/章节顺序.md`。

---

## Phase 2：纯写作（每批循环）

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
