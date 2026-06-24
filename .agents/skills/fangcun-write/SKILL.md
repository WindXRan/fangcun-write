---
name: fangcun-write
version: 4.0.0
description: |
  方寸长篇写作引擎。支持章对章仿写和续写两种模式。
  触发方式：/fangcun-write、/仿写、/写章、「仿写这本书」「帮我仿写XX」「写第N章」「继续写」
metadata:
  author: fangcun-team
  pipeline: source → guides → write → compare
---

# fangcun-write：方寸长篇写作引擎

## 核心方法

### 仿写模式（章对章）

**换壳保骨**：保留源文的情绪弧线和叙事骨架，换掉人名、地名、具体情节。

```
源文分析 → 事件提取 → 章纲生成 → 逐章写作 → 对比审核
```

### 续写模式

**延续原作**：保留原作核心要素，自由创作新内容。

```
状态提取 → 大纲生成 → 逐章写作 → 质量审核
```

---

## 快速开始

### 1. 设置 API Key

```powershell
$env:API_KEY = "sk-xxx"
```

### 2. 创建配置

```json
{
  "book_name": "新书名",
  "author": "作者名",
  "source_book": "源书名",
  "rewrites_dir": "projects/作者/源书名/rewrites/新书名",
  "model": "deepseek-chat",
  "execution_mode": "api"
}
```

### 3. 开始写作

```powershell
# 完整流程
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/mybook.json --phase all

# 分步执行
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/mybook.json --phase open-book
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/mybook.json --phase guides --start 1 --end 10
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/mybook.json --phase write --start 1 --end 10
```

---

## 流程详解

### Phase 1: 开书（open-book）

生成设定文件：
- `concept.md` — 设定+角色+弧线
- `characters.md` — 角色名映射表（XML格式）
- `world.md` — 世界观设定
- `book_info.md` — 书名+简介

### Phase 2: 章纲生成（guides）

为每章生成功能需求清单：
- 本章释放的信息
- 场景设计
- 人设落地
- 原创名场面
- 结尾方式

### Phase 3: 写章（write）

按章纲逐章写作：
- 目标字数：源文字数 ±10%
- 角色名自动映射
- 超字数自动 trim

### Phase 4: 对比审核（compare）

生成对比报告：
- 基础统计（字数、段落、对话比例）
- 风格指纹（句长、标点、词汇）
- AI痕迹检测
- 换皮评分

---

## 角色名映射

仿写会自动替换角色名。映射表在 `characters.md`（XML格式）：

```xml
<角色名>
- 功能位：主角
- 性格内核：...
- 核心动机：...
- 口头禅/标志性台词：...
- 关系：...
</角色名>
```

---

## 字数控制

- 目标：源文字数 ±10%
- 超 3000 字自动 trim
- trim 在写章时自动执行

---

## 路由表

| 用户说 | 调用 | 命令 |
|--------|------|------|
| "继续写" / "写下一章" | write | `--phase write --start {N} --end {M}` |
| "写第N章" | write | `--phase write --start {N} --end {N}` |
| "看看对比" / "质量怎么样" | compare | `--phase compare --start {N} --end {M}` |
| "第X章字数不对" | postfix | `--phase postfix --start {X} --end {X}` |
| "第X章重写" | 删章 + write | 删 `ch_{X}.txt`，再跑 write |
| "审一下" / "检查问题" | review | `/审查` (story-review) |
| "修一下" / "修复问题" | fix | 根据审查报告手动修，或 `/去AI味` |
| "开书" / "仿写这本书" | open-book | `--phase open-book` |

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
    ├── characters.md          ← 角色映射表（XML格式）
    ├── guides/plot_{N}.md     ← 章纲
    ├── chapters/ch_{N}.txt    ← 正文
    └── compare/               ← 对比报告
```

---

## Prompt 文件

| 文件 | 用途 |
|------|------|
| `plot-guide.md` | 生成功能需求清单 |
| `write-chapter.md` | 按功能需求写章 |
| `agent.md` | 系统提示词（全局缓存） |
