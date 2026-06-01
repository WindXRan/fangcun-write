# de-ai-numbers.ps1
# 数字模糊化：将精确数字改为模糊表达
# 用法：powershell -ExecutionPolicy Bypass -File de-ai-numbers.ps1 -Path "文件路径" [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [string]$Path,
    [switch]$DryRun
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (!(Test-Path $Path)) {
    Write-Output "ERROR: 文件不存在 $Path"
    exit 1
}

$content = Get-Content $Path -Raw -Encoding UTF8
$original = $content

# 对话行保留标记
$lines = $content -split "`n"
$newLines = @()
$changeCount = 0

foreach ($line in $lines) {
    # 对话行跳过
    if ($line -match '[\u201c\u201d\u300c\u300d""]') {
        $newLines += $line
        continue
    }

    $orig = $line

    # 1. 数字 + 米/里/尺/丈/公里 → 加"左右"
    $line = $line -replace '(\d+)(?=[米里尺丈公里厘米])', '$1{左右}'

    # 2. 数字 + 秒 → X来秒（<=99秒）
    $line = $line -replace '(\d{1,2})秒(?!\w)', '${1}来秒'

    # 3. 数量 + 两银子 → 几两银子
    $line = $line -replace '([一二两三四五六七八九十\d])两银子', '几两银子'

    # 4. 数字 + 天/日 → X来天
    $line = $line -replace '(\d{1,2})[天日](?!\w)', '${1}来天'

    # 5. 数字 + 步 → 步左右
    $line = $line -replace '(\d+)步(?!\w)', '${1}步左右'

    if ($line -ne $orig) {
        $changeCount++
    }

    $newLines += $line
}

$content = $newLines -join "`n"

# 替换占位符
$content = $content -replace '{左右}', '左右'

if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "修改: ~$diff 处字符, $changeCount 行"
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path ($changeCount 行修改)"
}
