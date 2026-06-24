---
version: 1
changelog: 从源文章纲 × 新书设定 → 生成新书章纲（换皮不换骨）
type: task
phase: chapter-map
description: 章纲映射生成
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.6}
---

<task>
为《{新书名}》第{start}-{end}章生成章纲。换皮不换骨。

**输入**：源文 events.json（左）和新书 concept.md（右）。你需要对每一章做骨架对齐——事件数对齐、角色位对齐、情绪弧线对齐，但场景/地点/具体事件全部换掉。

## 规则

### 换什么（皮）
- 地点、职业、具体台词、具体情节
- 源文"面馆怒怼上司" → 新书"外卖站怒怼站长" 或 "4S店怒怼经理"
- 源文"美容院" → 新书根据 concept.md 换圈子

### 不换什么（骨）
- 事件数量：源文几个场景 → 新书几个场景
- 角色位：源文 3 个角色位（主角/羞辱者/帮衬）→ 新书同样 3 个
- 信息释放节奏：源文释放 X、藏着 Y → 新书同样
- 情绪弧线：完全对齐

### 核心约束（concept.md 提取）
{贯穿目标}

### 输出格式
每章一行 events.json 条目（JSON数组）：
```json
[{
  "id": "1",
  "核心事件": "一句话概括本章新事件（区别于源文）",
  "开头承接": "冷开：新场景开头 或 承：接上章结尾",
  "结尾状态": "本章收束时的状态",
  "衔接": "→ 下章推动力",
  "情绪弧线": "压抑→爆发→轻松",
  "涉及角色": "新名1,新名2"
}]
```
</task>

<chapter_map_source>
【源文章纲】events.json 第{start}-{end}章条目：
{source_events}
</chapter_map_source>

<name_map>
{name_map}
</name_map>

<concept>
{concept}

{characters_context}
</concept>
