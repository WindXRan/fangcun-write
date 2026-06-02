---
name: story-distill
description: |
  网文作者蒸馏 · 从同一作者的多本小说中提取写作决策框架或审稿编辑框架。
  核心理念：提取「为什么这样写」，不是「写了什么」。
  两种模式：
    --mode=write（默认）：提取写作决策框架 → 仿写时注入风格
    --mode=review：提取审稿编辑框架 → 审稿时作为审查清单
  输入：作者名 + 原文 txt 路径（至少1本，推荐3-6本）
  输出：.claude/skills/story-style/{作者名}/SKILL.md + meta.json
trigger:
  - /story-distill、/蒸馏、/炼丹、蒸馏作者、提取文风、distill
---

# story-distill：网文作者蒸馏

**核心理念：大佬写的不是「文字」，是「决策」。提取决策框架，不是表面特征。**

**两种模式**：
- `--mode=write`（默认）：写作决策框架——心智模型、决策启发式、表达DNA
- `--mode=review`：审稿编辑框架——审稿红线、修改处方、质量阈值（增量附件）

**方法论**：cangjie-skill RIA-TV++ + nuwa-skill 六维研究 + oh-story-claudecode 拆文

---

## 流程总览

```
Phase 0      输入验证 → 确认格式+数量
Phase 0.5    断点续跑检查 → 跳过已完成的 phase
Phase 1      精读预处理（主线程）→ 并行精读（N agent，9维度）
Phase 2      并行提取 → write 10 / review 14 个提取器
Phase 3      统一验证（1 agent）→ 跨书/频率/独特性/可执行性
Phase 4      并行构造（10/14 agent）→ RIA++ 结构化
Phase 5      合成输出 → SKILL.md + meta.json + 脚本验证
Phase 6      Consolidation → 清理中间产物
```

**预计耗时**：write 8-12 分钟 / review 12-16 分钟（3本小说）

**模式差异**：Phase 0/1/3/5/6 完全复用，Phase 2 提取器数量不同（10 vs 14），Phase 4 构造器数量不同。

---

## Phase 0：输入验证

| 项目 | 要求 |
|------|------|
| 作者名 | 中文或英文，作为输出目录名 |
| 原文路径 | 一个或多个 txt 文件路径 |
| 编码 | UTF-8（非 UTF-8 自动尝试 GBK 转换） |
| 章节格式 | 每章以 `第X章` 开头 |
| 最低数量 | 至少 1 本（推荐 3+） |

**执行**：检查文件存在→编码→格式→创建输出目录结构：

```
.claude/skills/story-style/{作者名}/
├── references/          # 最终交付物
├── review/              # review 模式交付物
└── .distill/            # 工作目录，Phase 6 删除
    ├── book-overviews/  # Phase 1
    ├── excerpts/        # Phase 1
    ├── candidates/      # Phase 2
    ├── constructed/     # Phase 4
    └── rejected/        # Phase 3
```

---

## Phase 0.5：断点续跑

| Phase | 检查文件 | 跳过条件 |
|-------|---------|---------|
| 1 | `book-overviews/*.md` + `excerpts/*.txt` | 全部存在 |
| 2 | `candidates/*.md` | 全部存在 |
| 3 | `rejected/quick-filter.md` | 存在 |
| 4 | `constructed/*.md` | 全部存在 |

用户说「继续蒸馏」时自动检测，无需额外参数。

---

## Phase 1：整书理解

### 1.0 精读片段预处理（主线程）

1. 读取全书目录，确定章节目录
2. 选定精读章节：基础层（1-3章+最后3章）+ 扩展层（1/4、1/2、3/4处各±1章）+ 专家层（情绪高点+转折点）
3. 提取章节文本，写入 `.distill/excerpts/{书名}-excerpts.txt`（约3-5万字）
4. 写入 `.distill/book-structure/{书名}.md`（章名列表+精读标记）

**Token 节省**：subagent 读精读片段 5万字/本 ≈ 7.5万 token/本，比全书 30万字节省 83%。

### 1.1 并行精读

**并行** spawn N 个 agent（每本书一个）。每个 agent 执行：

**1. 目录分析**：章名风格、章节密度、情绪曲线推断

**2. 深度精读（9维度）**：

| 维度 | 问题 | 要求 |
|------|------|------|
| 结构 | 这段在全书中的位置？作用？ | 说明和前后文关系 |
| 解释 | 作者做了什么选择？为什么？ | 有原文引用 |
| 批判 | 换一种选择会怎样？ | 说明原作为什么更好 |
| 应用 | 这个规则可以用在什么场景？ | 「如果{条件}，则{行动}」 |
| 情绪密度 | 情绪强度 1-10？用了什么手法？ | 区分铺垫/爆发/留白 |
| 对话权力 | 谁占主导？有潜台词/试探？ | 标注权力关系变化 |
| 悬念设计 | 埋了什么伏笔？怎么回收？ | 追踪完整链条 |
| 情绪节奏曲线 | 全书情绪如何变化？ | 标记高低点和转折 |
| 作者价值观 | 作者的价值观/世界观？ | 从多本书提取稳定模式 |

**3. 语感样本（7类，每类200-300字）**：

| 类型 | 来源 | 用途 |
|------|------|------|
| 开篇语感 | 第1章第1-3段 | 校准开头节奏 |
| 日常语感 | 第N/2章中段（非高潮） | 校准日常基线 |
| 高潮语感 | 3/4处情绪最激烈段落 | 校准情绪密度 |
| 对话语感 | 1/4或1/2处关键对话 | 校准对话节奏 |
| 描写语感 | 环境/心理描写段落 | 校准描写风格 |
| 结尾语感 | 最后1章最后3段 | 校准结尾冲击 |
| 句式节奏语感 | 高点章节的重复/排比/短句 | 校准微观节奏 |

**4. 悬念链条**：找出所有悬念/伏笔，标记埋设→强化→回收→手法

**5. 句式节奏模式**：重复句式、排比、短句堆叠的频率和效果

**产出**：
- `.distill/book-overviews/{书名}.md`（结构分析）
- `.distill/writing-samples-{书名}.md`（7类语感样本）
- `.distill/suspense-chains-{书名}.md`（悬念链条+句式节奏）

### 1.2 选书策略

| 书数 | 策略 |
|------|------|
| 1本 | 精读全书 |
| 2-3本 | 精读评分最高的1本 + 其余各读关键章节 |
| 4-6本 | 精读评分最高的1本 + 其余各读前3+中段3+后3章 |

### 1.3 汇总

所有 agent 完成后，主线程合并各书的 book-overviews、writing-samples、suspense-chains。

---

## Phase 2：并行提取

**并行** spawn 提取器（write 10个 / review 14个）：

| # | 维度 | 读取 | 产出 | 要点 |
|---|------|------|------|------|
| 1 | 心智模型+人设架构 | book-overviews + excerpts | mental-models.md | 区分叙事技法/设定DNA，R-I-A2-E-B 格式，附反例 |
| 2 | 决策启发式 | 同上 | decision-heuristics.md | 开篇/章尾/信息揭示/节奏控制四类 |
| 3 | 节奏直觉+节奏曲线 | 同上 | rhythm-intuition.md | 读者预期/情绪曲线/信息差/承诺兑现 |
| 4 | 表达DNA | 同上 | expression-dna.md | 短句动作链/口语化独白/感官细节/微表情 |
| 5 | 反模式 | 同上 | anti-patterns.md | 词汇/句式/结构/情节/角色/对话反模式 |
| 6 | 书名简介 | 每本书书名+简介+标签 | synopsis-patterns.md | 书名公式+简介结构 |
| 7 | 章纲模板+钩子分析 | excerpts + book-structure | chapter-template.md | 章节命名/结构/事件密度/钩子类型 |
| 8 | 去AI策略 | excerpts + de-ai-modules | de-ai-strategy.md | 预选3-5个模块 |
| 9 | 爽点分布 | book-overviews + excerpts | satisfaction-points.md | 爽点类型/位置/手法 |
| 10 | 评分模型 | book-overviews + candidates + excerpts | scoring-model.md | 质量维度/权重/阈值 |
| **11** | 审稿红线 | book-overviews + excerpts + anti-patterns | review-redlines.md | 判定标准+严重等级 |
| **12** | 修改处方 | book-overviews + excerpts + candidates | edit-prescriptions.md | 改前改后示例 |
| **13** | 质量阈值 | excerpts + book-overviews + writing-samples | quality-thresholds.md | 作者基线+告警阈值 |
| **14** | 审稿人格 | book-overviews + excerpts + candidates | review-persona.md | 第一人称审稿风格 |

**#11-14 仅 review 模式。**

### 每条规则格式（RIA++）

```
### [规则名称]
**性质**：[叙事技法] 或 [设定DNA]
**R（原文引用）**：≤150字，附书名+章节号
**I（决策解读）**：用自己的话说明选择
**A2（触发场景）**：如果{条件}，则{行动}
**E（执行步骤）**：1-3步
**B（边界与盲点）**：至少1条
**反例**：至少1个「不应该这样做」的示例
```

### 硬性要求

- 每个 subagent 独立读文件、独立提取、独立写文件
- 产出写入 `.distill/candidates/`
- 每条规则附原文引用和出处
- 发现矛盾保留矛盾，标注「场景A用X，场景B用Y」

### 超时

| Phase | 任务 | 超时 | 调整 |
|-------|------|------|------|
| 1 | 单本书精读 | 120s | >50万字→180s；<10万字→60s |
| 2 | 单个提取器 | 90s | 多本书→120s |
| 3 | 统一验证 | 180s | 维度>14时每多1个+10s |
| 4 | 单个构造器 | 60s | 规则>20条→90s |
| 5 | 合成输出 | 120s | — |

超时处理：等待 30s 重试一次，仍超时继续推进，Phase 3 标注「信息不足」。

---

## Phase 3：统一验证

**并行** spawn 1 个验证 agent，执行 5 种验证：

| 顺序 | 验证类型 | 标准 | 处理 |
|------|---------|------|------|
| 1 | 快速过滤 | 无原文引用 / 在黑名单中 | 直接淘汰→`rejected/quick-filter.md` |
| 2 | 跨书验证 | 同一规则在 ≥2 本书出现 | 标记「可能偶然」 |
| 3 | 频率验证 | 出现频率 ≥5% | 低频→`rejected/low-frequency.md` |
| 4 | 独特性验证 | 满足任一锚点（频率>60%/与主流不同/有反例） | 不满足→`rejected/generic.md` |
| 5 | 可执行性验证 | 有清晰 A2+E | 缺失标记「待补充」 |

**独特性锚点**（满足任一即通过）：
- 频率锚点：该规则在本书中出现频率 >60%
- 对比锚点：与同类题材主流写法不同
- 反例锚点：能找到「不这样做」的对比案例

**对比基准**：扫描其他作者 SKILL.md 或用通用常识（每章有钩子/对话有潜台词/角色有动机/冲突要升级）。

**单本书例外**：跳过跨书验证，只做频率+独特性验证。

### 质量检查

验证完成后，主线程检查：
- 规则具体性：≥80% 有清晰 A2+E
- 边界清晰度：≥70% 有 B
- 覆盖完整度：write 10维度缺失 ≤2 / review 14维度缺失 ≤3
- 可执行性：待补充规则 ≤20%
- 不达标→回炉 Phase 2 补充提取

---

## Phase 4：RIA++ 构造

**并行** spawn 构造器（write 10个 / review 14个），每个读取对应 candidates 文件，按 RIA++ 结构化输出到 `constructed/`。

与 Phase 2 的区别：Phase 2 提取原始规则，Phase 4 结构化+补充 A1（书中案例）+补充 E（执行步骤）。

---

## Phase 5：合成输出

### 5.1 输出结构与 story-style 接口对齐

**输出 SKILL.md 必须使用以下标准 section 名**（与 story-style 接口契约一致）：

```
## 心智模型
## 决策启发式
## 节奏直觉
## 表达DNA              ← 接口契约标准名
## 六、反模式            ← 接口契约标准名
## 七、章纲模板          ← 接口契约标准名
## 八、书名与简介        ← 接口契约标准名
## 九、去AI策略          ← 接口契约标准名
## 十、反抄袭检查        ← 接口契约标准名（继承通用规则）
## 十一、质量检查        ← 接口契约标准名（继承通用规则）
## 写作检查清单          ← 可选
```

**区分叙事技法和设定DNA**：
- 叙事技法：去掉具体人名/地名后规则仍成立，所有仿写项目可用
- 设定DNA：绑定具体身份组合/世界观，仿写源书时需反调色盘确认

### 5.2 review 模式

review SKILL.md 是增量附件，只包含审稿专用内容，写作规则引用 `../SKILL.md`：

```
review SKILL.md 结构：
├── 审稿人设（第一人称）
├── 审稿流程（快速判定表）
├── 审稿红线（摘要表，详见 references/）
├── 修改处方（摘要表，详见 references/）
├── 质量阈值（阈值表+检测脚本）
├── 去AI检查清单
└── 多agent审改流程（章数≥30时自动启用）
    ├── Phase 0：自动分卷
    ├── Phase 1：并行审稿（每卷1 agent）
    ├── Phase 2：交叉复审（边界章节）
    └── Phase 3：汇总报告
```

**触发条件**：<30章单agent / 30-100章2-3卷 / >100章4-6卷

### 5.3 meta.json

| 模式 | 内容 |
|------|------|
| write | name、description、source_skill、chapter_word_count、decision_framework（各维度计数）、extraction_info |
| review | name、description、companion_of、review_framework（红线数+处方数+阈值数）、quality_baselines |

### 5.4 去AI策略归档

Phase 2 提取器 8 已完成预选，本步归档到 SKILL.md「去AI策略」section。distill 职责到此为止，执行顺序由 story-rewrite 负责。

### 5.5 脚本验证统计数据

**核心原则：涉及统计的数据必须用脚本验证，禁止人工估算。**

写入 SKILL.md 前，对所有量化数据执行脚本验证：

| 统计项 | 验证方法 | 阈值 |
|--------|---------|------|
| 对话占比 | 引号内字数/总字数 | 与声称值误差 ≤5% |
| 副词密度 | 「微微/轻轻/淡淡/缓缓」次数/总字数 | 精确到小数点后2位 |
| 连接词密度 | 「于是/然而/因此/所以/但是」次数/总字数 | 精确到小数点后2位 |
| 单句成段占比 | 单句段落数/总段落数 | 与声称值误差 ≤5% |
| 章名风格 | 陈述句/疑问句/其他比例 | 精确到百分比 |

**执行**：编写 Python 脚本→运行→将数值写入 SKILL.md→保留脚本到 `verify_stats.py`。

**违规处理**：误差 >10% 必须修正；无法运行脚本则标注「待验证」。

### 5.6 写入文件

- `.claude/skills/story-style/{作者名}/SKILL.md`
- `.claude/skills/story-style/{作者名}/meta.json`
- `{输出目录}/verify_stats.py`

---

## Phase 6：Consolidation

**原则**：中间产物写到 `.distill/`，Phase 6 末尾删除。最终交付物只含 SKILL.md + meta.json + references/ + review/。

### 6.1 五步清理

| Step | 动作 | 失败处理 |
|------|------|----------|
| 1 | 删除原文 `.distill/sources/` | 强制 |
| 2 | 合并 `constructed/*.md` → `references/*.md` | 检查重名覆盖 |
| 3 | 删除 `constructed/` + `candidates/` + `rejected/` | 强制 |
| 4 | 删除 `.distill/` 整个目录 | 强制 |
| 5 | 交付物自检 | 不通过→重跑 Phase 6 |

### 6.2 交付物自检

```
# 文件数：write ≤14，review ≤20
# SKILL.md ≤20KB，references/ 单文件 ≤15KB，总和 ≤60KB
# .distill/ 不存在
```

### 6.3 失败回滚

Phase 6 中途失败：保留 `.distill/`，SKILL.md 标记 `[DRAFT - Phase 6 INCOMPLETE]`，不允许 story-rewrite 调用。

---

## 输出结构（最终交付物）

### write 模式

```
.claude/skills/story-style/{作者名}/
├── SKILL.md              # 写作决策框架（15-20KB）
├── meta.json             # 量化数据
├── test-prompts.json     # 验证产物（可选）
└── references/           # 11个维度文件
    ├── writing-samples.md
    ├── mental-models.md
    ├── decision-heuristics.md
    ├── rhythm-intuition.md
    ├── expression-dna.md
    ├── anti-patterns.md
    ├── synopsis-patterns.md
    ├── chapter-template.md
    ├── de-ai-strategy.md
    ├── satisfaction-points.md
    └── scoring-model.md
```

### review 模式（在 write 基础上增加）

```
├── review/
│   ├── SKILL.md          # 审稿框架（~80行）
│   └── meta.json
└── references/           # 4个审稿专用
    ├── review-redlines.md
    ├── edit-prescriptions.md
    ├── quality-thresholds.md
    └── review-persona.md
```

---

## 蒸馏后验证

跑完 distill 后执行 `/story-distill-verify`：压力测试→验证完整性→闭环回馈。review 模式额外运行 `verify_stats.py` 验证阈值。

---

## 蒸馏反例黑名单

| # | 反模式 | 替代做法 |
|---|--------|---------|
| 1 | 提取表面特征而非决策 | 每条规则回答「作者做了什么选择」 |
| 2 | 把通用规则写入 SKILL | 用独特性验证锚点过滤 |
| 3 | 调和矛盾而非保留矛盾 | 保留矛盾，标注场景差异 |
| 4 | 跳过 Phase 1 直接提取 | 必须完成整书理解 |
| 5 | subagent 合并执行 | 每个独立读/提/写 |
| 6 | Phase 3 验证流于形式 | 三条验证都必须执行 |
| 7 | 去AI策略预选过多模块 | 预选 3-5 个 |
| 8 | 用 AI 腔描述规则 | 规则必须有 A2+E |
| 9 | 人工估算统计数据 | 必须用 Python 脚本验证 |
| 10 | （review）红线没有判定标准 | 必须有具体判定条件 |
| 11 | （review）处方没有改前改后示例 | 必须有示例 |
| 12 | （review）阈值人工估算 | 必须用脚本统计 |
