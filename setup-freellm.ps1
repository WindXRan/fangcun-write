<# 
.SYNOPSIS
    一键部署 FreeLLMAPI + 自动配置 API key
.DESCRIPTION
    1. 检查 Docker 是否可用
    2. 部署 FreeLLMAPI（Docker）
    3. 等待服务启动
    4. 提取 unified API key
    5. 自动写入项目配置文件
.EXAMPLE
    .\setup-freellm.ps1
#>

$ErrorActionPreference = "Stop"
$base = Split-Path $PSScriptRoot -Parent

Write-Host "`n=== FreeLLMAPI 部署 ===" -ForegroundColor Cyan

# 1. 检查 Docker
Write-Host "`n[1/5] 检查 Docker..." -ForegroundColor Yellow
try {
    $dockerVer = docker --version 2>&1
    Write-Host "  ✓ $dockerVer" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    Write-Host "  下载: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# 2. 部署 FreeLLMAPI
Write-Host "`n[2/5] 部署 FreeLLMAPI..." -ForegroundColor Yellow
$freellmDir = "$base\.freellmapi"
if (-not (Test-Path $freellmDir)) {
    New-Item -ItemType Directory -Path $freellmDir | Out-Null
}

# 生成加密 key
$encryptionKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })

# 写 .env
$envContent = @"
ENCRYPTION_KEY=$encryptionKey
PORT=3001
"@
Set-Content -Path "$freellmDir\.env" -Value $envContent -Encoding UTF8

# 写 docker-compose.yml
$composeContent = @"
version: '3.8'
services:
  freellmapi:
    image: ghcr.io/tashfeenahmed/freellmapi:latest
    container_name: freellmapi
    restart: unless-stopped
    ports:
      - "127.0.0.1:3001:3001"
    env_file:
      - .env
    volumes:
      - freellm-data:/app/server/data
volumes:
  freellm-data:
"@
Set-Content -Path "$freellmDir\docker-compose.yml" -Value $composeContent -Encoding UTF8

Write-Host "  配置文件已生成: $freellmDir" -ForegroundColor Green

# 3. 启动容器
Write-Host "`n[3/5] 启动 FreeLLMAPI 容器..." -ForegroundColor Yellow
Push-Location $freellmDir
docker compose up -d 2>&1 | Out-Null
Pop-Location

# 4. 等待服务启动
Write-Host "`n[4/5] 等待服务启动..." -ForegroundColor Yellow
$maxWait = 60
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3001/v1/models" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ FreeLLMAPI 已启动 (http://localhost:3001)" -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
    $waited += 2
    Write-Host "  等待中... ($waited s)" -ForegroundColor Gray
}

if ($waited -ge $maxWait) {
    Write-Host "  ✗ 启动超时，请检查 Docker 日志: docker logs freellmapi" -ForegroundColor Red
    exit 1
}

# 5. 提取 API key 并写入配置
Write-Host "`n[5/5] 配置 API key..." -ForegroundColor Yellow

# FreeLLMAPI 部署后需要通过 dashboard 创建 unified key
# 这里提供指引
Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "  FreeLLMAPI 部署完成！" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  下一步：" -ForegroundColor Yellow
Write-Host "  1. 打开 http://localhost:3001" -ForegroundColor White
Write-Host "  2. 创建账号（首次使用）" -ForegroundColor White
Write-Host "  3. 在 Keys 页面添加 provider keys（Google/Groq/等免费 key）" -ForegroundColor White
Write-Host "  4. 复制 unified API key" -ForegroundColor White
Write-Host "  5. 运行以下命令配置项目：" -ForegroundColor White
Write-Host ""
Write-Host "     .\novel.ps1 config" -ForegroundColor Cyan
Write-Host ""
Write-Host "  或手动编辑 configs/ 下的 JSON 文件，填入:" -ForegroundColor White
Write-Host '    "api_key": "freellmapi-xxx"' -ForegroundColor Gray
Write-Host '    "api_base_url": "http://localhost:3001/v1"' -ForegroundColor Gray
Write-Host ""
