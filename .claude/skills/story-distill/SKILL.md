---
name: story-distill
description: |
  网文作者蒸馏 · 从同一作者的多本小说中提取写作决策框架。
  方法论：借鉴 cangjie-skill 的 RIA-TV++ 流水线 + nuwa-skill 的六维研究。
  核心理念：提取「为什么这样写」，不是「写了什么」。
  触发方式：/story-distill、/蒸馏、/炼丹、「蒸馏作者」「提取文风」
  输入：作者名 + 原文 txt 路径（至少1本，推荐3-6本）
  输出：.claude/skills/story-style/{作者名}/SKILL.md + meta.json
---

# story-distill：网文作者蒸馏

**核心理念：大佬写的不是「文字」，是「决策」。我们要提取决策框架，不是表面特征。**

**方法论来源**：
- cangjie-skill: RIA-TV++ 流水线（整书理解→并行提取→三重验证→结构化输出）
- nuwa-skill: 六维研究 + 三重验证 + subagent prompt 模板
- oh-story-claudecode: 拆文流程
- webnovel-writer: 追读力系统

---

## 流程总览

```
Phase 0    输入验证 → 确认原文格式+数量
Phase 1    整书理解（Adler分析）→ 精读关键场景 + 语感样本 → ⚠️ 等待用户确认骨架
Phase 2    并行提取（8个 subagent）→ 从原文中提取决策框架（含去AI策略）
Phase 3    三重验证 → 跨书验证+频率验证+独特性验证 → ⚠️ 等待用户确认提炼
Phase 4    RIA++构造 → 结构化输出，附原文引用
Phase 5    合成输出 → 生成 SKILL.md + meta.json
Phase 5.5  去AI策略（桥梁）→ 归档 Phase 2 预选结果，供 rewrite 消费
Phase 6    压力测试 → test-prompts.json + 回炉
Phase 7    验证注册 → 手动检查 + 确认 story-rewrite 可读取
```

**预计耗时**：30-60 分钟（3本小说，精读关键场景）

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

| 情况 | 处理 |
|------|------|
| 文件不存在 | 停止，提示用户检查路径 |
| 编码非UTF-8 | 尝试 GBK 转 UTF-8，失败则提示用户 |
| 章节格式不匹配 | 统计前5章的开头格式，提示用户修正 |
| 只有1本书 | 正常继续，跳过跨书验证 |

---

## Phase 1：整书理解（Adler 分析）

**借鉴**：cangjie-skill 的 Adler 分析阅读法

**目的**：精读关键场景，理解故事结构、角色弧线、情绪曲线

### 1.1 目录分析（新增）

**核心思路**：先通读章节目录，从章名推断情绪曲线和节奏，再动态选择精读章节。

**执行步骤**：

1. **提取全书章节目录**
   ```bash
   grep -n "第.*章" {book_name}.txt | head -100
   ```

2. **章名分析**（四字章名信息量大）
   - 识别情绪关键词：喜、怒、哀、惊、变、危、杀、婚、离、死
   - 识别事件关键词：揭、露、真相、阴谋、反目、和解
   - 识别节奏关键词：初、始、终、归、别、逢

3. **推断情绪曲线**
   - 标记情绪高点章节（如：XX之死、大婚、真相揭露）
   - 标记转折点章节（如：变故突生、反目成仇）
   - 标记节奏变化（如：连续短章=紧张，连续长章=舒缓）

4. **动态选择精读章节**
   - 开篇：第1-3章（固定）
   - 情绪高点：从目录中识别的高情绪章节
   - 转折点：从目录中识别的转折章节
   - 高潮：从目录中识别的高潮章节
   - 结局：最后3章（固定）

5. **输出：精读计划表**
   ```
   《书名》精读计划：
   - 开篇：第1-3章
   - 情绪高点：第X章（章名：XXXX）、第Y章（章名：YYYY）
   - 转折点：第Z章（章名：ZZZZ）
   - 高潮：第W章（章名：WWWW）
   - 结局：最后3章
   ```

### 1.2 选书策略

| 书数 | 策略 |
|------|------|
| 1本 | 精读全书 |
| 2-3本 | 精读评分最高的1本 + 其余各读关键章节 |
| 4-6本 | 精读评分最高的1本 + 其余各读前3章+中段3章+后3章 |

### 1.3 精读内容（每本书）

**动态选择**（基于目录分析）：

| 位置 | 来源 | 读什么 | 目的 |
|------|------|--------|------|
| 开篇 | 第1-3章（固定） | 开篇方式、破冰方式、人设展示 | 提取开篇决策 |
| 情绪高点 | 目录识别 | 情绪最激烈的章节 | 提取情绪控制决策 |
| 转折点 | 目录识别 | 剧情转折的关键章节 | 提取决策规则 |
| 高潮 | 目录识别 | 冲突爆发的章节 | 提取高潮决策 |
| 结局 | 最后3章（固定） | 结局、伏笔回收、情绪终点 | 提取结局决策 |

**兜底方案**：如果章名信息量不足（如纯数字章节），回退到硬编码位置：
- 1/4处：第N/4章 ±1章
- 1/2处：第N/2章 ±1章
- 3/4处：第3N/4章 ±1章

### 1.4 分析维度（每个精读场景）

| 维度 | 问题 |
|------|------|
| **结构** | 这段在全书中的位置？起什么作用？ |
| **解释** | 作者在这里做了什么选择？为什么？ |
| **批判** | 如果换一种选择会怎样？哪种更好？ |
| **应用** | 这个决策规则可以用在什么场景？ |

### 1.5 语感样本选取标准

每本书提取 **4 类语感样本**，每类 1 段（200-300字）：

| 类型 | 选取标准 | 用途 |
|------|---------|------|
| **开篇语感** | 第1章第1-3段 | 校准开头节奏 |
| **高潮语感** | 情绪最激烈的段落（从目录识别的高潮章节中选取） | 校准情绪密度 |
| **对话语感** | 推进剧情的关键对话 | 校准对话节奏 |
| **描写语感** | 环境/心理描写段落 | 校准描写风格 |

**选取原则**：
- 选「最有代表性」的段落，不是「最华丽」的
- 段落必须完整（有开头有结尾）
- 每段附出处标注（书名+章节号）

### 1.6 产出文件

全部写入 `.claude/skills/story-style/{作者名}/references/`：

| 文件 | 内容 |
|------|------|
| `book-overviews/{书名}.md` | 每本书的结构分析（含目录分析+精读计划） |
| `writing-samples.md` | 4类语感样本，每段附出处 |

### ⚠️ Phase 1 → Phase 2 检查点

**暂停，展示给用户确认**：

```
整书理解摘要：
- 精读书目：{书名1}（{N}章）、{书名2}（{N}章）...
- 目录分析：识别情绪高点{N}个、转折点{N}个
- 精读计划：开篇3章 + 情绪高点{N}章 + 转折点{N}章 + 高潮{N}章 + 结局3章
- 提取语感样本：{N}段
- 初步观察：{1-2句核心发现}

骨架理解对吗？有没有需要重点突出的方向？
```

**等待用户确认后** → 进入 Phase 2。

### 错误处理

| 情况 | 处理 |
|------|------|
| 章名信息量不足（纯数字/无意义） | 回退到硬编码位置（1/4、1/2、3/4处） |
| 章节总数不确定 | 用 grep 统计 `第.*章` 的数量 |
| 找不到转折点 | 用「第1/4、1/2、3/4处」替代 |
| 语感样本选不出来 | 跳过该类型，在 writing-samples.md 中标注「未找到合适段落」 |

---

## Phase 2：并行提取（8个 subagent）

**借鉴**：cangjie-skill 的8个并行提取器 + nuwa-skill 的 prompt 模板

**目的**：从精读场景中提取决策框架

### Subagent 任务表

**并行** spawn 8 个 Task sub-agents（使用 Agent 工具，一次调用中发起 8 个）：

| subagent | 读取的 prompt | 读取的数据 | 产出文件 |
|----------|--------------|-----------|---------|
| 1 心智模型 | `extractors/mental-model-extractor.md` | `references/book-overviews/*.md` + `sources/*.txt` | `references/candidates/mental-models.md` |
| 2 决策启发式 | `extractors/decision-heuristic-extractor.md` | `references/book-overviews/*.md` + `sources/*.txt` | `references/candidates/decision-heuristics.md` |
| 3 节奏直觉 | `extractors/rhythm-intuition-extractor.md` | `references/book-overviews/*.md` + `sources/*.txt` | `references/candidates/rhythm-intuition.md` |
| 4 表达DNA | `extractors/expression-dna-extractor.md` | `references/book-overviews/*.md` + `sources/*.txt` | `references/candidates/expression-dna.md` |
| 5 反模式 | `extractors/anti-pattern-extractor.md` | `references/book-overviews/*.md` + `sources/*.txt` | `references/candidates/anti-patterns.md` |
| 6 书名简介 | `extractors/synopsis-extractor.md` | 每本书的书名+简介+标签 | `references/candidates/synopsis-patterns.md` |
| 7 章纲模板 | `extractors/chapter-parser.md` | `sources/*.txt` | `references/candidates/chapter-template.md` |
| 8 去AI策略 | `extractors/de-ai-extractor.md` | `sources/*.txt` + `de-ai-modules/*.md` | `references/candidates/de-ai-strategy.md` |

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

每个模型必须：
1. 有原文引用（R）：直接引用书中段落，≤150字
2. 有决策解读（I）：用自己的话说明作者做了什么选择
3. 有触发场景（A2）：什么条件下使用这个模型
4. 有边界说明（B）：这个模型的局限性

输出要求：
- 写入 {输出目录}/references/candidates/mental-models.md
- 每条模型附原文出处（书名+章节号）
- 发现矛盾直接记录，不要调和
- 区分「作者明确表达的」vs「从行为推断的」
```

其他7个 subagent 按同样结构调整读取数据、提取内容、输出文件名。

### 硬性要求

- 每个 subagent 独立读文件、独立提取、独立写文件
- 产出必须写入 `references/candidates/` 目录
- 每条规则附原文引用和出处标注
- 发现矛盾保留矛盾

### 错误处理

| 情况 | 处理 |
|------|------|
| 某个 subagent 超时/失败 | 不等待，继续推进。该维度在 Phase 3 标注「信息不足」 |
| 提取结果为空 | 写入 candidates 文件标注「未找到」，Phase 3 处理 |
| subagent 冲突 | 保留两个版本，Phase 3 由主 agent 裁决 |

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

### 3.1 执行验证

1. 读取 `references/candidates/` 下所有8个文件
2. 对每条规则执行三重验证：

| 验证 | 标准 | 不通过处理 |
|------|------|-----------|
| **跨书验证** | 同一决策规则在 ≥2 本书中出现 | 标记为「可能偶然」，降低权重 |
| **频率验证** | 出现频率 ≥5%（非偶发） | 标记为「低频特征」，写入 `rejected/` |
| **独特性验证** | 满足以下任一即通过（见下方锚点） | 标记为「通用规则」，写入 `rejected/` |

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

### 审计轨迹

- **通过的规则**：保留在 `references/candidates/` 对应文件
- **不通过的规则**：写入 `references/rejected/{提取器名}.md`，每条附淘汰原因
- 用户可事后捞回被淘汰的规则

### ⚠️ Phase 3 → Phase 4 检查点

**暂停，展示提炼摘要给用户确认**：

```
提炼结果摘要：
- 心智模型：{N}个（列出名称）
- 决策启发式：{N}条
- 节奏直觉：{N}条
- 表达DNA：{N}条
- 反模式：{N}条
- 书名与简介规则：{N}条
- 章纲模板：{N}条
- 语感样本：{N}段
- 淘汰规则：{N}条（见 rejected/）
- 矛盾点：{N}处

确认OK？还是需要调整某个维度？
```

**等待用户确认后** → 进入 Phase 4。

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

### 执行步骤

1. 读取 `references/candidates/` 下通过验证的规则
2. 按上述结构逐条构造
3. 输出到 `references/constructed/` 目录（Phase 5 组装用）

---

## Phase 5：合成输出

### 5.1 读取模板

读取 `templates/SKILL_template.md` 获取标准结构。

### 5.2 填充内容

将 Phase 4 的 RIA++ 结构化内容填入模板的对应 section。

### 5.3 生成 meta.json

```json
{
  "name": "{作者名}",
  "label": "{作者名}风格",
  "description": "从{N}本小说中提取的写作决策框架",
  "source_skill": ".claude/skills/story-style/{作者名}/SKILL.md",
  "compatible_genres": ["{题材1}", "{题材2}"],
  "chapter_word_count": {平均章均字数},
  "decision_framework": {
    "mental_models": ["{模型1}", "{模型2}"],
    "decision_heuristics_count": {规则数量},
    "anti_patterns_count": {反模式数量},
    "synopsis_rules_count": {简介规则数量},
    "chapter_template_count": {章纲规则数量}
  },
  "features": {
    "avg_chapter_words": {平均章均字数}
  },
  "extraction_info": {
    "source_books": ["{书名1}", "{书名2}"],
    "extraction_date": "{日期}",
    "novel_distill_version": "2.0.0"
  }
}
```

### 5.4 写入文件

- 写入 `.claude/skills/story-style/{作者名}/SKILL.md`
- 写入 `.claude/skills/story-style/{作者名}/meta.json`

---

## Phase 5.5：去AI策略（蒸馏→重写桥梁）

**目的**：预选去AI模块 + 写后扫描确认，两阶段确保覆盖实际 AI 特征。

**定位**：Phase 5.5 不是 distll 的独立执行步骤，而是连接 distill 和 rewrite 的桥梁：
- 5.5a（预选）→ 已在 Phase 2 由 extractor 8 完成，本节仅归档说明
- 5.5b（写后扫描）→ 由 story-rewrite 在 Phase 3 调用，本节提供参考

### 5.5a 基础策略（已在 Phase 2 完成）

extractor 8（`extractors/de-ai-extractor.md`）在 Phase 2 并行执行：
1. 分析作者写作习惯（连接词/句长/副词/标点等8个维度）
2. 对照 de-ai-modules 模块库选择 3-5 个匹配模块
3. 产出写入 `references/candidates/de-ai-strategy.md`
4. 后续由主线程在 Phase 5 合成时写入 SKILL.md 的「去AI策略」section

**不重复执行**，Phase 2 已覆盖。

### 5.5b 写后扫描（由 story-rewrite 调用）

**时机**：narrative-writer 写完每章正文后，由 story-rewrite Phase 3 调用

**扫描器 prompt**：`extractors/post-write-scanner.md`

**扫描指标**见 post-write-scanner.md，包含 8 个维度的阈值检测。

### 模块库

去AI模块存放在 `de-ai-modules/` 目录下，执行脚本（`.py`/`.ps1`）在 `story-rewrite/tools/`：

| 模块 | 作用 | 脚本位置 |
|------|------|---------|
| 删连接词 | 去掉逻辑连接词 | story-rewrite/tools/de-ai-connectors.py |
| 拆长句 | >25字句子拆短句 | — |
| 降级副词 | 程度副词降级/替换 | — |
| 轻微倒装 | 语序微调 | — |
| 加微重复 | 模拟人类重复 | — |
| 加模糊词 | 加入模糊表达 | — |
| 数字模糊化 | 精确数字模糊化 | story-rewrite/tools/de-ai-numbers.ps1 |
| 污染AI流畅性 | 加入卡顿感 | — |
| 真实人类口误 | 加入微小错误 | — |
| 风格迁移 | 按目标风格改写 | — |
| 降低ai预测概率 | 提高文本熵值 | — |
| 精简字句 | 删除冗余描写 | — |
| 去ai味提示词升级版 | 综合方案 | — |
| 标点后处理 | **必选，最后执行** | story-rewrite/tools/de-ai-punctuation.ps1 |
| 得的地 | **必选，标点后处理之后执行** | — |

### 与 story-rewrite 的集成

story-rewrite Phase 3 按此流程调用：
1. 读取 SKILL.md 的「去AI策略」section，获取预选模块列表
2. 每批正文写完后，对每章运行 post-write-scanner（8个指标）
3. 超标项对照预选模块 → 补充遗漏（上限2个）
4. 执行：预选模块 → 补充模块 → 标点后处理 → 得的地
5. 调用脚本见 `story-rewrite/tools/`

---

## Phase 6：压力测试

**借鉴**：cangjie-skill 的阶段4压力测试

**目的**：验证蒸馏出的决策框架可用，不是纸上谈兵

### 6.1 生成 test-prompts.json

为每个核心决策规则设计 2-3 条测试 prompt，覆盖三类：

| 类型 | 说明 | 示例 |
|------|------|------|
| **应调用** | 该规则明确适用的场景 | 「写一个古言开篇，需要快速建立代入感」 |
| **不应调用（诱饵）** | 看似适用但规则不覆盖的场景 | 「写一个现代都市开篇，需要交代背景」 |
| **边界模糊** | 规则可能适用但需要判断的场景 | 「写一个穿越开篇，需要同时建立代入感和交代背景」 |

### 6.2 本地跑一遍

用 test-prompts 带着 SKILL.md 让 agent 回答，检查：
- 应调用的 → agent 是否正确使用了规则？
- 不应调用的 → agent 是否避免了误用？
- 边界模糊的 → agent 是否给出了合理的边界判断？

### 6.3 回炉标准

| 问题 | 处理 |
|------|------|
| 应调用但没调用 | 规则的 A2（触发场景）不够明确 → 修改 |
| 不应调用但调用了 | 规则的 B（边界）不够清晰 → 修改 |
| 边界模糊判断错误 | 补充边界说明 → 修改 |

**不过的回炉 Phase 4 重做**，不做表面修补。

### 6.4 输出

写入 `.claude/skills/story-style/{作者名}/test-prompts.json`（darwin-skill 兼容格式）。

### ⚠️ Phase 6 → Phase 7 检查点

**展示测试结果给用户确认**：

```
压力测试结果：
- 总测试：{N}条
- 通过：{X}条
- 回炉修复：{Y}条
- 最终通过率：{Z}%

确认交付？
```

**等待用户确认后** → 进入 Phase 7。

---

## Phase 7：验证注册

### 7.1 手动验证

检查 SKILL.md 是否满足以下标准：
- 心智模型数量（≥3）
- 每个模型有局限性说明
- 表达DNA辨识度
- 诚实边界（≥3条）
- 内在张力（≥2对）
- 一手来源占比（>50%）

### 7.2 格式验证

检查 SKILL.md 是否包含必要 section：
- [ ] frontmatter（name、description、trigger）
- [ ] 心智模型（有原文引用）
- [ ] 决策启发式（有原文引用）
- [ ] 节奏直觉（有原文引用）
- [ ] 表达DNA（有原文引用）
- [ ] 反模式（有原文引用）
- [ ] 书名与简介（有原文示例）
- [ ] 章纲模板（有原文引用）
- [ ] 写作样本（有语感锚点）
- [ ] 写作检查清单

### 7.3 兼容性验证

确认 story-rewrite 能找到并读取：
- [ ] 路径为 `.claude/skills/story-style/{作者名}/SKILL.md`
- [ ] 文件存在
- [ ] 格式正确

---

## 输出结构

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                    # 决策框架（RIA++结构）
├── meta.json                   # 量化数据
├── test-prompts.json           # 压力测试（darwin兼容）
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

---

## 与下游的集成

### story-rewrite 如何使用决策框架

```
story-distill → .claude/skills/story-style/{作者名}/SKILL.md
                    │
                    ├─→ story-architect 读取「心智模型」+「决策启发式」+「章纲模板」
                    │       └─→ 设计章纲时：
                    │           - 按作者的「故事观」设计结构
                    │           - 按「决策启发式」设计钩子和爽点
                    │           - 按「章纲模板」控制章节节奏
                    │
                    ├─→ narrative-writer 读取「决策启发式」+「表达DNA」+「反模式」+「写作样本」
                    │       └─→ 写正文时：
                    │           - 按「决策启发式」做写作决策
                    │           - 按「表达DNA」控制信息密度
                    │           - 按「反模式」避免禁忌写法
                    │           - 按「写作样本」校准语感
                    │
                    ├─→ story-rewrite Phase 3 读取「去AI策略」
                    │       └─→ 写后扫描时：
                    │           - 读取预选模块列表
                    │           - 调用 post-write-scanner 扫描 AI 输出
                    │           - 补充遗漏模块（上限2个）
                    │           - 执行：预选→补充→标点后处理→得的地
                    │
                    └─→ story-synopsis 读取「书名与简介规则」
                            └─→ 生成简介时：
                                - 按「书名规则」命名
                                - 按「简介规则」写文案
                                - 按「标签规则」选标签
```

---

## 参考文件

| 文件 | 用途 |
|------|------|
| `methodology/extraction-framework.md` | 提取方法论详情 |
| `methodology/triple-verification.md` | 三重验证规则 |
| `methodology/ria-construction.md` | RIA++构造方法 |
| `methodology/output-templates.md` | 输出模板规范 |
| `extractors/mental-model-extractor.md` | 心智模型提取器 prompt |
| `extractors/decision-heuristic-extractor.md` | 决策启发式提取器 prompt |
| `extractors/rhythm-intuition-extractor.md` | 节奏直觉提取器 prompt |
| `extractors/expression-dna-extractor.md` | 表达DNA提取器 prompt |
| `extractors/anti-pattern-extractor.md` | 反模式提取器 prompt |
| `extractors/synopsis-extractor.md` | 书名与简介风格提取器 prompt |
| `extractors/chapter-parser.md` | 章纲模板提取器 prompt |
| `extractors/de-ai-extractor.md` | 去AI策略提取器 prompt（Phase 2 并行） |
| `extractors/post-write-scanner.md` | 写后扫描器 prompt（rewrite Phase 3 调用） |
| `story-rewrite/tools/validate-aigc.ps1` | 输出合理性验证（Phase 7 手动） |
| `templates/SKILL_template.md` | SKILL.md模板 |
| `templates/meta_template.json` | meta.json模板 |
