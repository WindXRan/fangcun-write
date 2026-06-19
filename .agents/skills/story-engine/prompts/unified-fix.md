---
version: 1
changelog: 初始化修复prompt
type: user
phase: unified_fix
description: 统一审改 - 修复
required_vars: ["issues_text", "chapter_content", "orig_chars", "target_chars", "min_chars", "max_chars"]
optional_vars: ["adjacent_context", "源文全文"]
system_prompt: system-generic.md
defaults: {"model": "mimo-v2.5-pro", "reasoning_effort": "low", "temperature": 0.6}
---

# 统一审改：修复任务

你是资深网文编辑，负责修复以下章节的问题。

## 待修复问题

{issues_text}

## 字数要求

- 当前字数：{orig_chars}
- 目标字数：{target_chars}
- 可接受范围：{min_chars}~{max_chars}

## 上下文（相邻章节）

{adjacent_context}

## 源文参考

{源文全文}

## 原文内容

{chapter_content}

## 修复规则

1. **只修复列出的问题**，不要擅自改动其他内容
2. **保持字数在范围内**，修复后字数必须在 {min_chars}~{max_chars} 之间
3. **保持情节完整**，不要删减重要情节
4. **保持风格一致**，修复后的文风要与原文一致
5. **AI痕迹词**：直接删除句首路标词，不要重写整句
6. **比喻过多**：删除多余的比喻，保留最贴切的
7. **直抒情**：用动作/细节代替直接表达
8. **台词雷同**：重写台词，保持意思但换表达方式

## 输出要求

直接输出修复后的完整章节，不要加任何解释。

第一行必须是：第X章 [章名]

末尾必须加：【字数：XXX字】
