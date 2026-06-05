<#
.SYNOPSIS
    AIGC Structure Validation Script
.PARAMETER Path
    File path to validate
#>
param([Parameter(Mandatory=$true)][string]$Path)

# Windows鐜缂栫爜淇
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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
$emotion = "蹇冮噷鍜檾|蹇冭烦婕忎簡涓€鎷峾鎰ｄ綇浜唡鍍典綇浜唡澶ц剳绌虹櫧|蹇冧腑涓€鎯妡蹇冨ご涓€闇噟蹇冧腑娑岃捣|鎮潃鐨勫績缁堜簬姝讳簡|涓ょ溂涓€榛憒鐪煎啋閲戞槦|鎵嬪績鍐掓睏|鍚庤儗鍙戝噳"
$em = [regex]::Matches($content, $emotion)
$msg = "[1] Emotion templates: $($em.Count) (max 1)"
if ($em.Count -ge 2) { $warnings += "Emotion templates: $($em.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 2. Inner monologue chains
$inner = [regex]::Matches($content, '[\u3002\uff01\uff1f][^\u3002\uff01\uff1f]{10,}(鎯硘瑙夊緱|鐭ラ亾|鏄庣櫧|鎰忚瘑鍒皘鍙戠幇)[^\u3002\uff01\uff1f]{10,}[\u3002\uff01\uff1f]')
$msg = "[2] Inner monologue chains: $($inner.Count) (max 2)"
if ($inner.Count -ge 3) { $warnings += "Inner monologue: $($inner.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 3. Dialog tag density
$tags = [regex]::Matches($content, '(浠栬|濂硅|浠栭棶|濂归棶|浠栫瓟|濂圭瓟)')
if ($charCount -gt 0) {
    $density = [math]::Round($tags.Count / ($charCount / 100), 1)
    $msg = "[3] Dialog tags: $density/100 chars (max 3)"
    if ($density -gt 3) { $warnings += "Dialog tags: $density/100"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }
}

# 4. Paragraph length std dev (adjusted for web novel style)
$paragraphs = ($content -split '\r?\n\r?\n') | Where-Object { $_.Trim() -ne '' }
if ($paragraphs.Count -ge 3) {
    $lengths = $paragraphs | ForEach-Object { ($_ -replace '\s+','').Length }
    $avg = ($lengths | Measure-Object -Average).Average
    $variance = ($lengths | ForEach-Object { [math]::Pow($_ - $avg, 2) } | Measure-Object -Average).Average
    $std = [math]::Sqrt($variance)
    $msg = "[4] Paragraph std dev: $($std.ToString('F1')) (min 10)"
    if ($std -lt 10) { $warnings += "Paragraph std: $std"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }
}

# 5. Single-sentence paragraphs
$singleCount = 0
foreach ($p in $paragraphs) {
    $pl = ($p -split '\r?\n') | Where-Object { $_.Trim() -ne '' }
    if ($pl.Count -eq 1) { $singleCount++ }
}
$msg = "[5] Single-sentence paragraphs: $singleCount (min 3)"
if ($singleCount -lt 3) { $warnings += "Single-sentence: $singleCount"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 6. Consecutive similar-length paragraphs (adjusted: check char count ranges, not exact line count)
$pCharRanges = @()
foreach ($p in $paragraphs) {
    $charLen = ($p -replace '\s+','').Length
    if ($charLen -le 15) { $pCharRanges += "short" }
    elseif ($charLen -le 40) { $pCharRanges += "medium" }
    else { $pCharRanges += "long" }
}
$maxCons = 0; $cons = 0
for ($i = 1; $i -lt $pCharRanges.Count; $i++) {
    if ($pCharRanges[$i] -eq $pCharRanges[$i-1]) { $cons++; if ($cons -gt $maxCons) { $maxCons = $cons } } else { $cons = 0 }
}
$msg = "[6] Consecutive similar-length: $maxCons (max 10)"
if ($maxCons -ge 11) { $warnings += "Consecutive similar-length: $maxCons"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 7. Internet slang frequency
$slang = "濂藉浼檤钖涘畾璋攟鎮潃鐨勫績缁堜簬姝讳簡|涓ょ溂涓€榛憒鏌ュ矖鍝浜烘満|PUA"
$sm = [regex]::Matches($content, $slang)
$msg = "[7] Internet slang: $($sm.Count) (max 2)"
if ($sm.Count -gt 2) { $warnings += "Slang: $($sm.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# 8. Banned words
$banned = "浠夸經|鐘瑰|瀹涜嫢|濡傚悓|涓€涓潀涓€鎶箌娣卞惛涓€鍙ｆ皵|缂撶紦|涓嶇|寰井|杞昏交|娣℃贰|鐪间腑闂繃|鍢磋鍕捐捣|鐪夊ご寰毐|蹇冧腑涓€鍔▅蹇冨ご涓€闇噟蹇冧笅浜嗙劧|涓嶇敱寰梶闂儊鐫€鍏夎姃|鑴歌壊涓€鍙榺鐩厜濡傜偓|娌夊０閬搢鍙|涓嶇敱鑷富|鐬冲瓟寰缉"
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

# 10. First person (exclude dialogue lines, allow proportional usage)
$dialogLines = [regex]::Matches($content, '[\u201c\u0022][^\u201d\u0022]*[\u201d\u0022]')
$contentNoDialog = $content
foreach ($dl in $dialogLines) {
    $contentNoDialog = $contentNoDialog.Replace($dl.Value, '')
}
$fp = [regex]::Matches($contentNoDialog, '\u6211')
$maxAllowed = [math]::Max(10, [math]::Floor($charCount / 500))
$msg = "[10] First person 'wo' (excl. dialogue): $($fp.Count) (max $maxAllowed)"
if ($fp.Count -gt $maxAllowed) { $warnings += "First person: $($fp.Count)"; Write-Output "[WARN] $msg" } else { Write-Output "[OK]   $msg" }

# Summary
Write-Output ""
Write-Output "=========================================="
if ($warnings.Count -eq 0) { Write-Output "Result: ALL PASSED" } else {
    Write-Output "Result: $($warnings.Count) WARNINGS"
    Write-Output "------------------------------------------"
    foreach ($w in $warnings) { Write-Output "  - $w" }
}
Write-Output "=========================================="
