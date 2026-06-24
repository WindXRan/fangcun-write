# download_by_author.ps1
# 按作者批量下载番茄小说（纯 HTTP API，不依赖 Chrome/CDP）
# 用法: powershell -ExecutionPolicy Bypass -File download_by_author.ps1 -Author "初点点"

param(
    [Parameter(Mandatory=$true)]
    [string]$Author,
    [int]$ServerPort = 0,          # 0=自动检测
    [int]$MaxWaitSeconds = 600,
    [string]$Range,                # 可选：章节范围，如 "1-50"，留空下载全部
    [switch]$NoArchive,            # 跳过归档步骤
    [switch]$KeepServer            # 完成后不关闭 server
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SkillDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "    ERROR: $msg" -ForegroundColor Red }

function Get-ServerPort {
    if ($ServerPort -ne 0) { return $ServerPort }
    $logFile = Get-ChildItem "$SkillDir\logs\*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($logFile) {
        $logContent = Get-Content $logFile.FullName -Raw
        if ($logContent -match 'listening on.*?(\d{4,5})') { return [int]$Matches[1] }
    }
    return 0
}

function Ensure-Server {
    Write-Step "检查 TomatoNovelDownloader server"
    $port = Get-ServerPort
    if ($port -ne 0) {
        try {
            $null = Invoke-WebRequest "http://127.0.0.1:$port/api/status" -UseBasicParsing -TimeoutSec 3
            Write-Ok "Server 已运行，端口: $port"
            return $port
        } catch {}
    }

    Write-Host "    Server 未运行，正在启动..."
    Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1

    $exe = "$SkillDir\TomatoNovelDownloader-Win64-v2.4.11.exe"
    if (!(Test-Path $exe)) { Write-Err "下载器不存在: $exe"; exit 1 }

    Start-Process -FilePath $exe -ArgumentList "--data-dir", $SkillDir, "--server" `
        -WorkingDirectory $SkillDir -WindowStyle Hidden
    Start-Sleep -Seconds 5

    $port = Get-ServerPort
    if ($port -eq 0) { Write-Err "无法检测 server 端口"; exit 1 }
    Write-Ok "Server 已启动，端口: $port"
    return $port
}

function Wait-Downloads($port, $maxWait) {
    Write-Step "等待下载完成（最长 $maxWait 秒）"
    $startTime = Get-Date
    $lastRunning = @()

    while ($true) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        if ($elapsed -gt $maxWait) {
            Write-Warn "等待超时"
            break
        }

        try {
            $jobsResp = Invoke-WebRequest "http://127.0.0.1:$port/api/jobs" -UseBasicParsing -TimeoutSec 5
            $jobs = $jobsResp.Content | ConvertFrom-Json

            $running = @($jobs.items | Where-Object { $_.state -eq "running" -or $_.state -eq "queued" })
            $failed = @($jobs.items | Where-Object { $_.state -eq "failed" })
            $done = @($jobs.items | Where-Object { $_.state -eq "done" })

            if ($running.Count -eq 0) {
                if ($failed.Count -gt 0) {
                    Write-Warn "有 $($failed.Count) 个任务失败"
                    foreach ($f in $failed) {
                        Write-Err "  失败: $($f.title) - $($f.message)"
                    }
                }
                if ($done.Count -gt 0) {
                    Write-Ok "所有下载已完成 ($($done.Count) 本)"
                }
                return $done.Count
            }

            $statusLine = ($running | ForEach-Object {
                $saved = if ($_.progress) { $_.progress.saved_chapters } else { 0 }
                $total = if ($_.progress) { $_.progress.chapter_total } else { 0 }
                "$($_.title): $saved/$total"
            }) -join " | "

            # 只在状态变化时输出
            $currentHash = $statusLine.GetHashCode()
            if ($currentHash -ne ($lastRunning -join "").GetHashCode()) {
                Write-Host "    $statusLine" -ForegroundColor Gray
                $lastRunning = $running
            }
        } catch {
            Write-Warn "获取任务状态失败: $_"
        }

        Start-Sleep -Seconds 5
    }
    return 0
}

# ============================================================
# Main
# ============================================================

$port = Ensure-Server
$baseUrl = "http://127.0.0.1:$port"

# Step 1: 搜索作者
Write-Step "搜索: $Author"
try {
    $searchResp = Invoke-WebRequest "$baseUrl/api/search?q=$([Uri]::EscapeDataString($Author))" -UseBasicParsing -TimeoutSec 15
    $searchData = $searchResp.Content | ConvertFrom-Json
} catch {
    Write-Err "搜索失败: $_"
    exit 1
}

$books = @($searchData.items | Where-Object { $_.author -eq $Author })
if ($books.Count -eq 0) {
    # 模糊匹配：包含关键词即可
    $books = @($searchData.items | Where-Object { $_.author -like "*$Author*" -or $_.title -like "*$Author*" })
}

if ($books.Count -eq 0) {
    Write-Err "未找到作者 '$Author' 的作品"
    exit 1
}

Write-Host "    找到 $($books.Count) 本书:" -ForegroundColor Green
foreach ($b in $books) {
    Write-Host "      - $($b.title) ($($b.book_id))" -ForegroundColor Gray
}

# Step 2: 创建下载任务
Write-Step "创建下载任务"
$submitted = 0
foreach ($b in $books) {
    $payload = @{ book_id = $b.book_id }

    if ($Range) {
        $parts = $Range -split '-'
        if ($parts.Count -eq 2) {
            $payload.range_start = [int]$parts[0]
            $payload.range_end = [int]$parts[1]
        }
    }

    try {
        $body = $payload | ConvertTo-Json -Compress
        $null = Invoke-WebRequest "$baseUrl/api/jobs" -Method POST -ContentType "application/json" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing -TimeoutSec 15
        $submitted++
        Write-Ok "已提交: $($b.title)"
    } catch {
        Write-Err "提交失败: $($b.title) - $_"
    }
}

if ($submitted -eq 0) {
    Write-Err "没有任务提交成功"
    exit 1
}

# Step 3: 等待完成
$completed = Wait-Downloads $port $MaxWaitSeconds

# Step 4: 归档
if (-not $NoArchive) {
    Write-Step "归档下载文件"
    $convertScript = "$SkillDir\scripts\jsonl_to_txt.py"
    
    # 删除epub文件（下载器bug，配置txt但仍输出epub）
    Get-ChildItem "$SkillDir\*.epub" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } | Remove-Item -Force
    
    # 查找所有下载的 jsonl 文件（最近5分钟内）
    $jsonlFiles = Get-ChildItem "$SkillDir\*\downloaded_chapters.jsonl" -ErrorAction SilentlyContinue | 
        Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
        Sort-Object LastWriteTime -Descending
    
    if (-not $jsonlFiles) {
        $jsonlFiles = Get-ChildItem "$SkillDir\downloads\*\downloaded_chapters.jsonl" -ErrorAction SilentlyContinue | 
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } |
            Sort-Object LastWriteTime -Descending
    }
    
    if ($jsonlFiles) {
        foreach ($jsonlFile in $jsonlFiles) {
            $bookDir = $jsonlFile.Directory
            
            # 从 status.json 读取书籍信息
            $statusFile = Join-Path $bookDir "status.json"
            $bookName = $bookDir.Name
            $authorName = $Author
            
            if (Test-Path $statusFile) {
                $statusData = Get-Content $statusFile -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($statusData.book_name) { $bookName = $statusData.book_name }
                if ($statusData.author) { $authorName = $statusData.author }
            }
            
            $safeAuthor = $authorName -replace '[\\/:*?"<>|]', '_'
            $safeBookName = $bookName -replace '[\\/:*?"<>|]', '_'
            $archiveDir = "$SkillDir\projects\$safeAuthor\$safeBookName"
            New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
            
            # 转换 jsonl → txt
            $txtPath = "$archiveDir\$safeBookName.txt"
            $convertCmd = "python `"$convertScript`" `"$($jsonlFile.FullName)`" `"$txtPath`" `"$bookName`" `"$authorName`" `"$statusFile`""
            $convertResult = Invoke-Expression $convertCmd 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "$safeBookName.txt -> projects/$safeAuthor/$safeBookName/"
            } else {
                Write-Err "转换失败: $convertResult"
                continue
            }
            
            # 复制 status.json
            if (Test-Path $statusFile) {
                Copy-Item $statusFile "$archiveDir\status.json" -Force
            }
            
            # 复制封面
            $coverFile = Join-Path $bookDir "cover.png"
            if (Test-Path $coverFile) {
                Copy-Item $coverFile "$archiveDir\cover.png" -Force
            }
            
            # 清理下载器缓存
            Remove-Item $bookDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    } else {
        Write-Warn "未找到下载的 jsonl 文件"
    }
}

# Step 5: 清理
if (-not $KeepServer) {
    Write-Step "清理进程"
    Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "完成！共提交 $submitted 本，成功 $completed 本" -ForegroundColor Green
if (-not $NoArchive) {
    Write-Host "  归档: $SkillDir\projects\$Author\"
}
Write-Host "========================================" -ForegroundColor Green
