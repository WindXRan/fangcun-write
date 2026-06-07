---
name: story-engine
description: |
    仿写引擎 v4：开书→写章。写章agent四步：读源文感受情绪→读节奏数据→读情绪节拍表→用Completion Prompting写。
    知识图谱追踪角色状态（Limited Cognition：每章只看相关节点）。
    触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
    不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-engine v4

> 情绪驱动 + 知识图谱 + Completion Prompting + Limited Cognition

## 文件结构

```
仿写/{新书名}/
├── 设定/
│   ├── 新书设定.md（书名+类型+卖点+人设+NPC映射+世界观+简介）
│   └── 全书弧线.md（情绪曲线+角色成长+伏笔+章节映射）
├── 追踪/
│   └── graph.json（知识图谱：角色节点+事件节点+情绪影响）
└── 正文/第N章.txt
```

## Pipeline

```
开书(2 agents串行) → 写章(10 agents × N批) → 批后处理(Scorer+知识图谱更新)
```

## 开书编排

### Step 1：创建项目目录

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <新书名>
```

### Step 2：开书（2 agents 串行）

| 顺序 | Agent | Prompt | 输出 |
|------|-------|--------|------|
| 1 | A1：新书设定 | `prompts/arc-concept.md` | `设定/新书设定.md` |
| 2 | A2：全书弧线 | `prompts/arc-skeleton-core.md` | `设定/全书弧线.md` + `追踪/graph.json` |

### Step 3：生成源文节奏数据

```bash
python .agents/skills/story-engine/tools/calc_style_profile.py <源文路径> -o <输出路径>
```

输出：句长/对话占比/段长/句首分布/词频TOP20 + 情绪节拍表

### Step 4：写章（10 agents × N批）

每个写章 agent 的工作流：

```
1. 读源文第N章（感受情绪曲线）
2. 读节奏数据（句长/对话占比/段长/句首分布/词频TOP20）
3. 读情绪节拍表（每段的情绪类型+强度+写章指令）
4. 读知识图谱（Limited Cognition：只看本章相关角色节点）
5. 用 Completion Prompting 格式写：
   - 不用"写第N章"，用"从这段续写：[上一章最后200字]"
   - 风格迁移效果提升23.5倍
6. 写完自检：句长误差≤±2字，对话比例差≤±3%
7. 输出：第N章.txt + 状态变更
```

⛔ **一次出稿。不校验，不重写。**

### Step 5：批后处理

| 检查项 | 说明 |
|--------|------|
| Scorer Agent | 对本批10章评分（连贯/创造/共情/意外/复杂/沉浸） |
| 知识图谱更新 | 根据状态变更更新 graph.json |
| 冲突检测 | 角色位置/关系阶段/伏笔状态矛盾 |

### Step 6：导出

```bash
cat 仿写/{新书名}/正文/*.txt > 仿写/{新书名}/{新书名}.txt
```

## 关键技术

| 技术 | 来源 | 效果 |
|------|------|------|
| 知识图谱 | CreAgentive (2509.26461) | 2770章质量稳定不衰减 |
| Limited Cognition | CreAgentive | 消除全知视角，角色行为更真实 |
| Completion Prompting | 风格迁移研究 | 风格模仿效果提升23.5倍 |
| 情绪节拍表 | 我们的实践+认知语言学 | 补Immersion缺口（-1.8→0） |
| 节奏数据对齐 | StoryScope (2604.03136) | 叙事特征检测93.2%→对齐源文分布 |
