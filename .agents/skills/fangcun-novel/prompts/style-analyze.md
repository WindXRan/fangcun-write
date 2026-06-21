---
name: style-analyze
version: 20
changelog: XML标签输出，不解析内容
description: 提取源文特征，输出3个文件
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.3}
---

读这一章，提取特征，用XML标签分隔输出。**你只能分析给你看的这一章。**

<style>
## 风格类型
- 题材类型：
- 叙事基调：
- 幽默风格：
- 情绪基调：

## 写法指令
- [指令] 具体怎么写
（15条左右）
</style>

<structure>
## 场景功能
- [场景] 功能=xxx，源文实现方式=xxx

## 冲突升级模式
- 阶段1：xxx
- 阶段2：xxx
- 阶段3：xxx

## 信息释放节奏
- 本章释放：xxx
- 本章暗示：xxx
- 本章藏住：xxx
- 结尾悬念：xxx
</structure>

<blacklist>
- 核心桥段：xxx
- 标志性台词：xxx
- 标志性道具：xxx
</blacklist>

本章锚点：{style_anchors}
章节：{chapter_text}
