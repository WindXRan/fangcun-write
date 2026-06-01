# de-ai-punctuation.ps1
# 标点后处理（规则化部分）：分号/冒号转逗号、破折号转省略号、删除单引号
# 用法：powershell -ExecutionPolicy Bypass -File de-ai-punctuation.ps1 -Path "文件路径" [-DryRun]

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

# 1. 分号 → 逗号
$content = $content -replace '；', '，'

# 2. 冒号 → 逗号（注意：对话中的冒号保留，通过检测是否在引号内）
# 临时保护对话内的冒号
$lines = $content -split "`n"
$newLines = @()
foreach ($line in $lines) {
    if ($line -match '[\u201c\u201d\u300c\u300d""]') {
        # 对话行：保留冒号
        $newLines += $line
    } else {
        # 非对话行：冒号转逗号
        $newLines += $line -replace '：', '，'
    }
}
$content = $newLines -join "`n"

# 3. 顿号 → 逗号
$content = $content -replace '、', '，'

# 4. 破折号(2个或以上) → 省略号
$content = $content -replace '——+', '……'

# 5. 删除单引号（所有变体）
$content = $content -replace "[\u2018\u2019']", ''

# 6. 省略号规范化（多个省略号合并）
$content = $content -replace '……+', '……'

if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "修改: ~$diff 处字符"
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path"
}
