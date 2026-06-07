# count-words.ps1 — 番茄标准字数统计
# 用法: .\count-words.ps1 <文件路径> [目标字数] [容差]
# 示例: .\count-words.ps1 "第1章.txt" 1679 200

param(
    [string]$FilePath,
    [int]$Target = 2500,
    [int]$Tolerance = 500
)

if (-not (Test-Path $FilePath)) {
    Write-Host "文件不存在: $FilePath"
    exit 1
}

$content = Get-Content $FilePath -Raw -Encoding UTF8
$chars = ($content -replace '\s', '').Length

Write-Host "番茄字数: $chars | 目标: $Target (±$Tolerance)"

$min = $Target - $Tolerance
$max = $Target + $Tolerance

if ($chars -lt $min) {
    Write-Host "⚠️ 字数不足: $chars < $min"
} elseif ($chars -gt $max) {
    Write-Host "⚠️ 字数超标: $chars > $max"
} else {
    Write-Host "✅ 字数合格"
}
