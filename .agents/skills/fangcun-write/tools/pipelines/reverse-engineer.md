# 逆向拆书管线

**目标：** 把源书正文拆成结构化数据（事件表/总纲/骨架/文风指纹/改编策略）
**输入：** `projects/{author}/{book}/正文/正文/` 下有章节文件
**产出：** events.json + 作品信息/主题/*.xml + 故事骨架.md + 拆文库/文风.md + 改编策略.md
**入口：** `run_tool("工具名", {参数}, project_dir)`

---

## Step 1: 提取事件

从每章正文提取事件摘要，存入 events.json。

```
run_tool("character-extract", {
  "workers": 5,       # 并行数
  "source_dir": ""    # 源文目录，空则用 project_dir
}, project_dir)
```

**耗时：** 192 章约 5-10 分钟（workers=5）
**产出：** `events.json`（每章一条：{id, chapter_index, chapter, event}）
**成功标准：** events.json 中有 `total` = 总章数，且 `event` 非空条目 ≥ 90%

---

## Step 2: 导入总纲/简介/标签

读取前三章正文 + 事件表 → 生成总纲/简介/标签。

```
run_tool("book-import", {}, project_dir)
```

**变量依赖：**
- `@故事名称` → 自动从 `project.xml` 读取
- `@作品信息/事件表` → 上一步 events.json
- `@模板_总纲` → `schemas/story.schema.xml`

**产出：**
- `作品信息/主题/总纲.xml` — 故事元素/金手指/故事线/故事大纲
- `作品信息/主题/简介.xml` — 简介文案
- `作品信息/主题/标签.xml` — 四维标签

**成功标准：** 三个文件都存在，内容非空

---

## Step 3: 故事骨架

从事件表分析故事结构，生成三幕/起承转合+冲突升级节奏。

```
run_tool("skeleton", {}, project_dir)
```

**变量依赖：**
- `@总章数` → 运行时传入

**产出：** `故事骨架.md` — 结构总览/冲突升级节奏/情绪弧线/关键转折点

**成功标准：** 已产出，包含章节分段标记

---

## Step 4: 文风分析

采样前三章+随机五章，分析句长/对话比例/段落节奏/情绪交替周期/钩子类型。

```
run_tool("style-analysis", {}, project_dir)
```

**变量依赖：**
- `@本章正文` → 自动读取前三章
- `@前文` → 随机五章正文

**产出：** `拆文库/文风.md` — 句长分布/标点习惯/对话比例/段落节奏/情绪交替周期/原文锚点

**成功标准：** 已产出，包含可量化的风格参数

---

## Step 5: 改编策略

从故事骨架制定换皮方案+爽点内核+卖点+禁区。

```
run_tool("adaptation", {}, project_dir)
```

**变量依赖：**
- 上一步产出的故事骨架.md

**产出：** `改编策略.md` — 爽点内核/换皮方向/核心卖点/禁区

**成功标准：** 已产出，包含具体的换皮方案

---

## 完成标记

所有 5 步完成后，在项目根创建标记文件：

```python
Path(project_dir / "_cache" / "reverse_engineer_done").touch()
```

下次可以跳过已完成的步骤，从 `outline-build` 管线开始。
