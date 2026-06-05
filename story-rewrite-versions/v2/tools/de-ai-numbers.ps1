# de-ai-numbers.ps1
# 鏁板瓧妯＄硦鍖栵細灏嗙簿纭暟瀛楁敼涓烘ā绯婅〃杈?# 鐢ㄦ硶锛歱owershell -ExecutionPolicy Bypass -File de-ai-numbers.ps1 -Path "鏂囦欢璺緞" [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [string]$Path,
    [switch]$DryRun
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (!(Test-Path $Path)) {
    Write-Output "ERROR: 鏂囦欢涓嶅瓨鍦?$Path"
    exit 1
}

$content = Get-Content $Path -Raw -Encoding UTF8
$original = $content

# 瀵硅瘽琛屼繚鐣欐爣璁?$lines = $content -split "`n"
$newLines = @()
$changeCount = 0

foreach ($line in $lines) {
    # 瀵硅瘽琛岃烦杩?    if ($line -match '[\u201c\u201d\u300c\u300d""]') {
        $newLines += $line
        continue
    }

    $orig = $line

    # 1. 鏁板瓧 + 绫?閲?灏?涓?鍏噷 鈫?鍔?宸﹀彸"
    $line = $line -replace '(\d+)(?=[绫抽噷灏轰笀鍏噷鍘樼背])', '$1{宸﹀彸}'

    # 2. 鏁板瓧 + 绉?鈫?X鏉ョ锛?=99绉掞級
    $line = $line -replace '(\d{1,2})绉??!\w)', '${1}鏉ョ'

    # 3. 鏁伴噺 + 涓ら摱瀛?鈫?鍑犱袱閾跺瓙
    $line = $line -replace '([涓€浜屼袱涓夊洓浜斿叚涓冨叓涔濆崄\d])涓ら摱瀛?, '鍑犱袱閾跺瓙'

    # 4. 鏁板瓧 + 澶?鏃?鈫?X鏉ュぉ
    $line = $line -replace '(\d{1,2})[澶╂棩](?!\w)', '${1}鏉ュぉ'

    # 5. 鏁板瓧 + 姝?鈫?姝ュ乏鍙?    $line = $line -replace '(\d+)姝??!\w)', '${1}姝ュ乏鍙?

    if ($line -ne $orig) {
        $changeCount++
    }

    $newLines += $line
}

$content = $newLines -join "`n"

# 鏇挎崲鍗犱綅绗?$content = $content -replace '{宸﹀彸}', '宸﹀彸'

if ($DryRun) {
    Write-Output "DRY RUN: $Path"
    $diff = 0
    for ($j = 0; $j -lt [Math]::Min($original.Length, $content.Length); $j++) {
        if ($original[$j] -ne $content[$j]) { $diff++ }
    }
    Write-Output "淇敼: ~$diff 澶勫瓧绗? $changeCount 琛?
} else {
    Set-Content $Path -Value $content -Encoding UTF8
    Write-Output "OK: $Path ($changeCount 琛屼慨鏀?"
}
