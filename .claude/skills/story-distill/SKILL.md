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
    ├── /story-distill --mode=write（或无 --mode）  → 写作模式（Phase 2: 8个提取器）
    │
    └── /story-distill --mode=review               → 审稿模式（Phase 2: 11个提取器）
```

**复用关系**：
- Phase 0（输入验证）：完全复用
- Phase 1（整书理解）：完全复用
- Phase 2（并行提取）：write 模式 8 个提取器 → review 模式 11 个提取器（原 8 个 + 审稿红线 + 修改处方 + 质量阈值）
- Phase 3（三重验证）：完全复用
- Phase 4（RIA++ 构造）：完全复用
- Phase 5（合成输出）：write 模式用写作模板，review 模式用审稿模板

---

## 流程总览

```
Phase 0    输入验证 → 确认原文格式+数量
Phase 1    并行精读（N个 agent）→ 每本书独立分析
Phase 2    并行提取 → 从原文中提取决策框架
              write 模式：10个 subagent
              review 模式：14个 subagent
Phase 3    并行验证（3个 subagent）→ 跨书/频率/独特性 + 质量检查
Phase 4    并行构造（10/14个 subagent）→ RIA++ 结构化输出，附原文引用
Phase 5    合成输出 → 生成 SKILL.md + meta.json
```

**预计耗时**：
- write 模式：12-18 分钟（3本小说）
- review 模式：18-25 分钟（3本小说，多4个提取器）

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
2. 创建输出目录结构：
   ```
   .claude/skills/story-style/{作者名}/
   ├── references/
   │   ├── book-overviews/
   │   ├── candidates/
   │   ├── rejected/
   │   └── （后续阶段产出）
   └── sources/
   ```
3. 复制原文到 `sources/{book_name}.txt`

**不满足要求时**：提示用户修正格式后重试。

### 错误处理

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| 文件不存在 | 检查路径拼写，尝试相邻目录 | 停止，提示用户检查路径 |
| 编码非UTF-8 | 自动检测编码，尝试 GBK/GB2312 转 UTF-8 | 停止，提示用户提供 UTF-8 文件 |
| 章节格式不匹配 | 统计前5章开头格式，自动适配 | 提示用户修正格式 |
| 只有1本书 | 正常继续，跳过跨书验证 | — |

---

## Phase 1：整书理解（Adler 分析）

**借鉴**：cangjie-skill 的 Adler 分析阅读法

**目的**：精读关键场景，理解故事结构、角色弧线、情绪曲线

### 1.1 并行精读

**并行** spawn N 个 Task sub-agents（每本书一个）：

每个 agent 负责一本书的：
1. 目录分析（章名分析 + 章节密度 + 情绪曲线推断）
2. 分层精读选择（基础层 + 扩展层 + 专家层）
3. 精读关键场景（按精读计划表）
4. 提取 5 类语感样本

**产出**：每本书写入 `references/book-overviews/{书名}.md` + `writing-samples-{书名}.md`

**Subagent prompt 模板**：

```
你的任务：精读《{书名}》，提取结构分析和语感样本。

读取数据：
- 读取 {输出目录}/sources/{书名}.txt

执行步骤：
1. 提取全书章节目录，分析章名风格（情绪/事件/节奏关键词）
2. 统计章节密度（短章/标准章/长章分布）
3. 推断情绪曲线，标记高点和转折点
4. 按分层精读选择关键章节：
   - 基础层：第1-3章 + 最后3章
   - 扩展层：1/4、1/2、3/4处各±1章
   - 专家层：情绪高点 + 转折点（章名信息量充足时）
5. 精读关键场景，分析每个场景的：结构、解释、批判、应用
6. 提取 5 类语感样本（开篇/日常/高潮/对话/描写）

输出要求：
- 写入 {输出目录}/references/book-overviews/{书名}.md
- 语感样本写入 {输出目录}/references/writing-samples-{书名}.md
- 每段语感附出处标注（书名+章节号）
```

### 1.2 选书策略

| 书数 | 策略 |
|------|------|
| 1本 | 精读全书 |
| 2-3本 | 精读评分最高的1本 + 其余各读关键章节 |
| 4-6本 | 精读评分最高的1本 + 其余各读前3章+中段3章+后3章 |

### 1.3 分析维度（每个精读场景）

| 维度 | 问题 |
|------|------|
| **结构** | 这段在全书中的位置？起什么作用？ |
| **解释** | 作者在这里做了什么选择？为什么？ |
| **批判** | 如果换一种选择会怎样？哪种更好？ |
| **应用** | 这个决策规则可以用在什么场景？ |

### 1.4 语感样本选取标准

每本书提取 **5 类语感样本**，每类 1 段（200-300字）：

| 类型 | 来源层 | 选取标准 | 用途 |
|------|--------|---------|------|
| **开篇语感** | 基础层 | 第1章第1-3段 | 校准开头节奏 |
| **日常语感** | 基础层 | 第N/2章中段（非高潮、非转折的日常叙述段落） | 校准日常写作基线 |
| **高潮语感** | 扩展层 | 3/4处章节中情绪最激烈的段落 | 校准情绪密度 |
| **对话语感** | 扩展层 | 1/4处或1/2处推进剧情的关键对话 | 校准对话节奏 |
| **描写语感** | 扩展层 | 环境/心理描写段落 | 校准描写风格 |

**日常语感选取原则**：
- 位置：第N/2章的中间段落（非开头、非结尾）
- 排除：不能是情绪高点、不能有重大剧情转折、不能是战斗/争吵场景
- 优先选：角色日常互动、过渡性描写、闲笔/闲聊段落

**通用选取原则**：
- 选「最有代表性」的段落，不是「最华丽」的
- 段落必须完整（有开头有结尾）
- 每段附出处标注（书名+章节号）

### 1.5 产出文件

全部写入 `.claude/skills/story-style/{作者名}/references/`：

| 文件 | 内容 |
|------|------|
| `book-overviews/{书名}.md` | 每本书的结构分析（含章名风格+章节密度+分层精读计划） |
| `writing-samples-{书名}.md` | 每本书的 5 类语感样本，每段附出处 |

### 1.6 汇总

所有 agent 完成后，主线程：
1. 汇总各书的 `book-overviews/` 和 `writing-samples-*.md`
2. 合并语感样本到 `writing-samples.md`

---

## Phase 2：并行提取

**借鉴**：cangjie-skill 的8个并行提取器 + nuwa-skill 的 prompt 模板

**目的**：从精读场景中提取决策框架

### Subagent 任务表

**并行** spawn 12 个 Task sub-agents：

| subagent | 读取的 prompt | 读取的数据 | 产出文件 |
|----------|--------------|-----------|---------|
| 1 心智模型+人设架构 | `extractors/mental-model-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/mental-models.md` |
| 2 决策启发式 | `extractors/decision-heuristic-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/decision-heuristics.md` |
| 3 节奏直觉+节奏曲线 | `extractors/rhythm-intuition-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/rhythm-intuition.md` |
| 4 表达DNA | `extractors/expression-dna-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/expression-dna.md` |
| 5 反模式 | `extractors/anti-pattern-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/anti-patterns.md` |
| 6 书名简介 | `extractors/synopsis-extractor.md` | 每本书的书名+简介+标签 | `candidates/synopsis-patterns.md` |
| 7 章纲模板+钩子分析 | `extractors/chapter-parser.md` | `sources/*.txt` | `candidates/chapter-template.md` |
| 8 去AI策略 | `extractors/de-ai-extractor.md` | `sources/*.txt` + `de-ai-modules/*.md` | `candidates/de-ai-strategy.md` |
| 9 爽点分布 | `extractors/satisfaction-point-extractor.md` | `book-overviews/*.md` + `sources/*.txt` | `candidates/satisfaction-points.md` |
| 10 评分模型 | `extractors/scoring-model-extractor.md` | `book-overviews/*.md` + `candidates/*.md` + `sources/*.txt` | `candidates/scoring-model.md` |
| **11 审稿人格** | `extractors/review-persona-extractor.md` | `book-overviews/*.md` + `sources/*.txt` + `candidates/*.md` | `candidates/review-persona.md` |
| **12 修改能力** | `extractors/revision-capability-extractor.md` | `book-overviews/*.md` + `sources/*.txt` + `candidates/*.md` + `candidates/review-persona.md` | `candidates/revision-capability.md` |

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
- 读取 {输出目录}/references/book-overviews/*.md（每本书的结构分析）
- 读取 {输出目录}/sources/*.txt（原文，重点读精读章节）

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
3. 有触发场景（A2）：什么条件下使用这个模型
4. 有边界说明（B）：这个模型的局限性
5. **有性质标注**：[叙事技法] 或 [设定DNA]

输出要求：
- 写入 {输出目录}/references/candidates/mental-models.md
- 每条模型附原文出处（书名+章节号）
- 发现矛盾直接记录，不要调和
- 区分「作者明确表达的」vs「从行为推断的」
- **叙事技法和设定DNA分开展示**
```

其他7个 subagent 按同样结构调整读取数据、提取内容、输出文件名。

### 硬性要求

- 每个 subagent 独立读文件、独立提取、独立写文件
- 产出必须写入 `references/candidates/` 目录
- 每条规则附原文引用和出处标注
- 发现矛盾保留矛盾

### 错误处理

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| 某个 subagent 超时/失败 | 等待 30s 后重试一次 | 不等待，继续推进。该维度在 Phase 3 标注「信息不足」 |
| 提取结果为空 | 换一个精读章节重新提取 | 写入 candidates 文件标注「未找到」，Phase 3 处理 |
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

### 3.1 并行验证

**并行** spawn 3 个 Task sub-agents：

| subagent | 验证类型 | 读取数据 | 产出 |
|----------|---------|---------|------|
| 1 跨书验证 | 同一决策规则在 ≥2 本书中出现 | `references/candidates/*.md` | 标记「可能偶然」的规则 |
| 2 频率验证 | 出现频率 ≥5%（非偶发） | `references/candidates/*.md` | 低频规则写入 `rejected/` |
| 3 独特性验证 | 满足任一锚点即通过 | `references/candidates/*.md` + 对比基准 | 通用规则写入 `rejected/` |

**Subagent prompt 模板**：

```
你的任务：对提取的决策规则执行{验证类型}验证。

读取数据：
- 读取 {输出目录}/references/candidates/*.md（所有提取的规则）
- 读取对比基准（如适用）

验证标准：
{验证标准}

输出要求：
- 不通过的规则写入 {输出目录}/references/rejected/{验证类型}.md
- 每条附淘汰原因
- 通过的规则保留在 candidates/ 中，标记为「已验证」
```

### 独特性验证锚点（满足任一即通过）

| 锚点 | 标准 | 示例 |
|------|------|------|
| **频率锚点** | 该规则在本书中出现频率 > 60%（是稳定模式，非偶然） | 「开篇用他人对话碎片」在6本书的第1章都出现 → 通过 |
| **对比锚点** | 与同类题材主流写法不同 | 古言通常用旁白交代背景，但这位作者用角色视角碎片 → 通过 |
| **反例锚点** | 能找到「不这样做」的对比案例 | 其他作者用「说道」标签，这位作者用动作beat替代 → 通过 |

**都不满足** → 判定为通用规则，写入 `rejected/`。

### 通用规则黑名单（不写入 SKILL.md）

- 每章要有钩子（太通用）
- 对话要有潜台词（太通用）
- 角色要有动机（太通用）
- 冲突要有升级（太通用）

### 单本书例外

如果只有1本书，跳过跨书验证，只做频率验证和独特性验证。

### 3.2 汇总 + 质量检查

所有 agent 完成后，主线程：
1. 合并各验证结果
2. 统计淘汰规则数
3. 标记矛盾点
4. **质量检查**：
   - 规则具体性：≥80% 规则有清晰 A2+E
   - 边界清晰度：≥70% 规则有 B
   - 覆盖完整度：write 模式 10 个维度都有输出，缺失 ≤2；review 模式 14 个维度都有输出，缺失 ≤3
   - 不达标 → 回炉 Phase 2 补充提取

### 审计轨迹

- **通过的规则**：保留在 `references/candidates/` 对应文件
- **不通过的规则**：写入 `references/rejected/{验证类型}.md`，每条附淘汰原因
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
| 1 | 心智模型+人设架构 | `candidates/mental-models.md` | `constructed/mental-models.md` |
| 2 | 决策启发式 | `candidates/decision-heuristics.md` | `constructed/decision-heuristics.md` |
| 3 | 节奏直觉+节奏曲线 | `candidates/rhythm-intuition.md` | `constructed/rhythm-intuition.md` |
| 4 | 表达DNA | `candidates/expression-dna.md` | `constructed/expression-dna.md` |
| 5 | 反模式 | `candidates/anti-patterns.md` | `constructed/anti-patterns.md` |
| 6 | 书名简介 | `candidates/synopsis-patterns.md` | `constructed/synopsis-patterns.md` |
| 7 | 章纲模板+钩子分析 | `candidates/chapter-template.md` | `constructed/chapter-template.md` |
| 8 | 去AI策略 | `candidates/de-ai-strategy.md` | `constructed/de-ai-strategy.md` |
| 9 | 爽点分布 | `candidates/satisfaction-points.md` | `constructed/satisfaction-points.md` |
| 10 | 评分模型 | `candidates/scoring-model.md` | `constructed/scoring-model.md` |

### 并行构造（review 模式）

**并行** spawn 14 个 Task sub-agents（上述 10 个 + 下述 4 个）：

| subagent | 维度 | 读取文件 | 产出文件 |
|----------|------|---------|---------|
| 1-10 | 同 write 模式 | 同 write 模式 | 同 write 模式 |
| 11 | 审稿红线 | `candidates/review-redlines.md` | `constructed/review-redlines.md` |
| 12 | 修改处方 | `candidates/edit-prescriptions.md` | `constructed/edit-prescriptions.md` |
| 13 | 质量阈值 | `candidates/quality-thresholds.md` | `constructed/quality-thresholds.md` |
| 14 | 审稿人格 | `candidates/review-persona.md` | `constructed/review-persona.md` |

**Subagent prompt 模板**：

```
你的任务：将{维度}的规则按 RIA++ 结构化。

读取数据：
- 读取 {输出目录}/references/candidates/{文件名}.md

RIA++ 结构要求：
- R（原文引用）：≤150字，附书名+章节号
- I（决策解读）：用自己的话说明作者做了什么选择
- A1（书中案例）：至少1个案例
- A2（触发场景）：「如果{条件}，则{行动}」格式
- E（可执行步骤）：1-3步
- B（边界与盲点）：至少1条

输出要求：
- 写入 {输出目录}/references/constructed/{文件名}.md
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

1. 编写 Python 脚本，从 `sources/*.txt` 和 `writing-samples-*.md` 提取正文
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

## 输出结构

### write 模式输出

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                    # 写作决策框架（RIA++结构）
├── meta.json                   # 量化数据
├── references/
│   ├── book-overviews/         # 每本书的结构分析
│   ├── mental-models.md        # 心智模型（附原文引用）
│   ├── decision-heuristics.md  # 决策启发式（附原文引用）
│   ├── rhythm-intuition.md     # 节奏直觉（附原文引用）
│   ├── expression-dna.md       # 表达DNA（附原文引用）
│   ├── anti-patterns.md        # 反模式（附原文引用）
│   ├── synopsis-patterns.md    # 书名与简介风格（附原文示例）
│   ├── chapter-template.md     # 章纲模板（附原文引用）
│   ├── writing-samples.md      # 语感样本（附出处标注）
│   ├── de-ai-strategy.md       # 去AI策略（预选模块+阈值）
│   ├── candidates/             # 提取器原始产出 + 通过验证的规则
│   └── rejected/               # 淘汰的规则+原因（审计用）
└── sources/                    # 原文备份
    └── {book_name}.txt
```

### review 模式输出

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                    # 写作决策框架（write 模式产出，或已有）
├── meta.json                   # 写作量化数据
├── review/
│   ├── SKILL.md                # 审稿编辑框架（增量附件，~80行）
│   ├── meta.json               # 审稿量化数据
│   └── verify_stats.py         # 质量检测脚本
├── references/
│   ├── （write 模式的共用文件）
│   ├── review-redlines.md      # 审稿红线详情（review 专用）
│   ├── edit-prescriptions.md   # 修改处方详情（review 专用）
│   ├── quality-thresholds.md   # 质量阈值详情（review 专用）
│   ├── review-persona.md       # 审稿人格（review 专用，像真人编辑）
│   └── revision-capability.md  # 修改能力（review 专用，审改一体）
└── sources/
```

**关键**：review/SKILL.md 是**增量附件**（~80行），只含摘要表+检查清单，详细内容放 references/。写作规则引用 `../SKILL.md`，不重复。

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
| 5 | **subagent 合并执行** | 8个提取器并行是为了独立视角，合并会相互污染 | 每个 subagent 独立读文件、独立提取、独立写文件 |
| 6 | **Phase 3 验证流于形式** | 跨书验证/频率验证/独特性验证缺一不可 | 三条验证都必须执行，不通过的写入 rejected/ |
| 7 | **去AI策略预选过多模块** | 预选超过5个模块会过度约束写作 | Phase 2 预选3-5个 |
| 8 | **用 AI 腔描述规则** | "根据情况灵活把握""建议适当调整"是废话 | 规则必须有明确的 A2（触发场景）和 E（执行步骤） |
| 9 | **人工估算统计数据** | "对话占比约60%""副词密度约0.3次/百字"是瞎估，误差可达40%+ | 涉及统计的数据必须用 Python 脚本验证，脚本保存到输出目录 |
| 10 | **（review）红线没有判定标准** | "写得不好就改"是废话，审稿时无法执行 | 红线必须有具体判定条件（如「连续≥3章无冲突」） |
| 11 | **（review）处方没有改前改后示例** | "加强描写"是废话，作者不知道怎么改 | 处方必须有改前示例（问题写法）和改后示例（作者风格的替代方案） |
| 12 | **（review）阈值人工估算** | "对话占比约60%"误差可达40%+，告警阈值形同虚设 | 所有数值必须用脚本统计，脚本保存到输出目录 |
