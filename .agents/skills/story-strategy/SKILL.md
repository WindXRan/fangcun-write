---
name: story-strategy
description: |
  源文叙事策略分析：排除项+节奏骨架+叙事策略。
  输出 strategy_guide_N.md。
  触发条件：「分析叙事策略」「跑策略分析」「提取叙事策略」。
  依赖 phase0-style 产出的源文章节文件。可与 phase0-style 并行运行。
allowed-tools: Bash(python *) Bash(ls *) Bash(mkdir *)
shell: powershell
---

# story-strategy

> 源文叙事策略分析，可缓存。

## 前置依赖

需要 `novel-download-authors/{作者名}/{源书名}/源文/` 目录下有拆章后的章节文件。
如果没有，先运行 `/story-style` 拆章。

## 输出

```
novel-download-authors/{作者名}/{源书名}/
└── 蒸馏/mode-b/
    └── strategy_guide_N.md    # 排除项+节奏骨架+叙事策略
```

## 流程

### 叙事策略提取（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。**

Task prompt 见 [prompts/strategy-guide-task.md](prompts/strategy-guide-task.md)。输出保存到 `strategy_guide_N.md`。

## 缓存策略

- `strategy_guide_*.md` 齐全 → 跳过
- 抽检3个：排除项≥2个？节奏骨架有数值？叙事策略5子维度非空？
- 不合格 → 重跑该章
- 手动刷新 → 删除 `strategy_guide_*.md`
