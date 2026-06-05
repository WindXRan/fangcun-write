# de-ai-connectors.ps1
# 鍘籄I锛氳繛鎺ヨ瘝闄嶉 + 寰楀湴鐨勪慨姝?# 鐢ㄦ硶锛歱owershell -ExecutionPolicy Bypass -File de-ai-connectors.ps1 -Path "鏂囦欢璺緞" [-DryRun]

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

# 寰?de) 鈫?鐨勶紙鎺掗櫎寰梔臎i锛?$deiPattern = '寰梉浜嗚蛋鎯宠刀娉ㄥ皬鎶撳敖鐪嬭鍋氬幓鏉ユ兂鎵剧敤鎷夸拱鍗栧悆鍠濈潯閱掔珯鍧愯汉韫茶藩鐖烦椋炴父璺戣蛋鎵撻獋澶告仺鐖辨€曟€ユ皵绱洶楗挎复鍐风儹鐤肩棐閰搁夯杈ｇ敎鑻﹀捀娣℃祿绋犵█纭蒋鑴嗛煣婊戠矖缁嗗帤钖勫绐勯暱鐭珮鐭ぇ灏忓灏戝揩鎱㈡棭鏅氳繙杩戞繁娴呬寒鏆楀搷杞婚噸绱ф澗寮洿鏂滄姝ｅ亸鍙嶅€掔珫妯钩闄￠櫓绋崇墷涓ュ瘑娓呮祳鍑€鑴忓共婀挎疆娑︾嚗榛忔订绯欏厜姣涚毐榧撶槳鍑稿嚬鍦嗘墎鏂瑰皷閽濆埄鎬ョ紦鐚涚儓寮哄急寮圭矘]
$content = $content -replace "(?<!$deiPattern)寰??!$deiPattern)", '鐨?

# 鍦?de) 鈫?鐨勶紙鎺掗櫎鍦癲矛锛?$diPattern = '鍦熷湴|鍦版柟|鍦伴潰|鍦颁笂|鍦颁笅|鍦扮悊|鍦拌川|鍦伴亾|鍦伴渿|鍦伴搧|鍦板潃|鍦版|鍦版|鍦板娍|鍦板甫|鍦板煙|鍦板３|鍦板眰|鍦扮獤|鍦版礊|鍦版|鍦扮毊|鍦版澘|鍦板熀|鍦板|鍦扮|鍦颁富|鍦扮嫳|鍦板浘|鍦扮悆|鍦板舰|澶╁湴|闃靛湴|棰嗗湴|澧冨湴|椹诲湴|钀藉湴|鍚勫湴|鍐呭湴|澶栧湴|鏈湴|鍩哄湴|闄嗗湴|婀垮湴|鑽掑湴|鐢板湴|鏋楀湴|鍥湴|绌哄湴|缁垮湴|鑽夊湴|鑿滃湴|鑰曞湴|娲煎湴|楂樺湴|浣庡湴|骞冲湴|澶у湴|婊″湴|閬嶅湴|涓€鍦皘鏁村湴|鐫€鍦皘甯湴|澶卞湴|椋炲湴|鐩殑鍦皘鍙戞簮鍦皘鏍规嵁鍦皘绛栨簮鍦皘澶勫コ鍦?
# 鍏堜繚鎶ゅ湴(d矛)璇嶏紙鍊掑簭閬嶅巻閬垮厤绱㈠紩鍋忕Щ锛?$diWords = [regex]::Matches($content, $diPattern) | Sort-Object Index -Descending
$protected = @{}
$i = 0
foreach ($m in $diWords) {
    $key = "<<<$i>>>"
    $protected[$key] = $m.Value
    $content = $content.Substring(0, $m.Index) + $key + $content.Substring($m.Index + $m.Length)
    $i++
}
# 鏇挎崲鍦?de) 鈫?鐨?$content = $content -replace '鍦?, '鐨?
# 鎭㈠鍦?d矛)璇?foreach ($key in $protected.Keys) {
    $content = $content.Replace($key, $protected[$key])
}

# 鍗曞瓧杩炴帴璇嶉檷棰戯紙闈炲璇濊锛?$lines = $content -split "`n"
$newLines = @()
foreach ($line in $lines) {
    # 瀵硅瘽琛屼繚鐣?    if ($line -match '[\u201c\u201d\u2018\u2019\u300c\u300d]') {
        $newLines += $line
        continue
    }
    # 鍒犻櫎鍗曞瓧杩炴帴璇?    $line = $line -replace '\u002c浣?, '\u002c'
    $line = $line -replace '\u002c鍙?, '\u002c'
    $line = $line -replace '\u002c鍗?, '\u002c'
    $line = $line -replace '\u002c灏?, '\u002c'
    $line = $line -replace '\u002c涔?, '\u002c'
    $line = $line -replace '\u002c杩?, '\u002c'
    $newLines += $line
}
$content = $newLines -join "`n"

# 杈撳嚭
if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    # 缁熻淇敼
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "Changes: ~$diff chars"
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path"
}

