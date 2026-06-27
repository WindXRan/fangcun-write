# novel.ps1 - fangcun-write 快捷命令
# 用法: .\novel.ps1 <command> [options]

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(Position=1)]
    [string]$Config = "configs\example.json",
    
    [int]$Start = 1,
    [int]$End = 10,
    [int]$Workers = 10,
    [switch]$Help
)

$SKILL_DIR = $PSScriptRoot
$PIPELINE = "$SKILL_DIR\tools\pipeline.py"

# 显示帮助
function Show-Help {
    Write-Host ""
    Write-Host "fangcun-write 仿写引擎" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "用法:" -ForegroundColor Yellow
    Write-Host "  .\novel.ps1 <command> [options]" -ForegroundColor White
    Write-Host ""
    Write-Host "命令:" -ForegroundColor Yellow
    Write-Host "  write     写章" -ForegroundColor White
    Write-Host "  compare   对比审核" -ForegroundColor White
    Write-Host "  status    查看状态" -ForegroundColor White
    Write-Host "  export    导出 TXT" -ForegroundColor White
    Write-Host "  help      显示帮助" -ForegroundColor White
    Write-Host ""
    Write-Host "参数:" -ForegroundColor Yellow
    Write-Host "  --config <path>    配置文件路径 (默认: configs\example.json)" -ForegroundColor White
    Write-Host "  --start <n>        起始章 (默认: 1)" -ForegroundColor White
    Write-Host "  --end <n>          结束章 (默认: 10)" -ForegroundColor White
    Write-Host "  --workers <n>      并行数 (默认: 10)" -ForegroundColor White
    Write-Host ""
    Write-Host "示例:" -ForegroundColor Yellow
    Write-Host "  .\novel.ps1 write --config configs\mybook.json --start 1 --end 10" -ForegroundColor White
    Write-Host "  .\novel.ps1 compare --config configs\mybook.json --start 1 --end 10" -ForegroundColor White
    Write-Host "  .\novel.ps1 status --config configs\mybook.json" -ForegroundColor White
    Write-Host ""
}

# 检查配置文件
function Test-Config {
    if (-not (Test-Path $Config)) {
        Write-Host "错误: 配置文件不存在: $Config" -ForegroundColor Red
        Write-Host "请先创建配置: copy configs\example.json $Config" -ForegroundColor Yellow
        exit 1
    }
}

# 检查 API Key
function Test-ApiKey {
    if (-not $env:API_KEY) {
        Write-Host "错误: API Key 未设置" -ForegroundColor Red
        Write-Host "请运行: `$env:API_KEY = `"sk-xxx`"" -ForegroundColor Yellow
        exit 1
    }
}

# 执行命令
function Invoke-Command {
    param([string]$Phase)
    
    Test-Config
    Test-ApiKey
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  执行: $Phase" -ForegroundColor Cyan
    Write-Host "  配置: $Config" -ForegroundColor Cyan
    Write-Host "  范围: $Start - $End" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    python $PIPELINE --config $Config --phase $Phase --start $Start --end $End --workers $Workers
}

# 主逻辑
if ($Help -or -not $Command) {
    Show-Help
    exit 0
}

switch ($Command.ToLower()) {
    "write" {
        Invoke-Command "write"
    }
    "compare" {
        Invoke-Command "compare"
    }
    "status" {
        Test-Config
        python $PIPELINE --config $Config --status
    }
    "export" {
        Test-Config
        python $PIPELINE --config $Config --phase export
    }
    "help" {
        Show-Help
    }
    default {
        Write-Host "未知命令: $Command" -ForegroundColor Red
        Write-Host "运行 .\novel.ps1 help 查看帮助" -ForegroundColor Yellow
        exit 1
    }
}
