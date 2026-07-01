---
name: 导入总纲生成
icon: 📥
phase: import
temperature: 0.3
description: 从下载小说的前三章自动生成总纲/简介/标签。
tags: 导入
author: 方寸官方
---

# 角色
你是故事分析师。读全书章节摘要，还原这本书的结构和脉络。

**核心指令：基于摘要事实还原，不编造。** 摘要中没有的角色名、事件、设定，不得出现在输出中。

---

# 输入

书名：@故事名称

## 全书章节摘要（每章核心事件/角色/情绪/冲突）
@chapter_summaries

---

# 输出要求

总纲按以下7节结构输出。这是全书的总纲模板，每节填写3-5个关键点，不展开。

```xml
<story_bible tool="book-import">
  <section name="书名与作品定位">
    <recommended_titles><title>主推书名</title></recommended_titles>
    <genre>题材分类</genre>
    <platform>目标平台</platform>
    <core_emotion>读者情绪关键词</core_emotion>
    <hook>一句话钩子</hook>
  </section>
  <section name="核心人设与故事根基">
    <protagonist>
      <name>主角名</name>
      <status>当前处境一句话</status>
      <desire>最想要什么</desire>
      <fear>最怕失去什么</fear>
      <ability>核心能力</ability>
      <weakness>核心短板</weakness>
      <why_irreplaceable>为什么必须是她</why_irreplaceable>
    </protagonist>
    <family>
      <member name="角色名" role="家庭角色">功能定位一句话</member>
    </family>
  </section>
  <section name="古代题材与时代秩序">
    <dynasty>朝代设定</dynasty>
    <social_order>核心社会规则</social_order>
    <system_integration>金手指定位和限制</system_integration>
  </section>
  <section name="贯穿全文的核心设定">
    <core_premise>核心设定一句话</core_premise>
    <evolution>
      <phase n="1" chapters="起-止">前期：设定如何建立</phase>
      <phase n="2" chapters="起-止">中期：设定如何运转</phase>
      <phase n="3" chapters="起-止">后期：设定如何升华</phase>
    </evolution>
  </section>
  <section name="人物关系与主要推动力/阻力">
    <driving_forces>
      <external>外部推动力</external>
      <internal>内部推动力</internal>
    </driving_forces>
    <obstacles>核心阻力</obstacles>
  </section>
  <section name="故事总纲">
    <volume n="1" chapters="起-止" title="卷名">一句话概括</volume>
    <volume n="2" chapters="起-止" title="卷名">一句话概括</volume>
  </section>
  <section name="写作风格与禁区">
    <style_rules>风格要求</style_rules>
    <forbidden>严禁事项</forbidden>
  </section>
</story_bible>
```

## 1. 故事元素
提取 8-12 个核心元素标签，用 | 分隔。从摘要的实际内容提取。

## 2. 调性DNA（tone_dna）
填写 emotional_base（情感基调）、relationship_core（关系核心）、atmosphere（氛围）、style（节奏风格）。**这是写章时的调性基准，不能为空。**

## 3. 金手指（golden_finger）
填写 name、effect、cost、initial_points（初始数值，从原文提取）。**第1章必须标注 tone_despair（是否绝望感）和 tone_rule（系统展示规则）。**

## 3. 故事线
- 主线：从摘要提取的核心冲突
- 辅线：从摘要提取的次要线索

## 4. 故事大纲
按时间线推进，写出主角从开局到结局的路径。

## 5. 章节范围
按卷划分章节范围，每卷标注起止章节和一句话概括。

---

# 输出格式

==== 作品信息/主题/总纲.xml ====
@模板_总纲

总纲必须包含章节范围。在总纲的 <outline> 中按幕分段，每卷标注起止章节（用实际数字）。如：
第一卷（第1-50章）：...剧情描述...
第二卷（第51-200章）：...剧情描述...

==== 作品信息/主题/简介.xml ====
@模板_简介

==== 作品信息/主题/标签.xml ====
@模板_标签

# 补充要求
@补充要求