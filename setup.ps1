<# 
.SYNOPSIS
    一键配置 story-engine / source-engine / drama-engine 环境
.DESCRIPTION
    1. 检查 Python 版本
    2. 安装依赖（requests）
    3. 创建项目目录结构
    4. 生成示例配置文件
.EXAMPLE
    .\setup.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== story-engine 环境配置 ===" -ForegroundColor Cyan

# 1. 检查 Python
Write-Host "`n[1/4] 检查 Python..." -ForegroundColor Yellow
$python = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $python = $cmd
                Write-Host "  ✓ $ver ($cmd)" -ForegroundColor Green
                break
            }
        }
    } catch {}
}
if (-not $python) {
    Write-Host "  ✗ 需要 Python 3.10+" -ForegroundColor Red
    exit 1
}

# 2. 安装依赖
Write-Host "`n[2/4] 安装依赖..." -ForegroundColor Yellow
& $python -m pip install -q requests 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ requests 已安装" -ForegroundColor Green
} else {
    Write-Host "  ✗ pip install 失败" -ForegroundColor Red
    exit 1
}

# 3. 检查 API Key
Write-Host "`n[3/4] 检查 API Key..." -ForegroundColor Yellow
if ($env:API_KEY) {
    Write-Host "  ✓ API_KEY 已设置 ($($env:API_KEY.Substring(0,8))...)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ API_KEY 未设置，运行前请执行: `$env:API_KEY = 'sk-xxx'" -ForegroundColor Yellow
}

# 4. 检查项目结构
Write-Host "`n[4/4] 检查项目结构..." -ForegroundColor Yellow
$base = Split-Path $PSScriptRoot -Parent
$skills = @("story-engine", "source-engine", "drama-engine")
foreach ($s in $skills) {
    $skillPath = Join-Path $base ".agents\skills\$s"
    if (Test-Path $skillPath) {
        Write-Host "  ✓ $s" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $s 缺失" -ForegroundColor Red
    }
}

Write-Host "`n=== 配置完成 ===" -ForegroundColor Cyan
Write-Host "用法: $python .agents/skills/story-engine/tools/pipeline.py --config {config.json} --phase {phase}" -ForegroundColor White
Write-Host ""
