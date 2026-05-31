<#
.SYNOPSIS
    Agent 格式转换脚本：从 _shared/agents/ 生成 Claude Code 和 OpenCode 格式
.DESCRIPTION
    读取 skills/_shared/agents/ 中的通用格式 agent 文件，
    转换为 .claude/agents/ (Claude Code) 和 .opencode/agents/ (OpenCode) 格式。
.PARAMETER Agent
    只转换指定的 agent（不含 .md 后缀），不指定则转换全部
.PARAMETER DryRun
    只输出差异，不实际写入
.EXAMPLE
    .\sync-agents.ps1
    .\sync-agents.ps1 -Agent narrative-writer
    .\sync-agents.ps1 -DryRun
#>

param(
    [string]$Agent = "",
    [switch]$DryRun
)

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sharedDir = "$PSScriptRoot\agents"
$claudeDir = "$projectRoot\.claude\agents"
$opencodeDir = "$projectRoot\.opencode\agents"

# Ensure target dirs exist
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null }
if (-not (Test-Path $opencodeDir)) { New-Item -ItemType Directory -Path $opencodeDir -Force | Out-Null }

# Get agent files to process
if ($Agent) {
    $files = @(@{Name="$Agent.md"; FullName="$sharedDir\$Agent.md"})
    if (-not (Test-Path "$sharedDir\$Agent.md")) {
        Write-Error "Agent not found: $sharedDir\$Agent.md"
        exit 1
    }
} else {
    $files = Get-ChildItem "$sharedDir\*.md" -ErrorAction SilentlyContinue
}

if (-not $files -or $files.Count -eq 0) {
    Write-Error "No agent files found in $sharedDir"
    exit 1
}

Write-Output "=========================================="
Write-Output "Agent Sync: _shared/ -> .claude/ + .opencode/"
Write-Output "=========================================="

foreach ($file in $files) {
    $agentName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    $content = Get-Content $file.FullName -Raw -Encoding UTF8

    # Parse frontmatter
    if ($content -match '^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$') {
        $frontmatter = $Matches[1]
        $body = $Matches[2]
    } else {
        Write-Warning "No frontmatter found in $($file.Name), skipping"
        continue
    }

    # Extract fields from shared frontmatter
    $description = ""
    $claudeConfig = @{}
    $opencodeConfig = @{}

    # Parse description
    if ($frontmatter -match 'description:\s*\|?\s*\r?\n([\s\S]*?)(?=\r?\n\w|\r?\nplatform:|\r?\n---)') {
        $description = $Matches[1].Trim()
    }

    # Parse platform configs
    if ($frontmatter -match 'claude:\s*\r?\n([\s\S]*?)(?=\r?\n\s+opencode:|\r?\n\w|\r?\n---)') {
        $claudeBlock = $Matches[1]
    if ($claudeBlock -match 'tools:\s*\[([^\]]+)\]') { $claudeConfig['tools'] = $Matches[1] }
    if ($claudeBlock -match 'disallowedTools:\s*\[([^\]]+)\]') { $claudeConfig['disallowedTools'] = $Matches[1] }
    if ($claudeBlock -match 'model:\s*(\S+)') { $claudeConfig['model'] = $Matches[1] }
        if ($claudeBlock -match 'maxTurns:\s*(\d+)') { $claudeConfig['maxTurns'] = $Matches[1] }
        if ($claudeBlock -match 'skills:\s*\[([^\]]+)\]') { $claudeConfig['skills'] = $Matches[1] }
        if ($claudeBlock -match 'memory:\s*(\S+)') { $claudeConfig['memory'] = $Matches[1] }
    }
    if ($frontmatter -match 'opencode:\s*\n([\s\S]*?)$') {
        $opencodeBlock = $Matches[1]
        if ($opencodeBlock -match 'mode:\s*(\S+)') { $opencodeConfig['mode'] = $Matches[1] }
        if ($opencodeBlock -match 'permission:\s*\[([^\]]+)\]') { $opencodeConfig['permission'] = $Matches[1] }
    }

    # Generate Claude Code format
    $claudeFrontmatter = "---`nname: $agentName`ndescription: |`n"
    foreach ($line in ($description -split "`n")) {
        $claudeFrontmatter += "  $line`n"
    }
    if ($claudeConfig['tools']) { $claudeFrontmatter += "tools: [$($claudeConfig['tools'])]`n" }
    if ($claudeConfig['model']) { $claudeFrontmatter += "model: $($claudeConfig['model'])`n" }
    if ($claudeConfig['maxTurns']) { $claudeFrontmatter += "maxTurns: $($claudeConfig['maxTurns'])`n" }
    if ($claudeConfig['skills']) { $claudeFrontmatter += "skills: [$($claudeConfig['skills'])]`n" }
    if ($claudeConfig['memory']) { $claudeFrontmatter += "memory: $($claudeConfig['memory'])`n" }
    $claudeFrontmatter += "---`n"
    $claudeContent = $claudeFrontmatter + $body

    # Generate OpenCode format
    $opencodeFrontmatter = "---`ndescription: |`n"
    foreach ($line in ($description -split "`n")) {
        $opencodeFrontmatter += "  $line`n"
    }
    if ($opencodeConfig['mode']) { $opencodeFrontmatter += "mode: $($opencodeConfig['mode'])`n" }
    # Generate permissions: use explicit if available, else derive from Claude tools/disallowedTools
    $opencodeFrontmatter += "permission:`n"
    if ($opencodeConfig['permission']) {
        $perms = $opencodeConfig['permission'] -split ',\s*'
        foreach ($p in $perms) {
            $p = $p.Trim()
            $opencodeFrontmatter += "  ${p}: allow`n"
        }
    } elseif ($claudeConfig['tools']) {
        # Derive from Claude tools (allow listed tools)
        $tools = $claudeConfig['tools'] -split ',\s*'
        foreach ($t in $tools) {
            $t = $t.Trim().ToLower()
            $opencodeFrontmatter += "  ${t}: allow`n"
        }
    } elseif ($claudeConfig['disallowedTools']) {
        # Derive from disallowedTools (allow everything NOT disallowed)
        $disallowed = $claudeConfig['disallowedTools'] -split ',\s*' | ForEach-Object { $_.Trim().ToLower() }
        $allPerms = @("read","glob","grep","write","edit","bash")
        foreach ($p in $allPerms) {
            if ($disallowed -contains $p) {
                $opencodeFrontmatter += "  ${p}: deny`n"
            } else {
                $opencodeFrontmatter += "  ${p}: allow`n"
            }
        }
        # Also check disallowedTools
        # (already handled by not including them)
    } else {
        $opencodeFrontmatter += "  read: allow`n  glob: allow`n  grep: allow`n"
    }
    $opencodeFrontmatter += "---`n"
    $opencodeContent = $opencodeFrontmatter + $body

    # Write or diff
    $claudePath = "$claudeDir\$($file.Name)"
    $opencodePath = "$opencodeDir\$($file.Name)"

    $claudeChanged = -not (Test-Path $claudePath) -or ((Get-Content $claudePath -Raw -Encoding UTF8) -ne $claudeContent)
    $opencodeChanged = -not (Test-Path $opencodePath) -or ((Get-Content $opencodePath -Raw -Encoding UTF8) -ne $opencodeContent)

    if ($DryRun) {
        $claudeStatus = if ($claudeChanged) { "CHANGED" } else { "OK" }
        $opencodeStatus = if ($opencodeChanged) { "CHANGED" } else { "OK" }
        Write-Output "  ${agentName}: .claude/=${claudeStatus} .opencode/=${opencodeStatus}"
    } else {
        if ($claudeChanged) {
            Set-Content $claudePath -Value $claudeContent -Encoding UTF8 -NoNewline
            Write-Output "  [WRITE] $claudePath"
        } else {
            Write-Output "  [OK]    $claudePath"
        }
        if ($opencodeChanged) {
            Set-Content $opencodePath -Value $opencodeContent -Encoding UTF8 -NoNewline
            Write-Output "  [WRITE] $opencodePath"
        } else {
            Write-Output "  [OK]    $opencodePath"
        }
    }
}

Write-Output ""
Write-Output "Done."
