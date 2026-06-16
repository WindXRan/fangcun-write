---
name: translate-chapter
description: 中文章节翻译成英文，适配 Webnovel 风格
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-pro
  max_tokens: 8192
  reasoning_effort: high
  temperature: 0.7
---

将以下中文章节翻译成英文，适配 Webnovel 平台风格。

## 翻译规则

1. **对话直译** — 保持原文的对话节奏和语气
2. **叙述意译** — 用英文网文习惯重写，不要逐字翻译
3. **文化适配** — 中式表达改成英文读者能理解的方式
4. **术语一致** — 人名/地名按术语表翻译，全文统一
5. **风格保留** — 保持原文的句式节奏、对话风格

## 格式要求

- 每章 1500-3000 词
- 标题格式：Chapter {N}: {Title}
- 段落之间空行分隔
- 无中文标点（全部换成英文标点）

## 术语表

{glossary}

## 中文原文

{zh_text}
