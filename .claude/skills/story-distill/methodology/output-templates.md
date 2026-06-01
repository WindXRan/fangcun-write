# 输出模板规范

## 概述

story-distill 的输出必须符合 story-style 的格式要求，确保 story-rewrite 能正确读取。

---

## 输出目录结构

```
.claude/skills/story-style/{作者名}/
├── SKILL.md                    # 决策框架（RIA++结构，必需）
├── meta.json                   # 量化数据（必需）
├── test-prompts.json           # 压力测试（可选）
├── references/                 # 详细分析（必需）
│   ├── book-overviews/         # 每本书的结构分析
│   ├── mental-models.md        # 心智模型（附原文引用）
│   ├── decision-heuristics.md  # 决策启发式（附原文引用）
│   ├── rhythm-intuition.md     # 节奏直觉（附原文引用）
│   ├── expression-dna.md       # 表达DNA（附原文引用）
│   ├── anti-patterns.md        # 反模式（附原文引用）
│   ├── synopsis-patterns.md    # 书名与简介风格（附原文示例）
│   ├── chapter-template.md     # 章纲模板（附原文引用）
│   ├── writing-samples.md      # 语感样本（附出处标注）
│   ├── candidates/             # 提取器原始产出 + 通过验证的规则
│   └── rejected/               # 淘汰的规则+原因（审计用）
└── sources/                    # 原文备份（可选）
    └── {book_name}.txt
```

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

使用 `scripts/validate_output.py` 验证：

```bash
python .claude/skills/story-distill/scripts/validate_output.py .claude/skills/story-style/{作者名} {作者名}
```

---

## 与 story-rewrite 的集成

story-rewrite 通过以下方式读取风格：

1. `--style={作者名}` 参数
2. 读取 `.claude/skills/story-style/{作者名}/SKILL.md`
3. 读取 `.claude/skills/story-style/{作者名}/meta.json`

确保路径正确，文件存在，格式符合要求。
