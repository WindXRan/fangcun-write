---
name: story-rewrite_vPlan
description: |
  仿写引擎 vPlan：全书规划先行，一次出稿。
  触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
  全书规划（弧线+章纲+映射）在写作前完成，写作阶段纯并行无后处理。
  不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-rewrite_vPlan

> 全书规划先行，纯写作出稿。

## 文件结构

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/
├── 蒸馏/mode-b/
│   ├── style_profile_N.json     # 脚本指纹
│   ├── style_guide_N.md         # LLM inkos 8维度风格指南
│   └── strategy_guide_N.md      # LLM 排除项+节奏骨架+叙事策略

{新书名}/
├── 设定/
│   ├── 新书概念.md
│   ├── story_bible.md
│   ├── 全书弧线骨架.md
│   ├── 章节顺序.md
│   └── 支线大纲.md
├── 大纲/章纲_N.md
└── 正文/第N章.txt
```

## 去重等级

默认 Lv1+Lv2。Lv2 触发逻辑标准（至少满足2条）：起因不同、动机不同、后果不同、参与人不同。

---

## Phase 0：源文分析（一次性，可缓存）

### 缓存策略

**读取缓存时**：抽检3个 `style_guide_N.md` + 3个 `strategy_guide_N.md`，验证质量：
- style_guide：8维度齐全、≥600字、每维度有例句？
- strategy_guide：排除项≥2个、节奏骨架有数值、叙事策略5子维度非空？

全部合格 → 跳过，用缓存。有不合格 → 删掉该章缓存，重跑。

**写入缓存时**：同样验证，合格才写入。不合格最多重跑2轮。

**手动刷新**：删除 `蒸馏/mode-b/` 目录下文件，重新运行 Phase 0。

### 0.1 拆章
```bash
python .claude/skills/story-rewrite_vPlan/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
```

### 0.2 风格指纹 + 风格分析

脚本指纹：
```bash
python .claude/skills/story-rewrite_vPlan/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
```

LLM 风格分析（10 agents × N批，并行，`context: fork`）：

⚠️ **每个 agent 只分析1章，禁止合并多章到同一个 agent。** 每批启动10个独立 Task。

Task prompt 见 [prompts/style-analysis-task.md](prompts/style-analysis-task.md)。每章输出保存到 `蒸馏/mode-b/style_guide_N.md`。

LLM 叙事策略提取（10 agents × N批，并行，`context: fork`）：

⚠️ 与风格分析并行，同样每 agent 只处理1章。

Task prompt 见 [prompts/strategy-guide-task.md](prompts/strategy-guide-task.md)。每章输出保存到 `蒸馏/mode-b/strategy_guide_N.md`。

---

## Phase 1：全书规划（每本新书都要做）

字数约束：2000-2500字，硬上限3000字。

### 1.0 新书概念 + 世界观 + 题材识别

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
cat {新书名}/正文/*.txt > {新书名}/{新书名}.txt
```
