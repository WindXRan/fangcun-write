# 方寸 | 网文仿写引擎深度解析——构建 AI 小说量产流水线

### 一、AI 写作工具的单点困局

2026 年，AI 写作工具已成红海。但绝大多数工具只解决**单章生成**，而非**全书量产**。

核心矛盾：**能写一章，写不了一本**。

- ChatGPT/Claude：对话式单章生成，无全流程覆盖
- Sudowrite：单章润色/续写，无批量能力
- NovelAI：单章补全，无质量控制

方寸的定位：**不是"帮你写一章"，而是"帮你开渔场"**。

源文输入 → 全书换皮 → 自动审改 → 批量出稿，0 人工。

### 二、架构总览：六阶段流水线设计

方寸的 pipeline 按「生产阶段」划分为六层：

```
┌─────────────────────────────────────────────────────────┐
│  Phase 6：统一审改层                                      │
│  批次审查(7维全检) + 全局维度审查(人设/节奏/伏笔)          │
│  → 总结 → P0/P1/P2 → N个修复Agent并行修复                │
├─────────────────────────────────────────────────────────┤
│  Phase 4：对比层                                         │
│  本地算法对比（0 token），自动存档                         │
├─────────────────────────────────────────────────────────┤
│  Phase 3.5：精简层                                       │
│  超字数20%的章自动裁剪                                    │
├─────────────────────────────────────────────────────────┤
│  Phase 3：写章层                                         │
│  并行写章，超30%偏差自动重试                               │
├─────────────────────────────────────────────────────────┤
│  Phase 2：章纲层                                         │
│  节拍映射 + 冲突替换 + 高光标注                            │
├─────────────────────────────────────────────────────────┤
│  Phase 1-1.5：开书层                                     │
│  概念设定 + 文笔指纹（双层：算法锚点 + LLM分析）            │
└─────────────────────────────────────────────────────────┘
```

以上 6 个阶段通过 **Python 脚本 + opencode agent** 双模式驱动，以「源文输入 → 概念生成 → 章纲映射 → 并行写章 → 自动审改」为标准产线，覆盖仿写全场景。

### 三、Phase 1-1.5：开书层——从源文到生产蓝图

#### 3.1 概念生成（open-book）

输入源文，输出 `concept.md`——包含设定、角色名、角色行为模式、全局节奏图、弧线。

技术链路：

```
源文全文
    ↓
深度分析（pro模型，reasoning=high）
    ↓
提取：设定/角色/行为模式/节奏图/弧线
    ↓
输出 concept.md
```

**关键设计：** 行为模式卡片（应激/决策/情感/弱点）注入后续所有 prompt，从源头防止角色漂移。

#### 3.2 文笔指纹（双层）

写章时每个源文章节生成双层指纹，注入 prompt：

| 层级 | 内容 | 成本 |
|------|------|------|
| Layer 1 — 算法锚点 | 句长/对话比/段长/代词密度/词汇丰富度/标点风格/开头结尾类型 | 0 token，纯正则 <30ms |
| Layer 2 — LLM 分析 | 提取 2-3 个可复制写法特征 + 原文例句，2 个易被 AI 写走样的点 | 1 次 flash 调用 |

**效率对比：** 传统人工分析一章文风约需 30 分钟；双层指纹自动生成 <1 秒，且无主观偏差。

### 四、Phase 2-3：章纲与写章层——从蓝图到正文

#### 4.1 章纲生成（plot-guide）

每章生成独立章纲，核心设计：

```
源文章节                    新书章纲
┌─────────────┐            ┌─────────────┐
│ 节拍 1      │  ───映射──→ │ 节拍 1'     │
│ 节拍 2      │  ───映射──→ │ 节拍 2'     │
│ 冲突类型 A  │  ───替换──→ │ 冲突类型 B  │
│ 高光时刻    │  ───标注──→ │ 高光时刻'   │
└─────────────┘            └─────────────┘
```

**关键约束：**
- 冲突类型强制换（身份→利益/信息差/道德，不可相同）
- 台词 0 重合（6 字以上连续匹配视为违规）
- 换皮检验：剥掉人名地名，认不出源文→合格

#### 4.2 并行写章（write-chapter）

```bash
# N 章批量写入，--workers 控制并发数
python tools/rewrite_chapters.py --config configs/xxx.json \
  --start 1 --end N --workers 30
```

**模型策略：**

| 阶段 | 模型 | 原因 |
|------|------|------|
| 开书 | pro (reasoning=high) | 需要深度分析源文模式 |
| 章纲/写章/指纹/审改 | flash | 速度快，成本低 |

**字数控制：** `max_tokens = 目标字数 × 1.6`，prompt 中用 ±10% 区间约束。

**已知天花板：**
- 单章字数 ±20% 波动（60-70% 章达标）
- ~10% 随机失效（角色漂移、偶抄源文、过短）→ 重跑即可
- 句长偏短、对话偏多是模型特征，非 AI 痕迹

### 五、Phase 6：统一审改层——生产可持续性的关键

#### 5.1 混合架构设计

```
Layer 1a: 批次审查 (7维全检)
  审查 Agent 1 (批1-10章) ──┐
  审查 Agent 2 (批11-20章) ──┤
  ...                        │
  审查 Agent N              ─┘
                              │
Layer 1b: 全局维度审查 (3个agent并行)          ├──→ 总结 Agent → 派任务 Agent → 修复 Agent
  全局-Agent A (人设一致性) ──┤
  全局-Agent B (感情逻辑)    ──┤
  全局-Agent C (节奏/伏笔)   ──┘
```

#### 5.2 七维检查项

| 检查项 | 类型 | auto_fixable |
|--------|------|--------------|
| 字数偏差 (±15%) | word_count | No |
| 比喻过多 (源文+3) | metaphor | No |
| AI路标词 (源文+1) | ai_marker | Yes |
| 直抒情过多 (源文+2) | direct_emotion | No |
| 台词雷同 (8字匹配) | plagiarism | No |
| AI痕迹词 (句首) | ai_trace | Yes |
| LLM审稿 (钩子/情绪/人设) | hook/emotion/character | No |

**关键设计：** 算法检测 + LLM 审稿双保险，算法负责可量化的硬指标，LLM 负责语义层面的质量判断。

#### 5.3 执行模式

```bash
# 审查（默认 LLM 模式，算法+LLM 全面检查）
python .agents/skills/story-engine/tools/unified_fixer.py \
  --config configs/xxx.json --dry-run

# 审查+修复
python .agents/skills/story-engine/tools/unified_fixer.py \
  --config configs/xxx.json
```

### 六、双执行模式：API 模式 vs Agent 模式

engine 支持两种执行模式，由 `config.json` 中的 `execution_mode` 控制：

| 模式 | 执行者 | API 调用 | 适用场景 |
|------|--------|----------|----------|
| `api`（默认） | Python 脚本直接调 DeepSeek API | 由脚本发起 | 批量生产、快速出稿 |
| `agent` | opencode agent 派生子 agent 执行 | **不调 API**，agent 本身是 LLM | 高质量单章、需要迭代优化的场景 |

**核心区别：** agent 模式不经过 Python 调 API。opencode agent 作为编排器，派生子 agent 并行写章。子 agent 自主读文件、写文件、校验迭代，不产生额外 API 成本。

```json
{
  "execution_mode": {
    "default": "api",
    "write": "agent"
  }
}
```

### 七、文件结构：工程化的记忆系统

一部长篇动辄几十万字、几百章。设定冲突、伏笔断线、时间线对不上——写到最后全靠记忆硬撑，迟早翻车。

方寸用文件系统把设定、章纲、正文、对比拆开，每个维度独立维护。对话只负责创作，不负责记忆。

```
projects/{作者}/{书名}/
├── _cache/chapters/第N章.txt      # 源文拆章
└── rewrites/{新书名}/
    ├── concept.md                  # 开书产物（设定+角色+行为模式+节奏图+弧线）
    ├── guides/plot_{N}.md         # 章纲（节拍映射+冲突替换+高光）
    ├── chapters/ch_{N}.txt        # 正文
    ├── styles/style_{N}.json      # 文笔指纹（双层）
    ├── compare/                    # 对比报告（本地算法，0 token）
    └── _debug/                     # --debug 模式下 prompt 存档
```

### 八、快速开始

```bash
# 1. 配置 API key
$env:API_KEY="sk-xxx"

# 2. 完整跑一本书（--end 指定源文总章数，--workers 控制并发）
python .agents/skills/story-engine/tools/pipeline.py \
  --config configs/xxx.json \
  --start 1 --end 100 --workers 30

# 3. 分步执行
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase open-book
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase write --start 1 --end 10

# 4. 只看 prompt 不调 API（debug 模式）
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase write --debug

# 5. 统一审改
python .agents/skills/story-engine/tools/unified_fixer.py --config configs/xxx.json

# 6. Agent 模式写章
python tools/rewrite_chapters.py --config configs/xxx.json --phase write --execution-mode agent
```

### 九、config.json 配置

```json
{
  "book_name": "新书名",
  "author": "源文作者",
  "source_book": "源文书名",
  "rewrites_dir": "projects/作者/源书/rewrites/新书",
  "model": "deepseek-v4-flash",
  "api_key": null,
  "execution_mode": "api"
}
```

`api_key` 为 null 时从 `$env:API_KEY` 读取。不要将 key 写入配置文件。

### 十、总结

方寸仿写引擎的核心价值在于：**不是单章生成工具，而是面向网文量产的系统性 AI 覆盖**。从源文输入到全书输出，从自动审改到批量生产，每一层都有对应的机制支撑，流程由 pipeline 统一驱动，质量由算法锚点 + LLM 指纹 + 多 Agent 审改兜底。

这种「源文输入 → 概念生成 → 章纲映射 → 并行写章 → 自动审改」的标准化生产矩阵，是当前 AI 写作领域最接近工业流水线逻辑的实现方案——**每章自动出稿，0 人工**。

## License

MIT
