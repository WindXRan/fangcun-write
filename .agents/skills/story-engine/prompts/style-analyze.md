---
name: style-analyze
description: 提取可复制的写法特征（正面仿写+反面避坑）
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-flash
  max_tokens: 1024
  reasoning_effort: low
  temperature: 0.3
---

读这一章，提取写法特征。

## 正面（仿写时必须做到，每条附原文例句）

找出 2-3 个本章最具体的写法特征，每个用一句话+原文例句说明。
- 句式/节奏特征
- 对话写法习惯
- 情绪处理方式

## 反面（仿写时必须避免，每条说明为什么）

找出 2 个本章写法最可能被 AI 模仿走样的点。
- 最容易写成 AI 味的特征
- 最容易写得千篇一律的地方

## 输出格式

正面：
1. [写法特征] — 例："原文例句..."
2. ...

反面：
1. [避免什么] — [为什么]
2. ...

上下文参考（不要复述数字）: {style_anchors}

章节:
{chapter_text}
