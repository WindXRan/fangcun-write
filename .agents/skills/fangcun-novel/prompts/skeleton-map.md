---
version: 1
changelog: 骨架映射：分析源文结构，设计新骨架
type: user
phase: skeleton_map
description: 骨架映射（源文章节→新书章节）
required_vars: ["新书名", "源书名", "events_text", "skeleton", "concept"]
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<instructions>
你是仿写架构师。你的任务是分析源文的骨架结构，然后设计新书的章节骨架。

**核心原则：**
- 不是逐章抄作业，而是读懂源文的骨架后，用自己的方式重新搭建
- 砍掉水章、合并过渡章、保留核心章、补充缺失的节奏点
- 新书的节奏应该比源文更紧凑、更有吸引力

**你必须输出 JSON 格式的骨架映射表。**
</instructions>

<concept>
{concept}
</concept>

<skeleton>
{skeleton}
</skeleton>

<events>
{events_text}
</events>

<task>
## 任务

### 第一步：分析源文骨架

读源文的事件表和故事骨架，回答：
1. 源文一共有多少章？
2. 哪些是**核心章**（推动主线、关键转折、高潮）？列出章号
3. 哪些是**过渡章**（承上启下、信息传递）？列出章号
4. 哪些是**水章**（节奏慢、信息密度低、可砍）？列出章号
5. 源文的节奏有什么问题？（如：过渡太长、高潮来得太慢、收尾太急）

### 第二步：设计新骨架

基于分析结果，设计新书的章节结构：
1. **保留核心章**：源文的核心章必须保留，但可以合并相邻的核心章
2. **合并过渡章**：多个过渡章合并为一章（最多5章一组）
3. **砍掉水章**：节奏太慢的章标记为 trim，说明理由
4. **补充节奏点**：如果源文缺少某些节奏点（如：缺少轻松搞笑的调剂章），新增章节
5. **重新分幕**：按新骨架划分幕次，每幕有明确的功能
6. **全覆盖**：每个源文章节都必须出现在某个新章节的 source 中，或标记为 trim。不允许遗漏。

### 第三步：输出 JSON

输出完整的骨架映射表（JSON 格式，见下方格式要求）。
</task>

<output_format>
## 输出格式

先输出分析文字，然后输出 JSON 代码块。

```json
{
  "analysis": {
    "source_chapters": 153,
    "core_chapters": [1, 2, 3, 10, 15, 20, ...],
    "transition_chapters": [4, 5, 11, 12, ...],
    "filler_chapters": [6, 7, 8, ...],
    "pacing_issues": "源文前30章节奏太慢，中间50-80章重复冲突较多"
  },
  "new_structure": {
    "total_chapters": 105,
    "acts": [
      {"act": 1, "name": "身世危机", "chapters": [1, 2, 3, 4, 5], "function": "建立核心矛盾"},
      {"act": 2, "name": "双线作战", "chapters": [6, 7, ...], "function": "矛盾升级"}
    ]
  },
  "chapters": [
    {
      "ch": 1,
      "title": "认亲风波",
      "source": [1, 2],
      "action": "merge",
      "function": "抛出核心矛盾：被抱错的孩子回到亲生家庭"
    },
    {
      "ch": 2,
      "title": "第一顿饭",
      "source": [3],
      "action": "keep",
      "function": "通过吃饭场景展示两个家庭的差异"
    },
    {
      "ch": 3,
      "title": "校园初印象",
      "source": [],
      "action": "new",
      "function": "建立校园线，展示主角在学校的处境"
    }
  ]
}
```

**action 取值：**
- `keep`：源文章节保留（1:1）
- `merge`：多个源文章节合并为一章（合并后目标字数控制在 2000-4000 字）
- `trim`：源文章节砍掉，不写（必须标注 reason）
- `new`：全新设计，源文没有对应
- `merge+trim`：合并后只保留部分内容

**铁律要求：**
1. **源文章节全覆盖**：每个源文章节必须出现在某个新章节的 `source` 数组中，或者有独立的 `trim` 条目。不允许遗漏。
2. **合并字数控制**：合并后的目标字数应在 2000-4000 字。如果源文章节平均 2000 字，最多合并 2 章；如果平均 1000 字，可以合并 3-4 章。根据实际字数灵活判断。
3. **trim 必须有理由**：砍掉的章节必须在 `trim_reasons` 中说明为什么砍。
4. **不要只砍不补**：关键节奏点缺失时要新增章节。

**trim 章节单独列出**（不在 chapters 数组中，而在 trim_reasons 数组中）：
```json
"trim_reasons": [
  {"source": [29], "reason": "纯过渡章，内容可合并到下一章"},
  {"source": [82], "reason": "节奏太慢，信息密度低"}
]
```
</output_format>
