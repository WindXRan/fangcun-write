---
version: 1
changelog: 初始版本
type: user
phase: unified
description: 修复章节
required_vars: ["issues_text", "adjacent_context", "orig_chars", "target_chars", "min_chars", "max_chars", "chapter_content"]
defaults: {"model": "deepseek-v4-flash", "max_tokens": 8000, "reasoning_effort": "low", "temperature": 0.6}
---

# 统一修复提示词

你是资深网文写手。根据以下问题一次性修复章节。

## 需修复的问题

{issues_text}

## 相邻章节上下文

{adjacent_context}

## 原始章节（{orig_chars}字，目标{target_chars}字）

{chapter_content}

## 要求

1. 一次性修复所有问题，只改有问题的地方
2. 字数：{min_chars}~{max_chars}字
3. 禁止出现路标词：首先、其次、然后、最后、与此同时、值得注意的是、此外、综上所述
4. 用动作细节代替直抒胸臆
5. 台词口语化
6. 直接输出完整章节，不要加任何分析或说明
