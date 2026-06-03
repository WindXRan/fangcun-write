---
name: story-rewrite
description: |
  仿写引擎：输入源文 txt，AI 自动生成新书。
  文风仿写 + 结构仿写，可独立或结合使用。
trigger:
  - /story-rewrite、/仿写
---

# story-rewrite：仿写引擎

## 速查表

```
输入：源文 txt
输出：完整小说

Phase 1：初始化
  [ ] 源文样本分析（20000字符）→ 追踪/源文特征.md
  [ ] 市场扫描（可选）→ 同题材热门
  [ ] 新书概念生成 → 设定/新书概念.md
  [ ] 卷纲生成 → 大纲/卷纲.md
  [ ] 设定生成 → 设定/story_bible.md + book_rules.md
  [ ] 简介生成 → 简介.md
  [ ] 初始化 truth files

Phase 2：写作（每区间 10 章，循环直到完成）
  [ ] 提取源文对应章节 → 追踪/源文_{x-y}.txt
  [ ] 源文逐章分析 → 追踪/源文特征_{x-y}.md
  [ ] 文风蒸馏 → 追踪/蒸馏_{x-y}.md
  [ ] 结构提取 → 追踪/结构映射_{x-y}.md
  [ ] 章纲细化 → 大纲/章纲_{x-y}.md
  [ ] 写新章（10 并行）→ 正文/第N章.txt  ⚠️ 必须用Task工具启动子agent
  [ ] 校验 → pass/fail
  [ ] Observer + Settler → 更新 truth files

⚠️ 重要：写新章必须使用Task工具启动子agent，详见「执行指南.md」

Phase 3：收尾
  [ ] 全书去AI
  [ ] 一致性终检
  [ ] 字数总校验
```

---

## 仿写模式

| 模式 | 说明 |
|------|------|
| `--mode=style` | 文风仿写 |
| `--mode=structure` | 结构仿写 |
| `--mode=both` | 文风+结构 |

---

## Phase 1：初始化

### 1.1 源文样本分析

读取源文前 20000 字符，提取：
- world_rules（世界规则）
- character_profiles（角色特征）
- power_system（力量体系）

prompt：`prompts/source-analyzer.md`
输出：`追踪/源文特征.md`

**注意：源文特征.md 不直接传给 writer，而是用于生成派生文件（1.5 设定生成 + 2.5 角色语音）。**

### 1.2 市场扫描

**数据来源**：`references/market-data.json`（从story-scan集成）

**数据字段**：
| 字段 | 用途 |
|------|------|
| `hot_genres` | 热门题材热度排行，用于选题材 |
| `title_patterns` | 书名命名模式，用于定书名 |
| `tag_combinations` | 标签组合公式，用于配标签 |
| `golden_three` | 黄金三章标准，用于前3章检查 |
| `chapter_spec` | 章节字数/节奏标准 |

**更新方式**：运行 `/story-scan` 后手动同步到 `references/market-data.json`

### 1.3 新书概念生成

方法论：同题材 + 同受众 + 保留成功因子 + 交叉验证 + 微创新

- 分析源文成功因子（钩子/角色/情绪/爽点）
- **读取市场数据**（`references/market-data.json`）：
  - `hot_genres`：选择热门题材
  - `title_patterns`：参考书名模式
  - `tag_combinations`：配置标签组合
- 交叉验证（源文成功因子 ∩ 热门元素）
- 生成新书概念（保留结构，替换元素）
- 书名参考热门模式

输出：`设定/新书概念.md`

### 1.4 卷纲生成

基于源文特征 + 新书概念：
- 故事弧线（三幕结构）
- 主要转折点
- 高潮位置
- 卷/章节规划

输出：`大纲/卷纲.md`

### 1.5 设定生成

- `story_bible.md`：世界设定
- `book_rules.md`：写作规则

### 1.6 简介生成

基于卷纲 + 设定，生成多个版本。
输出：`简介.md`

### 1.7 初始化 truth files

```
追踪/current_state.md    ← 初始状态
追踪/pending_hooks.md    ← 空
追踪/chapter_summaries.md ← 空
追踪/character_matrix.md  ← 初始角色关系
追踪/emotional_arcs.md   ← 空
```

---

## Phase 2：写作（每区间 10 章）

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--chunk-size` | 10 | 每区间写几章 |
| `--parallel` | 10 | 每区间并行 agent 数（可调大） |

**加速**：调大 `--chunk-size` 和 `--parallel`（如 30/30），区间更大、agent 更多，速度更快。

### 2.1 提取源文对应章节

```bash
python source_chapter_splitter.py extract <源文.txt> <start> <end> <追踪/源文_{start}-{end}.txt>
```

### 2.2 源文逐章分析

从本区间源文章节提取：
- plot_structure（逐章情节骨架）
- key_events（关键事件）

prompt：`prompts/source-analyzer.md`
输出：`追踪/源文特征_{start}-{end}.md`

### 2.3 文风蒸馏（style/both）⚠️ 每个区间必须重新蒸馏

**⚠️ 关键：每个区间必须对本区间的源文重新进行文风蒸馏，不能复用其他区间的蒸馏数据！**

Layer A：`python style_analyzer.py 追踪/源文_{x-y}.txt`
Layer B：`prompts/style-analysis.md`，temperature 0.3
Layer C：读取 `追踪/写作方法论.md`（首次生成，后续复用）

输出：`追踪/蒸馏_{start}-{end}.md`

### 2.4 结构提取（structure/both）

从源文分析结果提取逐章映射。
输出：`追踪/结构映射_{start}-{end}.md`

### 2.5 角色语音（style/both，首次）

从 character_profiles 提取。
输出：`追踪/角色语音.md`（首次生成，后续复用）

### 2.6 章纲细化

基于：卷纲 + 源文分析 + 当前 truth files
输出：`大纲/章纲_{start}-{end}.md`

### 2.7 写新章

spawn M 个 writer agent（M = `--parallel`）。

**system prompt**（动态拼接）：

```
{writer-system.md 内容}

## 文风指南（本区间）
{蒸馏_{x-y}.md 内容}

## 文风指纹（统计约束）
{统计约束：平均句长/短句占比/段落长度等}

## 写作方法论
{写作方法论.md 内容}

## 角色语音（style/both）
{角色语音.md 内容}
```

**user message**（每章不同）：

```
【世界设定】请先读取：{设定/story_bible.md}

【写作规则】请先读取：{设定/book_rules.md}

【卷纲】请先读取：{大纲/卷纲.md}

【本章章纲】{章纲内容}

【结构映射】（structure/both）{本章映射}

【当前状态卡】请先读取：{追踪/current_state.md}

【伏笔池】请先读取：{追踪/pending_hooks.md}

【章节摘要】请先读取：{追踪/chapter_summaries.md}

【上章结尾】（第2章起）{上章最后500字}

【输出要求】
- 输出到：{书名}/正文/第{N}章.txt
- 字数：2000-2500 字
```

**⚠️ 关键：蒸馏文件注入 system prompt，不是 user message。**

### 2.8 校验

- 字数合规（2000-2500 字）
- AI 痕迹检测
- 禁用词/句式检查
- 章节完整性

fail → 重写1次 → 仍 fail 标记 manual_required

### 2.9 状态沉淀（每区间一次）

Observer：`prompts/observer-system.md` → 提取事实
Settler：`prompts/settler-system.md` → 更新 truth files

更新：
- `追踪/current_state.md`
- `追踪/pending_hooks.md`
- `追踪/chapter_summaries.md`
- `追踪/character_matrix.md`
- `追踪/emotional_arcs.md`

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
│   ├── 新书概念.md
│   ├── story_bible.md
│   └── book_rules.md
├── 大纲/
│   ├── 卷纲.md
│   └── 章纲_{x-y}.md
├── 简介.md
├── 追踪/
│   ├── 源文特征.md
│   ├── 源文特征_{x-y}.md
│   ├── 蒸馏_{x-y}.md
│   ├── 结构映射_{x-y}.md
│   ├── 写作方法论.md
│   ├── 角色语音.md
│   ├── 源文_{x-y}.txt
│   ├── 进度.md
│   ├── current_state.md
│   ├── pending_hooks.md
│   ├── chapter_summaries.md
│   ├── character_matrix.md
│   └── emotional_arcs.md
└── 正文/第{N}章.txt
```

---

## 附属文件

| 文件 | 用途 |
|------|------|
| `source_chapter_splitter.py` | 源文章节提取 |
| `style_analyzer.py` | 统计指纹（Layer A） |
| `prompts/source-analyzer.md` | 源文分析器 |
| `prompts/writer-system.md` | Writer system prompt |
| `prompts/style-analysis.md` | 文风分析 |
| `prompts/observer-system.md` | Observer |
| `prompts/settler-system.md` | Settler |
| `references/market-data.json` | 番茄市场数据（从story-scan集成） |
| `执行指南.md` | 详细执行步骤和常见错误 |

---

## 常见错误

❌ **错误1**：主agent自己直接写新章
✅ **正确**：必须使用Task工具启动子agent

❌ **错误2**：不传提示词，只传章纲给writer agent
✅ **正确**：传递完整的user message模板（包含世界设定、写作规则、卷纲、章纲、文风指南、角色语音等）

❌ **错误3**：串行执行，一章一章写
✅ **正确**：并行执行，同时启动10个agent

❌ **错误4**：不读取参考文件
✅ **正确**：在prompt中明确要求先读取所有参考文件

❌ **错误5**：用第1-10章的蒸馏数据写第11-20章
✅ **正确**：每个区间必须重新蒸馏，用本区间的蒸馏数据

❌ **错误6**：跳过蒸馏步骤，直接写新章
✅ **正确**：必须先完成Step 1-5（提取、分析、蒸馏、映射、章纲），再执行Step 6写新章

---

## 执行指南

**详细执行步骤请参考**：`执行指南.md`

该文件包含：
- 每区间完整流程（8个步骤）
- Writer Agent Prompt模板
- 常见错误和正确做法
- 检查清单
- 执行示例
