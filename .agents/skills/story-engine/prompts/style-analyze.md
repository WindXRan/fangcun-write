---
name: style-analyze
description: 提取可复制的写法特征（正面仿写+反面避坑）
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-flash
  max_tokens: 4096
  reasoning_effort: low
  temperature: 0.3
---

提取本章写法特征，每条附例句。

标点(引号/省略号/感叹号/破折号/逗句节奏/特殊标点/排版)
正面2-3条(句式/对话/情绪) | 反面2条(AI易走样)

锚点: {style_anchors}
章节: {chapter_text}
