# Phase 6 Consolidation 自检清单

**用途**：Phase 6 完成后、story-rewrite 调用前必须通过的 3 项自检。
**位置**：`templates/CONSOLIDATION_CHECKLIST.md`
**关联**：`methodology/post-processing.md` 第 6.3 节

---

## 速查表

| 检查项 | write 模式 | review 模式 | 失败处理 |
|--------|-----------|------------|----------|
| 文件数 | ≤ 14 | ≤ 21 | 删到上限 |
| SKILL.md | ≤ 20KB | ≤ 20KB | 精简到上限 |
| references/ 总和 | ≤ 60KB | ≤ 75KB | 拆分或精简 |
| 单个 references/*.md | ≤ 15KB | ≤ 15KB | 拆分 |
| 中间产物 | 0 个 | 0 个 | 跑 5 步清理 |

---

## 完整自检脚本（PowerShell）

```powershell
# === 1. 设置变量 ===
$root = ".claude/skills/story-style/{作者名}"
$mode = "write"  # 或 "review"
$skillFile = "$root/SKILL.md"
$refDir = "$root/references"

# === 2. 文件数检查 ===
$count = (Get-ChildItem -LiteralPath $root -Recurse -File | Measure-Object).Count
$maxCount = if ($mode -eq "write") { 14 } else { 21 }

if ($count -gt $maxCount) {
    Write-Error "[FAIL] 文件数 $count 超过 $mode 模式上限 $maxCount"
    exit 1
}
Write-Host "[OK] 文件数: $count / $maxCount"

# === 3. SKILL.md token 检查 ===
if (Test-Path -LiteralPath $skillFile) {
    $skillSize = (Get-Item -LiteralPath $skillFile).Length
    $maxSkill = 20 * 1024  # 20KB
    
    if ($skillSize -gt $maxSkill) {
        Write-Error "[FAIL] SKILL.md $([math]::Round($skillSize/1KB, 1))KB 超过 20KB 上限"
        exit 1
    }
    Write-Host "[OK] SKILL.md: $([math]::Round($skillSize/1KB, 1))KB / 20KB"
}

# === 4. references/ token 检查 ===
if (Test-Path -LiteralPath $refDir) {
    $refTotal = (Get-ChildItem -LiteralPath $refDir -File | Measure-Object Length -Sum).Sum
    $maxRef = if ($mode -eq "write") { 60 * 1024 } else { 75 * 1024 }
    
    if ($refTotal -gt $maxRef) {
        Write-Error "[FAIL] references/ 总和 $([math]::Round($refTotal/1KB, 1))KB 超过上限 $([math]::Round($maxRef/1KB, 1))KB"
        exit 1
    }
    Write-Host "[OK] references/ 总和: $([math]::Round($refTotal/1KB, 1))KB / $([math]::Round($maxRef/1KB, 1))KB"
    
    # === 5. 单文件 token 检查 ===
    Get-ChildItem -LiteralPath $refDir -File | ForEach-Object {
        $maxSingle = 15 * 1024
        if ($_.Length -gt $maxSingle) {
            Write-Warning "[WARN] references/$($_.Name) $([math]::Round($_.Length/1KB, 1))KB 超过 15KB"
        }
    }
}

# === 6. 中间产物检查 ===
$forbidden = @(
    "$refDir/book-overviews",
    "$refDir/candidates",
    "$refDir/rejected",
    "$refDir/constructed",
    "$root/sources",
    "$root/.distill"
)

$hasForbidden = $false
foreach ($path in $forbidden) {
    if (Test-Path -LiteralPath $path) {
        Write-Error "[FAIL] 禁止目录存在: $path"
        $hasForbidden = $true
    }
}
if (-not $hasForbidden) {
    Write-Host "[OK] 无中间产物"
}

# === 7. 副本检查（v1.0 兼容） ===
$duplicateFiles = Get-ChildItem -LiteralPath $refDir -File -Filter "constructed-*.md" -ErrorAction SilentlyContinue
if ($duplicateFiles.Count -gt 0) {
    Write-Error "[FAIL] 存在 constructed- 前缀副本: $($duplicateFiles.Name -join ', ')"
    exit 1
}

# === 8. per-book writing-samples 检查 ===
$perBookSamples = Get-ChildItem -LiteralPath $refDir -File -Filter "writing-samples-*.md" -ErrorAction SilentlyContinue
if ($perBookSamples.Count -gt 0) {
    Write-Error "[FAIL] 存在 per-book writing-samples 副本: $($perBookSamples.Name -join ', ')"
    Write-Error "       应合并为 writing-samples.md"
    exit 1
}

Write-Host ""
Write-Host "=== Phase 6 Consolidation 自检通过 ==="
Write-Host "$mode 模式 / $count 个文件 / SKILL.md $([math]::Round($skillSize/1KB, 1))KB / references $([math]::Round($refTotal/1KB, 1))KB"
```

---

## 5 步清理脚本（PowerShell）

自检失败时，跑这 5 步清理 `.distill/`：

```powershell
$root = ".claude/skills/story-style/{作者名}"
$refDir = "$root/references"

# Step 1: 删除原文
if (Test-Path -LiteralPath "$root/.distill/sources") {
    Remove-Item -LiteralPath "$root/.distill/sources" -Recurse -Force
    Write-Host "Step 1: 已删除 .distill/sources/"
}

# Step 2: 合并 RIA++ 终版（sanity check，Phase 5 已写）
if (Test-Path -LiteralPath "$root/.distill/constructed") {
    # 把 constructed/ 的文件覆盖到 references/（理论上 Phase 5 已做）
    Get-ChildItem -LiteralPath "$root/.distill/constructed" -Filter "*.md" | ForEach-Object {
        $target = Join-Path $refDir $_.Name
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
    Write-Host "Step 2: 已合并 .distill/constructed/ → references/"
}

# Step 3: 删除构造目录
if (Test-Path -LiteralPath "$root/.distill/constructed") {
    Remove-Item -LiteralPath "$root/.distill/constructed" -Recurse -Force
    Write-Host "Step 3: 已删除 .distill/constructed/"
}

# Step 4: 删除 candidates/ 和 rejected/
if (Test-Path -LiteralPath "$root/.distill/candidates") {
    Remove-Item -LiteralPath "$root/.distill/candidates" -Recurse -Force
}
if (Test-Path -LiteralPath "$root/.distill/rejected") {
    Remove-Item -LiteralPath "$root/.distill/rejected" -Recurse -Force
}
if (Test-Path -LiteralPath "$root/.distill/book-overviews") {
    Remove-Item -LiteralPath "$root/.distill/book-overviews" -Recurse -Force
}
if (Test-Path -LiteralPath "$root/.distill/writing-samples-*.md") {
    Remove-Item -LiteralPath "$root/.distill/writing-samples-*.md" -Force
}
Write-Host "Step 4: 已删除 .distill/{candidates,rejected,book-overviews,writing-samples-*}/"

# Step 5: 删除 .distill/ 容器
if (Test-Path -LiteralPath "$root/.distill") {
    Remove-Item -LiteralPath "$root/.distill" -Recurse -Force
    Write-Host "Step 5: 已删除 .distill/"
}

Write-Host ""
Write-Host "=== 清理完成。重新跑自检脚本验证 ==="
```

---

## 一次性回炉脚本（v1.0 → v2.0）

现有 4 个 skill（闻栖/初点点/空留/橙味薏米粥）按 v1.0 pipeline 蒸馏，需要回炉：

```powershell
# 1. 合并 constructed-X.md 和 X.md（去重）
$refDir = ".claude/skills/story-style/{作者名}/references"
$constructedDir = "$refDir/constructed"

if (Test-Path -LiteralPath $constructedDir) {
    Get-ChildItem -LiteralPath $constructedDir -Filter "constructed-*.md" | ForEach-Object {
        $plainName = $_.Name -replace "^constructed-", ""
        $plainPath = Join-Path $refDir $plainName
        
        if (Test-Path -LiteralPath $plainPath) {
            # 副本存在 → 用 constructed 覆盖 plain
            Copy-Item -LiteralPath $_.FullName -Destination $plainPath -Force
            Write-Host "覆盖: $plainName"
        } else {
            # 只有 constructed 版 → 改名为 plain
            Rename-Item -LiteralPath $_.FullName -NewName $plainName
            Write-Host "改名: $($_.Name) → $plainName"
        }
    }
    
    # 删除 constructed/ 目录
    Remove-Item -LiteralPath $constructedDir -Recurse -Force
    Write-Host "已删除 $constructedDir"
}

# 2. 删除 candidates/, rejected/, book-overviews/
foreach ($dir in @("candidates", "rejected", "book-overviews")) {
    $path = Join-Path $refDir $dir
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "已删除 $path"
    }
}

# 3. 删除 sources/
$sourcesDir = ".claude/skills/story-style/{作者名}/sources"
if (Test-Path -LiteralPath $sourcesDir) {
    Remove-Item -LiteralPath $sourcesDir -Recurse -Force
    Write-Host "已删除 $sourcesDir"
}

# 4. 合并 writing-samples-{书名}.md 为 writing-samples.md
# （手动执行或写脚本）
# 提示：6 个文件 → 1 个文件，按书名分节

# 5. 更新 meta.json
$metaPath = ".claude/skills/story-style/{作者名}/meta.json"
if (Test-Path -LiteralPath $metaPath) {
    $meta = Get-Content -LiteralPath $metaPath -Raw | ConvertFrom-Json
    $meta | Add-Member -NotePropertyName "pipeline_version" -NotePropertyValue "2.0" -Force
    $meta | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $metaPath
    Write-Host "已更新 meta.json: pipeline_version=2.0"
}

Write-Host ""
Write-Host "=== v1.0 → v2.0 回炉完成 ==="
```

---

## 失败处理流程图

```
Phase 6 自检
  ├─ 文件数超限 ──────→ 删多余文件 → 重跑自检
  ├─ token 超限 ──────→ 精简 SKILL.md 或拆分 references → 重跑自检
  ├─ 中间产物残留 ──→ 跑 5 步清理 → 重跑自检
  └─ 副本存在 ────────→ 删副本/合并 → 重跑自检
                            ↓
                       全部通过 → Phase 6 完成 → 通知 user
                            ↓
                       失败 → 报错给 user → 手动修复
```

---

## 关联文件

- `methodology/post-processing.md` — Phase 6 完整 spec
- `SKILL.md` Phase 6 章节 — 流程图
- `output-templates.md` — 目录结构规范
- `templates/SKILL_template.md` — 模板
