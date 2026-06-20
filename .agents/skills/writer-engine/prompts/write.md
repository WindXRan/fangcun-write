---
name: write
version: 1
description: 写章
type: user
phase: write
system_prompt: system-generic.md
---

你是一个专业的小说写手。请写《{book_name}》第{ch_num}章。

## 角色卡
{characters}

## 章纲
{guide}

## 前文内容
{prev_context}

## 写作要求

1. **风格一致**：延续原作的文笔风格（对话比例、段长、描写特点）
2. **角色一致**：角色名字、性格、说话方式必须与原作一致
3. **情节连贯**：承接前文情节，不出现矛盾
4. **字数控制**：2000-3000字
5. **章末钩子**：每章结尾留一个钩子，吸引读者继续看

## 输出格式

第{ch_num}章 [章名]

[正文内容]

【字数：XXX字】
