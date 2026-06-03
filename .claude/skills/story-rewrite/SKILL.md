---
name: story-rewrite
description: |
  仿写引擎：文风仿写 + 结构仿写。
  输入源文 txt，AI 自动生成新书。
  可集成扫榜数据，智能选择题材。
  输入：源文 txt（+ 可选新书概念）
  输出：完整小说
trigger:
  - /story-rewrite、/仿写
---

# story-rewrite：仿写引擎

**输入源文，AI 自动生成新书。**

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
Phase 1：初始化
  ├── 源文样本分析（20000字符）→ world_rules, character_profiles, power_system
  ├── 新书概念生成（用户未提供时，结合扫榜数据）
  ├── 卷纲生成 → 大纲/卷纲.md
  ├── 设定生成 → 设定/story_bible.md + book_rules.md
  ├── 简介生成 → 简介.md
  └── 初始化 truth files

Phase 2：写作（每区间 10 章）
  ├── 提取源文对应章节
  ├── 源文逐章分析 → plot_structure, key_events
  ├── 文风蒸馏（style/both）
  ├── 结构提取（structure/both）
  ├── 章纲细化（基于卷纲）→ 大纲/章纲_{x-y}.md
  ├── 写新章（10 并行）
  ├── 校验
  └── Observer + Settler

Phase 3：收尾
```

---

## Phase 1：初始化

### 输入

- 源文 txt（UTF-8，章节以「第X章」开头，≥3章）
- 新书概念（可选，不提供则 AI 自动生成）
- `--mode`：style / structure / both（默认 style）

### 步骤

1. **源文样本分析**

   分析源文前 20000 字符，提取：
   - `world_rules`：世界规则
   - `character_profiles`：角色特征（语癖/说话风格/行为模式）
   - `power_system`：力量体系

   prompt：`prompts/source-analyzer.md`
   输出：`追踪/源文特征.md`

2. **新书概念生成**（用户未提供时）

   方法论：同题材、同受众、保留成功因子、微创新。

   **Step 1：分析源文成功因子**
   - 什么钩子让读者追读？
   - 什么角色设定受欢迎？
   - 什么情绪节奏有效？
   - 什么爽点类型？

   **Step 2：分析同题材热门**（如可用，调用 `/story-scan`）
   - 获取同题材热门作品
   - 提取热门元素（人物设定/冲突类型/爽点类型）

   **Step 3：交叉验证**
   - 源文成功因子 ∩ 热门元素 = 高确定性元素
   - 只用交集内的元素，不冒险

   **Step 4：生成新书概念**
   - 保留：源文的结构/节奏/情绪模式
   - 替换：人物/场景/设定（用交集内的热门元素）
   - 差异化：1-2个微创新点

   输出：`设定/新书概念.md`

3. **卷纲生成**

   基于源文特征 + 新书概念，生成整体卷纲：
   - 故事弧线（三幕结构）
   - 主要转折点
   - 高潮位置
   - 卷/章节规划

   输出：`大纲/卷纲.md`

4. **设定生成**

   基于源文特征 + 新书概念：
   - `story_bible.md`：世界设定
   - `book_rules.md`：写作规则

5. **简介生成**

   基于卷纲 + 设定，生成多个版本简介供选择。
   输出：`简介.md`

6. **初始化 truth files**

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

从源文中提取本区间对应的章节：

```bash
python source_chapter_splitter.py extract <源文.txt> <start> <end> <追踪/源文_{start}-{end}.txt>
```

#### Step 2：源文逐章分析（每区间）

从本区间的源文章节中提取：
- `plot_structure`：逐章情节骨架
- `key_events`：关键事件时间线

prompt：`prompts/source-analyzer.md`
输出：`追踪/源文特征_{start}-{end}.md`

#### Step 3：文风蒸馏（style/only/both）

**Layer A：统计指纹**

```bash
python style_analyzer.py 追踪/源文_{start}-{end}.txt
```

**Layer B：LLM 8维度分析**
- prompt：`prompts/style-analysis.md`
- temperature：0.3

**Layer C：写作方法论**
- 首次区间生成 `追踪/写作方法论.md`，后续复用

**合并输出**：`追踪/蒸馏_{start}-{end}.md`

#### Step 4：结构提取（structure/only/both）

从本区间的源文分析结果中提取逐章映射：

每章映射：
- 源文核心事件 → 新书对应事件
- 源文情绪弧线 → 新书保持
- 源文钩子 → 新书对应钩子
- 源文转折 → 新书对应转折
- 源文角色动态 → 新书角色动态

输出：`追踪/结构映射_{start}-{end}.md`

#### Step 5：角色语音（style/only/both，首次区间）

从源文样本分析的 character_profiles 中提取角色语音特征。
输出：`追踪/角色语音.md`（首次区间生成，后续复用）

#### Step 6：章纲细化（本区间）

基于：
- 卷纲（整体规划）
- 源文分析的 plot_structure（structure/both）
- 当前 truth files（了解已有剧情）

生成本区间的详细章纲。

输出：`大纲/章纲_{start}-{end}.md`

#### Step 7：写新章

spawn M 个 writer agent（M = `--parallel`）。

**system prompt**：`prompts/writer-system.md`

**user message**：

```
【世界设定】请先读取：{设定/story_bible.md}

【写作规则】请先读取：{设定/book_rules.md}

【卷纲】请先读取：{大纲/卷纲.md}

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

#### Step 8：校验

对每章执行质量检查：
- 字数合规（2000-2500 字）
- AI 痕迹检测
- 禁用词/句式检查
- 章节完整性

fail → 重写1次 → 仍 fail 标记 manual_required

#### Step 9：状态沉淀（每区间一次）

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
├── 大纲/
│   ├── 卷纲.md                  # Phase 1 生成（整体规划）
│   ├── 章纲_{x-y}.md            # 每区间生成
│   └── ...
├── 简介.md
├── 追踪/
│   ├── 源文特征.md              # Phase 1 样本分析
│   ├── 源文特征_{x-y}.md       # 每区间逐章分析
│   ├── 蒸馏_{x-y}.md           # 每区间文风蒸馏
│   ├── 结构映射_{x-y}.md       # 每区间结构映射
│   ├── 写作方法论.md            # 首次区间生成（复用）
│   ├── 角色语音.md              # 首次区间生成（复用）
│   ├── 源文_{x-y}.txt          # 每区间提取的源文章节
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
| `source_chapter_splitter.py` | 源文章节提取 |
| `style_analyzer.py` | 统计指纹（Layer A） |
| `prompts/source-analyzer.md` | 源文分析器 prompt |
| `prompts/writer-system.md` | Writer system prompt |
| `prompts/style-analysis.md` | 文风分析 prompt（Layer B） |
| `prompts/observer-system.md` | Observer prompt |
| `prompts/settler-system.md` | Settler prompt |
