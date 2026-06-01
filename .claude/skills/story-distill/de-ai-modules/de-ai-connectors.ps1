# de-ai-connectors.ps1
# 去AI：连接词降频 + 得地的修正
# 用法：powershell -ExecutionPolicy Bypass -File de-ai-connectors.ps1 -Path "文件路径" [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [string]$Path,
    [switch]$DryRun
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (!(Test-Path $Path)) {
    Write-Output "ERROR: $Path"
    exit 1
}

$content = Get-Content $Path -Raw -Encoding UTF8
$original = $content

# 得(de) → 的（排除得děi）
$deiPattern = '得[了走想赶注小抓尽看说做去来想找用拿买卖吃喝睡醒站坐躺蹲跪爬跳飞游跑走打骂夸恨爱怕急气累困饿渴冷热疼痒酸麻辣甜苦咸淡浓稠稀硬软脆韧滑粗细厚薄宽窄长短高矮大小多少快慢早晚远近深浅亮暗响轻重紧松弯直斜歪正偏反倒竖横平陡险稳牢严密清浊净脏干湿潮润燥黏涩糙光毛皱鼓瘪凸凹圆扁方尖钝利急缓猛烈强弱弹粘]
$content = $content -replace "(?<!$deiPattern)得(?!$deiPattern)", '的'

# 地(de) → 的（排除地dì）
$diPattern = '土地|地方|地面|地上|地下|地理|地质|地道|地震|地铁|地址|地段|地步|地势|地带|地域|地壳|地层|地窖|地洞|地毯|地皮|地板|地基|地契|地租|地主|地狱|地图|地球|地形|天地|阵地|领地|境地|驻地|落地|各地|内地|外地|本地|基地|陆地|湿地|荒地|田地|林地|园地|空地|绿地|草地|菜地|耕地|洼地|高地|低地|平地|大地|满地|遍地|一地|整地|着地|席地|失地|飞地|目的地|发源地|根据地|策源地|处女地'
# 先保护地(dì)词
$diWords = [regex]::Matches($content, $diPattern)
$protected = @{}
$i = 0
foreach ($m in $diWords) {
    $key = "<<<$i>>>"
    $protected[$key] = $m.Value
    $content = $content.Substring(0, $m.Index) + $key + $content.Substring($m.Index + $m.Length)
    $i++
}
# 替换地(de) → 的
$content = $content -replace '地', '的'
# 恢复地(dì)词
foreach ($key in $protected.Keys) {
    $content = $content.Replace($key, $protected[$key])
}

# 单字连接词降频（非对话行）
$lines = $content -split "`n"
$newLines = @()
foreach ($line in $lines) {
    # 对话行保留
    if ($line -match '[\u201c\u201d\u2018\u2019\u300c\u300d]') {
        $newLines += $line
        continue
    }
    # 删除单字连接词
    $line = $line -replace '\u002c但', '\u002c'
    $line = $line -replace '\u002c又', '\u002c'
    $line = $line -replace '\u002c却', '\u002c'
    $line = $line -replace '\u002c就', '\u002c'
    $line = $line -replace '\u002c也', '\u002c'
    $line = $line -replace '\u002c还', '\u002c'
    $newLines += $line
}
$content = $newLines -join "`n"

# 输出
if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    # 统计修改
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "Changes: ~$diff chars"
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path"
}
