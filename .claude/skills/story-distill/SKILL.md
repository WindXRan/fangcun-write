---
name: story-distill
description: |
  网文作者蒸馏 · 从同一作者的多本小说中提取写作决策框架或审稿编辑框架。
  方法论：借鉴 cangjie-skill 的 RIA-TV++ 流水线 + nuwa-skill 的六维研究。
  核心理念：提取「为什么这样写」，不是「写了什么」。
  两种模式：
    --mode=write（默认）：提取写作决策框架 → 仿写时注入风格
    --mode=review：提取审稿编辑框架 → 审稿时作为审查清单
  输入：作者名 + 原文 txt 路径（至少1本，推荐3-6本）
  输出：
    write 模式：.claude/skills/story-style/{作者名}/SKILL.md + meta.json
    review 模式：.claude/skills/story-style/{作者名}/review/SKILL.md + meta.json（增量附件）
trigger:
  - /story-distill
  - /蒸馏
  - /炼丹
  - 蒸馏作者
  - 提取文风
  - distill
---

# story-distill：网文作者蒸馏

**核心理念：大佬写的不是「文字」，是「决策」。我们要提取决策框架，不是表面特征。**

**两种模式**：
- `--mode=write`（默认）：提取**写作决策框架**——怎么写？心智模型、决策启发式、表达DNA
- `--mode=review`：提取**审稿编辑框架**——怎么改？审稿红线、修改处方、质量阈值（增量附件，配合写作框架使用）

**方法论来源**：
- cangjie-skill: RIA-TV++ 流水线（整书理解→并行提取→三重验证→结构化输出）
- nuwa-skill: 六维研究 + 三重验证 + subagent prompt 模板
- oh-story-claudecode: 拆文流程
- webnovel-writer: 追读力系统

---

## 模式路由

```
用户输入
    │
    ├── /story-distill --mode=write（或无 --mode）  → 写作模式（Phase 2: 10个提取器）
    │
    └── /story-distill --mode=review               → 审稿模式（Phase 2: 14个提取器）
```

**复用关系**：
- Phase 0（输入验证）：完全复用
- Phase 1（整书理解）：完全复用
- Phase 2（并行提取）：write 模式 10 个提取器 → review 模式 14 个提取器（原 10 个 + 审稿红线 + 修改处方 + 质量阈值 + 审稿人格）
- Phase 3（三重验证）：完全复用
- Phase 4（RIA++ 构造）：完全复用
- Phase 5（合成输出）：write 模式用写作模板，review 模式用审稿模板

---

## 流程总览

```
Phase 0    输入验证 → 确认原文格式+数量
Phase 0.5  文件检查 → 断点续跑，跳过已完成的 phase
Phase 1    精读片段预处理（主线程）→ 提取精读章节，减少 token 消耗
           并行精读（N个 agent）→ 每本书独立分析（9个深度维度）
Phase 2    并行提取 → 从精读片段中提取决策框架
              write 模式：10个 subagent
              review 模式：14个 subagent
Phase 3    统一验证（1个 subagent）→ 跨书/频率/独特性/可执行性 + 质量检查
Phase 4    并行构造（10/14个 subagent）→ RIA++ 结构化输出，附原文引用
Phase 5    合成输出 → 生成 SKILL.md + meta.json
```

**预计耗时**：
- write 模式：8-12 分钟（3本小说，优化后减少4-6分钟）
- review 模式：12-16 分钟（3本小说，多4个提取器）

**优化说明**：
- Phase 1 精读片段预处理：subagent 只读精读片段（约5万字），不读全书（约30万字），节省约83%的读取token
- Phase 3 从3个并行subagent合并为1个统一验证subagent，减少调度开销
- Phase 1 增加2个深度分析维度（情绪节奏曲线、作者价值观），提升提取质量
- Phase 2 提取器prompt增加反例和格式要求，提升规则可执行性
- 支持断点续跑：用户说「继续蒸馏」时，自动跳过已完成的phase

**后续**：跑完 distill 后，可用 `/story-distill-verify` 进行压力测试 + 验证 + 闭环回馈。

---

## Phase 0：输入验证

### 输入要求

| 项目 | 要求 |
|------|------|
| 作者名 | 中文或英文，作为输出目录名 |
| 原文路径 | 一个或多个 txt 文件路径 |
| 编码 | UTF-8 |
| 章节格式 | 每章以 `第X章` 开头 |
| 最低数量 | 至少 1 本完整小说（推荐 3 本以上） |

### 执行步骤

1. 检查文件是否存在、编码是否 UTF-8、章节格式是否正确
2. 创建输出目录结构（**重要**：工作目录用 `.distill/` 前缀，蒸馏完成后整个删除）：
   ```
   .claude/skills/story-style/{作者名}/
   ├── references/                 # 最终交付物
   └── .distill/                   # 工作目录，Phase 6 删除
       ├── book-overviews/         # Phase 1 产出
       ├── book-structure/         # Phase 1 预处理产出
       ├── excerpts/               # Phase 1 预处理产出
       ├── candidates/             # Phase 2 原始产出
       ├── constructed/            # Phase 4 RIA++ 终版
       ├── rejected/               # Phase 3 淘汰
       └── sources/                # 原文备份
   ```
3. 复制原文到 `.distill/sources/{book_name}.txt`

**不满足要求时**：提示用户修正格式后重试。

### 错误处理

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| 文件不存在 | 检查路径拼写，尝试相邻目录 | 停止，提示用户检查路径 |
| 编码非UTF-8 | 自动检测编码，尝试 GBK/GB2312 转 UTF-8 | 停止，提示用户提供 UTF-8 文件 |
| 章节格式不匹配 | 统计前5章开头格式，自动适配 | 提示用户修正格式 |
| 只有1本书 | 正常继续，跳过跨书验证 | — |

---

## Phase 0.5：文件检查（断点续跑）

**目的**：支持断点续跑，如果之前蒸馏中断，可以跳过已完成的 phase，继续执行未完成的部分。

**执行逻辑**：

```
Phase 启动前检查：
  if 该 phase 的产出文件已存在且非空:
    跳过该 phase，直接进入下一 phase
  else:
    正常执行
```

**检查点**：

| Phase | 检查文件 | 跳过条件 |
|-------|---------|---------|
| Phase 1 | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | 所有书的 book-overviews 和 excerpts 都存在 |
| Phase 2 | `.distill/candidates/*.md` | 所有维度的 candidates 都存在 |
| Phase 3 | `.distill/rejected/quick-filter.md` | quick-filter.md 存在 |
| Phase 4 | `.distill/constructed/*.md` | 所有维度的 constructed 都存在 |

**使用方式**：
- 用户说「继续蒸馏」时，agent 自动检查已有产出，跳过已完成 phase
- 无需额外参数，自动检测

---

## Phase 1：整书理解（深度版）

**借鉴**：cangjie-skill 的 Adler 分析阅读法

**目的**：深度精读关键场景，捕捉作者的每一个写作决策，提取「为什么这样写」的决策框架

**质量标准**：提取的规则必须能复现原作的决策逻辑，不能是"大概对"，必须是"精确对"

### 1.0 精读片段预处理（主线程）

**目的**：减少 Phase 2 提取器的 token 消耗，通过主线程预处理精读片段，subagent 只读取片段而非全书。

**执行步骤**（主线程，不消耗 subagent token）：

1. **读取全书目录**，确定章节目录
2. **根据选书策略，选定精读章节**：
   - 基础层：第 1-3 章 + 最后 3 章
   - 扩展层：1/4、1/2、3/4 处各 ±1 章
   - 专家层：情绪高点 + 转折点（从章名关键词推断，如「真相」「反转」「离」「死」）
3. **从原文中提取这些章节的文本**，拼接为 excerpts.txt
4. **写入** `.distill/excerpts/{书名}-excerpts.txt`（精读片段，约 3-5 万字）
5. **同时写入** `.distill/book-structure/{书名}.md`（章名列表 + 章节数 + 精读章节标记）

**产出文件**：
- `.distill/excerpts/{书名}-excerpts.txt`：精读章节的完整文本
- `.distill/book-structure/{书名}.md`：章名列表 + 章节数 + 精读章节标记

**Token 节省**：
- 优化前：subagent 读全书 30 万字/本 ≈ 45 万 token/本
- 优化后：subagent 读精读片段 5 万字/本 ≈ 7.5 万 token/本
- 节省约 83% 的 Phase 1 读取 token（3 本书节省约 112 万 token）

### 1.1 并行精读

**并行** spawn N 个 Task sub-agents（每本书一个）：

每个 agent 负责一本书的：
1. 目录分析（章名分析 + 章节密度 + 情绪曲线推断）
2. 分层精读选择（基础层 + 扩展层 + 专家层）
3. 精读关键场景（7个维度，不是4个）
4. 提取 7 类语感样本（不是5类）
5. 追踪悬念链条（埋设→强化→回收）
6. 分析句式节奏模式（重复/排比/短句）

**产出**：每本书写入 `.distill/book-overviews/{书名}.md` + `.distill/writing-samples-{书名}.md` + `.distill/suspense-chains-{书名}.md`

**Subagent prompt 模板**：

```
你的任务：深度精读《{书名}》，提取作者的每一个写作决策。

读取数据：
- 读取 {输出目录}/.distill/excerpts/{书名}-excerpts.txt（精读片段）
- 读取 {输出目录}/.distill/book-structure/{书名}.md（结构信息）

执行步骤：

1. 目录分析
   - 提取全书章节目录，分析章名风格（情绪/事件/节奏关键词）
   - 统计章节密度（短章/标准章/长章分布）
   - 推断情绪曲线，标记高点和转折点

2. 分层精读选择
   - 基础层：第1-3章 + 最后3章
   - 扩展层：1/4、1/2、3/4处各±1章
   - 专家层：情绪高点 + 转折点（章名信息量充足时）

3. 深度精读关键场景（7个维度）
   - 结构：这段在全书中的位置？起什么作用？
   - 解释：作者在这里做了什么选择？为什么？
   - 批判：如果换一种选择会怎样？哪种更好？
   - 应用：这个决策规则可以用在什么场景？
   - 情绪密度：这段的情绪强度（1-10）？用了什么手法（铺垫/爆发/留白）？
   - 对话权力：对话中谁占主导？有没有潜台词/试探/压迫？
   - 悬念设计：这段埋了什么伏笔？怎么呼应的？怎么回收的？

4. 提取 7 类语感样本（每类1段，200-300字）
   - 开篇语感：第1章第1-3段，校准开头节奏
   - 日常语感：第N/2章中段，校准日常写作基线
   - 高潮语感：3/4处章节中情绪最激烈的段落，校准情绪密度
   - 对话语感：1/4处或1/2处推进剧情的关键对话，校准对话节奏
   - 描写语感：环境/心理描写段落，校准描写风格
   - 结尾语感：最后1章结尾段落，校准结尾冲击手法
   - 句式节奏语感：全书高点章节中的重复句式/排比/短句堆叠，校准微观节奏

5. 追踪悬念链条
   - 找出全书所有悬念/伏笔
   - 标记每个悬念的：埋设章、强化章、回收章、手法
   - 写入 .distill/suspense-chains-{书名}.md

6. 分析句式节奏模式
   - 在高点章节中找重复句式、排比、短句堆叠
   - 统计使用频率和场景
   - 标注节奏设计手法

输出要求：
- 结构分析写入 {输出目录}/.distill/book-overviews/{书名}.md
- 语感样本写入 {输出目录}/.distill/writing-samples-{书名}.md
- 悬念链条写入 {输出目录}/.distill/suspense-chains-{书名}.md
- 每段语感附出处标注（书名+章节号）
- 每个决策附原文引用（≤150字）
```

### 1.2 选书策略

| 书数 | 策略 |
|------|------|
| 1本 | 精读全书 |
| 2-3本 | 精读评分最高的1本 + 其余各读关键章节 |
| 4-6本 | 精读评分最高的1本 + 其余各读前3章+中段3章+后3章 |

### 1.3 深度分析维度（9个）

| 维度 | 问题 | 深度要求 |
|------|------|----------|
| **结构** | 这段在全书中的位置？起什么作用？ | 必须说明和前后文的关系 |
| **解释** | 作者在这里做了什么选择？为什么？ | 必须有原文引用 |
| **批判** | 如果换一种选择会怎样？哪种更好？ | 必须说明为什么原作选择更好 |
| **应用** | 这个决策规则可以用在什么场景？ | 必须有「如果...则...」格式 |
| **情绪密度** | 这段的情绪强度（1-10）？用了什么手法？ | 必须区分铺垫/爆发/留白 |
| **对话权力** | 对话中谁占主导？有没有潜台词/试探/压迫？ | 必须标注权力关系变化 |
| **悬念设计** | 这段埋了什么伏笔？怎么呼应的？怎么回收的？ | 必须追踪完整链条 |
| **情绪节奏曲线** | 全书的情绪节奏如何变化？高潮和低谷在哪里？ | 必须绘制情绪曲线图，标记关键转折点 |
| **作者价值观** | 作者的价值观/世界观/情感倾向是什么？ | 必须从多本书中提取稳定的价值观模式 |

### 1.4 语感样本选取标准（7类）

每本书提取 **7 类语感样本**，每类 1 段（200-300字）：

| 类型 | 来源层 | 选取标准 | 用途 |
|------|--------|---------|------|
| **开篇语感** | 基础层 | 第1章第1-3段 | 校准开头节奏 |
| **日常语感** | 基础层 | 第N/2章中段（非高潮、非转折） | 校准日常写作基线 |
| **高潮语感** | 扩展层 | 3/4处章节中情绪最激烈的段落 | 校准情绪密度 |
| **对话语感** | 扩展层 | 1/4处或1/2处推进剧情的关键对话 | 校准对话节奏 |
| **描写语感** | 扩展层 | 环境/心理描写段落 | 校准描写风格 |
| **结尾语感** | 基础层 | 最后1章最后3段 | 校准结尾冲击手法 |
| **句式节奏语感** | 扩展层 | 高点章节中的重复句式/排比/短句 | 校准微观节奏设计 |

**结尾语感选取原则**：
- 位置：最后1章的最后3段
- 必须是情绪收束段落，不是情节交代
- 分析手法：重复/对比/留白/金句

**句式节奏语感选取原则**：
- 位置：全书情绪高点章节
- 优先选：重复句式（同一句出现2次以上）、排比（3个以上并列）、短句堆叠（连续3句以上≤10字的句子）
- 分析效果：节奏感、强调感、冲击力

**日常语感选取原则**：
- 位置：第N/2章的中间段落（非开头、非结尾）
- 排除：不能是情绪高点、不能有重大剧情转折、不能是战斗/争吵场景
- 优先选：角色日常互动、过渡性描写、闲笔/闲聊段落

**通用选取原则**：
- 选「最有代表性」的段落，不是「最华丽」的
- 段落必须完整（有开头有结尾）
- 每段附出处标注（书名+章节号）

### 1.5 悬念链条追踪

每本书必须输出悬念链条表：

```markdown
## 悬念链条

| 悬念 | 埋设章 | 强化章 | 回收章 | 手法 | 效果 |
|------|--------|--------|--------|------|------|
| 玉簪（母亲遗物） | 第1章 | 第75章 | 第148章 | 信物呼应 | 首尾呼应，情感闭环 |
| 父亲入狱真相 | 第1章 | 第50章 | 第136章 | 证据链递进 | 悬念升级，真相渐明 |
| 霍砚庭真实目的 | 第3章 | 第100章 | 第120章 | 利用→真情 | 人物弧光，关系反转 |
```

**追踪要求**：
- 找出全书所有悬念/伏笔（包括小悬念）
- 标记每个悬念的完整生命周期
- 分析作者的悬念手法（信物/证据链/信息差/误会）

### 1.6 句式节奏模式分析

每本书必须分析句式节奏模式：

```markdown
## 句式节奏模式

### 重复句式
| 句式 | 出现位置 | 频率 | 效果 |
|------|----------|------|------|
| "她攥紧手里的包袱" | 第80、81章结尾 | 2次 | 强调决心 |
| "三年了" | 第80、81章 | 2次 | 时间跨度感 |

### 排比
| 排比 | 出现位置 | 效果 |
|------|----------|------|
| "嫁妆单子。账本抄本。松田正一的供词。" | 第80章 | 证据罗列，节奏紧凑 |

### 短句堆叠
| 段落 | 出现位置 | 效果 |
|------|----------|------|
| "不重。""够了。""走。" | 第80章开头 | 决断感，节奏快 |
```

### 1.7 产出文件

| 文件 | 内容 |
|------|------|
| `.distill/book-overviews/{书名}.md` | 结构分析（含章名风格+章节密度+分层精读计划+深度分析） |
| `.distill/writing-samples-{书名}.md` | 7 类语感样本，每段附出处 |
| `.distill/suspense-chains-{书名}.md` | 悬念链条表 + 句式节奏模式 |

### 1.8 汇总

所有 agent 完成后，主线程：
1. 汇总各书的 `.distill/book-overviews/`、`.distill/writing-samples-*.md`、`.distill/suspense-chains-*.md`
2. 合并语感样本到 `writing-samples.md`
3. 合并悬念链条到 `suspense-chains.md`
4. 合并句式节奏模式到 `rhythm-patterns.md`

---

## Phase 2：并行提取

**借鉴**：cangjie-skill 的8个并行提取器 + nuwa-skill 的 prompt 模板

**目的**：从精读场景中提取决策框架

### Subagent 任务表

**并行** spawn 14 个 Task sub-agents（write 模式 10 个，review 模式额外 4 个）：

| subagent | 读取的 prompt | 读取的数据 | 产出文件 |
|----------|--------------|-----------|---------|
| 1 心智模型+人设架构 | `extractors/mental-model-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/mental-models.md` |
| 2 决策启发式 | `extractors/decision-heuristic-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/decision-heuristics.md` |
| 3 节奏直觉+节奏曲线 | `extractors/rhythm-intuition-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/rhythm-intuition.md` |
| 4 表达DNA | `extractors/expression-dna-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/expression-dna.md` |
| 5 反模式 | `extractors/anti-pattern-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/anti-patterns.md` |
| 6 书名简介 | `extractors/synopsis-extractor.md` | 每本书的书名+简介+标签 | `.distill/candidates/synopsis-patterns.md` |
| 7 章纲模板+钩子分析 | `extractors/chapter-parser.md` | `.distill/excerpts/*.txt` + `.distill/book-structure/*.md` | `.distill/candidates/chapter-template.md` |
| 8 去AI策略 | `extractors/de-ai-extractor.md` | `.distill/excerpts/*.txt` + `de-ai-modules/*.md` | `.distill/candidates/de-ai-strategy.md` |
| 9 爽点分布 | `extractors/satisfaction-point-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/satisfaction-points.md` |
| 10 评分模型 | `extractors/scoring-model-extractor.md` | `.distill/book-overviews/*.md` + `.distill/candidates/*.md` + `.distill/excerpts/*.txt` | `.distill/candidates/scoring-model.md` |
| **11 审稿红线** | `extractors/review-redline-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` + `.distill/candidates/anti-patterns.md` | `.distill/candidates/review-redlines.md` |
| **12 修改处方** | `extractors/edit-prescription-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` + `.distill/candidates/*.md` | `.distill/candidates/edit-prescriptions.md` |
| **13 质量阈值** | `extractors/quality-threshold-extractor.md` | `.distill/excerpts/*.txt` + `.distill/book-overviews/*.md` + `.distill/writing-samples-*.md` | `.distill/candidates/quality-thresholds.md` |
| **14 审稿人格** | `extractors/review-persona-extractor.md` | `.distill/book-overviews/*.md` + `.distill/excerpts/*.txt` + `.distill/candidates/*.md` | `.distill/candidates/review-persona.md` |

**增强维度说明**：
- 提取器1（心智模型）增加了「人设架构」子维度（角色首次出场+核心特质+动机+弧光+关系网）
- 提取器3（节奏直觉）增加了「节奏曲线」子维度（按章情绪密度+高低点分布+节奏模式）
- 提取器4（表达DNA）增加了「动作电影感」「对话层次」「环境情绪映射」3个子维度
- 提取器7（章纲模板）增加了「钩子类型分析」子维度（章首/章尾钩子分类+频率分布）

### Subagent prompt 模板

spawn subagent 时，用以下结构给任务（以提取器1心智模型为例）：

```
你的任务：从{作者名}的小说中提取心智模型。

读取数据：
- 读取 {输出目录}/.distill/book-overviews/*.md（每本书的结构分析）
- 读取 {输出目录}/.distill/excerpts/*.txt（精读片段，重点读精读章节）

提取内容：
- 故事观：作者怎么看「好故事」（反复出现≥3次的观点）
- 角色观：作者怎么看「好角色」
- 冲突观：作者怎么看「好冲突」
- 爽感观：作者怎么看「爽」

**关键要求：区分「叙事技法」和「设定DNA」**

每条规则必须标注性质：
- **叙事技法**：通用写作方法，不绑定具体设定，所有仿写项目可用
  - 判断标准：去掉具体人名/地名后，规则仍然成立
  - 示例：「信息差张力」「延迟满足」「微物传情」「反套路」
- **设定DNA**：具体设定机制，仿写源书时需反调色盘确认
  - 判断标准：规则绑定具体身份组合/世界观/核心机制
  - 示例：「穿书女配×失忆总裁」「假冒身份」「重生复仇」

每个模型必须：
1. 有原文引用（R）：直接引用书中段落，≤150字
2. 有决策解读（I）：用自己的话说明作者做了什么选择
3. 有触发场景（A2）：什么条件下使用这个模型，必须用「如果{条件}，则{行动}」格式
4. 有执行步骤（E）：具体怎么执行，1-3步
5. 有边界说明（B）：这个模型的局限性，至少1条
6. **有性质标注**：[叙事技法] 或 [设定DNA]
7. **有反例**：至少1个「不应该这样做」的示例，帮助区分好的规则和坏的规则

输出要求：
- 写入 {输出目录}/.distill/candidates/mental-models.md
- 每条模型附原文出处（书名+章节号）
- 发现矛盾直接记录，不要调和
- 区分「作者明确表达的」vs「从行为推断的」
- **叙事技法和设定DNA分开展示**
- **格式要求**：每条规则必须用以下格式：
  ```
  ### [规则名称]
  **性质**：[叙事技法] 或 [设定DNA]
  **R（原文引用）**：≤150字，附书名+章节号
  **I（决策解读）**：用自己的话说明作者做了什么选择
  **A2（触发场景）**：如果{条件}，则{行动}
  **E（执行步骤）**：1-3步
  **B（边界与盲点）**：至少1条
  **反例**：至少1个「不应该这样做」的示例
  ```
```

其他 subagent 按同样结构调整读取数据、提取内容、输出文件名。

### 硬性要求

- 每个 subagent 独立读文件、独立提取、独立写文件
- 产出必须写入 `.distill/candidates/` 目录
- 每条规则附原文引用和出处标注
- 发现矛盾保留矛盾

### 超时建议值

| Phase | 任务 | 建议超时 | 来源说明 | 调整方法 |
|-------|------|---------|---------|---------|
| Phase 1 | 单本书精读 | 120s | 基于 30 万字小说的精读耗时估算 | 书超过 50 万字时调至 180s；书少于 10 万字时调至 60s |
| Phase 2 | 单个提取器 | 90s | 基于提取器读取精读摘要 + 精读片段的耗时 | 提取器需要读取多本书时调至 120s |
| Phase 3 | 统一验证 | 180s | 基于 14 个维度的验证耗时 | 维度数超过 14 时每多 1 个维度加 10s |
| Phase 4 | 单个 RIA++ 构造 | 60s | 基于单维度的 RIA++ 结构化耗时 | 规则数超过 20 条时调至 90s |
| Phase 5 | 合成输出 | 120s | 基于模板填充 + 脚本验证耗时 | — |

**超时处理策略**：

| 情况 | 处理 |
|------|------|
| 单个 subagent 超时 | 等待 30s 后重试一次 |
| 重试仍超时 | 不等待，继续推进。该维度在 Phase 3 标注「信息不足」 |
| 整个 Phase 超时（所有 subagent 都超时） | 检查是否有文件锁定/路径问题，修复后重跑该 Phase |

### 错误处理

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| 某个 subagent 超时/失败 | 等待 30s 后重试一次 | 不等待，继续推进。该维度在 Phase 3 标注「信息不足」 |
| 提取结果为空 | 换一个精读章节重新提取 | 写入 `.distill/candidates/` 文件标注「未找到」，Phase 3 处理 |
| subagent 冲突 | 对比两个版本的原文引用质量 | 保留两个版本，Phase 3 由主 agent 裁决 |

---

## Phase 3：三重验证

**借鉴**：cangjie-skill 的 RIA-TV++ 三重验证

**目的**：确保提取的决策框架是可靠的，不是偶然的

### 3.0 建立对比基准

独特性验证需要参照系。在验证前，先建立「主流写法」基准：

| 基准来源 | 读取方式 |
|---------|---------|
| **其他作者的 SKILL.md** | 扫描 `.claude/skills/story-style/` 下其他作者的 SKILL.md，提取其决策规则作为对比基准 |
| **通用网文写作常识** | 如果没有其他作者的 SKILL.md，用以下常识作为基准：每章有钩子、对话有潜台词、角色有动机、冲突要升级、节奏有起伏、开篇要吸引人、结局要圆满 |

**输出**：内部参考（不需要写入文件），用于独特性验证的对比锚点判断。

### 3.1 统一验证（单 agent）

**优化**：将 3 个并行 subagent 合并为 1 个统一验证 agent，减少调度开销，同时增加「可执行性验证」。

spawn 1 个 Task sub-agent，执行以下 4 种验证：

| 验证顺序 | 验证类型 | 验证标准 | 处理 |
|----------|---------|----------|------|
| 1 | **快速过滤** | 无原文引用 / 在通用规则黑名单中 | 直接淘汰 |
| 2 | **跨书验证** | 同一决策规则在 ≥2 本书中出现 | 标记「可能偶然」，保留 |
| 3 | **频率验证** | 出现频率 ≥5%（非偶发） | 低频规则写入 `rejected/` |
| 4 | **独特性验证** | 满足任一锚点即通过 | 通用规则写入 `rejected/` |
| 5 | **可执行性验证** | 规则必须有清晰的 A2（触发场景）和 E（执行步骤） | 缺失的标记「待补充」，Phase 4 补充 |

**Subagent prompt 模板**：

```
你的任务：对提取的决策规则执行统一验证。

读取数据：
- 读取 {输出目录}/.distill/candidates/*.md（所有提取的规则）
- 读取对比基准（如适用）

验证流程：
1. 快速过滤：
   - 检查每条规则是否有原文引用（R）
   - 检查每条规则是否在通用规则黑名单中
   - 不通过的直接淘汰，写入 rejected/quick-filter.md

2. 跨书验证：
   - 检查同一规则是否在 ≥2 本书中出现
   - 标记「可能偶然」的规则

3. 频率验证：
   - 统计每条规则的出现频率
   - 频率 <5% 的写入 rejected/low-frequency.md

4. 独特性验证：
   - 检查是否满足任一锚点（频率/对比/反例）
   - 不满足的写入 rejected/generic.md

5. 可执行性验证：
   - 检查每条规则是否有清晰的 A2（触发场景）和 E（执行步骤）
   - 缺失的标记「待补充」，保留在 candidates/ 中

输出要求：
- 不通过的规则写入 {输出目录}/.distill/rejected/{验证类型}.md
- 每条附淘汰原因
- 通过的规则保留在 `.distill/candidates/` 中，标记为「已验证」
- 生成验证报告：通过率、淘汰原因分布、待补充数量
```

### 独特性验证锚点（满足任一即通过）

| 锚点 | 标准 | 示例 |
|------|------|------|
| **频率锚点** | 该规则在本书中出现频率 > 60%（是稳定模式，非偶然） | 「开篇用他人对话碎片」在6本书的第1章都出现 → 通过 |
| **对比锚点** | 与同类题材主流写法不同 | 古言通常用旁白交代背景，但这位作者用角色视角碎片 → 通过 |
| **反例锚点** | 能找到「不这样做」的对比案例 | 其他作者用「说道」标签，这位作者用动作beat替代 → 通过 |

**都不满足** → 判定为通用规则，写入 `.distill/rejected/`。

### 通用规则黑名单（不写入 SKILL.md）

- 每章要有钩子（太通用）
- 对话要有潜台词（太通用）
- 角色要有动机（太通用）
- 冲突要有升级（太通用）

### 单本书例外

如果只有1本书，跳过跨书验证，只做频率验证和独特性验证。

### 3.2 汇总 + 质量检查

验证 agent 完成后，主线程：
1. 读取验证报告（通过率、淘汰原因分布、待补充数量）
2. 统计淘汰规则数
3. 标记矛盾点
4. **质量检查**：
   - 规则具体性：≥80% 规则有清晰 A2+E
   - 边界清晰度：≥70% 规则有 B
   - 覆盖完整度：write 模式 10 个维度都有输出，缺失 ≤2；review 模式 14 个维度都有输出，缺失 ≤3
   - 可执行性：待补充的规则数量 ≤20%
   - 不达标 → 回炉 Phase 2 补充提取

### 审计轨迹

- **通过的规则**：保留在 `.distill/candidates/` 对应文件
- **不通过的规则**：写入 `.distill/rejected/{验证类型}.md`，每条附淘汰原因
- 用户可事后捞回被淘汰的规则

---

## Phase 4：RIA++ 构造

**借鉴**：cangjie-skill 的 RIA++ 结构化方法

**目的**：将验证通过的决策框架结构化，附原文引用

### RIA++ 结构

每个决策规则必须包含：

| 维度 | 说明 | 要求 |
|------|------|------|
| **R**（原文引用） | 原文中的一段话 | ≤150字，附书名+章节号 |
| **I**（决策解读） | 作者在这里做了什么选择 | 用自己的话，不照搬原文 |
| **A1**（书中案例） | 这个规则在书中的具体应用 | 至少1个案例 |
| **A2**（触发场景） | 什么条件下使用这个规则 | 「如果{条件}，则{行动}」格式 |
| **E**（可执行步骤） | 具体怎么执行 | 1-3步 |
| **B**（边界与盲点） | 这个规则的局限性 | 至少1条 |

### 并行构造（write 模式）

**并行** spawn 10 个 Task sub-agents（每个维度一个）：

| subagent | 维度 | 读取文件 | 产出文件 |
|----------|------|---------|---------|
| 1 | 心智模型+人设架构 | `.distill/candidates/mental-models.md` | `.distill/constructed/mental-models.md` |
| 2 | 决策启发式 | `.distill/candidates/decision-heuristics.md` | `.distill/constructed/decision-heuristics.md` |
| 3 | 节奏直觉+节奏曲线 | `.distill/candidates/rhythm-intuition.md` | `.distill/constructed/rhythm-intuition.md` |
| 4 | 表达DNA | `.distill/candidates/expression-dna.md` | `.distill/constructed/expression-dna.md` |
| 5 | 反模式 | `.distill/candidates/anti-patterns.md` | `.distill/constructed/anti-patterns.md` |
| 6 | 书名简介 | `.distill/candidates/synopsis-patterns.md` | `.distill/constructed/synopsis-patterns.md` |
| 7 | 章纲模板+钩子分析 | `.distill/candidates/chapter-template.md` | `.distill/constructed/chapter-template.md` |
| 8 | 去AI策略 | `.distill/candidates/de-ai-strategy.md` | `.distill/constructed/de-ai-strategy.md` |
| 9 | 爽点分布 | `.distill/candidates/satisfaction-points.md` | `.distill/constructed/satisfaction-points.md` |
| 10 | 评分模型 | `.distill/candidates/scoring-model.md` | `.distill/constructed/scoring-model.md` |

### 并行构造（review 模式）

**并行** spawn 14 个 Task sub-agents（上述 10 个 + 下述 4 个）：

| subagent | 维度 | 读取文件 | 产出文件 |
|----------|------|---------|---------|
| 1-10 | 同 write 模式 | 同 write 模式 | 同 write 模式 |
| 11 | 审稿红线 | `.distill/candidates/review-redlines.md` | `.distill/constructed/review-redlines.md` |
| 12 | 修改处方 | `.distill/candidates/edit-prescriptions.md` | `.distill/constructed/edit-prescriptions.md` |
| 13 | 质量阈值 | `.distill/candidates/quality-thresholds.md` | `.distill/constructed/quality-thresholds.md` |
| 14 | 审稿人格 | `.distill/candidates/review-persona.md` | `.distill/constructed/review-persona.md` |

**Subagent prompt 模板**：

```
你的任务：将{维度}的规则按 RIA++ 结构化。

读取数据：
- 读取 {输出目录}/.distill/candidates/{文件名}.md

RIA++ 结构要求：
- R（原文引用）：≤150字，附书名+章节号
- I（决策解读）：用自己的话说明作者做了什么选择
- A1（书中案例）：至少1个案例
- A2（触发场景）：「如果{条件}，则{行动}」格式
- E（可执行步骤）：1-3步
- B（边界与盲点）：至少1条

输出要求：
- 写入 {输出目录}/.distill/constructed/{文件名}.md
- 逐条按 RIA++ 结构构造
- 保留原文出处标注
```

### 汇总

所有 agent 完成后，主线程合并各维度的构造结果。

---

## Phase 5：合成输出

### 5.1 读取模板

根据模式选择模板：

| 模式 | 模板文件 | 产出路径 |
|------|---------|---------|
| write | `templates/SKILL_template.md` | `.claude/skills/story-style/{作者名}/SKILL.md` |
| review | `templates/SKILL_review_template.md` | `.claude/skills/story-style/{作者名}/review/SKILL.md` |

### 5.2 填充内容

#### write 模式

将 Phase 4 的 RIA++ 结构化内容填入写作模板的对应 section。

**关键要求：SKILL.md 必须明确区分「叙事技法」和「设定DNA」**

SKILL.md 的结构必须按以下分区：

```
## 叙事技法（通用 · 可用于所有仿写项目）

以下技法是从多本小说中提取的通用写作方法，不绑定具体设定。
仿写任何书时均可使用。

### 信息差张力
**性质**：叙事技法（通用）
...
### 延迟满足
**性质**：叙事技法（通用）
...

---

## 设定DNA（具体 · 仿写源书时需反调色盘）

以下是从多本小说中提取的设定模式。
仿写源书时，不能使用与源书相同的设定DNA组合。

### 身份错位模式
**性质**：设定DNA（仿写源书时禁用同类组合）
**定义**：角色的真实身份与表面身份不一致
**具体实现**：
- 《书A》：穿书女配×失忆总裁
- 《书B》：假千金×落魄反派
...

---

## 节奏技法（通用 · 可用于所有仿写项目）
...

## 表达技法（通用 · 可用于所有仿写项目）
...
```

**判断标准**：
- 叙事技法：去掉具体人名/地名后，规则仍然成立
- 设定DNA：规则绑定具体身份组合/世界观/核心机制

#### review 模式

将 Phase 4 的 RIA++ 结构化内容填入审稿模板。

**review SKILL.md 是增量附件**，只包含审稿专用内容（红线+处方+阈值+检查清单），写作规则引用 `../SKILL.md`。

```
review SKILL.md 结构：
├── 审稿人设（第一人称，像作者自我介绍）
├── 审稿流程（快速判定表）
├── 审稿红线（摘要表，详细见 references/review-redlines.md）
├── 修改处方（摘要表，详细见 references/edit-prescriptions.md）
├── 质量阈值（阈值表+检测脚本）
└── 去AI检查清单
```

**review 模式的关键要求**：
- **审稿人格必须提取**：从源书中提取作者的审稿风格，用第一人称写，像真人编辑
- 审稿红线必须有「判定标准」和「严重等级」
- 修改处方必须有「改前示例」和「改后示例」
- 质量阈值必须有「作者基线」和「告警阈值」
- 质量阈值的数值必须用 Python 脚本验证，不能人工估算
- **文件要小**：红线/处方只写摘要表，详细内容放 references/
- **多agent审改流程必须内置**：长篇小说（≥30章）自动启用多agent并行审稿

#### review SKILL.md 结构（v2.1）

```
review SKILL.md 结构：
├── 审稿人设（第一人称，像作者自我介绍）
├── 审稿流程（快速判定表）
├── 审稿红线（摘要表，详细见 references/review-redlines.md）
├── 修改处方（摘要表，详细见 references/edit-prescriptions.md）
├── 质量阈值（阈值表+检测脚本）
├── 去AI检查清单
└── 多agent审改流程（长篇专用）    ← 新增
    ├── Phase 0：自动分卷
    ├── Phase 1：并行审稿（N个agent，每卷一个）
    ├── Phase 2：交叉复审（边界章节）
    └── Phase 3：汇总报告
```

#### 多agent审改流程模板

在 review SKILL.md 中必须包含以下 section：

```markdown
## 多agent审改流程（长篇专用）

> 章数 ≥ 30 时自动启用

### Phase 0：自动分卷
- 有章纲：按章纲的卷结构分
- 无章纲：按每卷 20-40 章等分
- 标记边界章节（每卷前后各 2 章）

### Phase 1：并行审稿
spawn N 个 Task sub-agents（每卷一个）

每个 agent：
1. 读取该卷所有章节
2. 对照红线逐章检查
3. 统计质量阈值
4. 审查爽点/人设/节奏
5. 输出该卷审稿报告

### Phase 2：交叉复审
spawn 2 个 agent（首尾卷各一个）

每个 agent：
1. 读取相邻卷的边界章节
2. 检查节奏断裂、人设不一致、伏笔断裂

### Phase 3：汇总报告
主线程：
1. 合并各卷报告
2. 生成总评（判定/评分/修改清单）
3. 写入 {书名}/追踪/审稿报告.md
```

**触发条件**：
| 章数 | 审稿方式 |
|------|----------|
| < 30 | 单agent审稿 |
| 30-100 | 多agent（2-3卷） |
| > 100 | 多agent（4-6卷） |

### 5.3 生成 meta.json

根据模式选择模板：

| 模式 | 模板文件 | 产出路径 |
|------|---------|---------|
| write | `templates/meta_template.json` | `.claude/skills/story-style/{作者名}/meta.json` |
| review | `templates/meta_review_template.json` | `.claude/skills/story-style/{作者名}/review/meta.json` |

**write 模式**包含：name、label、description、source_skill、compatible_genres、chapter_word_count、decision_framework（各维度计数）、extraction_info（源书+日期+版本）。

**review 模式**包含：name、label、description、companion_of（指向写作SKILL）、review_framework（红线数+处方数+阈值数）、quality_baselines（各项基线值）、extraction_info（源书+日期+mode）。比 write 模式更精简，不重复写作框架的数据。

### 5.4 去AI策略归档

Phase 2 extractor 8 已完成预选，本步仅归档：
- 分析作者写作习惯（连接词/句长/副词/标点等8个维度）
- 对照 `de-ai-modules/` 模块库选择 3-5 个匹配模块
- 写入 SKILL.md 的「去AI策略」section

**distill 职责到此为止**。执行顺序、写后扫描等由 story-rewrite 负责。

### 5.5 脚本验证统计数据

**核心原则：涉及统计的数据必须用脚本验证，禁止人工估算。**

在写入 SKILL.md 前，对所有量化数据执行脚本验证：

| 统计项 | 验证方法 | 阈值 |
|--------|---------|------|
| 对话占比 | 统计引号内字数 / 总字数 | 与声称值误差 ≤5% |
| 副词密度 | 统计「微微/轻轻/淡淡/缓缓」次数 / 总字数 | 精确到小数点后2位 |
| 连接词密度 | 统计「于是/然而/因此/所以/但是」次数 / 总字数 | 精确到小数点后2位 |
| 单句成段占比 | 统计单句段落数 / 总段落数 | 与声称值误差 ≤5% |
| 章名风格 | 统计陈述句/疑问句/其他比例 | 精确到百分比 |

**执行步骤**：

1. 编写 Python 脚本，从 `.distill/sources/*.txt` 和 `.distill/writing-samples-*.md` 提取正文
2. 运行脚本，输出各项统计数据
3. 将脚本输出的数值写入 SKILL.md，替代人工估算
4. 保留脚本文件到 `{输出目录}/verify_stats.py` 供复核

**脚本模板**：

```python
import re
from pathlib import Path

def count_chinese(text):
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def extract_dialogue(text):
    return "".join(re.findall(r'"([^"]*)"', text))

def count_pattern(text, patterns):
    return sum(len(re.findall(p, text)) for p in patterns)

# 对话占比
total = count_chinese(content)
dialogue = count_chinese(extract_dialogue(content))
dialogue_ratio = dialogue / total * 100

# 副词密度
adverbs = ['微微', '轻轻', '淡淡', '缓缓']
adverb_density = count_pattern(content, adverbs) / total * 100

# 连接词密度
connectors = ['于是', '然而', '因此', '所以', '但是']
connector_density = count_pattern(content, connectors) / total * 100
```

**违规处理**：
- 如果脚本验证结果与声称值误差 >10%，必须修正 SKILL.md
- 如果无法运行脚本，标注「待验证」而非填写估算值

### 5.6 写入文件

- 写入 `.claude/skills/story-style/{作者名}/SKILL.md`
- 写入 `.claude/skills/story-style/{作者名}/meta.json`
- 保留 `{输出目录}/verify_stats.py` 脚本文件

---

## Phase 6：Consolidation（蒸馏收口）

**目的**：把 Phase 2-5 生成的中间产物（candidates/、constructed/、rejected/、sources/、book-overviews/）清出生产目录，保留最终交付物。

**核心原则**：
- 所有中间产物从 Phase 2 开始写到 `.distill/` 子目录
- Phase 6 末尾整个 `.distill/` 目录删除
- 最终交付物只含 SKILL.md + meta.json + references/ + review/
- 写完必须跑自检（文件数 + token 预算 + 无中间产物）

### 6.1 工作目录规范

```
{输出根}/{作者名}/
├── SKILL.md                      ← 交付物（write 模式）
├── meta.json                     ← 交付物
├── test-prompts.json             ← 交付物（验证阶段产物）
├── review/                       ← 交付物（review 模式）
│   ├── SKILL.md
│   └── meta.json
├── references/                   ← 交付物（详细规则）
│   ├── writing-samples.md
│   ├── mental-models.md
│   ├── decision-heuristics.md
│   ├── rhythm-intuition.md
│   ├── expression-dna.md
│   ├── anti-patterns.md
│   ├── synopsis-patterns.md
│   ├── chapter-template.md
│   ├── de-ai-strategy.md
│   ├── satisfaction-points.md
│   ├── scoring-model.md
│   ├── review-redlines.md         ← review 模式
│   ├── edit-prescriptions.md      ← review 模式
│   ├── quality-thresholds.md      ← review 模式
│   └── review-persona.md          ← review 模式
└── .distill/                     ← 工作目录，Phase 6 末尾删除
    ├── book-overviews/            ← Phase 1 产出
    ├── candidates/                ← Phase 2 原始产出
    ├── constructed/               ← Phase 4 RIA++ 终版（拷贝目标）
    ├── rejected/                  ← Phase 3 淘汰
    └── sources/                   ← 原文备份
```

### 6.2 必须执行的 5 步清理

| Step | 动作 | 来源 | 去向 | 失败处理 |
|------|------|------|------|----------|
| 1 | 删除原文 | `.distill/sources/` | （删） | 强制 |
| 2 | 合并 RIA++ 终版 | `.distill/constructed/*.md` | `references/*.md` | 检查重名覆盖 |
| 3 | 删除构造目录 | `.distill/constructed/` | （删） | 强制 |
| 4 | 删除抽取目录 | `.distill/candidates/` `.distill/rejected/` | （删） | 强制 |
| 5 | 删除工作目录 | `.distill/` | （删） | 强制 |

**禁止遗漏**：任何一步失败都视为蒸馏未完成，不应被 story-rewrite 调用。

### 6.3 交付物自检 3 项

```bash
# 1. 文件数
$count = (Get-ChildItem -Recurse -File | Measure-Object).Count
# 写模式上限 14，审稿模式上限 20（多 review/ 2 + 6 review 专用 references）

# 2. token 预算
# SKILL.md ≤ 20KB
# references/ 单文件 ≤ 15KB
# references/ 总和 ≤ 60KB

# 3. 无中间产物
Test-Path .distill -ErrorAction SilentlyContinue   # 必须 $false
Get-ChildItem references/candidates,references/rejected,references/book-overviews -ErrorAction SilentlyContinue
# 必须为空
```

不通过 → 立即重跑 Phase 6，禁止输出。

### 6.4 v1.0 遗产标记

为不破坏现有 4 个 skill（闻栖/初点点/空留/橙味薏米粥）的向后兼容：
- 旧 skill 不迁移，标记为 `pipeline_version: "1.0"` in meta.json
- 新蒸馏按 Phase 6 走，meta.json 标记 `pipeline_version: "2.0"`
- 旧 skill 可用 `scripts/consolidate_legacy.py`（待补）一次性回炉

### 6.5 失败回滚

如果 Phase 6 中途失败（脚本崩溃、路径冲突）：
1. 保留 `.distill/` 完整内容
2. SKILL.md 标记 `[DRAFT - Phase 6 INCOMPLETE]`
3. 不允许 story-rewrite 调用此 skill
4. 用户可重跑 Phase 6 或手动补救

---

## 输出结构（v2.0：post-consolidation）

**重要**：以下结构是 Phase 6 Consolidation 跑完后的最终交付物形态。Phase 1-5 期间，所有中间产物写在 `.distill/` 子目录（详见 Phase 6）。

### write 模式最终交付

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                          # 写作决策框架（15-20KB）
├── meta.json                         # 量化数据
├── test-prompts.json                 # 验证产物（可选）
└── references/                       # 11 个维度文件
    ├── writing-samples.md            # 合并的语感样本
    ├── mental-models.md              # 心智模型
    ├── decision-heuristics.md        # 决策启发式
    ├── rhythm-intuition.md           # 节奏直觉
    ├── expression-dna.md             # 表达DNA
    ├── anti-patterns.md              # 反模式
    ├── synopsis-patterns.md          # 书名与简介
    ├── chapter-template.md           # 章纲模板
    ├── de-ai-strategy.md             # 去AI策略
    ├── satisfaction-points.md        # 爽点分布
    └── scoring-model.md              # 评分模型
```

= 14 个文件（SKILL.md + meta.json + test-prompts.json + 11 references）

### review 模式最终交付

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                          # 写作框架（write 模式产出）
├── meta.json
├── test-prompts.json
├── review/                           # 2 个
│   ├── SKILL.md                      # 审稿框架（增量附件，~80 行）
│   └── meta.json
└── references/                       # 15 个
    ├── （write 模式的 11 个）
    ├── review-redlines.md            # 审稿红线
    ├── edit-prescriptions.md         # 修改处方
    ├── quality-thresholds.md         # 质量阈值
    └── review-persona.md             # 审稿人格
```

= 20 个文件（write 14 + review/ 2 + 4 review 专用 references）

### 不允许出现的目录/文件

以下目录/文件在最终交付物中**绝对不允许存在**（Phase 6 收口检查项）：

| 名称 | 类型 | 原因 |
|------|------|------|
| `references/book-overviews/` | 目录 | Phase 1 工作产物，已并入 SKILL.md |
| `references/candidates/` | 目录 | Phase 2 原始产出，验证后无价值 |
| `references/rejected/` | 目录 | Phase 3 淘汰，审计后可丢弃 |
| `references/constructed/` | 目录 | Phase 4 RIA++ 终版，合并后无价值 |
| `references/constructed/constructed-*.md` | 文件 | 副本，已合并 |
| `references/writing-samples-{书名}.md` | 文件 | 已合并为 writing-samples.md |
| `sources/` 或 `.distill/sources/` | 目录 | 原文备份，蒸馏后无价值 |
| `.distill/` 整个 | 目录 | 工作目录，必须删除 |

### v1.0 → v2.0 迁移说明

现有 4 个 skill（闻栖/初点点/空留/橙味薏米粥）按 v1.0 pipeline 蒸馏，不符合 v2.0 输出结构。处理方案：
- **不自动迁移**：避免破坏现有调用
- **标记 v1.0**：在 `meta.json` 显式标注 `pipeline_version: "1.0"`
- **新蒸馏按 v2.0**：所有新 skill 走 Phase 6
- **手动回炉**：如需迁移旧 skill，跑 `scripts/consolidate_legacy.py`（待补）

---

## 蒸馏后验证

蒸馏完成后，建议执行 `/story-distill-verify` 进行压力测试和验证：

```
/story-distill-verify
```

**验证内容**：
- 压力测试：用 test-prompts.json 测试规则是否可用
- 验证：检查规则的完整性和一致性
- 闭环回馈：根据测试结果修正规则

**review 模式额外验证**：
- 运行 `review/verify_stats.py` 脚本，验证质量阈值数值
- 用测试稿件跑一遍审稿流程，验证红线判定和处方可用性

**验证产出**：
- `test-prompts.json` — 测试用例
- 演化日志 — 记录规则的修正历史

**建议**：蒸馏完成后立即执行验证，确保规则质量。

---

## 蒸馏反例黑名单（不要做的事）

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|---------|
| 1 | **提取表面特征而非决策** | "喜欢用四字词"是表面特征，不是决策；"开篇用对话碎片建立代入感"才是决策 | 每条规则必须回答「作者在这里做了什么选择」 |
| 2 | **把通用规则写入 SKILL** | "每章要有钩子""对话要有潜台词"太通用，写了等于没写 | 用独特性验证锚点过滤：频率>60%、与主流不同、能找到反例 |
| 3 | **调和矛盾而非保留矛盾** | 两本书的开篇策略冲突时，不要强行统一 | 保留矛盾，标注「场景A用X，场景B用Y」 |
| 4 | **跳过 Phase 1 直接提取** | 没有整书理解的提取是盲人摸象 | 必须完成目录分析+精读计划+用户确认 |
| 5 | **subagent 合并执行** | 10/14个提取器并行是为了独立视角，合并会相互污染 | 每个 subagent 独立读文件、独立提取、独立写文件 |
| 6 | **Phase 3 验证流于形式** | 跨书验证/频率验证/独特性验证缺一不可 | 三条验证都必须执行，不通过的写入 `.distill/rejected/` |
| 7 | **去AI策略预选过多模块** | 预选超过5个模块会过度约束写作 | Phase 2 预选3-5个 |
| 8 | **用 AI 腔描述规则** | "根据情况灵活把握""建议适当调整"是废话 | 规则必须有明确的 A2（触发场景）和 E（执行步骤） |
| 9 | **人工估算统计数据** | "对话占比约60%""副词密度约0.3次/百字"是瞎估，误差可达40%+ | 涉及统计的数据必须用 Python 脚本验证，脚本保存到输出目录 |
| 10 | **（review）红线没有判定标准** | "写得不好就改"是废话，审稿时无法执行 | 红线必须有具体判定条件（如「连续≥3章无冲突」） |
| 11 | **（review）处方没有改前改后示例** | "加强描写"是废话，作者不知道怎么改 | 处方必须有改前示例（问题写法）和改后示例（作者风格的替代方案） |
| 12 | **（review）阈值人工估算** | "对话占比约60%"误差可达40%+，告警阈值形同虚设 | 所有数值必须用脚本统计，脚本保存到输出目录 |
