<#
.SYNOPSIS
    网文质量扫描脚本 — 标出"删了更好"的句子
.DESCRIPTION
    扫描正文，标记5类可删除的"AI废话"：
    1. 情绪告知（动作已在展示，文字在重复）
    2. 过渡句（场景切换的铺垫，可直接跳切）
    3. 解释（因为/原因是/之所以，让读者自己猜）
    4. 重复情绪（同一段里多个情绪表达，留最强的）
    5. 多余对话标签（上下文已能分清谁在说）
    不自动删除，只标出行号和建议。
.PARAMETER Path
    要扫描的正文文件路径
.EXAMPLE
    .\scan-quality.ps1 -Path "仿写试水库/试水_xxx.txt"
#>

param([Parameter(Mandatory=$true)][string]$Path)

if (-not (Test-Path $Path)) { Write-Error "File not found: $Path"; exit 1 }

$lines = Get-Content $Path -Encoding UTF8
$totalChars = ((Get-Content $Path -Raw -Encoding UTF8) -replace '[\s]','').Length

Write-Output "=========================================="
Write-Output "Quality Scan Report"
Write-Output "File: $Path"
Write-Output "Total chars: $totalChars"
Write-Output "=========================================="

$findings = @()

# ============================================
# 1. 情绪告知 — 直接告诉读者角色情绪的句子
# ============================================
$emotionTellPatterns = @(
    '她很紧张', '他很紧张', '她很害怕', '他很害怕', '她很愤怒', '他很愤怒',
    '她很伤心', '他很伤心', '她很绝望', '他很绝望', '她很震惊', '他很震惊',
    '她很惊讶', '他很惊讶', '她很尴尬', '他很尴尬', '她很无奈', '他很无奈',
    '她松了口气', '他松了口气', '她心里一紧', '他心里一紧',
    '她心跳漏了一拍', '他心跳漏了一拍', '她心跳加速', '他心跳加速',
    '她脑子嗡的一声', '他脑子嗡的一声', '她脑子一片混乱', '他脑子一片混乱',
    '她脑子一片空白', '他脑子一片空白', '她整个人僵住', '他整个人僵住',
    '她后背一凉', '他后背一凉', '她后背发凉', '他后背发凉',
    '她腿有点软', '他腿有点软', '她手指发凉', '他手指发凉',
    '恐惧从脚底', '紧张得手心', '害怕得手心'
)

for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) { continue }
    foreach ($pattern in $emotionTellPatterns) {
        if ($line -match [regex]::Escape($pattern)) {
            $findings += [PSCustomObject]@{
                Line = $i + 1
                Type = "EmotionTell"
                Text = $line.Substring(0, [Math]::Min(60, $line.Length))
                Suggestion = "Delete or replace with action"
            }
            break
        }
    }
}

# ============================================
# 2. 过渡句 — 场景切换的铺垫
# ============================================
$transitionPatterns = @(
    '^\s*她站起来', '^\s*他站起来', '^\s*她转身', '^\s*他转身',
    '^\s*她走出', '^\s*他走出', '^\s*她走进', '^\s*他走进',
    '^\s*她回到', '^\s*他回到', '^\s*她来到', '^\s*他来到',
    '^\s*第二天', '^\s*第二天早上', '^\s*第二天下午',
    '^\s*三天后', '^\s*过了几天', '^\s*过了很久',
    '^\s*傍晚', '^\s*深夜', '^\s*凌晨'
)

for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) { continue }
    foreach ($pattern in $transitionPatterns) {
        if ($line -match $pattern) {
            # Check if this line is the ONLY content in its paragraph (standalone transition)
            $prevEmpty = ($i -eq 0) -or ($lines[$i-1].Trim().Length -eq 0)
            $nextEmpty = ($i -eq $lines.Count - 1) -or ($lines[$i+1].Trim().Length -eq 0)
            if ($prevEmpty -and $nextEmpty) {
                $findings += [PSCustomObject]@{
                    Line = $i + 1
                    Type = "Transition"
                    Text = $line.Substring(0, [Math]::Min(60, $line.Length))
                    Suggestion = "Delete, jump cut to next scene"
                }
            }
            break
        }
    }
}

# ============================================
# 3. 解释 — 告诉读者为什么
# ============================================
$explainPatterns = @(
    '因为.*所以', '原因是', '之所以.*是因为',
    '她这么做是因为', '他这么做是因为',
    '她知道.*所以', '他知道.*所以',
    '她明白.*所以', '他明白.*所以'
)

for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) { continue }
    foreach ($pattern in $explainPatterns) {
        if ($line -match $pattern) {
            $findings += [PSCustomObject]@{
                Line = $i + 1
                Type = "Explanation"
                Text = $line.Substring(0, [Math]::Min(60, $line.Length))
                Suggestion = "Delete explanation, let reader infer"
            }
            break
        }
    }
}

# ============================================
# 4. 重复情绪 — 同一段里多个情绪表达
# ============================================
$paragraphs = @()
$currentPara = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) {
        if ($currentPara.Count -gt 0) {
            $paragraphs += ,@($currentPara)
            $currentPara = @()
        }
    } else {
        $currentPara += @{LineNum = $i + 1; Text = $line}
    }
}
if ($currentPara.Count -gt 0) { $paragraphs += ,@($currentPara) }

$emotionKeywords = '紧张|害怕|愤怒|伤心|绝望|震惊|惊讶|尴尬|无奈|心跳|发抖|发凉|僵住|空白|嗡'

foreach ($para in $paragraphs) {
    $emotionLines = @()
    foreach ($item in $para) {
        if ($item.Text -match $emotionKeywords) {
            $emotionLines += $item
        }
    }
    if ($emotionLines.Count -ge 2) {
        for ($j = 1; $j -lt $emotionLines.Count; $j++) {
            $findings += [PSCustomObject]@{
                Line = $emotionLines[$j].LineNum
                Type = "RepeatEmotion"
                Text = $emotionLines[$j].Text.Substring(0, [Math]::Min(60, $emotionLines[$j].Text.Length))
                Suggestion = "Duplicate emotion in same paragraph, keep only strongest"
            }
        }
    }
}

# ============================================
# 5. 多余对话标签
# ============================================
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) { continue }
    # Pattern: "dialogue" + 他说/她说 (when context already makes speaker clear)
    if ($line -match '^["「].*["」]\s*[，,]?\s*(他|她)(说|问|答|道|喊|叫)') {
        # Check if previous line has dialogue from the other person (context makes it clear)
        if ($i -gt 0) {
            $prevLine = $lines[$i-1].Trim()
            if ($prevLine -match '^["「].*["」]') {
                $findings += [PSCustomObject]@{
                    Line = $i + 1
                    Type = "RedundantTag"
                    Text = $line.Substring(0, [Math]::Min(60, $line.Length))
                    Suggestion = "Remove tag, context makes speaker clear"
                }
            }
        }
    }
}

# ============================================
# Summary
# ============================================
$byType = $findings | Group-Object Type

Write-Output ""
Write-Output "--- Findings by type ---"
foreach ($group in ($byType | Sort-Object Count -Descending)) {
    Write-Output "  $($group.Name): $($group.Count) lines"
}

Write-Output ""
Write-Output "--- Details ---"
foreach ($f in ($findings | Sort-Object Line)) {
    Write-Output "  Line $($f.Line) [$($f.Type)]: $($f.Text)"
    Write-Output "    -> $($f.Suggestion)"
}

$totalFindings = $findings.Count
$deleteEstimate = [math]::Round($totalFindings * 0.7)  # Assume 70% are safe to delete
$charReduction = [math]::Round($deleteEstimate * 30)    # Avg 30 chars per line

Write-Output ""
Write-Output "=========================================="
Write-Output "Total findings: $totalFindings"
Write-Output "Estimated safe deletions: $deleteEstimate lines (~$charReduction chars)"
Write-Output "Estimated new length: $($totalChars - $charReduction) chars"
Write-Output "=========================================="
