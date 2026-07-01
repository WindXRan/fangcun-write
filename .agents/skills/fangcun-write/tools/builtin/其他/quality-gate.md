---
name: quality-gate
icon: 🛡️
phase: quality
temperature: 0.2
description: 质量门禁。三种模式：preflight（写前检查角色卡/源文映射）、chapter（写后红线）、audit（跨章审计）。
tags: 质量,检查
category: 其他
output: 检查报告
---

# quality-gate

三种模式，不同阶段调用。

## preflight（写章前）

检查：章纲存在？角色卡完整？章纲已转换（无源文角色名）？前文衔接？
→ P0阻塞项不通过 → 禁止写章

## chapter（写章后）

检查：P0格式红线（总结升华/他说她道/万能比喻）、P1叙事规范、P2一致性
→ P0不通过 → 阻塞到修好

## audit（跨章审计）

检查：角色名统一、时间线无矛盾、管线映射完整、伏笔追踪
→ 修复建议
