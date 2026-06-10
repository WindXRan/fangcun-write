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
Phase 1:   开书 (pro, 1 call)        → concept.md（设定+角色名+角色行为模式+全局节奏图+弧线）
Phase 2:   Guides (flash, 2N 并行)   → plot_{N}.md + style_{N}.md（每章独立风格）
Phase 3:   写章 (flash, N 并行)      → ch_{N}.txt（章名自生成）
Phase 3.5: Trim (flash)              → 超字数 20% 的章自动精简
Phase 3.6: 衔接修复 (flash, N-1 并行) → 修章间重叠
Phase 4:   对比 (本地)                → compare/报告
Phase 6:   统一审查+修复              → unified_review.json + unified_fix.json
```

### 统一审改系统（Phase 6）

合并所有检查项为一次排查，输出结构化 JSON 报告：

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
python .agents/skills/story-engine/tools/unified_reviewer.py --config configs/xxx.json

# 只用算法（不开 LLM，快但粗糙）
python .agents/skills/story-engine/tools/unified_reviewer.py --config configs/xxx.json --no-llm

# 修复
python .agents/skills/story-engine/tools/unified_fixer.py --config configs/xxx.json

# pipeline 集成
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase unified
```

## 文件结构

```
projects/{作者}/{书名}/
├── _cache/chapters/第N章.txt        # 拆章缓存
├── style_analysis/style_{N}.json    # 每章风格数据（脚本生成）
└── rewrites/{新书名}/
    ├── concept.md                    # 设定+弧线+角色名+行为模式+全局节奏图
    ├── guides/plot_{N}.md           # 章纲（节拍映射+高光+角色模式+台词原创性）
    ├── guides/style_{N}.md          # 风格速查（定量锚点+执行规则）
    ├── chapters/ch_{N}.txt          # 正文
    └── compare/                      # 对比报告
```

## 模型策略

| 阶段 | 模型 | 原因 |
|------|------|------|
| 开书 | pro (reasoning=high) | 需要深度分析源文模式 |
| 风格分析 | 脚本（batch_style_analysis.py） | 自动提取，无需 LLM |
| Guides | flash | 够用，速度快 |
| 写章 | flash | 字数听话，指令执行好 |
| Trim/衔接 | flash | 简单任务 |

**pro 写章更好看但字数失控（+50%），flash 听话但偶有随机失效（~10%）。**
**字数控制：max_tokens = 目标字数 × 1.6，prompt 中用 ±10% 区间。**

## 角色命名反 AI

AI 默认起名三大通病：全员诗意双名（沈砚辞、林知意）、古风生僻字、统一格式。
破解：混搭单名双名、配角用常见姓（王李张刘陈）、允许外号、同辈字合理（姐弟可同辈字）。

## Prompt 设计原则

- **极简 write-chapter**：只写步骤，不写规则。规则归位到 style_guide
- **style_guide 每条可 grep**：不写"描写细腻"，写"用了'心中涌起'→ 违规"
- **plot_guide 显式映射**：源文列 vs 新书列，冲突类型不同，动作反应全换
- **高光时刻**：每章至少一个甜/虐/笑/反差/细节场景
- **角色行为模式前置**：open-book 阶段提取行为模式卡片（应激/决策/情感/弱点），注入 plot_guide 和 write-chapter，防角色漂移

## Flash 已知天花板

- 单章字数 ±20% 波动（60-70% 章达标）
- ~10% 随机失效（角色漂移、偶抄源文、过短）→ 重跑即可
- 并行无跨章感知 → 靠衔接修复补
- 句长偏短、对话偏多是模型特征，非 AI 痕迹
- 角色行为模式卡片能有效减少角色漂移（从~15%降到~5%），但不能完全消除

## 使用

```bash
# 完整 188 章
python tools/rewrite_chapters.py --config configs/xxx.json --start 1 --end 188 --workers 30

# 分步（concept 保护：已存在则自动跳过）
python tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
python tools/rewrite_chapters.py --config configs/xxx.json --phase guides,write,trim,continuity,compare

# 统一审改（新系统：一次排查所有问题并修复）
python tools/rewrite_chapters.py --config configs/xxx.json --phase unified

# 查看项目状态
python tools/rewrite_chapters.py --config configs/xxx.json --status

# 风格分析（一键完成，参考 inkos style-analyzer）
python tools/style_analyzer.py <源文目录> <输出目录>
python tools/fill_style_guides.py <guides目录> <源文目录> [api_key]
```

> ⚠️ `api_key` 为 null 时从 `$env:API_KEY` 读取。不要将 key 写入配置文件。
