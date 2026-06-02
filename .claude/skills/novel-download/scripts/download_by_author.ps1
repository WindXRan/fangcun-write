# download_by_author.ps1
# 一键按作者批量下载番茄小说
# 用法: powershell -ExecutionPolicy Bypass -File download_by_author.ps1 -Author "初点点"

param(
    [Parameter(Mandatory=$true)]
    [string]$Author,
    [int]$CdpPort = 9222,
    [int]$ServerPort = 0,          # 0=自动检测
    [int]$MaxWaitSeconds = 600,
    [switch]$CopyToStyle           # 下载后自动复制到 story-style
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SkillDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\novel-download"
$StoryStyleBase = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\story-style"

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "    ERROR: $msg" -ForegroundColor Red }

# ============================================================
# Step 1: 启动 server
# ============================================================
Write-Step "启动 TomatoNovelDownloader server"
Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

$exe = "$SkillDir\TomatoNovelDownloader-Win64-v2.4.11.exe"
if (!(Test-Path $exe)) { Write-Err "下载器不存在: $exe"; exit 1 }

Start-Process -FilePath $exe -ArgumentList "--data-dir", $SkillDir, "--server" `
    -WorkingDirectory $SkillDir -WindowStyle Hidden
Start-Sleep -Seconds 5

# 读取端口
if ($ServerPort -eq 0) {
    $logFile = Get-ChildItem "$SkillDir\logs\*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($logFile) {
        $logContent = Get-Content $logFile.FullName -Raw
        if ($logContent -match 'listening on.*?(\d{4,5})') { $ServerPort = [int]$Matches[1] }
    }
}
if ($ServerPort -eq 0) { Write-Err "无法检测 server 端口"; exit 1 }
Write-Ok "Server 端口: $ServerPort"

# ============================================================
# Step 2: 启动 CDP Chrome
# ============================================================
Write-Step "启动 CDP Chrome"
taskkill /F /IM chrome.exe 2>$null
Start-Sleep -Seconds 2

Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList `
    "--remote-debugging-port=$CdpPort", "--user-data-dir=C:\Users\Administrator\chrome-debug-profile", `
    "--no-first-run", "--no-default-browser-check" -WindowStyle Hidden
Start-Sleep -Seconds 5

# 验证
try {
    Invoke-WebRequest "http://127.0.0.1:$CdpPort/json/version" -UseBasicParsing -TimeoutSec 5 | Out-Null
    Write-Ok "CDP Chrome 已启动"
} catch {
    Write-Err "Chrome CDP 连接失败"; exit 1
}

# ============================================================
# Step 3: 搜索作者
# ============================================================
Write-Step "搜索: $Author"
$baseUrl = "http://127.0.0.1:$ServerPort"

agent-browser --cdp $CdpPort open "$baseUrl/#search" 2>$null
Start-Sleep -Seconds 2

agent-browser --cdp $CdpPort type 'input' $Author 2>$null
Start-Sleep -Seconds 1

agent-browser --cdp $CdpPort press "Enter" 2>$null
Start-Sleep -Seconds 5

# ============================================================
# Step 4: 逐本下载
# ============================================================
Write-Step "开始下载"

# 获取搜索结果中的下载按钮
$snapshot = agent-browser --cdp $CdpPort snapshot -i 2>&1
$downloadButtons = $snapshot | Select-String 'button "下载" \[ref=(e\d+)\]' | ForEach-Object { $_.Matches[0].Groups[1].Value }

if ($downloadButtons.Count -eq 0) {
    Write-Err "未找到下载按钮"
    exit 1
}

Write-Host "    找到 $($downloadButtons.Count) 个下载按钮"

$downloaded = 0
foreach ($btnRef in $downloadButtons) {
    # 重新获取快照（refs 会变化）
    $snapshot = agent-browser --cdp $CdpPort snapshot -i 2>&1
    $bookInfo = $snapshot | Select-String 'cell "(.+?)" \[ref=(e\d+)\]' -Context 0,4 | Select-Object -First 1
    
    # 点击下载按钮
    Write-Host "    点击下载按钮 @$btnRef ..."
    agent-browser --cdp $CdpPort click "@$btnRef" 2>$null
    Start-Sleep -Seconds 3

    # 检查预览弹窗
    $fullSnapshot = agent-browser --cdp $CdpPort snapshot 2>&1
    $confirmRef = ($fullSnapshot | Select-String 'button "确认下载" \[ref=(e\d+)\]').Matches[0].Groups[1].Value
    
    if ($confirmRef) {
        agent-browser --cdp $CdpPort click "@$confirmRef" 2>$null
        $downloaded++
        Write-Ok "已提交下载 ($downloaded)"
        Start-Sleep -Seconds 2
    } else {
        Write-Warn "未找到确认按钮，可能已在队列中"
    }
}

# ============================================================
# Step 5: 等待下载完成
# ============================================================
Write-Step "等待下载完成（最长 $MaxWaitSeconds 秒）"
$startTime = Get-Date

while ($true) {
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    if ($elapsed -gt $MaxWaitSeconds) {
        Write-Warn "等待超时"
        break
    }

    try {
        $jobsResp = Invoke-WebRequest "http://127.0.0.1:$ServerPort/api/jobs" -UseBasicParsing -TimeoutSec 5
        $jobs = $jobsResp.Content | ConvertFrom-Json
        
        $running = $jobs.items | Where-Object { $_.state -ne "done" }
        if ($running.Count -eq 0) {
            Write-Ok "所有下载已完成"
            break
        }
        
        $statusLine = ($running | ForEach-Object { "$($_.title): $($_.progress.saved_chapters)/$($_.progress.chapter_total)" }) -join " | "
        Write-Host "    $statusLine" -ForegroundColor Gray
    } catch {
        Write-Warn "获取任务状态失败"
    }
    
    Start-Sleep -Seconds 10
}

# ============================================================
# Step 6: 归档
# ============================================================
Write-Step "归档下载文件"
$authorDir = "$SkillDir\novel-download-authors\$Author"
New-Item -ItemType Directory -Path $authorDir -Force | Out-Null

$downloadedFiles = Get-ChildItem "$SkillDir\downloads\*.txt" -ErrorAction SilentlyContinue
foreach ($f in $downloadedFiles) {
    Move-Item $f.FullName "$authorDir\$($f.Name)" -Force
    Write-Ok "$($f.Name) -> $Author/"
}

# ============================================================
# Step 7: 验证编码 + 复制到 story-style
# ============================================================
Write-Step "验证编码"
$allFiles = Get-ChildItem "$authorDir\*.txt" -ErrorAction SilentlyContinue
$badFiles = @()

foreach ($f in $allFiles) {
    $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
    $head = $content.Substring(0, [Math]::Min(100, $content.Length))
    if ($head -match '[锛€浠涔﹀悕鐩綍]') {
        Write-Err "$($f.Name): 编码损坏"
        $badFiles += $f
    } else {
        Write-Ok "$($f.Name): 编码正常"
    }
}

if ($CopyToStyle) {
    Write-Step "复制到 story-style/$Author/sources/"
    $dstDir = "$StoryStyleBase\$Author\sources"
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null

    $goodFiles = $allFiles | Where-Object { $_ -notin $badFiles }
    foreach ($f in $goodFiles) {
        $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText("$dstDir\$($f.Name)", $content, $utf8NoBom)
        Write-Ok "$($f.Name) -> story-style/$Author/sources/"
    }
}

# ============================================================
# Step 8: 清理
# ============================================================
Write-Step "清理进程"
Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
taskkill /F /IM chrome.exe 2>$null

# ============================================================
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "完成！共下载 $downloaded 本" -ForegroundColor Green
Write-Host "  归档: $authorDir"
Write-Host "========================================" -ForegroundColor Green
