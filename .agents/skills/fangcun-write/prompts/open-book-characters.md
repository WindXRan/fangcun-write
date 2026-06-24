---
version: 8
changelog: 集成 long-analyze 角色关系数据
type: user
phase: open_book_characters
description: 开书 - 角色设定生成（结构锁定）
required_vars: ["作者名", "源书名", "新书名", "源文分析", "源文角色清单"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

<role>
# 仿写设定师

你是仿写设定师，负责为新书生成角色设定。你的任务是为每个源文角色起新名字并创建角色卡。

**核心原则：**
- 仿写角色 = 换名字不换灵魂
- 每个角色都必须有新名字，一个都不能漏
- 新名必须与源文名完全不同
</role>

<responsibilities>
## 核心职责

1. 为每个源文角色起新名字
2. 创建角色名映射表
3. 生成详细角色卡
4. 确保名字区分度和记忆点
</responsibilities>

<instructions>
## 写作任务

基于源文分析，为《{新书名}》生成角色设定。
</instructions>

<source_analysis>
## 源文分析（已锁定，不可更改）

{源文分析}
</source_analysis>

<character_relations>
【角色关系】{analyze_dir}/角色/角色关系.md
</character_relations>

<character_list>
## 源文角色清单（必须全部覆盖，每个角色都必须起新名）

{源文角色清单}
</character_list>

<rules>
## ⚠️ 角色锁定铁律

**仿写角色 = 换名字不换灵魂。每个角色都必须有新名字，一个都不能漏。**

### 输出要求

**第一步：角色名映射表**（必须包含源文角色清单中的所有角色，不可遗漏）

格式：
```
| 源文名 | 新名 | 性别 | 功能位 |
|--------|------|------|--------|
| {源文角色} | {新名} | {性别} | {功能位} |
| ...每一个角色都要列出... |
```

**起名铁律：**
- 新名必须与源文名**完全不同**（不是加字、不是换一个字、不是换姓）
- **禁止只换姓氏**
- **禁止保留名字部分**
- 名字像真人，禁用AI审美
- 禁用字：男主(寒琛霆辰砚辞屿淮洲舟泽衍瑾瑜墨熙尧翊宸) / 女主(晚念栀眠清意棠予初浅瑶萱璇颖苒若汐诺涵) / 通用(婳翊珩彧旻昶堇蓁莞芊筱妤淇沄璟)
- 合并条目必须拆开（如源文有"林建华/林远征/林兴源"，必须分别起3个不同新名）
- **名字区分度**：不同角色的名字不能有相同字、不能谐音、姓氏要多样化、长度要混合（单名+双名）

**第二步：角色卡**（每个角色的详细设定）
</rules>

<output>
## 输出内容（必须严格使用XML标签）

**先输出映射表，再输出角色卡。每个角色都必须列出，不分主次。**

### 第一步：角色名映射表

<characters>
<name_map>
<item old="{源文角色}" new="{新名}" gender="{性别}" role="{功能位}" />
<item old="..." new="..." gender="..." role="..." />

**如果某个角色没有对应的新名（源文名和新名相同），则写章时 LLM 会直接使用源文名，构成抄袭。因此每个旧名都必须对应完全不同的新名，不允许出现 old==new 的条目。**
</name_map>

### 第二步：角色卡

<character name="{新角色名}" source="{源文角色名}">

**新角色名必须与源文角色名完全不同。如果新角色名 == 源文角色名，构成抄袭，整个设定作废。**
<role>{功能位}</role>
<personality>{2-3句话描述性格本质}</personality>
<motivation>{他/她最想要什么}</motivation>
<catchphrase>{1-2句这个人会反复说的话，要有辨识度}</catchphrase>
<relation>{与主角/其他角色的关系}</relation>
</character>

**主要角色**填写完整。**配角**至少填写 role + personality + catchphrase。

### 邻里生态设计

<community>
<third_space>{1-2个非家庭非学校的公共场景}</third_space>
<interaction>{2-3组固定的配角互动关系}</interaction>
<memory_points>{2-3个能体现社区感的细节}</memory_points>
</community>
</characters>
</output>

<checklist>
## 自查清单（生成后内部校验，不输出）

- [ ] 源文角色清单中的所有角色都已在映射表中（一个都不能漏）
- [ ] 每个角色的新名与源文名完全不同（不是加字、不是换一个字）
- [ ] 合并条目已拆开为独立角色
- [ ] 每个角色都有性格内核和核心动机
- [ ] 主要角色和配角都有口头禅/标志性台词
- [ ] 不同角色的名字没有相同字、没有谐音、姓氏多样化、长度混合
- [ ] 有邻里生态设计：第三空间、互动模式、社区记忆点
</checklist>
