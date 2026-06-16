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
    [switch]$KeepServer,
    [switch]$Interactive           # 交互模式：搜索多结果时让用户选
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SkillDir = "C:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\novel-download"

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

    # 如果有多个结果且开启了交互模式
    if ($Interactive -and $searchData.items.Count -gt 1) {
        Write-Host "`n    搜索结果:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $searchData.items.Count; $i++) {
            $b = $searchData.items[$i]
            Write-Host "    [$($i+1)] $($b.title) - $($b.author) ($($b.book_id))" -ForegroundColor Gray
        }
        $choice = Read-Host "    选择编号 (回车默认 1)"
        if ($choice -and [int]::TryParse($choice, [ref]$null)) {
            $idx = [int]$choice - 1
            if ($idx -ge 0 -and $idx -lt $searchData.items.Count) {
                $match = $searchData.items[$idx]
                $bookId = $match.book_id
                $bookName = $match.title
                $Author = $match.author
                Write-Host "    已选择: $bookName" -ForegroundColor Green
            }
        }
    }
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
    if (-not $Author) { $Author = "未知作者" }
    if (-not $bookName) { $bookName = $bookId }

    # 标准化路径: projects/{作者}/{书名}/_cache/
    # 清理文件名中的特殊字符
    $safeAuthor = $Author -replace '[\\/:*?"<>|]', '_'
    $safeBookName = $bookName -replace '[\\/:*?"<>|]', '_'
    $bookDir = "$SkillDir\projects\$safeAuthor\$safeBookName"
    $cacheDir = "$bookDir\_cache"
    New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null

    # 移动 txt 文件（下载器可能保存在 skill 根目录或 downloads 目录）
    $downloadedFiles = @()
    $downloadedFiles += Get-ChildItem "$SkillDir\downloads\*.txt" -ErrorAction SilentlyContinue
    $downloadedFiles += Get-ChildItem "$SkillDir\*.txt" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) }
    $downloadedFiles = $downloadedFiles | Sort-Object LastWriteTime -Descending | Select-Object -Unique
    if ($downloadedFiles) {
        foreach ($f in $downloadedFiles) {
            $targetName = if ($f.Name -match $bookName) { $f.Name } else { "$bookName.txt" }
            $targetPath = "$cacheDir\$targetName"
            Move-Item $f.FullName $targetPath -Force
            Write-Ok "$targetName -> $Author/$bookName/_cache/"
            
            # 修复下载器 bug：去掉重复的章节标题
            # 格式：第X章 标题 第X章 标题 → 第X章 标题
            Write-Step "修复重复标题"
            $content = Get-Content $targetPath -Raw -Encoding UTF8
            $content = [regex]::Replace($content, '(第\d+章\s+.+?)\s+\1', '$1')
            # 去掉重复的卷名
            $content = [regex]::Replace($content, '(第.+?卷.+?)\s+\1\s+\1', '$1')
            Set-Content $targetPath -Value $content -Encoding UTF8 -NoNewline
            Write-Ok "重复标题已修复"
        }
    } else {
        Write-Warn "downloads 目录没有找到 txt 文件"
    }

    # 下载封面
    if ($coverUrl) {
        Write-Step "下载封面"
        try {
            $coverPath = "$cacheDir\cover.jpg"
            Invoke-WebRequest $coverUrl -OutFile $coverPath -UseBasicParsing -TimeoutSec 15
            Write-Ok "cover.jpg -> $Author/$bookName/_cache/"
        } catch {
            Write-Warn "封面下载失败: $_"
        }
    } else {
        Write-Warn "无封面 URL，跳过"
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
    if (-not $NoArchive -and $Author) {
        Write-Host "  归档: $SkillDir\projects\$Author"
    }
} else {
    Write-Host "下载未成功完成" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Green
