# AI网文小说项目 — 写作引擎

## 核心原则

**优化 workflow，不修单章。** Pipeline 自检返修，0 人工。

防线上移：
- 章纲 (events.json) 锁死每章骨架——事件数、角色位、开头承接、结尾状态、衔接
- 冲突类型强制换（身份→利益/信息差/道德）
- 台词 0 重合（6 字以上连续匹配 = S1 重写）
- 换皮检验：剥掉人名地名，认不出源文 = 合格

## 三层骨架

```
大纲.md        → 卷级：分几卷、每卷功能
events.json    → 章级：每章核心事件 / 开头承接 / 结尾状态 / 衔接 / 情绪弧线 / 涉及角色
plot_{N}.md    → 段级：长格式细纲（五段式+多线+情节点+钩子）
```

events.json 是唯一章纲，拆文库产、pipeline 读、人看表格。不再有独立的章纲.md。

## Pipeline

```
prep → source-analysis → open-book → chapter-map → guides → write → postfix → compare
```

| 阶段 | 功能 | 产物 |
|------|------|------|
| prep | 提取元数据 | _header.txt, _toc.txt（优先拆文库） |
| source-analysis | 事件/骨架/改编 | events.json, story_skeleton.md, adaptation_strategy.md（写入拆文库） |
| open-book | 生成新书设定 | concept.md, characters.md, world.md, book_info.md |
| chapter-map | 源文章纲 → 新书章纲（LLM换皮） | rewrites/events.json（每 10 章一批，全并行） |
| guides | 章纲 → 细纲 | guides/plot_{N}.md |
| write | 细纲 → 正文 | chapters/ch_{N}.txt |
| postfix | trim/expand | 修正字数偏差 |
| compare | 章对章仿写诊断 | compare/ 报告（S1-S4 × pipeline 根因） |

## 文件结构

```
拆文库/{书名}/                  ← 唯一数据源，替代 _cache
├── events.json                  ← 章纲（12字段：event管道 + 结构化字段）
├── 概要.md / 拆文报告.md / 文风分析.md
├── 原文/ / 章节/ / 角色/ / 剧情/ / 设定/

projects/{作者}/{源书名}/
├── _cache/                      ← 仅回退路径，拆文库存在时不需
└── rewrites/{新书名}/
    ├── events.json              ← 新书章纲（chapter-map 产出）
    ├── concept.md / characters.md / world.md / book_info.md
    ├── guides/plot_{N}.md       ← 细纲
    ├── chapters/ch_{N}.txt      ← 正文
    └── compare/                  ← 对比诊断报告
```

## 拆文库检测

pipeline 启动时自动检测 `拆文库/{源书名}/`。存在则：
- `load_events` 从拆文库读
- `get_source_text` 从拆文库 `章节/` 读
- system prompt 从拆文库 `文风分析.md` 读
- `_cache/` 全部数据优先回退拆文库

## 使用

```bash
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase all
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase open-book
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase chapter-map
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase guides --start 1 --end 192
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase write --start 1 --end 192
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --phase compare --start 1 --end 10
python .agents/skills/fangcun-write/tools/pipeline.py --config configs/xxx.json --status
```

## 模型策略

全用 `deepseek-chat`（reasoning_effort=low）。

## Prompt 修改原则

- 先提方案再动手，分段确认
- 通用性：prompt 不加具体书名/人名，变量注入
- 职责分离：write 写，compare 查
- 改完自查：placeholder 全替换、逻辑无矛盾
