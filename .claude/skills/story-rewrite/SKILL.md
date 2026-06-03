---
name: story-rewrite
description: |
  仿写引擎：文风仿写 + 结构仿写。
  从源文提取特征，指导新书写作。
  输入：源文 txt + 新书概念
  输出：完整小说
trigger:
  - /story-rewrite、/仿写
---

# story-rewrite：仿写引擎

**从源文提取特征，用特征指导新书写作。**

---

## 仿写模式

| 模式 | 说明 | 使用的源文特征 |
|------|------|---------------|
| `--mode=style` | 文风仿写 | character_profiles + 每区间文风蒸馏 |
| `--mode=structure` | 结构仿写 | plot_structure + key_events |
| `--mode=both` | 文风+结构 | 全部 |

---

## 流程

```
Phase 1：初始化（一次性）
  ├── 目录分析 + 分割源文章节
  ├── 源文分析（样本+逐章）→ 追踪/源文特征.md
  ├── 设定生成 → 设定/story_bible.md + book_rules.md
  ├── 章纲生成 → 大纲/章纲_*.md
  ├── 简介生成 → 简介.md
  ├── 写作方法论 → 追踪/写作方法论.md
  ├── 角色语音 → 追踪/角色语音.md（style/both）
  └── 初始化 truth files

Phase 2：写作（每区间 10 章）
  ├── 提取源文对应章节
  ├── 文风蒸馏（style/both）→ 追踪/蒸馏_{x-y}.md
  ├── 结构映射（structure/both）→ 追踪/结构映射_{x-y}.md
  ├── 写新章（10 并行）→ 正文/第N章.txt
  ├── 校验 → pass/fail
  └── Observer + Settler → 更新 truth files

Phase 3：收尾
  ├── 全书去AI
  ├── 一致性终检
  └── 字数总校验
```

---

## Phase 1：初始化

### 输入

- 源文 txt（UTF-8，章节以「第X章」开头，≥3章）
- 新书概念（题材/人物/冲突，可选）
- `--mode`：style / structure / both（默认 style）

### 步骤

1. **目录分析 + 分割源文章节**

   用 `source_chapter_splitter.py` 分割源文为独立章节：

   ```bash
   python source_chapter_splitter.py split <源文.txt> <源文章节目录>
   ```

   同时提取目录结构（章数、卷结构）。

2. **源文分析**

   **A. 样本分析**（世界规则/角色/力量体系）：
   - prompt：`prompts/source-analyzer.md`
   - 输入：源文前 20000 字符
   - temperature：0.3
   - 提取：world_rules, character_profiles, power_system

   **B. 结构分析**（情节骨架/关键事件）：
   - 逐章提取 plot_structure 和 key_events
   - 每章：核心事件/情绪弧线/钩子/角色动态/转折点/节奏标记
   - 可并行处理

   合并输出：`追踪/源文特征.md`

3. **设定生成**：基于源文特征 + 用户概念
   - `story_bible.md`：世界设定
   - `book_rules.md`：写作规则

4. **章纲生成**：
   - structure/both：章纲必须对齐 plot_structure
   - style：章纲独立设计

5. **简介生成**：基于 story_bible + 章纲

6. **写作方法论**（一次性）：`追踪/写作方法论.md`

7. **角色语音**（style/both，一次性）：从 character_profiles 提取 → `追踪/角色语音.md`

8. **初始化 truth files**：
   - `追踪/current_state.md`：初始状态
   - `追踪/pending_hooks.md`：空
   - `追踪/chapter_summaries.md`：空
   - `追踪/character_matrix.md`：初始角色关系
   - `追踪/emotional_arcs.md`：空

---

## Phase 2：写作

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--chunk-size` | 10 | 每区间写几章 |
| `--parallel` | 10 | 每区间并行 agent 数 |

### 每区间流程

#### Step 1：提取源文对应章节

从分割后的源文章节中提取本区间对应的章节：

```bash
python source_chapter_splitter.py extract <源文.txt> <start> <end> <追踪/源文_{start}-{end}.txt>
```

#### Step 2：文风蒸馏（style/only/both）

**Layer A：统计指纹**

```bash
python style_analyzer.py 追踪/源文_{start}-{end}.txt
```

**Layer B：LLM 8维度分析**
- prompt：`prompts/style-analysis.md`
- temperature：0.3

**Layer C：写作方法论**
- 读取 `追踪/写作方法论.md`

**合并输出**：`追踪/蒸馏_{start}-{end}.md`

#### Step 3：结构映射（structure/only/both）

从 `追踪/源文特征.md` 的 plot_structure 中提取本区间的逐章映射。

输出：`追踪/结构映射_{start}-{end}.md`

#### Step 4：写新章

spawn M 个 writer agent（M = `--parallel`）。

**system prompt**：`prompts/writer-system.md`

**user message**：

```
【世界设定】请先读取：{设定/story_bible.md}

【写作规则】请先读取：{设定/book_rules.md}

【本章章纲】{章纲内容}

【文风指纹】（style/only/both）{统计约束}

【文风指南】（style/only/both）请先读取：{追踪/蒸馏_{x-y}.md}

【写作方法论】请先读取：{追踪/写作方法论.md}

【角色语音】（style/only/both）请先读取：{追踪/角色语音.md}

【结构映射】（structure/only/both）{本章映射}

【当前状态卡】请先读取：{追踪/current_state.md}

【伏笔池】请先读取：{追踪/pending_hooks.md}

【章节摘要】请先读取：{追踪/chapter_summaries.md}

【上章结尾】（第2章起）{上章最后500字}

【输出要求】
- 输出到：{书名}/正文/第{N}章.txt
- 字数：2000-2500 字
```

#### Step 5：校验

对每章执行质量检查：
- 字数合规（2000-2500 字）
- AI 痕迹检测
- 禁用词/句式检查
- 章节完整性

fail → 重写1次 → 仍 fail 标记 manual_required

#### Step 6：状态沉淀（每区间一次）

spawn 2 个 agent 更新 truth files：

**Observer**：`prompts/observer-system.md`
- 从本区间所有章节正文中提取事实

**Settler**：`prompts/settler-system.md`
- 基于 Observer 输出 + 当前 truth files，更新状态

### 流水线规则

- 每区间校验完立即开始下一区间
- fail → 重写1次 → 仍 fail 标记 manual_required

### 断点续写

检测到 `正文/` 目录存在时：
1. 读取 `追踪/进度.md` 获得最大章号
2. 从 N+1 章续写

---

## Phase 3：收尾

1. 全书去AI
2. 一致性终检
3. 字数总校验

---

## 输出结构

```
{书名}/
├── 设定/
│   ├── story_bible.md
│   └── book_rules.md
├── 大纲/章纲_*.md
├── 简介.md
├── 源文章节/                    # 分割后的源文章节
│   ├── 第1章.txt
│   ├── 第2章.txt
│   └── ...
├── 追踪/
│   ├── 源文特征.md              # Phase 1 生成
│   ├── 写作方法论.md            # Phase 1 生成（一次性）
│   ├── 角色语音.md              # Phase 1 生成（style/both）
│   ├── 源文_{x-y}.txt          # 每区间提取的源文章节
│   ├── 蒸馏_{x-y}.md           # 每区间文风蒸馏
│   ├── 结构映射_{x-y}.md       # 每区间结构映射
│   ├── 进度.md
│   ├── current_state.md         # 每区间更新
│   ├── pending_hooks.md         # 每区间更新
│   ├── chapter_summaries.md     # 每区间追加
│   ├── character_matrix.md      # 每区间更新
│   └── emotional_arcs.md        # 每区间更新
└── 正文/第{N}章.txt
```

---

## 附属文件

| 文件 | 用途 |
|------|------|
| `source_chapter_splitter.py` | 源文章节分割 |
| `style_analyzer.py` | 统计指纹（Layer A） |
| `prompts/source-analyzer.md` | 源文分析器 prompt |
| `prompts/writer-system.md` | Writer system prompt |
| `prompts/style-analysis.md` | 文风分析 prompt（Layer B） |
| `prompts/observer-system.md` | Observer prompt |
| `prompts/settler-system.md` | Settler prompt |
