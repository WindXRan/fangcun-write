# setup.ps1 - fangcun-write 安装脚本
# 用法: .\setup.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  fangcun-write 仿写引擎 安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/3] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  错误: 未找到 Python，请先安装 Python 3.10+" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "[2/3] 安装依赖..." -ForegroundColor Yellow
pip install requests --quiet 2>&1 | Out-Null
Write-Host "  OK: requests" -ForegroundColor Green

# 检查 API Key
Write-Host "[3/3] 检查 API Key..." -ForegroundColor Yellow
if ($env:API_KEY) {
    Write-Host "  OK: API Key 已设置" -ForegroundColor Green
} else {
    Write-Host "  警告: API Key 未设置" -ForegroundColor Yellow
    Write-Host "  请运行: `$env:API_KEY = `"sk-xxx`"" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 设置 API Key: `$env:API_KEY = `"sk-xxx`"" -ForegroundColor White
Write-Host "  2. 创建配置: copy configs\example.json configs\mybook.json" -ForegroundColor White
Write-Host "  3. 开始仿写: .\novel.ps1 write --config configs\mybook.json --start 1 --end 10" -ForegroundColor White
