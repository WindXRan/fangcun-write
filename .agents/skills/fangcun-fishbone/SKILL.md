---
name: fangcun-fishbone
version: 1.0.0
description: |
  鱼骨式设定提取器。扫描源文全书→提取所有角色/地点/物品/势力/背景→并行生成结构化设定文件。
  用法：/fangcun-fishbone --source 全家偷听心声 --target 仿写新书
---

# fangcun-fishbone 鱼骨式设定提取

## 核心逻辑

扫描源文全书章纲，找出所有设定元素（角色/地点/物品/势力/背景），然后并行生成结构化设定文件。

```
主线扫描（一次）                   骨头填充（并行 agent）
─────────────────                  ─────────────────────────
扫全书章纲
  ├─ 找出所有角色名         → agent: 生成角色卡（完整 voice）
  ├─ 找出所有地点           → agent: 生成地点（环境+氛围）
  ├─ 找出所有物品/系统      → agent: 生成物品（规则+数值）
  ├─ 找出所有势力           → agent: 生成势力（成员+目标）
  └─ 找出所有背景概念       → agent: 生成世界观（规则+历史）
```

---

## 用户说

| 你说 | 我做 |
|------|------|
| `/fangcun-fishbone --source 全家偷听心声 --target 仿写新书` | 扫描源文全书，自动提取并生成所有设定文件 |

---

## 工作流程

### Step 1：主线扫描

扫描源文项目 `正文/章纲/` 下所有章纲文件，提取：

- **角色**：所有 `<character name="...">` 中出现的名字
- **地点**：所有 `<location>` 中出现的名称
- **物品**：所有 `<items_used>` 中出现的名称
- **势力**：正文中提到但未在章纲中标注的阵营
- **背景概念**：总纲中提到的世界观规则

### Step 2：去重 + 分类

将提取到的元素去重，按类别分组，过滤掉目标项目已有的设定文件。

### Step 3：并行生成设定骨头

对每个缺失的设定，启动独立 agent 读取源文全文生成结构化数据：

| 类型 | 输出文件 | 关键字段 |
|------|---------|---------|
| 角色 | `设定/角色/{名}.xml` | voice（口癖/OS风格/语气）, background, motivation, arc |
| 地点 | `设定/地点/{名}.xml` | description, atmosphere, layout |
| 物品 | `设定/物品/{名}.xml` | effect, cost, rules, limitations |
| 势力 | `设定/势力/{名}.xml` | members, goals, resources |
| 背景 | `设定/背景/{名}.xml` | world_rules, time_period, history |

### Step 4：生成关系图谱

扫描所有角色间的互动，输出 `设定/关系图谱.xml`。

---

## 输入来源

- 源文项目：`projects/{source}/正文/章纲/`（所有 XML 文件）
- 源文总纲：`projects/{source}/作品信息/主题/总纲`
- 目标项目已有设定：`projects/{target}/作品信息/设定/`

## 输出

- `projects/{target}/作品信息/设定/角色/*.xml`
- `projects/{target}/作品信息/设定/地点/*.xml`
- `projects/{target}/作品信息/设定/物品/*.xml`
- `projects/{target}/作品信息/设定/势力/*.xml`
- `projects/{target}/作品信息/设定/背景/*.xml`
- `projects/{target}/作品信息/设定/关系图谱.xml`
