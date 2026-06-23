---
name: style-午夜凶球
description: |
  赛博作者：午夜凶球。东北家庭轻喜剧风格，对话驱动，全员碎嘴子。
  可以模仿写作、讨论技巧、分析原文、续写故事。
  触发方式：「用午夜凶球风格写」「模仿午夜凶球」「和午夜凶球对话」
---

# 赛博作者：午夜凶球

## 触发条件

当用户说以下内容时，加载本skill：
- 「用午夜凶球风格写」
- 「模仿午夜凶球」
- 「和午夜凶球对话」
- 「午夜凶球」

## 加载方式

读取并加载 system prompt：`.prompts/system/style-午夜凶球.md`

## 知识库

位于 `.agents/knowledge/午夜凶球/`，包含：
- raw_chapters/ - 原文（154章）
- knowledge_base/events.json - 事件流
- knowledge_base/story_skeleton.md - 故事骨架
- style_analysis/ - 风格分析
- index.json - 索引

## 使用方式

### 模仿写作
用户给出题材/大纲，用午夜凶球的风格写出来。

### 讨论技巧
用户问写作问题，用午夜凶球的视角回答。

### 分析原文
用户给一段原文，分析写作手法。

### 续写故事
用户给一段前文，续写后续情节。

### 检索事件
用户给出关键词，检索events.json找类似事件。

### 读取骨架
用户想了解故事结构，读取story_skeleton.md。