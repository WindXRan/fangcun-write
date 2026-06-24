# download_book.ps1
# 单本下载番茄小说（纯 HTTP API，不依赖 Chrome/CDP）
# 支持：书名搜索、book_id、番茄链接
#
# 用法:
#   powershell -ExecutionPolicy Bypass -File download_book.ps1 -Query "惊华庭"
#   powershell -ExecutionPolicy Bypass -File download_book.ps1 -Query "7611913437316140057"
#   powershell -ExecutionPolicy Bypass -File download_book.ps1 -Query "https://fanqienovel.com/page/7611913437316140057"

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,                # 书名、book_id 或番茄链接
    [int]$ServerPort = 0,          # 0=自动检测
    [int]$MaxWaitSeconds = 300,
    [string]$Range,                # 章节范围，如 "1-50"
    [string]$Author,               # 归档作者名（可选，留空自动检测）
    [switch]$NoArchive,
    [switch]$KeepServer = $true    # 默认常驻 server，不自动关闭
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

function Parse-BookId($rawInput) {
    $trimmed = $rawInput.Trim()
    # 纯数字
    if ($trimmed -match '^\d+$') { return $trimmed }
    # URL 中的 book_id
    if ($trimmed -match 'book_id=(\d+)') { return $Matches[1] }
    if ($trimmed -match 'bookId=(\d+)') { return $Matches[1] }
    # /page/ID
    if ($trimmed -match '/page/(\d+)') { return $Matches[1] }
    return $null
}

function Wait-Downloads($port, $maxWait) {
    Write-Step "等待下载完成（最长 $maxWait 秒）"
    $startTime = Get-Date

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
                    Write-Warn "任务失败"
                    foreach ($f in $failed) {
                        Write-Err "  $($f.title): $($f.message)"
                    }
                }
                if ($done.Count -gt 0) {
                    $d = $done[0]
                    $saved = if ($d.progress) { $d.progress.saved_chapters } else { 0 }
                    $total = if ($d.progress) { $d.progress.chapter_total } else { 0 }
                    Write-Ok "下载完成: $($d.title) ($saved/$total 章)"
                }
                return $done.Count
            }

            $r = $running[0]
            $saved = if ($r.progress) { $r.progress.saved_chapters } else { 0 }
            $total = if ($r.progress) { $r.progress.chapter_total } else { 0 }
            $pct = if ($total -gt 0) { [math]::Round($saved/$total*100) } else { 0 }
            Write-Host "    $($r.title): $saved/$total ($pct%)" -ForegroundColor Gray
        } catch {}

        Start-Sleep -Seconds 3
    }
    return 0
}

# ============================================================
# Main
# ============================================================

$port = Ensure-Server
$baseUrl = "http://127.0.0.1:$port"

# 判断输入类型
$bookId = Parse-BookId $Query

if ($bookId) {
    # 直接用 book_id
    Write-Step "使用 book_id: $bookId"
} else {
    # 书名搜索
    Write-Step "搜索: $Query"
    try {
        $searchResp = Invoke-WebRequest "$baseUrl/api/search?q=$([Uri]::EscapeDataString($Query))" -UseBasicParsing -TimeoutSec 15
        $searchData = $searchResp.Content | ConvertFrom-Json
    } catch {
        Write-Err "搜索失败: $_"
        exit 1
    }

    if ($searchData.items.Count -eq 0) {
        Write-Err "未找到结果: $Query"
        exit 1
    }

    # 精确匹配优先
    $match = $searchData.items | Where-Object { $_.title -eq $Query } | Select-Object -First 1
    if (-not $match) {
        $match = $searchData.items | Where-Object { $_.title -like "*$Query*" } | Select-Object -First 1
    }
    if (-not $match) {
        $match = $searchData.items[0]
    }

    $bookId = $match.book_id
    $bookName = $match.title
    $Author = $match.author
    Write-Host "    匹配: $bookName (作者: $Author, ID: $bookId)" -ForegroundColor Green
}

# 预览（可选，获取书名和封面）
Write-Step "获取书籍信息"
$coverUrl = $null
try {
    $previewResp = Invoke-WebRequest "$baseUrl/api/preview/$bookId" -UseBasicParsing -TimeoutSec 15
    $preview = $previewResp.Content | ConvertFrom-Json
    $bookName = $preview.book_name
    if (-not $Author) { $Author = $preview.author }
    $chapterCount = $preview.chapter_count
    $coverUrl = $preview.cover
    Write-Ok "$bookName (作者: $Author, $chapterCount 章)"
} catch {
    Write-Warn "预览失败，将直接下载"
    $bookName = $bookId
}

# 创建下载任务
Write-Step "创建下载任务"
$payload = @{ book_id = $bookId }

if ($Range) {
    $parts = $Range -split '-'
    if ($parts.Count -eq 2) {
        $payload.range_start = [int]$parts[0]
        $payload.range_end = [int]$parts[1]
        Write-Host "    范围: $($parts[0])-$($parts[1])" -ForegroundColor Gray
    }
}

try {
    $body = $payload | ConvertTo-Json -Compress
    $null = Invoke-WebRequest "$baseUrl/api/jobs" -Method POST -ContentType "application/json" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing -TimeoutSec 15
    Write-Ok "任务已提交"
} catch {
    Write-Err "提交失败: $_"
    exit 1
}

# 等待完成
$completed = Wait-Downloads $port $MaxWaitSeconds

# 归档
if (-not $NoArchive -and $completed -gt 0) {
    Write-Step "归档"
    
    # 查找下载器输出的jsonl文件
    $jsonlFiles = @()
    $jsonlFiles += Get-ChildItem "$SkillDir\$bookId\downloaded_chapters.jsonl" -ErrorAction SilentlyContinue
    $jsonlFiles += Get-ChildItem "$SkillDir\downloads\$bookId\downloaded_chapters.jsonl" -ErrorAction SilentlyContinue
    $jsonlFiles += Get-ChildItem "$SkillDir\*\downloaded_chapters.jsonl" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) }
    $jsonlFiles = $jsonlFiles | Sort-Object LastWriteTime -Descending | Select-Object -Unique
    
    # 删除epub文件（下载器bug，配置txt但仍输出epub）
    Get-ChildItem "$SkillDir\*.epub" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) } | Remove-Item -Force

    if ($jsonlFiles) {
        $jsonlFile = $jsonlFiles[0]
        $bookDir = $jsonlFile.Directory
        
        # 从status.json读取正确信息
        $statusFile = Join-Path $bookDir "status.json"
        if (Test-Path $statusFile) {
            $statusData = Get-Content $statusFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($statusData.book_name) { $bookName = $statusData.book_name }
            if ($statusData.author) { $Author = $statusData.author }
            Write-Ok "从status.json读取: $bookName (作者: $Author)"
        }
        
        if (-not $Author) { $Author = "未知作者" }
        if (-not $bookName) { $bookName = $bookId }
        
        # 标准化路径: projects/{作者}/{书名}/
        $safeAuthor = $Author -replace '[\\/:*?"<>|]', '_'
        $safeBookName = $bookName -replace '[\\/:*?"<>|]', '_'
        $projectsDir = "$SkillDir\projects"
        $archiveDir = "$projectsDir\$safeAuthor\$safeBookName"
        Write-Host "    目录: $archiveDir" -ForegroundColor Gray
        New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        
        # 从jsonl转换为txt
        Write-Step "转换 → txt"
        $convertScript = "$SkillDir\scripts\jsonl_to_txt.py"
        $txtPath = "$archiveDir\$safeBookName.txt"
        $convertCmd = "python `"$convertScript`" `"$($jsonlFile.FullName)`" `"$txtPath`" `"$bookName`" `"$Author`" `"$statusFile`""
        $convertResult = Invoke-Expression $convertCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "$safeBookName.txt -> projects/$safeAuthor/$safeBookName/"
        } else {
            Write-Err "转换失败: $convertResult"
        }
        
        # 复制status.json
        Copy-Item $statusFile "$archiveDir\status.json" -Force
        Write-Ok "status.json -> projects/$safeAuthor/$safeBookName/"
        
        # 复制封面
        $coverFile = Join-Path $bookDir "cover.png"
        if (Test-Path $coverFile) {
            Copy-Item $coverFile "$archiveDir\cover.png" -Force
            Write-Ok "cover.png -> projects/$safeAuthor/$safeBookName/"
        }
        
        # 清理下载器缓存
        Write-Step "清理下载器缓存"
        Remove-Item $bookDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已清理: $bookDir"
    } else {
        Write-Warn "未找到下载的jsonl文件"
    }
}

# 清理
if (-not $KeepServer) {
    Write-Step "清理进程"
    Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
}

Write-Host "`n========================================" -ForegroundColor Green
if ($completed -gt 0) {
    Write-Host "下载完成！" -ForegroundColor Green
    if (-not $NoArchive) {
        Write-Host "  归档: projects/$safeAuthor/$safeBookName"
    }
} else {
    Write-Host "下载未成功完成" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Green
