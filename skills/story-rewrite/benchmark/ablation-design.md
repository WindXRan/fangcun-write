# 消融实验设计

> 目的：量化 persona 注入和写作规则各自贡献了多少改进。

## 实验设计

| 组别 | 配置 | 控制变量 |
|------|------|----------|
| A 组（baseline） | 无 persona，无写作规则 | "你是网文写作专家" + 纯章纲 |
| B 组（persona-only） | 有 persona，无写作规则 | persona 定义 + 语感样本 + 章纲 |
| C 组（rules-only） | 无 persona，有写作规则 | "你是网文写作专家" + 章纲 + 写作规则 |
| D 组（full） | 有 persona，有写作规则 | 当前完整 prompt |

## 每组运行

- 同一源文本（女配一睁眼）
- 同一章纲（Phase 2 输出）
- 同一 agent 类型（narrative-writer）
- 各 3 章

## 测量指标

| 指标 | 测量方式 | 工具 |
|------|----------|------|
| 验证警告数 | 统一脚本 | validate-aigc.ps1 |
| 编辑评分 | 人工评审 | 结构化反馈模板 |
| 网络梗频率 | 统一脚本 | validate-aigc.ps1 第 7 项 |
| 情绪模板词 | 统一脚本 | validate-aigc.ps1 第 1 项 |

## 预期结论

- A vs B：persona 贡献多少？
- A vs C：写作规则贡献多少？
- B vs D：写作规则在 persona 基础上额外贡献多少？
- C vs D：persona 在规则基础上额外贡献多少？

## 运行方式

```powershell
# 1. 运行 A 组（修改 Phase 3 prompt 为 baseline 版本）
# 2. 运行验证
.\skills\story-rewrite\tools\validate-aigc.ps1 -Path '仿写试水库/试水_xxx_A组.txt'

# 3. 运行 B 组（恢复 persona，注释掉反AI规则）
# 4. 运行验证
.\skills\story-rewrite\tools\validate-aigc.ps1 -Path '仿写试水库/试水_xxx_B组.txt'

# 5. 运行 D 组（当前完整版本）
# 6. 运行验证
.\skills\story-rewrite\tools\validate-aigc.ps1 -Path '仿写试水库/试水_xxx_D组.txt'
```
