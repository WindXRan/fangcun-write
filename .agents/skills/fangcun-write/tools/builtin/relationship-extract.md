---
name: 关系图谱提取
icon: 🔗
phase: source-analysis
temperature: 0.3
description: 从章节摘要提取角色关系图谱：家族关系、情感线、势力对立、盟友网络。
tags: 拆书,人设
category: 拆书
output: 关系
---

# 素材

## 全书章节摘要（每章出场角色/核心事件/情绪）
@chapter_summaries

---

# 任务

基于以上摘要，提取本书的角色关系网络。**每对关系写一条。**

关系分为四类：

## 1. 家族关系
有血缘或姻亲关系的角色。包含：
- source → target（方向）
- type: father/mother/sibling/spouse/child
- description: 关系描述

## 2. 情感线
有浪漫/情感张力的角色。包含：
- source → target
- type: crush/love/rival/breakup
- description: 发展过程

## 3. 势力对立
处于对立立场的角色。包含：
- source → target
- type: enemy/rival/conflict
- description: 冲突原因

## 4. 盟友/师徒
合作关系的角色。包含：
- source → target
- type: ally/mentor/follower
- description: 合作方式

# 提取要求
- 只提取摘要中确认的关系，不编造
- 关系是双向的（如 A 是 B 的父亲）
- 每类至少输出 1 条，不设上限
- 角色名必须与摘要一致

# 输出格式

<output>
  <file path="作品信息/设定/关系图谱.xml">
    <relationships>
      <relation source="乔娇娇" target="乔忠国" type="father" />
      <relation source="乔娇娇" target="沈元凌" type="love" />
      <relation source="乔忠国" target="沈元白" type="enemy" />
    </relationships>
  </file>
</output>

# 补充要求
@补充要求
