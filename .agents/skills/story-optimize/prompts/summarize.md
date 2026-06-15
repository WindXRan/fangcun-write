---
version: 1
type: user
phase: optimize-summarize
description: 汇总所有批次的问题清单
required_vars: ["all_analyses", "book_name"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 4096, "reasoning_effort": "low", "temperature": 0.3}
---

你是一个资深网文编辑。汇总以下分批审稿结果，生成统一的问题清单和修复指令。

## 任务

1. 合并所有批次的问题，去重
2. 按严重程度排序（high > medium > low）
3. 每个问题生成可执行的修复指令
4. 统计问题频率（出现在多少章）

## 输出格式

```json
{
  "summary": {
    "total_chapters": 125,
    "high_issues": 3,
    "medium_issues": 5,
    "low_issues": 2
  },
  "issues": [
    {
      "id": 1,
      "type": "ai_pattern",
      "category": "感官堆叠",
      "severity": "high",
      "count": 45,
      "description": "消毒水+木质调描写在45章中重复出现",
      "fix_instruction": "删除重复的感官描写，只在首次出场时保留，后续章节用其他感官替代",
      "affected_chapters": [1, 3, 5, 7, 9, 11, 13, 15, 17]
    }
  ],
  "fix_priorities": [
    "1. 先修 high 级别问题",
    "2. 感官堆叠和情绪公式是最大AI痕迹来源",
    "3. 章尾公式变化需要替换，不是删除"
  ]
}
```

## 批次分析结果

{all_analyses}
