---
name: rewrite
version: 1
description: 重写章节
type: user
phase: rewrite
system_prompt: system-generic.md
---

请重写《{book_name}》第{ch_num}章。

## 重写原因
{reason}

## 角色卡
{characters}

## 章纲
{guide}

## 前文内容
{prev_context}

## 重写要求

1. **解决上述问题**
2. **保持角色一致性**
3. **字数控制**：2000-3000字
4. **章末钩子**：留一个钩子

## 输出格式

第{ch_num}章 [章名]

[正文内容]

【字数：XXX字】
