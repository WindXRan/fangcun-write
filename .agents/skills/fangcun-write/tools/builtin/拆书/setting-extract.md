---
name: 设定提取（地点/物品/势力/背景）
icon: 🏛️
phase: source-analysis
temperature: 0.3
description: 从章节摘要提取地点/物品/势力/背景设定。角色由 character-deep 单独提取。
tags: 拆书,设定
category: 拆书
output: 地点,物品,势力,背景
---

# 素材

## 全书章节摘要
@chapter_summaries

---

# 任务

基于以上摘要数据，提取以下四类设定。**每类至少输出 2 个。**

只从摘要中出现的信息提取，不编造。

## 1. 地点
故事中出现的主要场所。如城市、建筑、特定场景。
每项包含：name（地名）、description（场景描述+发生的事件）

## 2. 物品
对剧情有推动作用的道具、信物、关键物品。
每项包含：name（物品名）、description（用途+在剧情中的作用）

## 3. 势力
故事中的组织、家族、集团、机构。
每项包含：name（势力名）、description（构成+目标+与主角的关系）

## 4. 背景
故事的世界观设定。
包含时代背景、特殊规则、力量体系（如有）。

# 输出格式

<output>
  <file path="作品信息/设定/地点/地名.xml">
    <location name="地名">
      <description>描述</description>
    </location>
  </file>
  <file path="作品信息/设定/物品/物品名.xml">
    <item name="物品名">
      <description>描述</description>
    </item>
  </file>
  <file path="作品信息/设定/势力/势力名.xml">
    <faction name="势力名">
      <description>描述</description>
    </faction>
  </file>
  <file path="作品信息/设定/背景/背景名.xml">
    <setting name="背景名">
      <description>描述</description>
    </setting>
  </file>
</output>

# 补充要求
@补充要求
