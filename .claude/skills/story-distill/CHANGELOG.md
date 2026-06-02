# story-distill 变更日志

## v2.0（2026-06-02）

### 核心变更

引入 **Phase 6：Consolidation（蒸馏收口）** + `.distill/` 工作目录概念，从上游解决蒸馏产物体积膨胀问题。

### 背景

v1.0 pipeline 蒸馏出的 4 个 skill（闻栖/初点点/空留/橙味薏米粥）平均 42 个文件，最大 67 个。问题：
- `candidates/`、`rejected/`、`constructed/` 三个目录并存
- 同一规则在 `candidates/X.md`、`references/constructed/X.md`、`references/constructed/constructed-X.md` 三处重复
- `sources/` 原文 8.1MB 永久保留
- `book-overviews/`、`writing-samples-*.md` 是审计数据，不被 story-rewrite 读取
- 没有任何机制在蒸馏完成后清理中间产物

### 变更内容

#### 新增

| 文件 | 用途 |
|------|------|
| `methodology/post-processing.md` | Phase 6 完整 spec（5 步清理 + 3 项自检 + 失败回滚） |
| `templates/CONSOLIDATION_CHECKLIST.md` | 运行时自检脚本（PowerShell） |
| `CHANGELOG.md` | 本文件 |

#### 修改

| 文件 | 变更 |
|------|------|
| `SKILL.md` | 加 Phase 6 section；更新 Phase 0/2/3/4 路径表；重写「输出结构」section 为 post-consolidation 视图；加文件数/token 预算/无中间产物 3 项自检 |
| `methodology/output-templates.md` | 引入双层目录概念（交付层 + 工作层）；加 v1.0 → v2.0 迁移对照表 |
| `methodology/extraction-framework.md` | Phase 2-5 输出路径全部加 `.distill/` 前缀；新增 Phase 5-6 衔接说明 |
| `templates/SKILL_template.md` | 删除审稿功能 section（应独立到 review 模板）；更新描述和参考数据 |
| `extractors/*.md`（15 个文件） | 读取路径加 `.distill/` 前缀；输出路径加 `.distill/candidates/` 前缀 |

### 不变更

- Phase 0-5 流程本身（除路径）
- 验证逻辑（三重验证规则不变）
- 提取器数量（write 10 + review 5）
- RIA++ 结构
- de-ai-modules/ 模块库

### 影响范围

| 对象 | 影响 |
|------|------|
| **现有 4 个 skill**（闻栖/初点点/空留/橙味薏米粥） | 不自动迁移，保持 v1.0 结构。在 `meta.json` 标注 `pipeline_version: "1.0"`（待补充） |
| **新蒸馏** | 按 v2.0 走，meta.json 标 `pipeline_version: "2.0"`（待补充） |
| **回炉工具** | 提供 `templates/CONSOLIDATION_CHECKLIST.md` 中的 PowerShell 脚本（一次性） |

### 验收标准

新蒸馏产物的预期指标：

| 指标 | v1.0 实际 | v2.0 目标 |
|------|---------|----------|
| write 模式文件数 | 49-67 | 14 |
| review 模式文件数 | 60-80 | 21 |
| SKILL.md 大小 | 22-38KB | 15-20KB |
| references/ 总和 | 100-200KB | 40-60KB |
| `candidates/` 残留 | 4-14 | 0 |
| `rejected/` 残留 | 0-6 | 0 |
| `constructed/` 残留 | 7-18 | 0 |
| `sources/` 残留 | 8.1MB | 0 |
| 副本（constructed-X + X） | 9 对 | 0 |

### 已知问题（v2.0 仍未解决）

1. `meta.json` 的 `pipeline_version` 字段需要补充到 `templates/meta_template.json`（v2.0 范围内，pending）
2. 旧 skill 回炉脚本需要从 `CONSOLIDATION_CHECKLIST.md` 拆到独立 `scripts/consolidate_legacy.py`（v2.1 计划）
3. 现有 4 个 skill 的 `meta.json` 未标注 `pipeline_version`（v2.0.1 patch）
4. `templates/SKILL_review_template.md` 缺失（v2.0 范围内，pending）

---

## v1.0（2025）

### 初始版本

基于 cangjie-skill RIA-TV++ + nuwa-skill 六维研究的方法论。

**已知缺陷**（v2.0 修复）：
- 无收口阶段，中间产物永久保留
- 工作目录与交付目录混用
- 无 token 预算/文件数自检
- 同一规则在多处重复

### 历史产出（v1.0 标记）

| Skill | 文件数 | 状态 |
|------|------|------|
| 闻栖 | 67 | 旧 v1.0 结构，保留可用 |
| 初点点 | 49 | 旧 v1.0 结构，保留可用 |
| 空留 | 37 | 旧 v1.0 结构，保留可用 |
| 橙味薏米粥 | 17 | 旧 v1.0 结构（1 本蒸馏所以更小），保留可用 |
