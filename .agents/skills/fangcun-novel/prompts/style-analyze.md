---
name: style-analyze
version: 13
changelog: 压缩格式
description: 提取源文的人类写法特征
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.3}
---

读这一章，提取这个作者的写法特征。目标：让仿写读起来像同一个人写的。

## 风格类型
- 题材类型：
- 叙事基调：
- 幽默风格：
- 情绪基调：

## 信息释放时机
- 本章释放的信息
- 本章暗示的信息
- 本章藏住的信息
- 结尾悬念

## 写法指令（15条左右）

从源文中提取这个作者的独特写法，每条格式：
- [指令] 具体怎么写

只输出正文，不加解释。

本章锚点：{style_anchors}
章节：{chapter_text}
