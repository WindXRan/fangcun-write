---
name: 设定提取（全类）
icon: 🌐
phase: source-analysis
temperature: 0.3
description: 从章节摘要提取全部设定：角色/地点/物品/势力/背景。角色按主次分档。
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

## 角色分级标准

提取时按角色重要性自动分档：

**主要角色（tier="main"）**——满足以下至少2条：
- 出场覆盖 3 卷以上
- 对主角命运有直接影响
- 有独立的人物弧线
- 与主角有 2 次以上的直接对手戏/情感互动

**次要角色（tier="minor"）**——不满足上述条件的其他角色

### 输出格式
所有角色统一使用以下模板（通过 @模板_角色 加载），**主要角色必须填满所有字段，包括 language_style 7维（口癖/节奏/信息偏好/立场/身份措辞/性格语气/进度态度）和 voice 段（speech_patterns / internal_os_style / humor_type / identity_anchor）**，次要角色只需精简字段：

@模板_角色

按 `==== 作品信息/设定/角色/角色名.xml ====` 格式逐角色输出。

## 2. 地点

提取故事中出现的主要场所。每个地点包含：

==== 作品信息/设定/地点/地名.xml ====
<location name="地名">
  <description>场景描述</description>
</location>

## 3. 物品

提取对剧情有推动作用的道具：

==== 作品信息/设定/物品/物品名.xml ====
<item name="物品名">
  <description>用途+意义</description>
</item>

## 4. 势力

提取故事中的组织/家族：

==== 作品信息/设定/势力/势力名.xml ====
<faction name="势力名">
  <description>构成+目标</description>
</faction>

## 5. 背景

提取故事的世界观设定：

==== 作品信息/设定/背景/背景名.xml ====
<setting name="背景名">
  <description>描述</description>
</setting>

# 补充要求
@补充要求
