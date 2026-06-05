<#
.SYNOPSIS
    缃戞枃璐ㄩ噺鎵弿鑴氭湰 鈥?鏍囧嚭"鍒犱簡鏇村ソ"鐨勫彞瀛?.DESCRIPTION
    鎵弿姝ｆ枃锛屾爣璁?绫诲彲鍒犻櫎鐨?AI搴熻瘽"锛?    1. 鎯呯华鍛婄煡锛堝姩浣滃凡鍦ㄥ睍绀猴紝鏂囧瓧鍦ㄩ噸澶嶏級
    2. 杩囨浮鍙ワ紙鍦烘櫙鍒囨崲鐨勯摵鍨紝鍙洿鎺ヨ烦鍒囷級
    3. 瑙ｉ噴锛堝洜涓?鍘熷洜鏄?涔嬫墍浠ワ紝璁╄鑰呰嚜宸辩寽锛?    4. 閲嶅鎯呯华锛堝悓涓€娈甸噷澶氫釜鎯呯华琛ㄨ揪锛岀暀鏈€寮虹殑锛?    5. 澶氫綑瀵硅瘽鏍囩锛堜笂涓嬫枃宸茶兘鍒嗘竻璋佸湪璇达級
    涓嶈嚜鍔ㄥ垹闄わ紝鍙爣鍑鸿鍙峰拰寤鸿銆?.PARAMETER Path
    瑕佹壂鎻忕殑姝ｆ枃鏂囦欢璺緞
.EXAMPLE
    .\scan-quality.ps1 -Path "{涔﹀悕}/姝ｆ枃/绗?绔?txt"
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
# 1. 鎯呯华鍛婄煡 鈥?鐩存帴鍛婅瘔璇昏€呰鑹叉儏缁殑鍙ュ瓙
# ============================================
$emotionTellPatterns = @(
    '濂瑰緢绱у紶', '浠栧緢绱у紶', '濂瑰緢瀹虫€?, '浠栧緢瀹虫€?, '濂瑰緢鎰ゆ€?, '浠栧緢鎰ゆ€?,
    '濂瑰緢浼ゅ績', '浠栧緢浼ゅ績', '濂瑰緢缁濇湜', '浠栧緢缁濇湜', '濂瑰緢闇囨儕', '浠栧緢闇囨儕',
    '濂瑰緢鎯婅', '浠栧緢鎯婅', '濂瑰緢灏村艾', '浠栧緢灏村艾', '濂瑰緢鏃犲', '浠栧緢鏃犲',
    '濂规澗浜嗗彛姘?, '浠栨澗浜嗗彛姘?, '濂瑰績閲屼竴绱?, '浠栧績閲屼竴绱?,
    '濂瑰績璺虫紡浜嗕竴鎷?, '浠栧績璺虫紡浜嗕竴鎷?, '濂瑰績璺冲姞閫?, '浠栧績璺冲姞閫?,
    '濂硅剳瀛愬棥鐨勪竴澹?, '浠栬剳瀛愬棥鐨勪竴澹?, '濂硅剳瀛愪竴鐗囨贩涔?, '浠栬剳瀛愪竴鐗囨贩涔?,
    '濂硅剳瀛愪竴鐗囩┖鐧?, '浠栬剳瀛愪竴鐗囩┖鐧?, '濂规暣涓汉鍍典綇', '浠栨暣涓汉鍍典綇',
    '濂瑰悗鑳屼竴鍑?, '浠栧悗鑳屼竴鍑?, '濂瑰悗鑳屽彂鍑?, '浠栧悗鑳屽彂鍑?,
    '濂硅吙鏈夌偣杞?, '浠栬吙鏈夌偣杞?, '濂规墜鎸囧彂鍑?, '浠栨墜鎸囧彂鍑?,
    '鎭愭儳浠庤剼搴?, '绱у紶寰楁墜蹇?, '瀹虫€曞緱鎵嬪績'
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
# 2. 杩囨浮鍙?鈥?鍦烘櫙鍒囨崲鐨勯摵鍨?# ============================================
$transitionPatterns = @(
    '^\s*濂圭珯璧锋潵', '^\s*浠栫珯璧锋潵', '^\s*濂硅浆韬?, '^\s*浠栬浆韬?,
    '^\s*濂硅蛋鍑?, '^\s*浠栬蛋鍑?, '^\s*濂硅蛋杩?, '^\s*浠栬蛋杩?,
    '^\s*濂瑰洖鍒?, '^\s*浠栧洖鍒?, '^\s*濂规潵鍒?, '^\s*浠栨潵鍒?,
    '^\s*绗簩澶?, '^\s*绗簩澶╂棭涓?, '^\s*绗簩澶╀笅鍗?,
    '^\s*涓夊ぉ鍚?, '^\s*杩囦簡鍑犲ぉ', '^\s*杩囦簡寰堜箙',
    '^\s*鍌嶆櫄', '^\s*娣卞', '^\s*鍑屾櫒'
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
# 3. 瑙ｉ噴 鈥?鍛婅瘔璇昏€呬负浠€涔?# ============================================
$explainPatterns = @(
    '鍥犱负.*鎵€浠?, '鍘熷洜鏄?, '涔嬫墍浠?*鏄洜涓?,
    '濂硅繖涔堝仛鏄洜涓?, '浠栬繖涔堝仛鏄洜涓?,
    '濂圭煡閬?*鎵€浠?, '浠栫煡閬?*鎵€浠?,
    '濂规槑鐧?*鎵€浠?, '浠栨槑鐧?*鎵€浠?
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
# 4. 閲嶅鎯呯华 鈥?鍚屼竴娈甸噷澶氫釜鎯呯华琛ㄨ揪
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

$emotionKeywords = '绱у紶|瀹虫€晐鎰ゆ€抾浼ゅ績|缁濇湜|闇囨儕|鎯婅|灏村艾|鏃犲|蹇冭烦|鍙戞姈|鍙戝噳|鍍典綇|绌虹櫧|鍡?

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
# 5. 澶氫綑瀵硅瘽鏍囩
# ============================================
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i].Trim()
    if ($line.Length -eq 0) { continue }
    # Pattern: "dialogue" + 浠栬/濂硅 (when context already makes speaker clear)
    if ($line -match '^["銆宂.*["銆峕\s*[锛?]?\s*(浠東濂?(璇磡闂畖绛攟閬搢鍠妡鍙?') {
        # Check if previous line has dialogue from the other person (context makes it clear)
        if ($i -gt 0) {
            $prevLine = $lines[$i-1].Trim()
            if ($prevLine -match '^["銆宂.*["銆峕') {
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
