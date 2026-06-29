---
name: 设定提取（全类）
icon: 🌐
phase: source-analysis
temperature: 0.3
description: 从章节摘要提取全部设定：角色/地点/物品/势力/背景。一次覆盖。
tags: 拆书,人设
category: 拆书
output: 角色,地点,物品,势力,背景
---

# 素材

## 全书章节摘要（每章核心事件/出场角色/情绪/冲突）
@chapter_summaries

---

# 任务

基于以上摘要数据，提取以下五类设定。**每类至少输出 2 个，不设上限。**
只从摘要中出现的信息提取，不编造。

## 1. 角色
提取所有重复出现的角色。每个角色包含：
- name（角色名，必须与摘要一致）
- role（protagonist/antagonist/love_interest/ally/sidekick）
- personality（2-3个特质）
- background（背景）
- motivation（想要什么）

## 2. 地点
提取故事中出现的主要场所。每个地点包含：
- name（地名）
- description（场景描述）

## 3. 物品
提取对剧情有推动作用的道具。每个物品包含：
- name（物品名）
- description（用途+意义）

## 4. 势力
提取故事中的组织/家族。每个势力包含：
- name（势力名）
- description（构成+目标）

## 5. 背景
提取故事的世界观设定。包含：
- 时代背景
- 特殊规则（如有）

# 输出格式

每个类别一个或多个文件，路径 = 作品信息/设定/{类别}/{名称}.xml

<output>
  <file path="作品信息/设定/角色/角色名.xml">
    <character name="角色名" role="protagonist">
      <background>背景</background>
      <personality>性格</personality>
      <motivation>动机</motivation>
    </character>
  </file>
  <file path="作品信息/设定/地点/地名.xml">
    <location name="地名">
      <description>描述</description>
    </location>
  </file>
  <file path="作品信息/设定/物品/物品名.xml">
    <item name="物品名">
      <description>用途</description>
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
