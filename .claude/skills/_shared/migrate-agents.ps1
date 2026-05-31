<#
.SYNOPSIS
    将现有 .opencode/ 和 .claude/ agent 文件批量迁移到 _shared/ 格式
.DESCRIPTION
    读取 .opencode/ 的 body 内容 + .claude/ 的 Claude 专有字段，
    生成 _shared/agents/ 通用格式文件。
#>

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$opencodeDir = "$projectRoot\.opencode\agents"
$claudeDir = "$projectRoot\.claude\agents"
$sharedDir = "$PSScriptRoot\agents"

if (-not (Test-Path $sharedDir)) { New-Item -ItemType Directory -Path $sharedDir -Force | Out-Null }

$agents = Get-ChildItem "$opencodeDir\*.md" -ErrorAction SilentlyContinue

foreach ($agent in $agents) {
    $name = $agent.BaseName
    $sharedPath = "$sharedDir\$($agent.Name)"

    # Skip if already exists in _shared
    if (Test-Path $sharedPath) {
        Write-Output "[SKIP] $name (already in _shared)"
        continue
    }

    # Read .opencode version (body)
    $ocContent = Get-Content $agent.FullName -Raw -Encoding UTF8
    if ($ocContent -match '^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$') {
        $ocFrontmatter = $Matches[1]
        $body = $Matches[2]
    } else {
        Write-Warning "[SKIP] $name (no frontmatter in .opencode)"
        continue
    }

    # Extract description from .opencode
    $description = ""
    if ($ocFrontmatter -match 'description:\s*\|?\s*\r?\n([\s\S]*?)(?=\r?\nmode:|\r?\npermission:|\r?\n---)') {
        $description = $Matches[1].TrimEnd()
    }

    # Extract opencode config
    $ocMode = "subagent"
    $ocPerms = @()
    if ($ocFrontmatter -match 'mode:\s*(\S+)') { $ocMode = $Matches[1] }
    # Match permission block: lines with "word: allow" pattern after "permission:"
    if ($ocFrontmatter -match 'permission:\s*\n((?:\s+\w+:\s*allow\s*\n?)*)') {
        $permBlock = $Matches[1]
        $ocPerms = ($permBlock -split '\n') | ForEach-Object {
            if ($_ -match '^\s+(\w+):\s*allow') { $Matches[1] }
        } | Where-Object { $_ }
    }

    # Read .claude version for Claude-specific fields
    $claudePath = "$claudeDir\$($agent.Name)"
    $claudeTools = "Read, Glob, Grep, Write, Edit"
    $claudeModel = "sonnet"
    $claudeMaxTurns = "20"
    $claudeSkills = ""
    $claudeMemory = ""

    if (Test-Path $claudePath) {
        $ccContent = Get-Content $claudePath -Raw -Encoding UTF8
        if ($ccContent -match '^---\r?\n([\s\S]*?)\r?\n---') {
            $ccFm = $Matches[1]
            if ($ccFm -match 'tools:\s*\[([^\]]+)\]') { $claudeTools = $Matches[1] }
            if ($ccFm -match 'disallowedTools:\s*\[([^\]]+)\]') {
                # Convert disallowedTools to allowed tools
                $disallowed = $Matches[1] -split ',\s*'
                $allTools = @("Read","Glob","Grep","Write","Edit","Bash")
                $allowed = $allTools | Where-Object { $disallowed -notcontains $_ }
                $claudeTools = $allowed -join ', '
            }
            if ($ccFm -match 'model:\s*(\S+)') { $claudeModel = $Matches[1] }
            if ($ccFm -match 'maxTurns:\s*(\d+)') { $claudeMaxTurns = $Matches[1] }
            if ($ccFm -match 'skills:\s*\[([^\]]+)\]') { $claudeSkills = $Matches[1] }
            if ($ccFm -match 'memory:\s*(\S+)') { $claudeMemory = $Matches[1] }
        }
    }

    # Generate shared frontmatter
    $shared = "---`nagent: $name`ndescription: |`n"
    foreach ($line in ($description -split "`n")) {
        $shared += "  $line`n"
    }
    $shared += "platform:`n"
    $shared += "  claude:`n"
    $shared += "    tools: [$claudeTools]`n"
    $shared += "    model: $claudeModel`n"
    $shared += "    maxTurns: $claudeMaxTurns`n"
    if ($claudeSkills) { $shared += "    skills: [$claudeSkills]`n" }
    if ($claudeMemory) { $shared += "    memory: $claudeMemory`n" }
    $shared += "  opencode:`n"
    $shared += "    mode: $ocMode`n"
    if ($ocPerms.Count -gt 0) {
        $shared += "    permission:`n"
        foreach ($p in $ocPerms) {
            $shared += "      ${p}: allow`n"
        }
    }
    $shared += "---`n`n"
    $shared += $body

    Set-Content $sharedPath -Value $shared -Encoding UTF8 -NoNewline
    Write-Output "[CREATE] $sharedPath"
}

Write-Output "`nDone. Run sync-agents.ps1 to deploy to .claude/ and .opencode/"
