<# 
.SYNOPSIS
    交互式配置向导 - 生成 story-engine / source-engine / drama-engine 配置文件
.EXAMPLE
    .\config.ps1
#>

$ErrorActionPreference = "Stop"
$base = Split-Path $PSScriptRoot -Parent

Write-Host "`n=== 配置向导 ===" -ForegroundColor Cyan

# 1. 选择引擎
Write-Host "`n选择引擎:" -ForegroundColor Yellow
Write-Host "  1) story-engine  (仿写小说)"
Write-Host "  2) drama-engine  (小说转短剧)"
$engineChoice = Read-Host "选择 (1/2)"
$engine = if ($engineChoice -eq "2") { "drama" } else { "story" }

# 2. 源书信息
Write-Host "`n源书信息:" -ForegroundColor Yellow
$author = Read-Host "作者名"
$sourceBook = Read-Host "源书名"

# 3. API 配置
Write-Host "`nAPI 配置:" -ForegroundColor Yellow
$apiKey = Read-Host "API Key (留空用 `$env:API_KEY)"
if (-not $apiKey) { $apiKey = $null }
$apiBase = Read-Host "API Base URL (回车用默认 DeepSeek)"
if (-not $apiBase) { $apiBase = "https://api.deepseek.com/v1" }
$model = Read-Host "模型名 (回车用 deepseek-chat)"
if (-not $model) { $model = "deepseek-chat" }

# 4. 引擎特定配置
if ($engine -eq "story") {
    Write-Host "`n仿写配置:" -ForegroundColor Yellow
    $bookName = Read-Host "新书名 (回车自动生成)"
    if (-not $bookName) { $bookName = "auto" }
    
    $rewritesDir = "projects/$author/$sourceBook/rewrites/$bookName"
    
    $config = @{
        book_name = $bookName
        author = $author
        source_book = $sourceBook
        rewrites_dir = $rewritesDir
        base_dir = $base
        api_key = $apiKey
        api_base_url = $apiBase
        model = $model
        prompt_overrides = @{
            "open-book.md" = @{model = $model}
            "open-book-bookinfo.md" = @{model = $model}
            "open-book-characters.md" = @{model = $model}
            "open-book-world.md" = @{model = $model}
            "open-book-plot.md" = @{model = $model}
            "open-book-concept.md" = @{model = $model}
            "plot-guide.md" = @{model = $model}
            "write-chapter.md" = @{model = $model}
            "style-analyze.md" = @{model = $model}
            "trim-chapter.md" = @{model = $model}
            "expand-chapter.md" = @{model = $model}
            "polish-chapter.md" = @{model = $model}
        }
    }
    
    $configName = "story_${sourceBook}"
} else {
    Write-Host "`n短剧配置:" -ForegroundColor Yellow
    $dramaName = Read-Host "剧本名"
    $episodes = [int](Read-Host "集数 (建议 30-80)")
    $duration = [int](Read-Host "单集时长(分钟, 回车默认2)")
    if (-not $duration) { $duration = 2 }
    $style = Read-Host "风格 (如: 甜宠喜剧/都市爽文)"
    $paywall = Read-Host "付费策略 (回车默认: 前3集免费)"
    if (-not $paywall) { $paywall = "前3集免费，第4集起付费" }
    
    $config = @{
        novel_name = $sourceBook
        drama_name = $dramaName
        source_dir = "projects/$author/$sourceBook/_cache/chapters"
        output_dir = "projects/$author/$sourceBook/drama"
        api_key = $apiKey
        api_base_url = $apiBase
        model = $model
        model_overrides = @{
            "event" = "deepseek-chat"
        }
        project = @{
            episodes = $episodes
            episode_duration = $duration
            chapter_range = @(1, 153)
            platform = "竖屏9:16"
            style = $style
            paywall = $paywall
        }
    }
    
    $configName = "drama_${sourceBook}"
}

# 5. 保存
$configsDir = Join-Path $base "configs"
if (-not (Test-Path $configsDir)) {
    New-Item -ItemType Directory -Path $configsDir | Out-Null
}
$configPath = Join-Path $configsDir "$configName.json"
$config | ConvertTo-Json -Depth 10 | Set-Content -Path $configPath -Encoding UTF8

Write-Host "`n✓ 配置已保存: $configPath" -ForegroundColor Green

# 6. 提示下一步
Write-Host "`n下一步:" -ForegroundColor Yellow
if ($engine -eq "story") {
    Write-Host "  .\novel.ps1 analyze --Config `"$configPath`"" -ForegroundColor White
    Write-Host "  .\novel.ps1 open --Config `"$configPath`"" -ForegroundColor White
    Write-Host "  .\novel.ps1 write --Config `"$configPath`" --start 1 --end 3" -ForegroundColor White
} else {
    Write-Host "  .\novel.ps1 drama --Config `"$configPath`"" -ForegroundColor White
}
Write-Host ""
