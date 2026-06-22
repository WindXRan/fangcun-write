---
name: fangcun-novel
version: 3.0.0
description: |
  小说仿写引擎。从源文生成新书：源文分析 → 章纲 → 写章 → 对比审核。
  触发方式：「仿写这本书」「帮我仿写XX」「写第N章」「继续写」
metadata:
  author: fangcun-team
  pipeline: source → guides → write → compare
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(mkdir *) Bash(rm *)
---

# fangcun-novel：小说仿写引擎

## 核心方法

**换壳保骨**：保留源文的情绪弧线和叙事骨架，换掉人名、地名、具体情节。

### 三层架构

```
style-analyze（文笔层）    → 提取源文写法特征
plot-guide（结构层）       → 生成功能需求清单
write-chapter（执行层）    → 按功能需求写全新内容
```

### 职责分离

| 层 | 负责什么 | 不负责什么 |
|----|----------|------------|
| style-analyze | 句长、对话比、写法指令 | 具体场景设计 |
| plot-guide | 情绪功能、冲突升级、信息流 | 具体怎么实现 |
| write-chapter | 按功能需求写全新内容 | 改变骨架结构 |

---

## 快速开始

### 1. 安装

```powershell
.\setup.ps1
```

### 2. 设置 API Key

```powershell
$env:API_KEY = "sk-xxx"
```

### 3. 创建配置

```powershell
# 复制示例配置
copy configs\example.json configs\mybook.json

# 编辑配置（填入作者名、源书名、新书名）
notepad configs\mybook.json
```

### 4. 开始仿写

```powershell
# 写前 10 章
.\novel.ps1 write --config configs\mybook.json --start 1 --end 10

# 查看状态
.\novel.ps1 status --config configs\mybook.json

# 对比审核
.\novel.ps1 compare --config configs\mybook.json --start 1 --end 10
```

---

## 流程详解

### Phase 1: 源文分析

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase source
```

产物：
- `_cache/events.json` — 事件表
- `_cache/story_skeleton.md` — 故事骨架
- `_cache/styles/style_{N}.md` — 文笔指纹

### Phase 2: 章纲生成

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase guides --start 1 --end {N}
```

产物：
- `guides/plot_{N}.md` — 功能需求清单

### Phase 3: 写章（含自动 trim）

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase write --start 1 --end {N}
```

产物：
- `chapters/ch_{N}.txt` — 正文

### Phase 4: 对比审核

```bash
python .agents/skills/fangcun-novel/tools/pipeline.py --config {config} --phase compare --start 1 --end {N}
```

产物：
- `compare/对比_{start}-{end}_报告.md` — 基础统计
- `compare/审核报告_{start}-{end}.md` — 审核结果
- `compare/改动报告_{start}-{end}.md` — 换皮评分

---

## 配置文件

```json
{
  "book_name": "新书名",
  "author": "作者名",
  "source_book": "源书名",
  "rewrites_dir": "projects/作者/源书名/rewrites/新书名",
  "model": "deepseek-v4-pro",
  "workers": 10,
  "skip_confirm": true
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| book_name | 否 | 新书名，"auto" = 自动起名 |
| author | 是 | 源文作者名 |
| source_book | 是 | 源文书名 |
| rewrites_dir | 是 | 输出目录 |
| model | 否 | 模型名 |
| workers | 否 | 并行数 |
| skip_confirm | 否 | 跳过确认 |

---

## 角色设定

角色卡在 `characters.md`，保留源文角色名：

```markdown
【角色名】（源文对应：源文角色名）
- 功能位：女主
- 性格内核：...
- 核心动机：...
- 关系：...
```

---

## 字数控制

- 目标：源文字数 ±10%
- 超 3000 字自动 trim
- trim 在写章时自动执行，无需手动调用

---

## 质量检查

### 自动检查

- 字数偏差 ±15%
- 角色名无泄漏
- 台词重复 0%
- AI 痕迹在合理范围

### 手动检查

```powershell
# 对比报告
.\novel.ps1 compare --config configs\mybook.json --start 1 --end 10

# 审核报告
.\novel.ps1 review --config configs\mybook.json --start 1 --end 10
```

---

## 常见问题

### Q: API Key 错误

```
$env:API_KEY = "sk-xxx"
```

### Q: 某章写得不好，重写

```powershell
# 删除该章
Remove-Item chapters\ch_003.txt

# 重写
.\novel.ps1 write --config configs\mybook.json --start 3 --end 3
```

### Q: 角色名不对

编辑 `characters.md`，然后重跑受影响的章节。

### Q: 字数超标

trim 会自动执行。如果还是超，重跑该章即可。

---

## 文件结构

```
projects/{作者}/{源书名}/
├── _cache/                    ← 源书级产物
│   ├── chapters/              ← 源文拆章
│   ├── events.json            ← 事件表
│   ├── story_skeleton.md      ← 故事骨架
│   └── styles/                ← 文笔指纹
└── rewrites/{新书名}/         ← 仿写产物
    ├── concept.md             ← 设定
    ├── characters.md          ← 角色映射表
    ├── guides/plot_{N}.md     ← 章纲
    ├── chapters/ch_{N}.txt    ← 正文
    └── compare/               ← 对比报告
```

---

## Prompt 文件

| 文件 | 用途 |
|------|------|
| `style-analyze.md` | 提取源文写法特征 |
| `plot-guide.md` | 生成功能需求清单 |
| `write-chapter.md` | 按功能需求写章 |
| `trim-chapter.md` | 精简超字数章 |
| `expand-chapter.md` | 扩写不足字数章 |
| `polish-chapter.md` | 润色章节 |
