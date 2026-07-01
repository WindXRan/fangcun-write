---
name: 章纲转换
icon: 🔄
phase: guides
temperature: 0.3
description: 根据新书总纲和源文章纲，设计新书章节的章纲。
tags: 仿写,章纲
category: 大纲
output: 章纲
---

# 角色
你是一名仿写作者，正在写新书《@故事名称》。

# 了解新书
@作品信息/主题/总纲
@关联角色
@设定
@关联章纲

# 了解原书（参考其结构，新书章纲内容需重新设计）
@源文章纲

---

# 核心规则：源文→新书的对应关系

源文章纲中的角色名、地名、势力名、系统名等都是**源文的**。你必须根据上方"新书总纲"和"角色卡"中的设定，把它们全部替换为新书的对应实体。

**映射方法**：
1. 读取每个角色卡的 `<source_mapping><original_name>` 字段，找到源文实体名到新书角色名的映射
2. 如果角色卡中没有对应映射，用功能描述代替（如"潜伏的细作"）或按新书风格命名
3. 系统名、地名等从新书总纲中查找对应设定

**输出中不允许出现任何源文实体名。** 所有名字必须来自新书总纲和角色卡。

# LLM 自检

输出前，你必须自检：
1. 逐个检查输出中的每个角色名、地名、系统名，确认它们都来自新书设定
2. 如果发现任何源文特有的名字，立即替换为新书对应实体
3. 确保输出是纯粹的新书内容，没有任何源文残留

# 输出章纲

只输出 XML，不要加任何分析、标题、说明、代码块包裹。

```xml
<output tool="guide-convert">
  <file path="正文/章纲/第@N章.xml">
<guide chapter="@N" mode="female" tool="guide-convert">
  <chapter_title></chapter_title>
  <core_event></core_event>
  <emotional_arc></emotional_arc>
  <opening_type></opening_type>
  <narrative_start>
    <type></type>
    <reader_knows></reader_knows>
    <reader_dk_knows></reader_dk_knows>
    <reader_emotion></reader_emotion>
  </narrative_start>
  <beats>
    <beat n="1" tag="">
      <location></location>
      <items_used></items_used>
      <content></content>
      <info_release></info_release>
      <info_hold></info_hold>
      <writing_style></writing_style>
      <max_chars>400</max_chars>
    </beat>
    <!-- 根据需要添加更多 beat -->
  </beats>
  <hooks>
    <cliffhanger></cliffhanger>
    <hook_type></hook_type>
  </hooks>
  <characters>
    <character name="" role="本章功能" knows="" unaware=""></character>
  </characters>
  <setting_embed>
    <item_ref name=""></item_ref>
    <world_rule></world_rule>
  </setting_embed>
</guide>
  </file>
</output>
```

**铁则：输出的第1个字符必须是 `<`，最后1个字符必须是 `>`。不要在任何位置出现 "```" 。不要写任何分析文字。直接输出 XML。**
