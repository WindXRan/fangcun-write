param(
  [string]$InputDir = "闻栖",
  [string]$OutputDir = "闻栖/_analysis"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$books = Get-ChildItem "$InputDir/*.txt" -ErrorAction SilentlyContinue
if (-not $books) { Write-Error "No .txt files found in $InputDir"; exit 1 }

Write-Output "=== 网文语料统计分析 ==="
Write-Output "发现 $($books.Count) 本书"

$allChapters = @()
$allDialogueRatios = @()
$bannedWords = @("仿佛","犹如","宛若","如同","深吸一口气","缓缓","不禁","微微","轻轻","淡淡","眼中闪过","嘴角勾起","眉头微皱","心中一动","心头一震")
$bannedEscaped = $bannedWords | ForEach-Object { [regex]::Escape($_) }

foreach ($book in $books) {
  $rawName = $book.Name -replace '\.txt$',''
  $content = Get-Content $book.FullName -Encoding UTF8 -Raw

  # Parse header
  $bookName = if ($content -match '(?m)^书名[：:]\s*(.+?)[\r\n]') { $matches[1].Trim() } else { $rawName }

  # Split by === separators
  $chapters = [regex]::Split($content, '={10,}') | Where-Object { $_ -match '第\d+章' }

  $bookChapters = @()
  $bookTotalChars = 0; $bookDialogueChars = 0; $bookBannedHits = 0
  $chapterRatios = @()

  foreach ($ch in $chapters) {
    $titleMatch = [regex]::Match($ch, '第(\d+)章\s*(.*?)[\r\n]')
    if (-not $titleMatch.Success) { continue }
    $chapNum = [int]$titleMatch.Groups[1].Value
    $title = $titleMatch.Groups[2].Value.Trim()

    # Body = everything after the title line
    $body = $ch -replace '^.*?第\d+章.*?[\r\n]', ''
    $stripped = $body -replace '\s',''
    $total = $stripped.Length

    # Count dialogue
    $dialogue = [regex]::Matches($stripped, '"([^"]*)"|"([^"]*)"').Value -join ''
    $dialogueLen = ($dialogue -replace '\s','').Length
    $dialRatio = if ($total -gt 0) { [math]::Round($dialogueLen / $total * 100, 1) } else { 0 }

    # Sentence count
    $sentences = [regex]::Split($body, '[。！？!?\n]') | Where-Object { $_ -match '\S' }
    $sentCount = $sentences.Count
    $avgSentLen = if ($sentCount -gt 0) { [math]::Round($total / $sentCount, 1) } else { 0 }

    # Banned word hits
    $bannedHits = 0
    foreach ($bw in $bannedEscaped) {
      $bannedHits += [regex]::Matches($body, $bw).Count
    }

    $chapter = @{
      book = $bookName; chapter = $chapNum; title = $title
      totalChars = $total; dialogueChars = $dialogueLen
      dialogueRatio = $dialRatio; sentenceCount = $sentCount
      avgSentenceLen = $avgSentLen; bannedHits = $bannedHits
    }
    $bookChapters += $chapter
    $bookTotalChars += $total; $bookDialogueChars += $dialogueLen
    $bookBannedHits += $bannedHits; $chapterRatios += $dialRatio
  }

  $bookDialRatio = if ($bookTotalChars -gt 0) { [math]::Round($bookDialogueChars / $bookTotalChars * 100, 1) } else { 0 }
  $avgDial = if ($chapterRatios.Count -gt 0) { [math]::Round(($chapterRatios | Measure-Object -Average).Average, 1) } else { 0 }
  $avgSent = if ($bookChapters.Count -gt 0) { [math]::Round(($bookChapters | ForEach-Object { $_.avgSentenceLen } | Measure-Object -Average).Average, 1) } else { 0 }

  # Save per-book CSV
  $csvPath = "$OutputDir/chapters_$rawName.csv"
  $bookChapters | ForEach-Object {
    [PSCustomObject]@{
      book = $_.book; chapter = $_.chapter; title = $_.title
      totalChars = $_.totalChars; dialogueChars = $_.dialogueChars
      dialogueRatio = $_.dialogueRatio; sentenceCount = $_.sentenceCount
      avgSentenceLen = $_.avgSentenceLen; bannedHits = $_.bannedHits
    }
  } | Export-Csv $csvPath -NoTypeInformation -Encoding UTF8

  # Save per-book JSON
  $bookStats = @{
    book = $bookName; file = $book.Name; chaptersParsed = $bookChapters.Count
    totalChars = $bookTotalChars; dialogueChars = $bookDialogueChars
    dialogueRatioOverall = $bookDialRatio
    dialogueRatioAvgPerChapter = $avgDial
    avgSentenceLen = $avgSent
    bannedHitsTotal = $bookBannedHits
  }
  ($bookStats | ConvertTo-Json -Depth 2) | Set-Content "$OutputDir/book_$rawName.json" -Encoding UTF8

  $allChapters += $bookChapters
  $allDialogueRatios += $chapterRatios

  Write-Output "  $($book.Name): $($bookChapters.Count) chapters | 对话 $bookDialRatio% / $avgDial% | 禁用词 $bookBannedHits | 均句 $avgSent 字"
}

# Cross-book aggregate
$totalCharsAll = ($allChapters | ForEach-Object { $_.totalChars } | Measure-Object -Sum).Sum
$dialCharsAll = ($allChapters | ForEach-Object { $_.dialogueChars } | Measure-Object -Sum).Sum
$overallDialRatio = if ($totalCharsAll -gt 0) { [math]::Round($dialCharsAll / $totalCharsAll * 100, 1) } else { 0 }
$overallAvgDial = [math]::Round(($allDialogueRatios | Measure-Object -Average).Average, 1)
$overallAvgSent = [math]::Round(($allChapters | ForEach-Object { $_.avgSentenceLen } | Measure-Object -Average).Average, 1)
$overallBanned = ($allChapters | ForEach-Object { $_.bannedHits } | Measure-Object -Sum).Sum

# Dialogue distribution
$allLow = ($allDialogueRatios | Where-Object { $_ -lt 40 }).Count
$allMid = ($allDialogueRatios | Where-Object { $_ -ge 40 -and $_ -lt 60 }).Count
$allHigh = ($allDialogueRatios | Where-Object { $_ -ge 60 }).Count
$allTotal = $allDialogueRatios.Count

$crossBook = @{
  totalBooks = $books.Count; totalChaptersParsed = $allChapters.Count
  totalChars = $totalCharsAll; dialogueChars = $dialCharsAll
  dialogueRatioOverall = $overallDialRatio
  dialogueRatioAvgPerChapter = $overallAvgDial
  avgSentenceLenOverall = $overallAvgSent
  bannedHitsTotal = $overallBanned
  bannedHitsPerChapter = if ($allTotal -gt 0) { [math]::Round($overallBanned / $allTotal, 1) } else { 0 }
  dialogueDistribution = @{
    total = $allTotal
    low_lt40 = $allLow
    low_lt40_pct = if ($allTotal -gt 0) { [math]::Round($allLow / $allTotal * 100, 1) } else { 0 }
    mid_40to60 = $allMid
    mid_40to60_pct = if ($allTotal -gt 0) { [math]::Round($allMid / $allTotal * 100, 1) } else { 0 }
    high_gt60 = $allHigh
    high_gt60_pct = if ($allTotal -gt 0) { [math]::Round($allHigh / $allTotal * 100, 1) } else { 0 }
  }
}
($crossBook | ConvertTo-Json -Depth 3) | Set-Content "$OutputDir/cross-book-stats.json" -Encoding UTF8

Write-Output ""
Write-Output "=== 跨书汇总 ==="
Write-Output "总章节: $($allChapters.Count)"
Write-Output "总体对话占比: $overallDialRatio%"
Write-Output "平均每章对话占比: $overallAvgDial%"
Write-Output "平均句长: $overallAvgSent 字"
Write-Output "禁用词总命中: $overallBanned"
Write-Output ""
Write-Output "对话占比分布 (<40/40-60/>60): $allLow / $allMid / $allHigh 章"
Write-Output "输出目录: $OutputDir"
