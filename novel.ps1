<# 
.SYNOPSIS
    story-engine / source-engine / drama-engine 统一入口
.DESCRIPTION
    简化命令，自动选择正确的引擎和参数
.EXAMPLE
    .\novel.ps1 analyze                              # 源书分析（source-engine）
    .\novel.ps1 open                                   # 开书（story-engine）
    .\novel.ps1 write --start 1 --end 10               # 写章
    .\novel.ps1 compare --start 1 --end 3              # 对比
    .\novel.ps1 drama --start 1 --end 10               # 写剧本（drama-engine）
    .\novel.ps1 status                                 # 查看状态
#>

param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("analyze", "open", "write", "compare", "trim", "expand", "drama", "drama-status", "status", "export")]
    [string]$Action,
    
    [string]$Config,
    [int]$Start = 1,
    [int]$End = 3,
    [int]$Workers = 5,
    [switch]$SkipConfirm,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$base = Split-Path $PSScriptRoot -Parent

# 自动查找 config
if (-not $Config) {
    $configs = Get-ChildItem "$base\configs\*.json" -ErrorAction SilentlyContinue
    if ($configs.Count -eq 1) {
        $Config = $configs[0].FullName
    } elseif ($configs.Count -gt 1) {
        Write-Host "找到多个配置文件，请用 --Config 指定:" -ForegroundColor Yellow
        $configs | ForEach-Object { Write-Host "  $($_.Name)" }
        exit 1
    } else {
        Write-Host "未找到配置文件，请在 configs/ 目录创建" -ForegroundColor Red
        exit 1
    }
}

$python = "python"
$skip = if ($SkipConfirm) { "--skip-confirm" } else { "" }
$dry = if ($DryRun) { "--dry-run" } else { "" }

# 设置环境变量
if (-not $env:API_KEY) {
    Write-Host "⚠ API_KEY 未设置" -ForegroundColor Yellow
}

switch ($Action) {
    "analyze" {
        Write-Host "源书分析 (source-engine)..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\source-engine\tools\pipeline.py" --config $Config --phase all --workers $Workers
    }
    "open" {
        Write-Host "开书 (story-engine)..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase open_book --skip-confirm
    }
    "write" {
        Write-Host "写章 (story-engine) 第$Start-$End章..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase write --start $Start --end $End --skip-confirm
    }
    "compare" {
        Write-Host "对比审核 (story-engine) 第$Start-$End章..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase compare --start $Start --end $End --skip-confirm
    }
    "trim" {
        Write-Host "精简 (story-engine)..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase trim --start $Start --end $End
    }
    "expand" {
        Write-Host "扩写 (story-engine)..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase expand --start $Start --end $End
    }
    "drama" {
        Write-Host "写剧本 (drama-engine) 第$Start-$End集..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\drama-engine\tools\pipeline.py" --config $Config --phase script --start $Start --end $End --skip-confirm
    }
    "drama-status" {
        & $python "$base\.agents\skills\drama-engine\tools\pipeline.py" --config $Config --phase status
    }
    "status" {
        # 显示所有引擎的状态
        Write-Host "=== story-engine ===" -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase write --start 1 --end 1 --skip-confirm 2>&1 | Select-String "STATE|chapters/"
        Write-Host "`n=== source-engine ===" -ForegroundColor Cyan
        & $python "$base\.agents\skills\source-engine\tools\pipeline.py" --config $Config --phase status
    }
    "export" {
        Write-Host "导出..." -ForegroundColor Cyan
        & $python "$base\.agents\skills\story-engine\tools\pipeline.py" --config $Config --phase export
    }
}
