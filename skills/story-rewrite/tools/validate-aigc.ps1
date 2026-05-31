<#
.SYNOPSIS
    AIGC Structure Validation Script
.PARAMETER Path
    File path to validate
#>
param([Parameter(Mandatory=$true)][string]$Path)

if (-not (Test-Path $Path)) { Write-Error "File not found: $Path"; exit 1 }

$content = Get-Content $Path -Encoding UTF8 -Raw
$lines = Get-Content $Path -Encoding UTF8
$charCount = ($content -replace '[\s]','').Length

Write-Output "=========================================="
Write-Output "AIGC Validation Report"
Write-Output "File: $Path"
Write-Output "Chars: $charCount"
Write-Output "=========================================="

$warnings = @()

# 1. Emotion template words
$emotion = "心里咯噔|心跳漏了一拍|愣住了|僵住了|大脑空白|心中一惊|心头一震|心中涌起|悬着的心终于死了|两眼一黑|眼冒金星|手心冒汗|后背发凉"
$em = [regex]::Matches($content, $emotion)
$msg = "[1] Emotion templates: $($em.Count) (max 1)"
if ($em.Count -ge 2) { $warnings += "Emotion templates: $($em.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 2. Inner monologue chains
$inner = [regex]::Matches($content, '[\u3002\uff01\uff1f][^\u3002\uff01\uff1f]{10,}(想|觉得|知道|明白|意识到|发现)[^\u3002\uff01\uff1f]{10,}[\u3002\uff01\uff1f]')
$msg = "[2] Inner monologue chains: $($inner.Count) (max 2)"
if ($inner.Count -ge 3) { $warnings += "Inner monologue: $($inner.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 3. Dialog tag density
$tags = [regex]::Matches($content, '(他说|她说|他问|她问|他答|她答)')
if ($charCount -gt 0) {
    $density = [math]::Round($tags.Count / ($charCount / 100), 1)
    $msg = "[3] Dialog tags: $density/100 chars (max 3)"
    if ($density -gt 3) { $warnings += "Dialog tags: $density/100"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }
}

# 4. Paragraph length std dev
$paragraphs = ($content -split '\r?\n\r?\n') | Where-Object { $_.Trim() -ne '' }
if ($paragraphs.Count -ge 3) {
    $lengths = $paragraphs | ForEach-Object { ($_ -replace '\s+','').Length }
    $avg = ($lengths | Measure-Object -Average).Average
    $variance = ($lengths | ForEach-Object { [math]::Pow($_ - $avg, 2) } | Measure-Object -Average).Average
    $std = [math]::Sqrt($variance)
    $msg = "[4] Paragraph std dev: $($std.ToString('F1')) (min 30)"
    if ($std -lt 30) { $warnings += "Paragraph std: $std"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }
}

# 5. Single-sentence paragraphs
$singleCount = 0
foreach ($p in $paragraphs) {
    $pl = ($p -split '\r?\n') | Where-Object { $_.Trim() -ne '' }
    if ($pl.Count -eq 1) { $singleCount++ }
}
$msg = "[5] Single-sentence paragraphs: $singleCount (min 3)"
if ($singleCount -lt 3) { $warnings += "Single-sentence: $singleCount"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 6. Consecutive same-length paragraphs
$pLineCounts = @()
foreach ($p in $paragraphs) {
    $pl = ($p -split '\r?\n') | Where-Object { $_.Trim() -ne '' }
    $pLineCounts += $pl.Count
}
$maxCons = 0; $cons = 0
for ($i = 1; $i -lt $pLineCounts.Count; $i++) {
    if ($pLineCounts[$i] -eq $pLineCounts[$i-1]) { $cons++; if ($cons -gt $maxCons) { $maxCons = $cons } } else { $cons = 0 }
}
$msg = "[6] Consecutive same-length: $maxCons (max 2)"
if ($maxCons -ge 3) { $warnings += "Consecutive same-length: $maxCons"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 7. Internet slang frequency
$slang = "好家伙|薛定谔|悬着的心终于死了|两眼一黑|查岗哥|人机|PUA"
$sm = [regex]::Matches($content, $slang)
$msg = "[7] Internet slang: $($sm.Count) (max 2)"
if ($sm.Count -gt 2) { $warnings += "Slang: $($sm.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 8. Banned words
$banned = "仿佛|犹如|宛若|如同|一丝|一抹|深吸一口气|缓缓|不禁|微微|轻轻|淡淡|眼中闪过|嘴角勾起|眉头微皱|心中一动|心头一震|心下了然|不由得|闪烁着光芒|脸色一变|目光如炬|沉声道|只见|不由自主|瞳孔微缩"
$bm = [regex]::Matches($content, $banned)
$msg = "[8] Banned words: $($bm.Count) (target 0)"
if ($bm.Count -gt 0) { $warnings += "Banned words: $($bm.Count)"; Write-Output "[WARN] $msg"; Write-Output "       Top: $(($bm | Select-Object -First 5).Value -join ', ')" } else { Write-Output "[OK]   $msg" }

# 9. Ultra-short sentence streak
$sentences = $content -split '[\u3002\uff01\uff1f]'
$ultra = 0; $maxUltra = 0
foreach ($s in $sentences) {
    $clean = ($s -replace '[\s]','').Trim()
    if ($clean.Length -le 5 -and $clean.Length -gt 0) { $ultra++; if ($ultra -gt $maxUltra) { $maxUltra = $ultra } } else { $ultra = 0 }
}
$msg = "[9] Ultra-short streak: $maxUltra (max 2)"
if ($maxUltra -ge 3) { $warnings += "Ultra-short streak: $maxUltra"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 10. First person
$fp = [regex]::Matches($content, '\u6211')
$msg = "[10] First person 'wo': $($fp.Count) (max 5 for long-form)"
if ($fp.Count -gt 5) { $warnings += "First person: $($fp.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# Summary
Write-Output ""
Write-Output "=========================================="
if ($warnings.Count -eq 0) { Write-Output "Result: ALL PASSED" } else {
    Write-Output "Result: $($warnings.Count) WARNINGS"
    Write-Output "------------------------------------------"
    foreach ($w in $warnings) { Write-Output "  - $w" }
}
Write-Output "=========================================="
