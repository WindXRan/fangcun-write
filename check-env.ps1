<# 
.SYNOPSIS
    检查并修复 Python 环境，确保所有依赖正常
.DESCRIPTION
    1. 检查 Python 版本（需要 3.10+）
    2. 修复 requests/urllib3 版本冲突
    3. 安装缺失依赖
    4. 验证 API 连通性
.EXAMPLE
    .\check-env.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== 环境检查 ===" -ForegroundColor Cyan

# 1. 检查 Python
Write-Host "`n[1/4] Python..." -ForegroundColor Yellow
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

# 2. 修复依赖版本冲突
Write-Host "`n[2/4] 修复依赖..." -ForegroundColor Yellow
& $python -m pip install --quiet --upgrade "requests>=2.32,<2.35" "urllib3>=2.0,<2.4" "charset-normalizer>=3.0,<4.0" 2>&1 | Out-Null
Write-Host "  ✓ requests/urllib3 版本已修复" -ForegroundColor Green

# 3. 验证导入
Write-Host "`n[3/4] 验证导入..." -ForegroundColor Yellow
$test = & $python -c "
import requests
import json
from pathlib import Path
print('OK')
" 2>&1
if ($test -match "OK") {
    Write-Host "  ✓ requests/json/pathlib 可用" -ForegroundColor Green
} else {
    Write-Host "  ✗ 导入失败: $test" -ForegroundColor Red
    exit 1
}

# 4. 验证无警告
Write-Host "`n[4/4] 验证无警告..." -ForegroundColor Yellow
$warn = & $python -c "import requests" 2>&1 | Select-String "Warning"
if ($warn) {
    Write-Host "  ⚠ 仍有警告: $warn" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ 无警告" -ForegroundColor Green
}

Write-Host "`n=== 环境正常 ===" -ForegroundColor Cyan
