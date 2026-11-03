[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Message = $env:SMKD_PUBLISH_MESSAGE,

    [ValidateSet('Preview', 'Commit', 'Push')]
    [string]$Action = 'Preview',

    [string]$Remote = $(if ($env:SMKD_PUBLISH_REMOTE) { $env:SMKD_PUBLISH_REMOTE } else { 'origin' }),
    [string]$Branch = $env:SMKD_PUBLISH_BRANCH,

    [string[]]$Include = @(),
    [string[]]$Exclude = @(),

    [switch]$AllAllowed,
    [switch]$AllowPreStaged,
    [switch]$Help,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs = @()
)

# npm/pnpm can append arguments after `--`; merge them with named parameters.
if ($ExtraArgs.Count -gt 0) {
    $parsed = @{}
    for ($i = 0; $i -lt $ExtraArgs.Count; $i++) {
        $token = $ExtraArgs[$i]
        if ($token -notmatch '^-(\w+)$') { throw "Unexpected argument: $token" }
        $key = $Matches[1]
        if ($key -in @('AllAllowed', 'AllowPreStaged', 'Help')) {
            $parsed[$key] = $true
        } else {
            if (($i + 1) -ge $ExtraArgs.Count -or $ExtraArgs[$i + 1] -match '^-(\w+)$') {
                throw "Argument -$key needs a value."
            }
            $parsed[$key] = $ExtraArgs[++$i]
        }
    }
    if ($parsed.ContainsKey('Message')) { $Message = $parsed.Message }
    if ($parsed.ContainsKey('Action')) { $Action = $parsed.Action }
    if ($parsed.ContainsKey('Remote')) { $Remote = $parsed.Remote }
    if ($parsed.ContainsKey('Branch')) { $Branch = $parsed.Branch }
    if ($parsed.ContainsKey('Include')) { $Include = @($parsed.Include -split '[,;]') }
    if ($parsed.ContainsKey('Exclude')) { $Exclude = @($parsed.Exclude -split '[,;]') }
    if ($parsed.ContainsKey('AllAllowed')) { $AllAllowed = $true }
    if ($parsed.ContainsKey('AllowPreStaged')) { $AllowPreStaged = $true }
    if ($parsed.ContainsKey('Help')) { $Help = $true }
}

$ErrorActionPreference = 'Stop'

if ($Help) {
    @'
SMKD publisher

Usage:
  pnpm publish                                  Preview eligible changes
  pnpm publish -- -Action Push -Message "docs: refresh README"
  pnpm publish -- -Include README.md,docs       Preview only selected paths
  pnpm publish -- -Action Commit -Include docs  Commit selected paths locally
  pnpm publish -- -Action Push -AllAllowed      Commit and push all allowed changes

Options:
  -Action Preview|Commit|Push  Preview, make a local commit, or commit and push
  -Message TEXT               Commit message (or SMKD_PUBLISH_MESSAGE)
  -Branch NAME                Target branch (defaults to the current branch)
  -Remote NAME                Git remote (default: origin; or SMKD_PUBLISH_REMOTE)
  -Include PATHS              Limit candidates to these repo-relative paths
  -Exclude PATHS              Exclude additional repo-relative paths
  -AllAllowed                 Include all configured safe source roots
  -AllowPreStaged             Permit already-staged paths if they pass safety checks

Safe source roots are configured in scripts/publish.ps1. Databases, logs, secrets,
build output, and the fast-framework submodule are always excluded.
'@ | Write-Host
    exit 0
}

$repoRoot = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repoRoot) {
    throw 'Run this script from inside the SMKD Git repository.'
}
Set-Location -LiteralPath $repoRoot

# Safe root-repository paths. Add a root here when the project layout changes.
$allowedRoots = @(
    'README.md', 'DOCS.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'AGENTS.md',
    '.gitignore', '.gitmodules', 'package.json', 'pnpm-lock.yaml',
    'capacitor.config.json', 'android', 'desktop', 'docs', 'launcher',
    'scripts', 'stock-signal-bot', '.github'
)

if (-not $Remote.Trim()) { throw 'Remote name cannot be empty.' }
$remoteUrl = git remote get-url $Remote 2>$null
if ($LASTEXITCODE -ne 0 -or -not $remoteUrl) { throw "Git remote '$Remote' was not found." }

if (-not $Branch) { $Branch = (git branch --show-current).Trim() }
if (-not $Branch) { throw 'Cannot publish from detached HEAD. Specify -Branch explicitly.' }

$tracked = @(git diff --name-only --diff-filter=ACDMRTUXB)
$unstagedCandidates = @($tracked + @(git ls-files --others --exclude-standard) | Sort-Object -Unique)
$preStaged = @(git diff --cached --name-only --diff-filter=ACDMRTUXB)

if ($preStaged.Count -gt 0 -and -not $AllowPreStaged) {
    $preStaged | ForEach-Object { Write-Host "Already staged: $_" }
    throw 'There are pre-staged changes. Commit them separately or pass -AllowPreStaged after reviewing them.'
}

$candidates = @($unstagedCandidates)
if ($AllowPreStaged) { $candidates = @($candidates + $preStaged | Sort-Object -Unique) }

if ($Include.Count -gt 0) {
    $includePaths = @($Include | ForEach-Object { $_.Replace('\\', '/').TrimEnd('/') })
    $candidates = @($candidates | Where-Object {
        $candidate = $_
        @($includePaths | Where-Object { $candidate -eq $_ -or $candidate.StartsWith("$_/", [System.StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
    })
} elseif (-not $AllAllowed) {
    # Default selection is current change set intersected with known safe roots.
}

if ($Exclude.Count -gt 0) {
    $excludePaths = @($Exclude | ForEach-Object { $_.Replace('\\', '/').TrimEnd('/') })
    $candidates = @($candidates | Where-Object {
        $candidate = $_
        @($excludePaths | Where-Object { $candidate -eq $_ -or $candidate.StartsWith("$_/", [System.StringComparison]::OrdinalIgnoreCase) }).Count -eq 0
    })
}

$selected = @()
$excluded = @()
foreach ($path in $candidates) {
    $safe = $false
    foreach ($root in $allowedRoots) {
        if ($path -eq $root -or $path.StartsWith("$root/", [System.StringComparison]::OrdinalIgnoreCase)) {
            $safe = $true
            break
        }
    }

    if ($path -match '(^|/)(\.env($|\.)|secrets?($|/)|credentials?($|/))' -or
        $path -match '(?i)(^|/)[^/]*\.(db|sqlite|sqlite3|log|pem|key)$' -or
        $path -match '(^|/)(node_modules|target|portable|bundle|\.venv|venv|__pycache__)(/|$)' -or
        $path -match '(^|/)fast-framework(/|$)') {
        $safe = $false
    }

    if ($safe) { $selected += $path } else { $excluded += $path }
}

if ($selected.Count -eq 0) {
    Write-Host 'No eligible source or documentation changes to publish.'
    if ($excluded.Count -gt 0) {
        Write-Host 'Excluded by allowlist or safety rules:'
        $excluded | ForEach-Object { Write-Host "  - $_" }
    }
    exit 0
}

Write-Host "Action: $Action | Remote: $Remote | Branch: $Branch"
Write-Host 'Files selected:'
$selected | ForEach-Object { Write-Host "  + $_" }
if ($excluded.Count -gt 0) {
    Write-Host 'Excluded by allowlist or safety rules:'
    $excluded | ForEach-Object { Write-Host "  - $_" }
}

if ($Action -eq 'Preview') {
    Write-Host ''
    Write-Host 'Preview only. Example publish command:'
    Write-Host '  pnpm publish -- -Action Push -Message "docs: update guide"'
    exit 0
}

if (-not $Message -or -not $Message.Trim()) {
    throw 'Provide -Message "type: concise description" or set SMKD_PUBLISH_MESSAGE.'
}

git add -- $selected
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Staged diff has whitespace errors; nothing was committed.' }

$stagedPaths = @(git diff --cached --name-only)
$unexpected = @($stagedPaths | Where-Object { $_ -notin $selected })
if ($unexpected.Count -gt 0) {
    throw "Unexpected paths are staged; review and unstage them before retrying: $($unexpected -join ', ')"
}

git commit -m $Message
if ($LASTEXITCODE -ne 0) { throw 'git commit failed.' }

if ($Action -eq 'Commit') {
    Write-Host "Committed locally on '$Branch'; push was not requested."
    exit 0
}

git push $Remote "HEAD:$Branch"
if ($LASTEXITCODE -ne 0) { throw "Push failed. The commit remains local; inspect Git status and retry after resolving the push error." }

Write-Host "Published commit to $Remote/$Branch."
