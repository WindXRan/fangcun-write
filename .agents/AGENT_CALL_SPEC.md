# Agent 发射决策与模板（统一参考）

所有 skill 共用此规范。skill 内不重复写，引用本文件即可。

---

## 决策树（4 步检查）

spawn 前按顺序检查，任一失败则降级主线程执行：

| 步骤 | 检查项 | 失败时 Fallback |
|------|--------|----------------|
| 1 | 当前不在子 agent 内 | `subagent recursion guard -> solo` |
| 2 | Agent/Task 工具可用 | `agent tool unavailable -> solo` |
| 3 | `.claude/agents/{type}.md` 存在且 frontmatter 正常 | `missing agents -> solo` |
| 4 | `.story-deployed` 存在且 `agents_version` >= 12 | `stale agents -> solo` |

---

## 调用模板（模板 + 替换）

```python
Agent(
  subagent_type: "{agent_type}",
  prompt: """项目目录：{dir}
任务描述：{task}
{其他字段，按场景拼接}"""
)
```

### 通用字段

| 字段 | 必填 | 替换为 |
|------|------|--------|
| `项目目录` | ✅ | 项目根目录绝对路径 |
| `任务描述` | ✅ | 一句话：写正文 / 架构审查 / 一致性审查 / 去AI味 / ... |

### 场景字段（按需拼接）

| 场景 | 拼接字段 |
|------|----------|
| 写章 | `章节` / `细纲文件` / `上一章` / `情绪目标` / `涉及角色` / `参考技法` / `格式硬约束` / `写作硬约束` |
| 审查 | `审查范围` / `审查基准包摘要` / `Rubric Source` / `检查项` |
| 一致性 | `审查范围` / `已知角色` / `检查项` |
| 去AI味 | `检查范围` / `AI味等级` / `处理策略` |
| 角色设计 | `查询参数` |

---

## 各 skill 的 Agent 调用点

| Skill | 调用点 | Agent 类型 | 前置条件 |
|-------|--------|-----------|----------|
| story-long-write | Phase 4 写章 | narrative-writer | agent 已部署 |
| story-long-write | Phase 4 上下文 | story-explorer | agent 已部署 |
| story-long-write | Phase 5 审查 | consistency-checker | agent 已部署 |
| story-long-analyze | Stage 2 逐章摘要 | chapter-extractor | agent 已部署 |
| story-short-write | Phase 3 写章 | narrative-writer | 用户要求/上下文不足 |
| story-short-write | Phase 4 精修 | narrative-writer + consistency-checker | agent 已部署 |
| story-review | Phase 2 审查 | story-architect / character-designer / narrative-writer / consistency-checker | full/lean 模式 |
| story-deslop | Phase 3 去AI味 | narrative-writer | agent 已部署 |

---

## 批量策略

- 每次 spawn 5-8 个 agent（避免并发限制）
- 等待当前批次完成后再 spawn 下一批
- 每批完成后更新进度

## 失败处理

1. 执行失败（crash/超时/空输出）→ 同模型重试 1 次
2. 质量失败 → 升级模型重试 1 次
3. 最终失败 → 标记跳过，记录到进度文件
