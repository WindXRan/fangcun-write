---
name: 角色深度提取
icon: 👤
phase: source-analysis
temperature: 0.3
description: 从章节摘要提取深度角色卡
tags: 拆书,人设
output: 角色
---

# 素材

## 全书章节摘要（含每章出场角色）
@chapter_summaries

---

# 任务

基于以上摘要，提取出现频率最高的 6-12 个核心角色。每个角色输出一个文件。

每个角色包含：
- name：角色名（必须与摘要中的名字一致）
- role：功能位
- personality：性格特质（用摘要中的行为佐证）
- motivation：想要什么、怕什么
- growth_arc：开局→结局

# 输出格式

==== 作品信息/设定/角色/角色名.xml ====
<character name="角色名" role="protagonist">
  <tags>标签</tags>
  <background>人物背景</background>
  <bio>人物小传</bio>
  <motivation>核心欲望 | 核心恐惧</motivation>
  <arc>
    <start>开局状态</start>
    <end>结局状态</end>
  </arc>
</character>

继续输出第二个角色。

# 补充要求
@补充要求