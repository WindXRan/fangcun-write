# Phase 6: Consolidation（蒸馏收口）

## 概述

Phase 6 是 story-distill 的最后阶段。目的：把 Phase 1-5 产生的中间产物（candidates/、constructed/、rejected/、sources/、book-overviews/、writing-samples-*.md）从生产目录清出，保留最终交付物。

**核心原则**：
- 工作目录 `.distill/` 是临时容器，Phase 6 末尾整个删除
- 最终交付物只含 `SKILL.md` + `meta.json` + `test-prompts.json` + `references/` + `review/`
- 收口后必须跑自检（文件数、token 预算、目录清理）

---

## 6.1 工作目录规范

Phase 0 起，所有中间产物写到 `.distill/` 子目录：

```
{输出根}/{作者名}/
├── SKILL.md                      # 交付物（write 模式）
├── meta.json
├── test-prompts.json             # 验证阶段产物
├── review/                       # 交付物（review 模式）
│   ├── SKILL.md
│   └── meta.json
├── references/                   # 交付物（详细规则）
│   ├── writing-samples.md
│   ├── mental-models.md
│   ├── decision-heuristics.md
│   ├── rhythm-intuition.md
│   ├── expression-dna.md
│   ├── anti-patterns.md
│   ├── synopsis-patterns.md
│   ├── chapter-template.md
│   ├── de-ai-strategy.md
│   ├── satisfaction-points.md
│   ├── scoring-model.md
│   ├── review-redlines.md        # review 模式
│   ├── edit-prescriptions.md     # review 模式
│   ├── quality-thresholds.md     # review 模式
│   ├── review-persona.md         # review 模式
│   └── revision-capability.md    # review 模式
└── .distill/                     # 工作目录，Phase 6 删除
    ├── book-overviews/           # Phase 1 产出
    ├── writing-samples-*.md      # Phase 1 产出（每本一个）
    ├── candidates/               # Phase 2 原始产出
    ├── constructed/              # Phase 4 RIA++ 终版
    ├── rejected/                 # Phase 3 淘汰
    └── sources/                  # 原文备份
```

**禁止**：在工作层 `.distill/` 和交付层 `references/` 同时存在同名文件。

---

## 6.2 5 步清理流程

| Step | 动作 | 来源 | 去向 | 失败处理 |
|------|------|------|------|----------|
| 1 | 删除原文 | `.distill/sources/*.txt` | （删） | 强制 |
| 2 | 合并 RIA++ 终版 | `.distill/constructed/*.md` | `references/*.md` | 检查重名覆盖 |
| 3 | 合并语感样本 | `.distill/writing-samples-*.md` | `references/writing-samples.md` | 合并 6 本为 1 个 |
| 4 | 删除工作目录 | `.distill/{candidates,constructed,rejected,book-overviews,writing-samples-*,sources}/` | （删） | 强制 |
| 5 | 删除 `.distill/` | 整个 `.distill/` | （删） | 强制 |

### Step 2 详解：合并 RIA++ 终版

```python
# 伪代码
for src in .distill/constructed/*.md:
    filename = basename(src)  # 如 mental-models.md
    target = references/{filename}
    
    if target.exists():
        # 已被 Phase 5 写入 → 覆盖
        target.write(src.content)
    else:
        target.write(src.content)
```

**注意**：Phase 5 已经基于 `.distill/constructed/*.md` 生成 SKILL.md。所以 references/ 中**只有** 11 个 write 维度文件 + 5 个 review 维度文件，没有 constructed/。Step 2 只是 sanity check。

### Step 3 详解：合并语感样本

每本书的语感样本在 `.distill/writing-samples-{书名}.md` 中。Phase 6 把 6 个文件合并为 1 个 `references/writing-samples.md`：

```markdown
# 合并后的 writing-samples.md

## 书 A 语感样本

### 开篇语感
> {原文 1}
> ——《书 A》第 1 章

### 日常语感
> {原文 2}
> ——《书 A》第 N/2 章

## 书 B 语感样本
...
```

### Step 4 详解：删除工作目录

```bash
# PowerShell
Remove-Item .distill/candidates -Recurse -Force
Remove-Item .distill/constructed -Recurse -Force
Remove-Item .distill/rejected -Recurse -Force
Remove-Item .distill/book-overviews -Recurse -Force
Remove-Item .distill/sources -Recurse -Force
Remove-Item .distill/writing-samples-*.md -Force
```

### Step 5 详解：删除 .distill/ 容器

```bash
# PowerShell
Remove-Item .distill -Recurse -Force
```

---

## 6.3 交付物自检 3 项

Phase 6 跑完后必须执行，不通过禁止输出。

### 检查 1：文件数

```powershell
$root = ".claude/skills/story-style/{作者名}"
$count = (Get-ChildItem -LiteralPath $root -Recurse -File | Measure-Object).Count

if ($count -gt 14 -and $mode -eq "write") {
    Write-Error "文件数 $count 超过 write 模式上限 14"
}
if ($count -gt 21 -and $mode -eq "review") {
    Write-Error "文件数 $count 超过 review 模式上限 21"
}
```

**上限**：
- write 模式：14 个（3 顶层 + 11 references）
- review 模式：21 个（write 14 + review/ 2 + 5 review 专用 references）

### 检查 2：token 预算

```powershell
$skillSize = (Get-Item "$root/SKILL.md").Length
$refTotal = (Get-ChildItem "$root/references" -File | Measure-Object Length -Sum).Sum

if ($skillSize -gt 20KB) {
    Write-Error "SKILL.md $([math]::Round($skillSize/1KB, 1))KB 超过 20KB 上限"
}
if ($refTotal -gt 60KB) {
    Write-Error "references/ 总和 $([math]::Round($refTotal/1KB, 1))KB 超过 60KB 上限"
}
```

**上限**：
- `SKILL.md` ≤ 20KB
- `references/` 总和 ≤ 60KB
- 单个 `references/*.md` ≤ 15KB

### 检查 3：无中间产物

```powershell
$forbidden = @(
    "$root/references/book-overviews",
    "$root/references/candidates",
    "$root/references/rejected",
    "$root/references/constructed",
    "$root/sources",
    "$root/.distill"
)

foreach ($path in $forbidden) {
    if (Test-Path -LiteralPath $path) {
        Write-Error "禁止目录存在: $path"
    }
}
```

**禁止存在的目录**：
- `references/book-overviews/`
- `references/candidates/`
- `references/rejected/`
- `references/constructed/`
- `references/constructed/constructed-*.md`（副本）
- `references/writing-samples-{书名}.md`（按书的副本）
- `sources/` 或 `.distill/sources/`
- `.distill/` 整个

---

## 6.4 v1.0 兼容

为不破坏现有 4 个 skill（闻栖/初点点/空留/橙味薏米粥）的向后兼容：

| 处理 | 说明 |
|------|------|
| **不自动迁移** | 避免破坏现有调用 |
| **标记 v1.0** | 在 `meta.json` 显式标注 `pipeline_version: "1.0"` |
| **新蒸馏按 v2.0** | 所有新 skill 走 Phase 6 |
| **手动回炉** | 跑 `scripts/consolidate_legacy.py`（待补）一次性回炉 |

### consolidate_legacy.py 行为（规划）

```python
# 伪代码
def consolidate_legacy(root):
    # 1. 合并 constructed-X.md 和 X.md（去重）
    for plain in root/references/*.md:
        constructed = root/references/constructed/constructed-{plain.name}
        if constructed.exists():
            # 用 constructed 覆盖 plain
            shutil.copy(constructed, plain)
    
    # 2. 删除 candidates/, rejected/, book-overviews/
    for dir in ['candidates', 'rejected', 'book-overviews', 'constructed']:
        shutil.rmtree(root/references/dir, ignore_errors=True)
    
    # 3. 删除 sources/
    shutil.rmtree(root/sources, ignore_errors=True)
    
    # 4. 合并 writing-samples-{书名}.md 为 writing-samples.md
    merge_writing_samples(root)
    
    # 5. 更新 meta.json
    meta = read_json(root/meta.json)
    meta['pipeline_version'] = '2.0'
    write_json(root/meta.json, meta)
```

---

## 6.5 失败回滚

如果 Phase 6 中途失败（脚本崩溃、路径冲突、合并冲突）：

1. **保留 `.distill/` 完整内容**——不要尝试自动恢复
2. **SKILL.md 标记 `[DRAFT - Phase 6 INCOMPLETE]`**——明确告知调用方
3. **不允许 story-rewrite 调用此 skill**——在 SKILL.md frontmatter 加 `status: draft`
4. **用户可手动补救**：
   - 检查 `.distill/constructed/*.md` 是否完整
   - 重跑 Phase 6
   - 或手动合并部分文件

### 检测失败

Phase 6 自检任意一项失败 → 视为整体失败 → 回滚：

```python
# 自检结果
checks = {
    'file_count': check_file_count(root),
    'token_budget': check_token_budget(root),
    'no_intermediate': check_no_intermediate(root)
}

if not all(checks.values()):
    failed = [k for k, v in checks.items() if not v]
    raise ConsolidationError(f"Phase 6 自检失败: {failed}")
```

---

## 6.6 与 Phase 5 的关系

Phase 5 写 SKILL.md + meta.json，Phase 6 清理 .distill/。两者顺序：

```
Phase 5 合成输出 → 生成 SKILL.md + meta.json 到交付层
                ↓
Phase 6 收口清理 → 删除 .distill/，保留交付层
                ↓
自检 3 项 → 不通过回滚，通过则蒸馏完成
```

**不允许** Phase 5 和 Phase 6 并行：Phase 6 必须等 Phase 5 完整写入交付层后才能开始。

---

## 6.7 与 verify 阶段的关系

Phase 6 跑完后，蒸馏过程结束。下一步是用户触发 `/story-distill-verify`：

- `/story-distill-verify` 读 `SKILL.md` + `references/*.md`
- 跑压力测试（`test-prompts.json`）
- 生成演化日志

**如果 verify 失败** → 用户修复规则 → 重跑 verify。不需要重跑 Phase 1-6。

---

## 6.8 速查表

| 路径 | 状态 | Phase 6 动作 |
|------|------|-------------|
| `SKILL.md` | 交付 | 保留 |
| `meta.json` | 交付 | 保留 |
| `test-prompts.json` | 交付 | 保留 |
| `review/SKILL.md` | 交付 | 保留 |
| `review/meta.json` | 交付 | 保留 |
| `references/writing-samples.md` | 交付 | 保留（合并自 6 个 per-book 文件） |
| `references/mental-models.md` | 交付 | 保留（来自 `.distill/constructed/`） |
| `references/decision-heuristics.md` | 交付 | 保留 |
| `references/rhythm-intuition.md` | 交付 | 保留 |
| `references/expression-dna.md` | 交付 | 保留 |
| `references/anti-patterns.md` | 交付 | 保留 |
| `references/synopsis-patterns.md` | 交付 | 保留 |
| `references/chapter-template.md` | 交付 | 保留 |
| `references/de-ai-strategy.md` | 交付 | 保留 |
| `references/satisfaction-points.md` | 交付 | 保留 |
| `references/scoring-model.md` | 交付 | 保留 |
| `references/review-redlines.md` | 交付（review 模式） | 保留 |
| `references/edit-prescriptions.md` | 交付（review 模式） | 保留 |
| `references/quality-thresholds.md` | 交付（review 模式） | 保留 |
| `references/review-persona.md` | 交付（review 模式） | 保留 |
| `references/revision-capability.md` | 交付（review 模式） | 保留 |
| `.distill/sources/*.txt` | 工作 | 删除 |
| `.distill/candidates/*.md` | 工作 | 删除 |
| `.distill/constructed/*.md` | 工作 | 删除（合并后） |
| `.distill/rejected/*.md` | 工作 | 删除 |
| `.distill/book-overviews/*.md` | 工作 | 删除 |
| `.distill/writing-samples-*.md` | 工作 | 删除（合并后） |
| `.distill/` 整个 | 工作 | 删除 |

---

## 6.9 参考

- `SKILL.md` Phase 6 章节（同名）
- `output-templates.md` 双层目录结构
- `extraction-framework.md` Phase 5-6 衔接说明
- `templates/CONSOLIDATION_CHECKLIST.md` 运行时自检脚本
- `scripts/consolidate_legacy.py`（待补）—— 旧 skill 回炉工具
