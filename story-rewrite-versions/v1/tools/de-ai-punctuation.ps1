# de-ai-punctuation.ps1
# 鏍囩偣鍚庡鐞嗭紙瑙勫垯鍖栭儴鍒嗭級锛氬垎鍙?鍐掑彿杞€楀彿銆佺牬鎶樺彿杞渷鐣ュ彿銆佸垹闄ゅ崟寮曞彿
# 鐢ㄦ硶锛歱owershell -ExecutionPolicy Bypass -File de-ai-punctuation.ps1 -Path "鏂囦欢璺緞" [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [string]$Path,
    [switch]$DryRun
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (!(Test-Path $Path)) {
    Write-Output "ERROR: 鏂囦欢涓嶅瓨鍦?$Path"
    exit 1
}

$content = Get-Content $Path -Raw -Encoding UTF8
$original = $content

# 1. 鍒嗗彿 鈫?閫楀彿
$content = $content -replace '锛?, '锛?

# 2. 鍐掑彿 鈫?閫楀彿锛堟敞鎰忥細瀵硅瘽涓殑鍐掑彿淇濈暀锛岄€氳繃妫€娴嬫槸鍚﹀湪寮曞彿鍐咃級
# 涓存椂淇濇姢瀵硅瘽鍐呯殑鍐掑彿
$lines = $content -split "`n"
$newLines = @()
foreach ($line in $lines) {
    if ($line -match '[\u201c\u201d\u300c\u300d""]') {
        # 瀵硅瘽琛岋細淇濈暀鍐掑彿
        $newLines += $line
    } else {
        # 闈炲璇濊锛氬啋鍙疯浆閫楀彿
        $newLines += $line -replace '锛?, '锛?
    }
}
$content = $newLines -join "`n"

# 3. 椤垮彿 鈫?閫楀彿
$content = $content -replace '銆?, '锛?

# 4. 鐮存姌鍙?2涓垨浠ヤ笂) 鈫?鐪佺暐鍙?$content = $content -replace '鈥斺€?', '鈥︹€?

# 5. 鍒犻櫎鍗曞紩鍙凤紙鎵€鏈夊彉浣擄級
$content = $content -replace "[\u2018\u2019']", ''

# 6. 鐪佺暐鍙疯鑼冨寲锛堝涓渷鐣ュ彿鍚堝苟锛?$content = $content -replace '鈥︹€?', '鈥︹€?

if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "淇敼: ~$diff 澶勫瓧绗?
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path"
}
