<#
.SYNOPSIS
    Benchmark 运行脚本 - 自动化试水验证
.DESCRIPTION
    读取 benchmark-config.json，运行指定测试用例，输出结构化报告。
.PARAMETER TestCase
    测试用例 ID（如 sweet-pet），不指定则运行全部
.PARAMETER AblationConfig
    消融配置 ID（no-persona / persona-only / full），默认 full
.EXAMPLE
    .\run-benchmark.ps1 -TestCase sweet-pet -AblationConfig full
#>

param(
    [string]$TestCase = "all",
    [string]$AblationConfig = "full"
)

$config = Get-Content "benchmark-config.json" -Encoding UTF8 -Raw | ConvertFrom-Json

$cases = if ($TestCase -eq "all") { $config.test_cases } else { $config.test_cases | Where-Object { $_.id -eq $TestCase } }

Write-Output "=========================================="
Write-Output "Benchmark 运行报告"
Write-Output "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Output "消融配置: $AblationConfig"
Write-Output "=========================================="

foreach ($case in $cases) {
    Write-Output ""
    Write-Output "--- 测试用例: $($case.name) ($($case.id)) ---"
    Write-Output "源文本: $($case.source_text)"
    Write-Output "Persona: $($case.persona_name) (Type $($case.persona))"
    Write-Output "状态: $($case.notes)"

    # 检查试水文件是否存在
    $outputFile = "仿写试水库/试水_*.txt"
    $existingFiles = Get-ChildItem $outputFile -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if ($existingFiles) {
        Write-Output "最新试水文件: $($existingFiles.Name)"
        Write-Output "运行验证脚本..."
        & ".\tools\validate-aigc.ps1" -Path $existingFiles.FullName
    } else {
        Write-Output "[SKIP] 无试水文件，请先运行仿写"
    }
}

Write-Output ""
Write-Output "=========================================="
Write-Output "Benchmark 完成"
Write-Output "=========================================="
