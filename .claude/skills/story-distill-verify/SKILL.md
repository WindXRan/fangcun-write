---
name: story-distill-verify
description: |
  蒸馏验证 · 对已蒸馏的 SKILL.md 进行压力测试、验证和闭环回馈。
  前置条件：已完成 story-distill，生成了 SKILL.md + meta.json。
  输入：.claude/skills/story-style/{作者名}/SKILL.md
  输出：test-prompts.json + 演化日志
trigger:
  - /story-distill-verify
  - /蒸馏验证
  - /验证skill
  - verify skill
---

# story-distill-verify：蒸馏验证

**前置条件**：已完成 story-distill，生成了 SKILL.md + meta.json。

**目的**：对蒸馏结果进行压力测试、验证注册、闭环回馈，确保 SKILL.md 可用且持续改进。

---

## 流程总览

```
Phase 6    压力测试 → test-prompts.json + 回炉
Phase 7    验证注册 → 手动检查 + 确认 story-rewrite 可读取
Phase 8    后蒸馏回馈 → 缺口检测 + 自动修正 + 演化日志 → 闭环到 Phase 0
```

**预计耗时**：10-20 分钟

---

## Phase 6：压力测试

**目的**：验证蒸馏出的决策框架可用，不是纸上谈兵

### 6.1 生成 test-prompts.json

为每个核心决策规则设计 2-3 条测试 prompt，覆盖三类：

| 类型 | 说明 | 示例 |
|------|------|------|
| **应调用** | 该规则明确适用的场景 | 「写一个古言开篇，需要快速建立代入感」 |
| **不应调用（诱饵）** | 看似适用但规则不覆盖的场景 | 「写一个现代都市开篇，需要交代背景」 |
| **边界模糊** | 规则可能适用但需要判断的场景 | 「写一个穿越开篇，需要同时建立代入感和交代背景」 |

### 6.2 本地跑一遍

用 test-prompts 带着 SKILL.md 让 agent 回答，检查：
- 应调用的 → agent 是否正确使用了规则？
- 不应调用的 → agent 是否避免了误用？
- 边界模糊的 → agent 是否给出了合理的边界判断？

### 6.3 回炉标准

| 问题 | 处理 |
|------|------|
| 应调用但没调用 | 规则的 A2（触发场景）不够明确 → 修改 |
| 不应调用但调用了 | 规则的 B（边界）不够清晰 → 修改 |
| 边界模糊判断错误 | 补充边界说明 → 修改 |

**不过的回炉 Phase 4 重做**，不做表面修补。

### 6.3.1 Hill-Climbing 迭代控制

回炉修改后重新评分，分数提升则保留，否则 revert。最多迭代 3 次，连续 2 轮 Δ < 2 分则触顶停止。

### 6.4 输出

写入 `.claude/skills/story-style/{作者名}/test-prompts.json`（darwin-skill 兼容格式）。

### 🔴 CHECKPOINT · Phase 6 → Phase 7

**展示测试结果给用户确认**：

```
压力测试结果：
- 总测试：{N}条
- 通过：{X}条
- 回炉修复：{Y}条
- 最终通过率：{Z}%

确认交付？
```

**等待用户确认后** → 进入 Phase 7。

---

## Phase 7：验证注册

检查 SKILL.md：
- 心智模型 ≥3 个，每个有局限性说明
- 表达DNA 有辨识度
- 诚实边界 ≥3 条
- 内在张力 ≥2 对
- 必要 section 齐全（frontmatter、心智模型、决策启发式、表达DNA、反模式、章纲模板、写作样本）
- story-rewrite 可读取（路径正确、格式正确）

不达标 → 回炉 Phase 4。

---

## Phase 8：后蒸馏回馈

**目的**：每次蒸馏完成后，改进工具链，让下次蒸馏更好。

### 8a：缺口检测

| 缺口类型 | 检测方法 |
|---------|---------|
| 执行缺口 | `references/candidates/` 文件数 vs 应有数（8个） |
| 质量缺口 | Phase 6 失败项追溯根因 |
| 收敛缺口 | `references/rejected/` 中因"信息不足"淘汰的规则数 |

### 8b：自动修正

1. **Extractor prompt 补充**：在对应 `extractors/{name}.md` 末尾追加已知遗漏案例
2. **阈值调整**：根据跨书验证数据动态调整
3. **模块库补充**：发现新特征时创建 `de-ai-modules/{feature-name}.md`

### 8c：演化日志

写入 `{作者名}/references/evolution-log.md`，记录本次蒸馏的缺口、修正和跨蒸馏参考。

---

## 输出结构

```
.claude/skills/story-style/{作者名}/
├── test-prompts.json           # 压力测试（darwin兼容）
├── references/
│   └── evolution-log.md        # Phase 8 演化日志（本次修正+跨蒸馏参考）
```

---

## 蒸馏反例黑名单（不要做的事）

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|---------|
| 7 | **压力测试只测 happy path** | 只测"应调用"场景，无法发现误用边界 | 必须包含"不应调用（诱饵）"和"边界模糊"测试 |
| 9 | **跳过 Phase 8 闭环** | 每次蒸馏不回馈，工具链不会进化 | 必须执行缺口检测+自动修正+演化日志 |
