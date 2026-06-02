# 输出模板规范（v2.0）

## 概述

story-distill 的输出必须符合 story-style 的格式要求，确保 story-rewrite 能正确读取。

**v2.0 变更**：引入 `.distill/` 工作目录概念。Phase 2-5 中间产物全部写到 `.distill/` 子目录，Phase 6 Consolidation 收口时合并到正式位置并删除 `.distill/`。

---

## 双层目录结构

### 概念

| 层 | 路径 | 生命周期 | 内容 |
|----|------|---------|------|
| **交付层** | `references/`、`review/` | 永久 | 最终交付物，被 story-rewrite 读取 |
| **工作层** | `.distill/` | 临时，Phase 6 删除 | Phase 1-5 中间产物 |

工作层和交付层物理隔离，避免：
- candidates/ 与 references/ 重复占用
- rejected/ 误导 story-rewrite 误读
- sources/ 占用磁盘

---

## 交付层（最终形态）

### write 模式（14 个文件）

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                          # 写作决策框架（15-20KB）
├── meta.json                         # 量化数据
├── test-prompts.json                 # 验证产物（可选）
└── references/                       # 11 个
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

### review 模式（21 个文件）

```
.claude/skills/story-style/{作者名}/
├── SKILL.md
├── meta.json
├── test-prompts.json
├── review/                           # 2 个
│   ├── SKILL.md
│   └── meta.json
└── references/                       # 16 个
    ├── （write 模式的 11 个）
    ├── review-redlines.md
    ├── edit-prescriptions.md
    ├── quality-thresholds.md
    ├── review-persona.md
    └── revision-capability.md
```

---

## 工作层（Phase 6 收口前形态）

```
.claude/skills/story-style/{作者名}/
└── .distill/
    ├── book-overviews/                # Phase 1 产出
    │   └── {书名}.md                  # 6 本书 = 6 文件
    ├── writing-samples-*.md           # Phase 1 产出（每本一个）
    ├── candidates/                    # Phase 2 原始产出
    │   ├── mental-models.md
    │   ├── decision-heuristics.md
    │   ├── ... (10 个 write 维度)
    │   ├── review-redlines.md         # review 模式
    │   └── ... (5 个 review 维度)
    ├── constructed/                   # Phase 4 RIA++ 终版
    │   └── （同 candidates 结构）
    ├── rejected/                      # Phase 3 淘汰
    │   ├── cross-book.md
    │   ├── frequency.md
    │   └── uniqueness.md
    └── sources/                       # 原文备份
        └── {书名}.txt
```

**禁止**：在工作层和交付层同时存在同名文件。Phase 6 必须保证工作层被清空。

---

## 迁移对照表（v1.0 → v2.0）

| v1.0 路径 | v2.0 路径 | 迁移动作 |
|----------|----------|---------|
| `references/candidates/X.md` | `.distill/candidates/X.md`（Phase 2-5）→ 验证后丢弃 | 不保留 |
| `references/rejected/X.md` | `.distill/rejected/X.md` | 不保留 |
| `references/constructed/X.md` | `.distill/constructed/X.md` | Phase 6 合并到 `references/X.md` |
| `references/constructed/constructed-X.md` | 删（与 X.md 重复） | 不保留 |
| `references/book-overviews/X.md` | `.distill/book-overviews/X.md` | 不保留 |
| `references/writing-samples-{书名}.md` | `.distill/writing-samples-{书名}.md` | 合并为 `references/writing-samples.md` |
| `references/writing-samples.md` | 同 v2.0 | 保留 |
| `references/X.md`（11 个维度） | 同 v2.0 | 保留 |
| `sources/{书名}.txt` | `.distill/sources/{书名}.txt` | 不保留 |
| 无 | `review/SKILL.md` | review 模式新增 |
| 无 | `test-prompts.json` | verify 阶段新增（v1.0 也有但散落） |

---

## SKILL.md 格式要求

### 必要 section

| Section | 说明 | 缺失影响 |
|---------|------|---------|
| 心智模型 | 故事观/角色观/冲突观/爽感观 | story-architect 无法理解作者的故事观 |
| 决策启发式 | 如果X则Y格式的决策规则 | story-architect 无法设计钩子和爽点 |
| 节奏直觉 | 读者预期管理/情绪曲线/信息差 | narrative-writer 无法控制节奏 |
| 表达DNA | 信息密度/感官/情绪/对话/句式 | narrative-writer 无法遵循风格 |
| 反模式 | 绝对不用的词/句式/结构/情节 | narrative-writer 可能犯禁忌错误 |
| 书名与简介 | 书名命名规则+简介写作规则 | story-synopsis 无法生成简介 |
| 章纲模板 | 章节命名/结构/事件密度 | story-architect 无法生成章纲 |
| 写作样本 | 4类语感锚点段落 | narrative-writer 无法校准语感 |
| 写作检查清单 | 写之前问自己+写完后检查 | 无法验证产出质量 |
| 去AI策略 | 连接词/副词/句长等阈值+预选模块 | 无法检测AI指纹，产出AI味重 |

### 格式规范

- 使用 Markdown 格式
- 每个 section 有清晰的标题
- 每条规则必须有原文引用（R）
- 触发场景用「如果{条件}，则{行动}」格式

---

## meta.json 格式要求

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

---

## references/ 格式要求

每个文件使用 Markdown 格式，包含：

1. **标题**：说明分析内容
2. **RIA++ 结构**：每条规则必须有 R/I/A1/A2/E/B
3. **原文示例**：引用原文片段，附书名+章节号

---

## 验证方式

手动检查 SKILL.md 是否包含所有必要 section（见下方格式要求）。

---

## 与 story-rewrite 的集成

story-rewrite 通过以下方式读取风格：

1. `--style={作者名}` 参数
2. 读取 `.claude/skills/story-style/{作者名}/SKILL.md`
3. 读取 `.claude/skills/story-style/{作者名}/meta.json`

确保路径正确，文件存在，格式符合要求。
