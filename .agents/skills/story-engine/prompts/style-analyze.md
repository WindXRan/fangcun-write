---
name: style-analyze
description: 提取可复制的写法特征（正面仿写+反面避坑）
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-flash
  max_tokens: 2048
  reasoning_effort: low
  temperature: 0.3
---

提取本章写法特征，每条附例句。

标点|正面2-3条(句式/对话/情绪)|反面2条(AI易走样)

{style_anchors} {chapter_text}
