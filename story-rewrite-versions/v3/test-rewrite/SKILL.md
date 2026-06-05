---
name: test-rewrite
description: |
  仿写引擎 v3：源文 → 风格指纹 → 章纲 → 写章 → 去AI。三轮并行 Agent。
  核心防洗稿：章纲不锁事件类型，只学节奏；Lv2 替换触发逻辑。
  适用：番茄/起点仿写、批量生产、需要防查重场景。
trigger:
  - /test-rewrite
  - /仿写v3
---

# test-rewrite：仿写引擎 v3.0

> Mode B 三轮并行 Agent。章纲即真相，每 20 章更新一次真相文件。

---

## 文件结构

```
novel-download-authors/{作者名}/{书名}/
├── 源文/                        # 拆章后的源文章节
├── 蒸馏/mode-b/
│   ├── style_profile_N.json     # 脚本统计指纹
│   └── style_guide_N.md         # LLM 8维风格指南

{书名}/
├── 设定/
│   ├── 新书概念.md              # 书名/类型/NPC映射/卖点
│   ├── story_bible.md           # 世界观
│   ├── 章节顺序.md              # Lv1：打乱后的功能顺序
│   └── 支线大纲.md              # Lv3：原创支线规划
├── 真相文件/                    # 每20章更新
│   ├── current_state.md
│   ├── pending_hooks.md
│   ├── chapter_summaries.md
│   ├── character_matrix.md
│   └── emotional_arcs.md
├── 大纲/章纲_N.md               # 每章一个
└── 正文/第N章.txt
```

---

## 去重等级

| 等级 | 做什么 | 风险 | 何时 |
|------|--------|------|------|
| **Lv1** | 按功能重排章节顺序 | 3/10 | B3 完成后 |
| **Lv2** | 替换每个关键情节的触发逻辑 | 1/10 | B3 写章纲 |
| **Lv3** | 加一条源文没有的原创支线 | 0 | Phase 1.5 + B3 |

**默认 Lv1+Lv2**。Lv2 的章纲模板字段：`触发逻辑：[为什么发生，必须和源文不同]`

---

## Phase 1：初始化

### 1.0 拆章 + 风格指纹
```bash
python .claude/skills/story-rewrite/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{书名}/源文/

for i in range(start, end+1):
    python .claude/skills/story-rewrite/tools/style_analyzer.py novel-download-authors/{作者名}/{书名}/源文/第{i}章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_{i}.json -Encoding utf8
```

### 1.1 新书概念
{书名}/设定/新书概念.md：书名、类型、核心卖点、**NPC命名映射表**（必填）、故事弧线、差异化

### 1.2 世界观
{书名}/设定/story_bible.md

### 1.3 真相文件
{书名}/真相文件/ 下 5 个文件，初始化时只填框架，详见 truth-files.md

### 1.4 题材识别
从源文标签选题材，应用 prompts/genre-management.md 中对应的 fatigue 词表

### 1.5 Lv3：原创支线规划
从候选支线选一个或自定义，规划开端→发展→高潮→结局，保存到 {书名}/设定/支线大纲.md

---

## Phase 2：写作（Mode B 三轮并行）

```
输入：源文.txt
    ↓
B1 每批 10 章风格指纹（拆章见 Phase 1.0）
    ↓
第一轮：10 个子 agent 做风格分析（B2）→ style_guide_X.md
    ↓
第二轮：10 个子 agent 做章纲（B3）→ 章纲_N.md
    ↓
[与 B4 并行] 主 agent 跑 B3.5 Lv1 重排下一批源文映射
    ↓
第三轮：10 个子 agent 写章（B4）→ 第N章.txt
    ↓
B5 去AI（每 10 章一次）
    ↓
B6 真相文件更新（每 20 章强制）
    ↓
B7 循环 → 回到 B1 启动下一批（已有新映射）
```

### B1 每批次：风格指纹（只跑新 10 章）
⚠️ 不是 Phase 1.0！Phase 1.0 跑一次拆章+全本指纹，B1 每批次只跑本批 10 章的指纹更新。

```bash
for i in 本批起始..本批结束:
    python .claude/skills/story-rewrite/tools/style_analyzer.py novel-download-authors/{作者名}/{书名}/源文/第{i}章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_{i}.json -Encoding utf8
```

### B2 第一轮：风格分析（并行 10 agent）
```
每个 Task 的 prompt：
"""
你是一位文学风格分析专家。请分析《{书名}》第N章的写作风格。

【源文】请读取：novel-download-authors/{作者名}/{书名}/源文/第N章.txt
【风格指纹】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_N.json

【输出格式】严格按 8 个维度，每个维度引用 1-2 个原文例句：

### 叙事声音与语气
（冷峻/热烈/讽刺/温情/...，附原文例句）

### 对话风格
（句子长短、口头禅、方言痕迹、对话节奏）

### 场景描写特征
（五感偏好、意象选择、描写密度、环境与情绪的关联）

### 转折与衔接手法
（场景切换、时间跳跃、段落过渡）

### 节奏特征
（长短句分布、段落长度、高潮/舒缓交替）

### 词汇偏好
（高频特色用词、比喻倾向、口语化程度）

### 情绪表达方式
（直白抒情 vs 动作外化、内心独白频率）

### 独特习惯
（值得模仿的个人写作习惯）

【输出】保存到：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_guide_N.md
"""
```

### B3 第二轮：章纲生成（并行 10 agent）
```
每个 Task 的 prompt：
"""
请为《{书名}》第N章生成章纲。

⚠️ 严格只输出以下 6 个字段，禁止添加任何其他字段（不要写"风格数据""场景设计""情节节点""合规自检"等额外段落）。
⚠️ 禁止展开场景和对话，不要把章纲写成半成品小说。
⚠️ 禁止在章纲中出现"对应源文XX""参考源文XX"等映射词，章纲必须看起来是 100% 原创故事。
⚠️ 字数控制在 10-15 行内（每行字段紧凑，不要长段落）。

【新书概念】请读取：{书名}/设定/新书概念.md
【前序章纲】请读取：{书名}/大纲/ 下已有章纲文件（如有）
【章节顺序】请读取：{书名}/设定/章节顺序.md（如有）→ 查找"新书第N章 = 源文第X章"
【源文】请读取：novel-download-authors/{作者名}/{书名}/源文/第X章.txt（X 从章节顺序表查；⚠️ 只提取节奏模式：情绪强度怎么变化、钩子在哪。不要提取具体事件）

## 第N章 [章名]

- 核心事件：[2-3句话，自己编的原创事件]
- 因果逻辑：[A→B→C→D，每个环节一句话]
- 触发逻辑：[⚠️ Lv2 去重：为什么发生，必须和源文不同]
- 节奏模式：[情绪强度变化，如 低→高→低]
- 钩子：[章末钩子，1句话]
- 爽点来源：[爽感公式，如"身份反转""装逼打脸"]

【输出】保存到：{书名}/大纲/章纲_N.md
"""
```

### B3.5 Lv1：重排下一批源文映射（主 agent 跑，不开子 agent）

**触发时机**：B3 写完本批章纲后，**与 B4 写本批章节并行**（不阻塞 B4）

**为什么放这里**：
- B3 已有本批完整章纲 → 重排有依据
- B4 在写本批时，重排结果为下一批 B3 准备 → 不浪费等待时间
- 第一批（B3 写完 1-10 章章纲后）跳过——没有"下一批"要排

**执行方式**：主 agent 自己跑（不并行子 agent），用 1 次 LLM 调用生成映射表。

**步骤**：
1. 读取本批 10 个章纲，分析剧情走向
2. 为下一批 10 章生成源文→新书映射（按功能冲突/甜宠/过渡/高潮重排）
3. 保存到 {书名}/设定/章节顺序.md

```
例（11-20 章写完后，重排 21-30）：
| 新书章号 | 源文章号 | 功能 | 章节核心 |
|---------|---------|------|---------|
| 21 | 23 | 甜宠 | 修闹钟+男主护妻 |
| 22 | 25 | 冲突 | 白月光上门 |
| 23 | 24 | 甜宠 | 送饭+耳根红 |
| ... |
```

### B4 第三轮：写章（并行 10 agent）
```
每个 Task 的 prompt：
"""
请写出《{书名}》第N章正文。

【章纲】请读取：{书名}/大纲/章纲_N.md
【章节顺序】请读取：{书名}/设定/章节顺序.md → 查找"新书第N章 = 源文第X章"
【风格指南】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_guide_X.md（X 从章节顺序表查）
【风格指纹】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_X.json（X 从章节顺序表查；把里面所有数值当作你这章的目标：句长均值、对话占比、短句比例、开头模式、AI痕迹等。写完即停，不要回头检测）

【规则】
- 事件、因果链、对话：全部原创，按章纲写
- 节奏模式：按章纲写，情绪强度变化一致
- 触发逻辑：按章纲写，不能用源文的触发方式
- 禁止照搬源文的事件、对话、场景
- 禁用词：读取 .claude/skills/test-rewrite/prompts/genre-management.md 中对应题材的 fatigueWords
- 风格要求 100% 来自风格指纹，不要加任何通用规则（如"短句为王"）

【输出】保存到：{书名}/正文/第N章.txt
字数：2000-2500字，硬上限3000字
"""
```

### B5 去AI（每 10 章）
用 prompts/de-ai-system.md 执行 anti-detect 流程

### B6 真相文件更新（每 20 章）
读取最近 20 章正文 + 上一版真相文件，更新 5 个文件

### B7 循环
1. 检查是否还有未写章节
2. 有 → 回到 B1 启动下一批（B3.5 已生成新映射，下一批 B3 用新映射）
3. 无 → 进入 Phase 3 收尾

---

## Phase 3：收尾

### 3.1 一致性终检
```bash
grep -n "源文原名" {书名}/正文/*.txt
```

### 3.2 仿写风险自测
任何一项"是"就立刻修改：
1. 是否只参考了一本书？
2. 主角性格/背景/目标是否和某爆款书几乎一样？
3. 剧情是否可"把原书人物名换成我的"来描述？
4. 因果链是否和原书完全一样？
5. 连续 3 章的剧情节点是否和原书对应？

### 3.3 导出
```bash
cat {书名}/正文/*.txt > {书名}/{书名}.txt
```

---

## 附属文件

| 文件 | 用途 | v3 用吗 |
|------|------|--------|
| `prompts/style-analysis.md` | 8 维风格分析模板 | ✅ B2 |
| `prompts/de-ai-system.md` | 去 AI 11 条规则 | ✅ B5 |
| `prompts/genre-management.md` | 6 题材 + fatigue 词表 | ✅ B4 |
| `prompts/auditor-system.md` | 33 维审计 | ❌ 预留 |
| `prompts/chapter-analyzer.md` | 章节结构分析 | ❌ 预留 |
| `prompts/chapter-intent.md` | 章节意图 | ❌ 预留 |
| `truth-files.md` | 5 个真相文件模板 | ✅ Phase 1.3 + B6 |
| `tools/source_chapter_splitter.py` | 拆章 | ✅ Phase 1.0 |
| `tools/style_analyzer.py` | 统计指纹 | ✅ B1 |
| `tools/word_count.py` | 字数统计 | ✅ 验证 |
| `scripts/validate_files.py` | 文件验证 | ✅ Phase 1 |
| `scripts/update_truth_files.py` | 真相文件更新 | ✅ B6 |
