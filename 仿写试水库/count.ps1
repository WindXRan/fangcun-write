$content = Get-Content -LiteralPath 'C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\仿写试水库\穿成替身新娘后失忆总裁每天给我洗袜子_试水.txt' -Raw -Encoding UTF8
$chapters = $content -split '----'
Write-Host ('Ch1: ' + ($chapters[1] -replace '\s','').Length)
Write-Host ('Ch2: ' + ($chapters[2] -replace '\s','').Length)
Write-Host ('Ch3: ' + ($chapters[3] -replace '\s','').Length)