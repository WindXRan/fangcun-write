---
name: story-optimize
description: |
    根据审稿反馈提取通用优化规则，沉淀到prompt里，让每次生成都更好。
    触发条件：用户说「优化prompt」「根据审稿优化」「沉淀规则」。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-optimize（规则沉淀器）

> 把审稿反馈变成通用规则，加到prompt里，让每次生成都更好。

## 工具

| 脚本 | 用途 |
|------|------|
| `tools/auto_optimize.py` | 自动迭代优化：对比→评分→分析问题→优化prompt→重跑 |

### CLI 用法

```bash
# 自动评分 + 优化建议
python .agents/skills/story-optimize/tools/auto_optimize.py --config configs/xxx.json --start 1 --end 10
```

## 流程

```
输入：审稿反馈 / 对比报告 / 用户描述的问题
↓
分析：这个问题是个例还是通用？
↓
提取：如果通用，提取成一条可执行规则
↓
沉淀：加到对应prompt里（plot-guide/style-guide/open-book）
↓
效果：后续每次生成都自动应用这条规则
```

## 规则沉淀原则

1. **只沉淀通用规则**：个例问题不沉淀，通用问题才沉淀
2. **规则必须可执行**：不说"节奏要快"，说"禁止连续2章纯日常"
3. **规则必须可验证**：写完能对着正文逐条打勾
4. **规则必须有正反例**：✅ 怎么做 / ❌ 不能做
5. **🔴 提示词精准原则**：能用一句话说清楚的，不用三句话。提示词不是越多越好，而是越精准越好。冗余的提示词会稀释重点，降低执行效果。

## 问题→规则映射

| 审稿反馈 | 通用规则 | 沉淀到 |
|---------|---------|-------|
| 节奏太慢 | 禁止连续2章纯日常 | plot-guide |
| 人设无记忆点 | 男主必须有钩子人设 | plot-guide |
| 开篇无吸引力 | 前3章必须完成核心悬念 | plot-guide |
| 省略号太多 | 省略号≤3个/章 | style-guide |
| AI味太重 | 禁止直抒情词/AI路标词 | style-guide |
| 简介质量差 | 简介必须有悬念+情感张力 | open-book |
| 人名不对 | 禁用字清单 | open-book |

## 使用方式

用户说「优化prompt」时：
1. 读取最近的审稿反馈或对比报告
2. 判断哪些问题是通用的
3. 提取成可执行规则
4. 沉淀到对应prompt
5. 提交git

## 输出

修改对应的prompt文件，提交到git。
