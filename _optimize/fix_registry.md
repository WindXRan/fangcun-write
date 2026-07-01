# 补丁注册表

**用途**：追踪每个补丁从"提出→应用→验证→解决"的完整生命周期。
**原则**：
- 每条补丁有唯一 ID，按类型编号
- 补丁的"应用"标准是**实际写入了目标文件**（不是写了 prompt_patch.md 方案描述）
- 补丁的"解决"标准是**验证有效**（compare 报告中该维度追平或接近原文）

---

## 快速总览

| # | 补丁 | 目标 | 状态 | 提出轮次 | 应用轮次 | 验证轮次 | 当前效果 |
|---|------|------|:----:|:--------:|:--------:|:--------:|---------|
| CH-001 | MC口癖强制对齐 | fanxie-chapter.md | ✅ solved | R1 | R4 | ⏳ 待R5验证 | R4应用，效果待确认 |
| CH-002 | 章尾钩子硬约束 | fanxie-chapter.md | ✅ solved | R1 | R4 | ⏳ 待R5验证 | 同上 |
| CH-003 | 重复咆哮限制 | fanxie-chapter.md | 🟡 indirect | R1 | — | — | 被CH-007间接覆盖 |
| CH-004 | 信息释放节奏三段 | fanxie-chapter.md | 🟡 indirect | R1 | — | — | 已有表格约束 |
| CH-005 | 心声格式硬约束 | fanxie-chapter.md | 🟡 indirect | R1 | — | — | 被CH-012间接覆盖 |
| CH-006 | 网文基调控 | fanxie-chapter.md | 🔴 pending | R1 | 未应用 | — | 待独立应用 |
| CH-007 | OS留白控制 | fanxie-chapter.md | ✅ solved | R3 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-008 | 呼吸空间约束 | fanxie-chapter.md | ✅ solved | R3 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-009 | 禁止逐字复制 | fanxie-chapter.md | ✅ solved | R2 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-010 | 微节奏保留 | fanxie-chapter.md | ✅ solved | R2 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-011 | 开场硬约束(前3行) | fanxie-chapter.md | ✅ solved | R4 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-012 | 母亲信任压缩 | fanxie-chapter.md | ✅ solved | R4 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-013 | 禁止单段信息dump | fanxie-chapter.md | ✅ solved | R4 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-014 | 系统展示压缩 | fanxie-chapter.md | ✅ solved | R4 | R4 | ⏳ 待R5验证 | R4应用 |
| CH-015 | 情感弧线画面支撑 | fanxie-chapter.md | ✅ solved | R4 | R4 | ⏳ 待R5验证 | R4应用 |
| PT-001 | 模式卡新增protagonist_voice | fanxie-pattern.md | 🔴 pending | R1 | 未应用 | — | 待应用 |
| SC-001 | 总纲金手指字段扩展 | story.schema.xml | 🔴 pending | R1 | 未应用 | — | 待应用 |
| SR-001 | 开场模式参考.xml数据 | 作品信息/设定/ | ✅ solved | R4 | R4 | — | 结构化数据 |
| VR-001 | @设定聚合变量增强 | variable_resolver.py | ✅ solved | R4 | R4 | — | 变量解析器 |

---

## 补丁详情

### CH-001 — MC口癖强制对齐

| 字段 | 内容 |
|------|------|
| 提出轮次 | R1 补丁A |
| 设计方案 | `_optimize/prompt_regression/round1/prompt_patch.md` 补丁A |
| 应用轮次 | R4 |
| 实际修改 | `tools/builtin/仿写/fanxie-chapter.md` — "# 角色"段末尾插入了"禁止逐字复制 + MC口癖强制 + 章尾钩子硬约束"段落 |
| old_string | (R4应用时替换的原文，参见 R4 fix_applied.md) |
| new_string | (同上) |
| 验证轮次 | ⏳ 待 R5 验证 |
| 效果 | — |
| 状态 | ✅ solved（已应用，待验证） |
| 备注 | 从 R1 设计到 R4 应用延迟了 3 轮 |

### CH-006 — 网文基调控（📌 待应用优先级最高）

| 字段 | 内容 |
|------|------|
| 提出轮次 | R1 补丁F |
| 设计方案 | `_optimize/prompt_regression/round1/prompt_patch.md` 补丁F |
| 应用轮次 | ❌ 未应用 |
| 未应用原因 | R4 应用时认为"待独立评估" |
| old_string | 待确认（需 Read fanxie-chapter.md 定位） |
| new_string | 待设计 |
| 状态 | 🔴 pending |
| 建议 | 在下轮迭代中作为 P1 补丁应用 |

### PT-001 — 模式卡新增 protagonist_voice 字段（📌 待应用）

| 字段 | 内容 |
|------|------|
| 提出轮次 | R1 补丁G |
| 设计方案 | `_optimize/prompt_regression/round1/prompt_patch.md` 补丁G |
| 应用轮次 | ❌ 未应用 |
| 状态 | 🔴 pending |
| 建议 | 在 fanxie-pattern.md 的 tone 对象中追加 protagonist_voice 字段 |

---

## 状态说明

| 状态 | 含义 | 后续动作 |
|------|------|---------|
| 🔴 pending | 设计了但未应用 | 安排到下一轮迭代中应用 |
| ✅ solved | 已实际写入目标文件 | 下一轮验证效果 |
| 🟡 indirect | 被其他补丁间接覆盖，非独立应用 | 验证间接覆盖是否足够 |
| ⏳ 待验证 | 已应用但未跑 compare 确认效果 | 下一轮跑 compare 后更新 |
| ❌ reverted | 应用后发现副作用被回退 | 记录回退原因 |

---

## 新增补丁模板

当 fanxie-prompt-opt 产出新补丁时，按以下模板追加：

```
### {补丁ID} — {补丁名}

| 字段 | 内容 |
|------|------|
| 提出轮次 | R{N} |
| 设计方案 | `_optimize/prompt_regression/round{N}/prompt_patch_ready.md` |
| 目标文件 | {文件路径} |
| old_string | `{文件中存在的原文本}` |
| new_string | `{替换后的新文本}` |
| 应用轮次 | ⏳ 待应用 |
| 验证轮次 | ⏳ 未验证 |
| 预期效果 | {一句话} |
| 实际效果 | — |
| 状态 | 🔴 pending |
```
