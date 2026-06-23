---
version: 50
changelog: 文件引用模式，不依赖代码注入
type: task
phase: guides
description: 章纲生成
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
为《{新书名}》第{N}章生成场景级章纲。

**第一步：读源文，只提取功能**
- 本章释放了什么信息？（只写功能层面，不写具体机制）
- 本章在全书中的功能是什么？
- 禁止提取：核心事件、冲突原因、标志性道具/台词

**第二步：合上源文，闭卷设计**
- 基于功能描述，自主设计完全原创的事件
- 事件的触发原因、冲突方式、收尾方式必须与源文完全不同
- 自检：把人名换成【A】【B】，读者能否判断是哪本书？能则重写

**第三步：输出章纲**
按输出格式输出，完成自检表。
</task>

<event>
{event}
</event>

<characters>
{characters}
</characters>

<blacklist>
{blacklist}
</blacklist>

<world>
{world}
</world>

<output_format>
## 输出格式

### 本章功能
{一句话}

### 本章释放的信息
- 信息1：{...}
- 信息2：{...}

### 场景设计
#### 场景1：{场景名}
- 地点/人物/事件/关键台词/情绪

### 人设落地（至少2处）

### 原创名场面
- 描述/记忆点

### 结尾方式
- 最后一句：{具体台词或动作}
</output_format>
