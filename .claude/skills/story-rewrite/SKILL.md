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
  [ ] 写新章（10 并行）→ 正文/第N章.txt
  [ ] 校验 → pass/fail
  [ ] Observer + Settler → 更新 truth files

Phase 3：收尾
  [ ] 全书去AI
  [ ] 一致性终检
  [ ] 字数总校验
```

---

## 仿写模式

| 模式 | 说明 |
|------|------|
| `--mode=style` | 文风仿写：模仿源文的写法 |
| `--mode=structure` | 结构仿写：模仿源文的情节骨架 |
| `--mode=both` | 文风+结构：两者都模仿 |

---

## Phase 1：初始化

### 1.1 源文样本分析

读取源文前 20000 字符，提取：
- world_rules（世界规则）
- character_profiles（角色特征）
- power_system（力量体系）

prompt：`prompts/source-analyzer.md`
输出：`追踪/源文特征.md`

### 1.2 市场扫描（可选）

调用 `/story-scan` 获取同题材热门。
提取：热门元素（人物设定/冲突类型/爽点类型/书名模式）

### 1.3 新书概念生成

方法论：同题材 + 同受众 + 保留成功因子 + 交叉验证 + 微创新

- 分析源文成功因子（钩子/角色/情绪/爽点）
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

### 2.3 文风蒸馏（style/both）

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

system prompt：`prompts/writer-system.md`

user message 包含：
- 世界设定 → `设定/story_bible.md`
- 写作规则 → `设定/book_rules.md`
- 卷纲 → `大纲/卷纲.md`
- 本章章纲
- 文风指纹（统计约束）
- 文风指南 → `追踪/蒸馏_{x-y}.md`
- 写作方法论 → `追踪/写作方法论.md`
- 角色语音 → `追踪/角色语音.md`
- 结构映射
- 当前状态卡 → `追踪/current_state.md`
- 伏笔池 → `追踪/pending_hooks.md`
- 章节摘要 → `追踪/chapter_summaries.md`
- 上章结尾（第2章起）

输出：`正文/第N章.txt`（2000-2500 字）

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
