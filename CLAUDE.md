# AI网文小说项目 — 仿写引擎

## 核心原则

**任何优化针对 workflow，不针对产出内容。** 不修单章，只修 pipeline。每次抽卡自动出稿，0 人工。

防线在流程里：
- 冲突类型强制换（身份→利益/信息差/道德，不可相同）
- 台词 0 重合（6 字以上连续匹配视为违规）
- 换皮检验：剥掉人名地名，认不出源文→合格
- 题材不变，血肉全换
- **主线定位**（concept.md必须明确标注）：每章必须有主线推进，不能跑偏

## Skill/Prompt 修改原则

- **通用性**：prompt 和 skill 里不加针对化内容（如具体套路列表），保持通用
- **职责分离**：write 只管写，检查逻辑放 validate 或 compare 阶段
- **CLAUDE.md 定位**：放 agent 交互原则，不放内容规则
- **内容规则归属**：换皮检验、撞梗检查等放到 plot-guide.md 或 writing-techniques-*.md

## Pipeline

```
Phase 0:   品类检测 (detect-genre)    → 自动检测品类（LLM读源文，判genre→写回config）
Phase 0.5: 热梗调研 (story-trend)     → trends/{题材名}/ 知识库（可选）
Phase 1:   开书 (pro, 1 call)        → concept.md（设定+角色名+角色行为模式+全局节奏图+弧线）
Phase 2:   plot-guide (flash, N 并行) → plot_{N}.md（节拍映射+冲突替换+高光标注）
Phase 3:   写章 (flash, N 并行)      → ch_{N}.txt（章名自生成，输入: plot_guide + 源文全文 + concept）
Phase 3.5: Trim (flash)              → 超字数 20% 的章自动精简
Phase 4:   对比 (本地)                → compare/报告  
（已移除旧 review/fix 系统，仅保留 unified 审改路径）
Phase 6:   多Agent审改                → unified_review_fix.json  
            (Scatter: N审查agent → Gather: 总结agent → Plan: 派任务agent → Scatter: N修复agent → Gather: 收集结果)
```

### 统一审改系统（Phase 6）

多 Agent 架构：Scatter → Gather → Plan → Scatter → Gather

```
审查 Agent 1 (批1-10章) ──┐
审查 Agent 2 (批11-20章) ──┤
审查 Agent 3 (批21-30章) ──┤──→ 总结 Agent → 派任务 Agent → 修复 Agent 1 (任务集A) ──┐
...                        │                                         修复 Agent 2 (任务集B) ──┤──→ 收集结果
审查 Agent N              ┘                                         修复 Agent N (任务集C) ──┘
```

每个 Agent 有明确契约：输入→输出。总结 Agent 给每个 issue 标 P0/P1/P2。

| 检查项 | 类型 | auto_fixable |
|--------|------|--------------|
| 字数偏差 (±15%) | word_count | No |
| 比喻过多 (源文+3) | metaphor | No |
| AI路标词 (源文+1) | ai_marker | Yes |
| 直抒情过多 (源文+2) | direct_emotion | No |
| 台词雷同 (8字匹配) | plagiarism | No |
| AI痕迹词 (句首) | ai_trace | Yes |
| LLM审稿 (钩子/情绪/人设) | hook/emotion/character | No |

```bash
# 审查（默认 LLM 模式，算法+LLM 全面检查）
python .agents/skills/story-engine/tools/unified_fixer.py --config configs/xxx.json --dry-run

# 审查+修复
python .agents/skills/story-engine/tools/unified_fixer.py --config configs/xxx.json

# Debug 模式：输出发给 API 的完整 prompt 到 _debug/ 目录（各阶段 1 样本，写章前 3 章）
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase all --debug

# pipeline 集成
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase unified
```

## 文件结构

```
projects/{作者}/{书名}/
├── _cache/chapters/第N章.txt        # 拆章缓存
└── rewrites/{新书名}/
    ├── concept.md                    # 设定+弧线+角色名+行为模式+全局节奏图
    ├── guides/plot_{N}.md           # 章纲（节拍映射+冲突替换+高光）
    ├── chapters/ch_{N}.txt          # 正文（直接对标源文全文）
    └── compare/                      # 对比报告

trends/{题材名}/                      # 热梗知识库（story-trend 生成）
├── overview.md                       # 题材概述+读者画像
├── mechanics.md                      # 核心机制/爽点循环
├── characters.md                     # 角色模板
├── plot_patterns.md                  # 情节模式
├── references.md                     # 参考素材/真实案例
├── keywords.md                       # 关键词/标签
└── style_notes.md                    # 风格备注
```

## 双执行模式

engine 支持两种执行模式，由 `config.json` 中的 `execution_mode` 控制：

| 模式 | 执行者 | API 调用 | 适用场景 |
|------|--------|----------|----------|
| `api`（默认） | Python 脚本直接调 DeepSeek API | 由脚本发起 | 批量生产、快速出稿 |
| `agent` | opencode agent 派生子 agent 执行 | **不调 API**，agent 本身是 LLM | 高质量单章、需要迭代优化的场景 |

**核心区别：** agent 模式不经过 Python 调 API。opencode agent 作为编排器，派生子 agent 并行写章。子 agent 自主读文件、写文件、校验迭代，不产生额外 API 成本。

### agent 模式写章流程

```
1. pipeline.py --execution-mode agent --phase write
   → 生成 _agent_tasks/write_manifest.json（任务清单）
2. opencode agent 读取任务清单
3. 每章派生子 agent（Task tool），并行执行
   - 子 agent 位：读 concept → 读 plot_guide → 读源文 → 写章 → 校验字数
4. 全部完成后，执行 postfix 做机械修正
   python pipeline.py --config xxx.json --phase postfix
```

### config 配置

```json
{
  "execution_mode": "api"                    // 全局默认
  // 或按 phase 覆盖:
  "execution_mode": {
    "default": "api",
    "write": "agent"                         // 只有写章用 agent 模式
  }
}
```

## 模型策略

| 阶段 | 模型 | 原因 |
|------|------|------|
| 开书 | pro (reasoning=high) | 需要深度分析源文模式 |
| Guides | flash | 够用，速度快 |
| 写章 | flash | 字数听话，指令执行好，风格直接从源文学 |
| Trim | flash | 简单任务 |

**pro 写章更好看但字数失控（+50%），flash 听话但偶有随机失效（~10%）。**
**字数控制：max_tokens = 目标字数 × 1.6，prompt 中用 ±10% 区间。**

## 角色命名反 AI

AI 默认起名三大通病：全员诗意双名（沈砚辞、林知意）、古风生僻字、统一格式。
破解：混搭单名双名、配角用常见姓（王李张刘陈）、允许外号、同辈字合理（姐弟可同辈字）。

## Prompt 设计原则

- **极简 write-chapter**：只写步骤，不写规则。风格直接从源文学
- **plot_guide 显式映射**：源文列 vs 新书列，冲突类型不同，动作反应全换
- **高光时刻**：每章至少一个甜/虐/笑/反差/细节场景
- **角色行为模式前置**：open-book 阶段提取行为模式卡片（应激/决策/情感/弱点），注入 plot_guide 和 write-chapter，防角色漂移

## Flash 已知天花板

- 单章字数 ±20% 波动（60-70% 章达标）
- ~10% 随机失效（角色漂移、偶抄源文、过短）→ 重跑即可
- 句长偏短、对话偏多是模型特征，非 AI 痕迹
- 角色行为模式卡片能有效减少角色漂移（从~15%降到~5%），但不能完全消除

## 使用

```bash
# 完整 188 章
python tools/rewrite_chapters.py --config configs/xxx.json --start 1 --end 188 --workers 30

# 分步（concept 保护：已存在则自动跳过）
python tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
python tools/rewrite_chapters.py --config configs/xxx.json --phase guides,write,trim,compare

# Agent 模式写章（生成任务清单 → opencode 派生子 agent → postfix）
python tools/rewrite_chapters.py --config configs/xxx.json --phase write --execution-mode agent
# 然后消费任务（opencode 自动处理）
# 最后机械修正
python tools/rewrite_chapters.py --config configs/xxx.json --phase postfix

# 统一审改（新系统：一次排查所有问题并修复）
python tools/rewrite_chapters.py --config configs/xxx.json --phase unified

# 查看项目状态
python tools/rewrite_chapters.py --config configs/xxx.json --status

# 对比两次 validate 的指标变化（自动存档，0 token）
python tools/rewrite_chapters.py --config configs/xxx.json --diff

# 改 prompt 后记录版本
python .agents/skills/story-engine/tools/prompt_loader.py bump write-chapter.md
python .agents/skills/story-engine/tools/prompt_loader.py bump write-chapter.md "手动说明"

# 按prompt覆盖模型参数（在config.json中添加）
# "prompt_overrides": {"unified-review.md": {"temperature": 0.1, "model": "deepseek-v4-pro"}}

```

> ⚠️ `api_key` 为 null 时从 `$env:API_KEY` 读取。不要将 key 写入配置文件。
