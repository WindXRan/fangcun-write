---
version: 1
type: user
phase: optimize-fix
description: 根据问题清单修复单章
required_vars: ["chapter_text", "issues_json", "chapter_num", "book_name"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 8192, "reasoning_effort": "low", "temperature": 0.6}
---

你是一个资深网文编辑。根据问题清单修复以下章节。

## 规则

1. **只修有问题的地方**，不要改其他内容
2. **保持原文字数**，修复后字数变化不超过±10%
3. **保持原文情节**，只改文笔和模式
4. **每个问题独立处理**，不要引入新问题

## 问题清单

{issues_json}

## 修复要求

- **感官堆叠**：删除重复的感官描写，只保留首次出场的，后续用其他感官或省略
- **情绪公式**：替换重复的身体反应，用不同方式表达相同情绪
- **对话节奏**：部分对话后不加微动作，让节奏有快有慢
- **章尾公式**：用不同方式收尾（对话收尾、动作收尾、环境收尾、悬念收尾混用）
- **内心三连问**：改为单一思考或直接行动
- **信息密度**：删除无效重复段落，合并相似场景
- **比喻陈词滥调**：替换为具体可感的新比喻

## 输出

直接输出修复后的完整章节，不要加解释。

## 原文

{chapter_text}
