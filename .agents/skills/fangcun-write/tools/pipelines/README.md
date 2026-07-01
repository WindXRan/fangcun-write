# 管线目录

每个管线定义一组按顺序执行的工具调用，完成一个独立的工作阶段。

## 核心规则（严格执行）

**所有写章操作必须先有三纲。** 总纲/卷纲/章纲缺一不可，不存在跳过三纲直接写的情况。

| 类型 | 三纲来源 | 写章工具 | 输出路径 |
|------|---------|---------|---------|
| **重写** | source-guide-reverse（从原文逆推） | write-chapter | `三纲逆推/正文/` |
| **仿写** | open-book（从源书生成新书框架）+ source-guide-reverse | fanxie-chapter | `正文/正文/` |

**重写流程：** 如果项目没有三纲 → 先跑拆书管线。如果有三纲 → source-guide-reverse（每章节纲）→ write-chapter

**仿写流程：** 如果项目没有 open-book 产物（总纲/角色卡/卷纲） → 先跑 open-book。如果有 → source-guide-reverse（从源文章纲）→ fanxie-chapter

## 管线一览

| 管线 | 阶段 | 工具 | 用途 |
|------|------|------|------|
| [拆书管线](拆书管线.md) | 逆向拆书 | character-extract → golden-chapters → book-import → skeleton → style-analysis → setting-extract → relationship-extract → analysis-report | 把源书拆成结构化数据 |
| [outline-build](outline-build.md) | 仿写搭建 | open-book → volume-outline → plot-guide | 从逆向结果生成新书框架 |
| [chapter-write](chapter-write.md) | 正文写作 | write-chapter / fanxie-chapter（每章循环） | 按章纲写正文 |
| [逆推法管线](逆推法管线.md) | 逆推法 | checker → compare（迭代循环） | 原文→三纲→逆推正文，验证prompt质量 |

## 调用方式

每个管线是 markdown 文档，**不是可执行脚本**。AI 读管线文档然后依次调 `run_tool()`。

```python
from tool_executor import run_tool
run_tool("character-extract", {"workers": 5}, "/path/to/project")
```

## 阶段总图

```
拆书管线（原文→结构化数据）
     ↓
open-book（仿写）或 source-guide-reverse（重写）→ 三纲就绪
     ↓
write-chapter（重写）/ fanxie-chapter（仿写）→ 正文
```

## 数据结构

```
三纲包含：
  总纲 — 全书框架、设定、节奏、人设支撑点
  卷纲 — 本章在全卷的节奏位置
  章纲 — 本章指令：info_release（释放什么）、info_hold（压住什么）、writing_style（写法参考）

原始XML注入 — 总纲/卷纲/章纲 都以原始XML结构传递，不扁平化。
```
