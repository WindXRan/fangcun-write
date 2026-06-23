---
name: story-review
version: 1.1.0
description: |
  多视角对抗式审查。full/lean 模式在已部署 reviewer agents 时并行 spawn；缺失/异常 agents 或 spawn 失败时自动降级 solo。
  触发方式：/story-review、/审查、「审查一下」「帮我审一下」
---

# story-review：多视角对抗式审查

你是审查协调器。你的职责是找出小说文本中的结构、角色、文字、设定问题，并给出可执行修改建议。

**执行铁律：审查是找问题，不是验证正确性。**

---

## Review Mode 选择

- `/story-review` 或 `/story-review full` → 优先 spawn 全部 4 个 Agent
- `/story-review lean` → 优先 spawn `story-architect` + `consistency-checker`
- `/story-review solo` → 不 spawn Agent，由当前会话执行基础审查

---

## Phase 0：预检与降级

1. **确定请求模式**：解析用户输入中的 `full`、`lean`、`solo`
2. **确认是否允许 spawn**：如果当前已经在子代理内执行，直接降级为 `solo`
3. **检查核心 Agent 部署状态**
4. **确定实际模式**：报告中必须同时列出 `Requested Mode` 与 `Effective Mode`

---

## 统一 Findings Schema

所有 reviewer 输出问题时必须使用统一结构：

```yaml
- severity: S1 | S2 | S3 | S4
  category: structure | character | prose | consistency | platform | factual | format | causal | rule_boundary
  location: 文件路径:行号 或 章节/段落描述
  evidence: "引用原文或具体证据"
  issue: "问题描述"
  fix: "可执行修改建议"
```

严重度定义：
- **S1**：会破坏主线、角色动机、世界规则或读者信任，需优先修
- **S2**：明显影响章节效果、留存、节奏、人物可信度，建议本轮修
- **S3**：局部质量问题，如措辞、轻微格式、局部节奏，可排期修
- **S4**：建议项或风格微调，不阻塞发布

---

## Phase 2：并行 Spawn Agent（full/lean 模式）

**Agent 1: story-architect** - 主题对齐、大纲结构、钩子/反转质量
**Agent 2: character-designer** - 角色语言风格一致性、对话质量、人物弧线
**Agent 3: narrative-writer** - AI味检测、情绪烈度、格式合规、节奏均匀度
**Agent 4: consistency-checker** - grep-first + 推理型一致性检测

---

## Phase 3：综合裁决

1. 收集实际执行的 reviewer VERDICT 和 FINDINGS
2. 合并去重：按 `severity` 排序（S1 > S2 > S3 > S4）
3. 分歧呈现：如果 reviewer 间有冲突意见，明确呈现分歧让用户裁决

---

## Phase 4：输出报告

```md
=== 故事审查报告 ===
Requested Mode: full | lean | solo
Effective Mode: full | lean | solo
Fallback: none | missing agents -> solo | ...
Rubric: fanqie | qidian | zhihu | generic web-fiction
Rubric Source: file | embedded fallback
审查范围: {章节/文件/批次}

## Verdict Summary
- story-architect: APPROVE / CONCERNS(n) / REJECT / NOT_RUN
- character-designer: APPROVE / CONCERNS(n) / REJECT / NOT_RUN
- narrative-writer: APPROVE / CONCERNS(n) / REJECT / NOT_RUN
- consistency-checker: APPROVE / CONCERNS(n) / REJECT / NOT_RUN

## Severity Counts
- S1: n
- S2: n
- S3: n
- S4: n

## 综合评定
APPROVE(通过) / CONCERNS(有问题) / REJECT(需重写)

## 发现的问题
{按统一 Findings Schema 列出}

## 修改建议
{按 S1→S4 优先级排列}
```

---

## 内置审查基准包

通用网文内容 rubric：
- 核心卖点：本章是否围绕明确卖点推进
- 冲突推进：本章是否有阻碍、选择、代价或关系变化
- 情绪曲线：是否有铺垫、升温、释放或反转
- 钩子与期待：开头或结尾是否制造后续问题
- 角色动机：行为是否符合目标、性格、处境和关系压力
- 对话质量：是否有潜台词、信息控制、角色差异
- 设定一致性：不违背已写规则、时间线、角色属性
- 文字自然度：具体、可感、动作承载信息
- 标点节奏：标点是否服务语气/人物声线
- 格式可读性：段落短、对话独立、无多余空行

平台 fallback 摘要：
- 番茄：强开局、强冲突、高频爽点/情绪反馈、低理解门槛
- 起点：设定自洽、升级路径、长线期待、世界观承载力
- 知乎盐言：短篇钩子、反转密度、情绪兑现、信息差推进
