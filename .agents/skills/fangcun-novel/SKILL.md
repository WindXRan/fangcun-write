---
name: fangcun-novel
version: 2.0.0
description: |
  小说仿写引擎。从源文生成新书：开书设定 → 章纲 → 写章 → 对比审核。
  触发方式：「仿写这本书」「帮我仿写XX」「写第N章」「继续写」「开书」
metadata:
  author: fangcun-team
  pipeline: open → guides → write → compare → review
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(mkdir *) Bash(rm *)
---

# fangcun-novel：小说仿写引擎

你是网络小说仿写助手。你的任务是帮用户从源文生成新书，保持题材和爽点，但换掉人名、地名、具体情节。

**核心原则：任何优化针对 workflow，不针对产出内容。不修单章，只修 pipeline。每次抽卡自动出稿，0 人工。**

---

## 核心方法

我们仿写不是复制粘贴，而是**结构提取 + 血肉替换**：

1. **先拆结构，再填内容**。从源文提取事件表、故事骨架、改编策略，然后用新的角色和设定填充。
2. **防线在流程里**。冲突类型强制换、台词 0 重合、换皮检验——这些都在 pipeline 中自动执行。
3. **批量生产，不逐章打磨**。一次跑 100+ 章，靠 pipeline 保证质量，不靠人工逐章修改。
4. **主线定位明确**。concept.md 必须标注主线，每章必须有主线推进，不能跑偏。

---

## 流程总览

根据用户意图和项目状态选择场景：

| 场景 | 触发条件 | 执行流程 |
|------|----------|----------|
| **开书** | "仿写这本书" / 配置文件存在 | 完整 Phase 0→1→2→3→4 |
| **写章** | "写第N章" / "继续写" | Phase 3（从断点继续） |
| **审查** | "看看写得怎么样" / "审查一下" | Phase 4 |
| **导出** | "导出这本书" | Phase 5 |

**匹配优先级**：写章 → 审查 → 导出 → 开书

无法判断场景时，列出上述场景表让用户选择，不要开放式提问。

---

## Phase 0：环境准备 + 源书分析

### 前置检查

1. **检查 API Key**：
   ```bash
   # 检查环境变量
   echo $env:API_KEY
   # 如果为空，提示用户设置
   ```

2. **检查配置文件**：
   ```bash
   # 检查 configs/ 目录下是否有对应配置
   ls configs/
   ```

3. **检查源文**：
   ```bash
   # 检查 projects/{author}/{source_book}/ 是否存在
   ls projects/{author}/{source_book}/
   ```

### 源书分析（可选但推荐）

如果用户提到对标书或需要分析源文：

```bash
# 运行源书分析
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase source
```

**产物**：
- `projects/{author}/{source_book}/_cache/events.json` — 事件表
- `projects/{author}/{source_book}/_cache/story_skeleton.md` — 故事骨架
- `projects/{author}/{source_book}/_cache/adaptation_strategy.md` — 改编策略

**完成标志**：`_cache/` 目录下存在 `events.json` 和 `story_skeleton.md`

---

## Phase 1：开书（核心设定）

### 执行命令

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase open
```

### 产物规范

| 文件 | 粒度 | 说明 |
|------|------|------|
| `concept.md` | 全书 | 设定+角色名+角色行为模式+全局节奏图+弧线 |
| `characters.md` | 全书 | 角色设定（新名字+性格+关系） |
| `world.md` | 全书 | 世界观设定 |
| `plot.md` | 全书 | 剧情设定（主线+支线） |
| `book_info.md` | 全书 | 书籍信息（书名+简介+标签） |

### 角色命名反 AI

AI 默认起名三大通病：全员诗意双名（沈砚辞、林知意）、古风生僻字、统一格式。

**破解方法**：
- 混搭单名双名
- 配角用常见姓（王李张刘陈）
- 允许外号
- 同辈字合理（姐弟可同辈字）

### Plot 确认点

开书后、写章前，pipeline 会自动暂停让用户确认设定：

```
是否继续？(y=确认/n=取消/q=退出):
```

**确认后**：创建 `.plot_confirmed` 文件，后续自动跳过

**跳过确认**：`--skip-confirm` 参数

### 完成标志

- `concept.md` 存在且非空
- `characters.md` 存在且非空
- `.plot_confirmed` 存在（或 `--skip-confirm`）

---

## Phase 2：生成章纲（Guides）

### 执行命令

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase guides --start 1 --end {N}
```

### 产物规范

| 文件 | 粒度 | 说明 |
|------|------|------|
| `guides/plot_{N}.md` | 每章 | 节拍映射+冲突替换+高光标注 |
| `guides/style_{N}.md` | 每章 | 风格锚点（句长/标点/对话比例） |

### 章纲质量要求

每章章纲必须包含：
1. **节拍映射**：源文节拍 → 新书节拍
2. **冲突替换**：源文冲突类型 → 新书冲突类型（不可相同）
3. **高光标注**：至少一个甜/虐/笑/反差/细节场景
4. **字数目标**：2000-3000 字

### 完成标志

- `guides/plot_{N}.md` 存在且非空
- 文件大小 > 100 bytes

---

## Phase 3：写章（核心阶段）

### 执行命令

```bash
# 写单章
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase write --start {N} --end {N}

# 批量写章
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase write --start 1 --end {N} --workers 30

# 从断点继续
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase write
```

### 双执行模式

engine 支持两种执行模式，由 `config.json` 中的 `execution_mode` 控制：

| 模式 | 执行者 | API 调用 | 适用场景 |
|------|--------|----------|----------|
| `api`（默认） | Python 脚本直接调 DeepSeek API | 由脚本发起 | 批量生产、快速出稿 |
| `agent` | opencode agent 派生子 agent 执行 | **不调 API**，agent 本身是 LLM | 高质量单章、需要迭代优化的场景 |

**核心区别**：agent 模式不经过 Python 调 API。opencode agent 作为编排器，派生子 agent 并行写章。

### Agent 模式写章流程

```bash
# 1. 生成任务清单
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase write --execution-mode agent

# 2. opencode agent 消费任务（自动）
#    - 每章派生子 agent（Task tool），并行执行
#    - 子 agent 读 concept → 读 plot_guide → 读源文 → 写章 → 校验字数

# 3. 全部完成后，执行 postfix 做机械修正
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase postfix
```

### 写章 Prompt 设计原则

- **极简 write-chapter**：只写步骤，不写规则。风格直接从源文学
- **plot_guide 显式映射**：源文列 vs 新书列，冲突类型不同，动作反应全换
- **高光时刻**：每章至少一个甜/虐/笑/反差/细节场景
- **角色行为模式前置**：open-book 阶段提取行为模式卡片（应激/决策/情感/弱点），注入 plot_guide 和 write-chapter，防角色漂移

### 字数控制

- **目标字数**：2000-3000 字/章
- **max_tokens** = 目标字数 × 1.6
- **prompt 中用 ±10% 区间**

### 产物规范

| 文件 | 粒度 | 说明 |
|------|------|------|
| `chapters/ch_{N}.txt` | 每章 | 正文（章名自生成） |

### 完成标志

- `chapters/ch_{N}.txt` 存在且非空
- 文件大小 > 500 bytes
- 字数在 1800-3500 范围内

---

## Phase 4：审查 + 修复（统一审改系统）

### 执行命令

```bash
# 审查（dry-run，只输出报告不修复）
python .agents/skills/fangcun-novel/tools/unified_fixer.py --config {config} --dry-run

# 审查 + 修复
python .agents/skills/fangcun-novel/tools/unified_fixer.py --config {config}

# 指定范围
python .agents/skills/fangcun-novel/tools/unified_fixer.py --config {config} --start 1 --end 50
```

### 审改架构（混合架构）

```
Layer 1a: 批次审查 (7维全检)
  审查 Agent 1 (批1-10章) ──┐
  审查 Agent 2 (批11-20章) ──┤
  ...                        │
  审查 Agent N              ─┘
                              │
Layer 1b: 全局维度审查 (3个agent并行)          ├──→ 总结 Agent → 派任务 Agent → 修复 Agent ──┐
  全局-Agent A (人设一致性: 对照行为卡片逐章检查) ──┤                                          ...    ├──→ 收集结果
  全局-Agent B (感情逻辑: 阶段渐进+情绪真实性)    ──┤                                          修复 Agent N ──┘
  全局-Agent C (节奏/伏笔)                       ──┘
```

### 检查项

| 检查项 | 类型 | auto_fixable | 说明 |
|--------|------|--------------|------|
| 字数偏差 (±15%) | word_count | No | 与源文对比 |
| 比喻过多 (源文+3) | metaphor | No | 防止过度修辞 |
| AI路标词 (源文+1) | ai_marker | Yes | 首先/其次/然后等 |
| 直抒情过多 (源文+2) | direct_emotion | No | 防止过度煽情 |
| 台词雷同 (8字匹配) | plagiarism | No | 换皮检验 |
| AI痕迹词 (句首) | ai_trace | Yes | 综上所述/换句话说等 |
| LLM审稿 (钩子/情绪/人设) | hook/emotion/character | No | 深度审查 |

### 严重度分级

| 级别 | 说明 | 处理方式 |
|------|------|----------|
| **P0** | 严重问题（台词雷同、人设崩塌） | 必须修复 |
| **P1** | 中等问题（字数偏差、钩子不足） | 建议修复 |
| **P2** | 轻微问题（比喻过多、AI痕迹） | 可选修复 |

### 完成标志

- `compare/unified_review_fix.json` 存在
- 报告中 P0 问题数为 0

---

## Phase 5：导出 + 交付

### 执行命令

```bash
# 导出 TXT
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase export

# 生成交付物
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase deliver
```

### 产物规范

| 文件 | 说明 |
|------|------|
| `export/{book_name}.txt` | 合并后的完整小说 |
| `compare/report.md` | 对比报告 |
| `state.json` | 最终状态 |

---

## 降级机制

### API 模式降级

当 API 调用失败时：

1. **429 限流**：指数退避重试（10/20/40 秒）
2. **5xx 服务端错误**：指数退避重试（5/10/20 秒）
3. **402 余额不足**：立即停止，不重试
4. **超时**：重试，超时时间翻倍

### Agent 模式降级

当 Agent 模式失败时：

1. **Agent 不可用**：自动降级到 api 模式
2. **子 agent 失败**：重试一次，仍失败则跳过该章
3. **任务清单生成失败**：降级到 api 模式

### 章节级降级

当单章写入失败时：

1. **第一次失败**：重试一次
2. **第二次失败**：标记为 failed，继续下一章
3. **连续失败 3 次**：跳过该章，记录到 state.json

---

## 质量门控

### 写章后检查（自动执行）

1. **字数检查**：1800-3500 字
2. **损坏检查**：无 AI 拒绝词（"抱歉"、"无法生成"等）
3. **角色名检查**：无源文角色名残留
4. **连贯性检查**：与上一章结尾衔接

### 审查后检查（自动执行）

1. **P0 问题**：必须为 0
2. **字数偏差**：±15% 以内
3. **台词雷同**：0 处

### 手动检查（建议执行）

1. **抽样阅读**：随机读 3-5 章，检查质量
2. **对比源文**：抽查 2-3 章，确认换皮彻底
3. **检查人设**：确认角色行为一致

---

## 断点续传

### 状态文件

`state.json` 记录：
- 各阶段完成状态
- 各章节写入状态
- 运行历史

### 恢复机制

```bash
# 从断点继续
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase resume

# 查看状态
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --status
```

### 状态值

| 状态 | 说明 |
|------|------|
| `pending` | 未开始 |
| `writing` | 写入中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `approved` | 人工审核通过 |

---

## 常见场景处理

### 场景 1：用户说"仿写这本书"

```
1. 问用户要配置文件路径（或帮用户创建）
2. 检查源文是否存在
3. 运行 --phase full（全流程）
4. 展示前 3 章结果
```

### 场景 2：用户说"写第5章"

```
1. 检查 guides/plot_5.md 是否存在
2. 如果不存在，先跑 --phase guides --start 5 --end 5
3. 运行 --phase write --start 5 --end 5
4. 展示结果
```

### 场景 3：用户说"继续写"

```
1. 读 state.json，找到断点
2. 运行 --phase resume
3. 定期汇报进度
```

### 场景 4：用户说"看看写得怎么样"

```
1. 运行 --phase unified_review_fix --dry-run
2. 展示审查报告
3. 问用户是否修复
```

### 场景 5：用户说"改一下第3章"

```
1. 删除 chapters/ch_003.txt
2. 运行 --phase write --start 3 --end 3
3. 展示新结果
```

### 场景 6：用户说"角色名不对"

```
1. 问用户正确的角色名
2. 修改 characters.md
3. 运行 --phase rename（重命名所有章节中的角色名）
4. 重跑受影响的章节
```

---

## 配置文件格式

```json
{
  "book_name": "auto",
  "author": "作者名",
  "source_book": "源书名",
  "rewrites_dir": "projects/作者/源书名/rewrites/auto",
  "base_dir": ".",
  "api_key": null,
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "reasoning_effort": "low",
  "execution_mode": "api",
  "workers": 30,
  "skip_confirm": false,
  "prompt_overrides": {
    "write-chapter.md": {"model": "deepseek-chat"},
    "plot-guide.md": {"model": "deepseek-chat"}
  },
  "batch_size": {
    "guides": 10,
    "write": 30
  }
}
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `book_name` | 否 | 新书名，"auto" = 让 LLM 自动起名 |
| `author` | 是 | 源文作者名 |
| `source_book` | 是 | 源文书名（目录名） |
| `rewrites_dir` | 是 | 仿写输出目录 |
| `base_dir` | 否 | 项目根目录（默认 "."） |
| `api_key` | 否 | API Key（默认从 $env:API_KEY 读取） |
| `api_base_url` | 否 | API 地址 |
| `model` | 否 | 模型名（默认 "deepseek-chat"） |
| `reasoning_effort` | 否 | 推理力度（默认 "low"） |
| `execution_mode` | 否 | 执行模式（默认 "api"） |
| `workers` | 否 | 并行数（默认 30） |
| `skip_confirm` | 否 | 跳过确认（默认 false） |
| `prompt_overrides` | 否 | 覆盖特定 prompt 的模型参数 |
| `batch_size` | 否 | 批大小配置 |

---

## 快捷命令

```powershell
# 首次使用：安装依赖
.\setup.ps1

# 设置 API Key
$env:API_KEY = "sk-xxx"

# 查看状态
.\novel.ps1 status

# 开书
.\novel.ps1 open

# 写章
.\novel.ps1 write --start 1 --end 10

# 审查
.\novel.ps1 review --start 1 --end 10

# 导出
.\novel.ps1 export
```

---

## 项目结构

```
projects/{作者}/{源书名}/
├── _cache/                    ← 源书级产物（自动管理）
│   ├── chapters/              ← 源文拆章
│   ├── events.json            ← 事件表
│   ├── story_skeleton.md      ← 故事骨架
│   └── adaptation_strategy.md ← 改编策略
├── rewrites/{新书名}/         ← 仿写产物（用户关心的）
│   ├── concept.md             ← 设定+弧线+角色名+行为模式+全局节奏图
│   ├── characters.md          ← 角色设定
│   ├── world.md               ← 世界观设定
│   ├── plot.md                ← 剧情设定
│   ├── book_info.md           ← 书籍信息
│   ├── characters/            ← 角色卡（每个角色独立文件）
│   ├── guides/                ← 章纲（plot_{N}.md + style_{N}.md）
│   ├── chapters/              ← 正文（ch_{N}.txt）
│   ├── compare/               ← 对比报告
│   ├── export/                ← 导出文件
│   ├── _log/                  ← 日志
│   └── state.json             ← 进度状态
└── configs/{config}.json      ← 配置文件
```

---

## 已知限制

### Flash 模型天花板

- 单章字数 ±20% 波动（60-70% 章达标）
- ~10% 随机失效（角色漂移、偶抄源文、过短）→ 重跑即可
- 句长偏短、对话偏多是模型特征，非 AI 痕迹
- 角色行为模式卡片能有效减少角色漂移（从~15%降到~5%），但不能完全消除

### 适用场景

- **适合**：批量生产、快速出稿、题材模仿
- **不适合**：高质量单章、需要深度打磨的作品

---

## 流程衔接

| 时机 | 跳转到 | 命令 |
|------|--------|------|
| 想分析源文 | fangcun-analyze | `/fangcun-analyze` |
| 想续写第二部 | open-book | 选择续写模式 |
| 想改编短剧 | fangcun-drama | `/fangcun-drama` |
| 想生成封面 | story-cover | `/story-cover` |
| 想导出小说 | story-export | `/story-export` |

---

## 参考资料索引

按场景加载，不一次全部加载。

### Phase 0：源书分析

| 场景 | 加载文件 |
|------|----------|
| 事件表提取 | `prompts/open-book.md` |
| 故事骨架生成 | `prompts/open-book-concept.md` |
| 改编策略制定 | `prompts/open-book-plot.md` |

### Phase 1：开书

| 场景 | 加载文件 |
|------|----------|
| 角色设定 | `prompts/open-book-characters.md` |
| 世界观设定 | `prompts/open-book-world.md` |
| 剧情设定 | `prompts/open-book-plot.md` |
| 概要生成 | `prompts/open-book-bookinfo.md` |

### Phase 2：章纲

| 场景 | 加载文件 |
|------|----------|
| 节拍映射 | `prompts/plot-guide.md` |
| 冲突替换 | `prompts/plot-guide.md` |
| 高光标注 | `prompts/plot-guide.md` |

### Phase 3：写章

| 场景 | 加载文件 |
|------|----------|
| 正文写作 | `prompts/write-chapter.md` |
| 风格模仿 | `prompts/style-analyze.md` |
| 精简 | `prompts/trim-chapter.md` |
| 润色 | `prompts/polish-chapter.md` |
| 扩写 | `prompts/expand-chapter.md` |
| 重写 | `prompts/rewrite-chapter.md` |

### Phase 4：审查

| 场景 | 加载文件 |
|------|----------|
| 统一审查 | `prompts/unified-review.md` |
| 统一修复 | `prompts/unified-fix.md` |
| 平台 rubric | `prompts/review-rubric-tomato.md` |

---

## 语言

- 跟随用户的语言回复，用户用什么语言就用什么语言回复
- 中文回复遵循《中文文案排版指北》
