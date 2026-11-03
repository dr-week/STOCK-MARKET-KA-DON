[CmdletBinding()]
param(
    [Parameter(Position = 0)] [string]$Message = $env:SMKD_PUBLISH_MESSAGE,
    [ValidateSet('Preview', 'Commit', 'Push')] [string]$Action = 'Preview',
    [string]$Remote = $(if ($env:SMKD_PUBLISH_REMOTE) { $env:SMKD_PUBLISH_REMOTE } else { 'origin' }),
    [string]$Branch = $env:SMKD_PUBLISH_BRANCH,
    [ValidateSet('All', 'Tracked', 'Untracked', 'Changed')]
    [string]$ChangeSet = 'Changed',
    [string[]]$Include = @(),
    [string[]]$Exclude = @(),
    [string]$Preset = '',
    [string]$Config = '',
    [switch]$AllAllowed,
    [switch]$NoVerify,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
$changeSetExplicit = $PSBoundParameters.ContainsKey('ChangeSet')

function Show-Help {
    @'
SMKD publisher (PowerShell)

Usage:
  pnpm repo:publish -- -Help
  pnpm repo:publish -- -Preset docs
  pnpm repo:publish -- -Action Commit -Preset docs -Message "docs: update guides"
  pnpm repo:publish -- -Action Push -ChangeSet Changed -Message "fix: update scanner"
  pnpm repo:publish -- -Action Push -Config scripts/publish.config.json

Options:
  -Action Preview|Commit|Push     Preview, commit locally, or commit and push
  -Message TEXT                  Commit message; may use SMKD_PUBLISH_MESSAGE
  -Remote NAME -Branch NAME      Destination; defaults to origin/current branch
  -ChangeSet Changed|Tracked|Untracked|All
                                 Choose changed paths, modified paths, new files, or all tracked files
  -Include PATHS -Exclude PATHS  Repo-relative path filters (comma/semicolon lists)
  -Preset NAME                   Named scope from the JSON config; CLI paths override it
  -Config FILE                   Optional JSON defaults; see publish.config.example.json
  -AllAllowed                    Scan safe roots whether modified or not (tracked files only)
  -NoVerify                      Skip Git hooks (normally keep hooks enabled)

All modes always reject secrets, databases, logs, generated outputs, and the
fast-framework submodule. Use Preview first; the regular Git index is preserved.
'@ | Write-Host
}

if ($Help) { Show-Help; exit 0 }

$moduleRoot = Join-Path $PSScriptRoot 'publish/modules'
. (Join-Path $moduleRoot 'Git.ps1')
. (Join-Path $moduleRoot 'Configuration.ps1')
. (Join-Path $moduleRoot 'Paths.ps1')
$repoRoot = Get-PublishRepoRoot
Set-Location -LiteralPath $repoRoot

if (-not $Config) {
    $localConfig = Join-Path $repoRoot 'scripts/publish.config.json'
    $Config = if (Test-Path -LiteralPath $localConfig) { $localConfig } else { 'scripts/publish.config.example.json' }
}
$configData = Read-PublishConfig $Config $repoRoot

if ($Preset) {
    $presetData = Get-PublishPreset $configData $Preset
    if ($Include.Count -eq 0 -and $presetData.include) { $Include = @($presetData.include) }
    if ($Exclude.Count -eq 0 -and $presetData.exclude) { $Exclude = @($presetData.exclude) }
    if (-not $changeSetExplicit -and $presetData.changeSet) { $ChangeSet = $presetData.changeSet }
}

$allowedRoots = @(
    'README.md', 'DOCS.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'AGENTS.md',
    '.gitignore', '.gitmodules', 'package.json', 'pnpm-lock.yaml',
    'capacitor.config.json', 'android', 'desktop', 'docs', 'launcher',
    'scripts', 'stock-signal-bot', '.github'
)
if ($configData.allowedRoots) { $allowedRoots = @($configData.allowedRoots) }
$allowedRoots = Normalize-PublishPaths $allowedRoots

$blockedPatterns = @(
    '(^|/)(\.env($|\.)|secrets?($|/)|credentials?($|/))',
    '(?i)(^|/)[^/]*\.(db|sqlite|sqlite3|log|pem|key|pfx|p12)$',
    '(^|/)(node_modules|target|portable|bundle|\.venv|venv|__pycache__|\.runtime)(/|$)',
    '(^|/)fast-framework(/|$)'
)
if ($configData.blockedPatterns) { $blockedPatterns += @($configData.blockedPatterns) }

if ($configData.remote -and $Remote -eq 'origin' -and -not $env:SMKD_PUBLISH_REMOTE) { $Remote = $configData.remote }
if ($configData.branch -and -not $Branch) { $Branch = $configData.branch }
if ($configData.changeSet -and -not $changeSetExplicit -and -not ($Preset -and $presetData.changeSet)) { $ChangeSet = $configData.changeSet }
if ($Include.Count -eq 0 -and $configData.include) { $Include = @($configData.include) }
if ($Exclude.Count -eq 0 -and $configData.exclude) { $Exclude = @($configData.exclude) }
if (-not $Message -and $configData.message) { $Message = $configData.message }
$Include = Normalize-PublishPaths $Include
$Exclude = Normalize-PublishPaths $Exclude

if (-not $Remote.Trim()) { throw 'Remote name cannot be empty.' }
$remoteUrl = git remote get-url $Remote 2>$null
if ($LASTEXITCODE -ne 0 -or -not $remoteUrl) { throw "Git remote '$Remote' was not found." }
if (-not $Branch) { $Branch = (git branch --show-current).Trim() }
if (-not $Branch) { throw 'Detached HEAD: specify -Branch.' }

$staged = @(git diff --cached --name-only --diff-filter=ACDMRTUXB)
if ($staged.Count -gt 0) {
    $staged | ForEach-Object { Write-Host "Already staged: $_" }
    throw 'Pre-staged changes detected. Unstage them or commit them separately, then retry.'
}

$tracked = @(git diff --name-only --diff-filter=ACDMRTUXB)
$untracked = @(git ls-files --others --exclude-standard)
switch ($ChangeSet) {
    'Tracked' { $candidates = @($tracked) }
    'Untracked' { $candidates = @($untracked) }
    'Changed' { $candidates = @($tracked + $untracked) }
    default { $candidates = @(git ls-files) + $untracked }
}
if ($AllAllowed) {
    $allTracked = @(git ls-files)
    $candidates = @($candidates + $allTracked | Sort-Object -Unique)
}
$candidates = @($candidates | Sort-Object -Unique)

$selection = Select-PublishPaths $candidates $allowedRoots $blockedPatterns $Include $Exclude
$selected = @($selection.Selected)
$excluded = @($selection.Excluded)

if ($selected.Count -eq 0) {
    Write-Host 'No eligible changes.'
    if ($excluded.Count -gt 0) { Write-Host ('Excluded: ' + ($excluded -join ', ')) }
    exit 0
}

Write-Host "Action: $Action | Changes: $ChangeSet | Remote: $Remote | Branch: $Branch"
Write-Host ('Selected: ' + ($selected -join ', '))
if ($excluded.Count -gt 0) { Write-Host ('Excluded: ' + ($excluded -join ', ')) }
if ($Action -eq 'Preview') { Write-Host 'Preview only. Use -Action Commit or -Action Push to publish.'; exit 0 }
if (-not $Message -or -not $Message.Trim()) { throw 'A commit message is required (-Message or SMKD_PUBLISH_MESSAGE).' }

# Prepare selected file contents outside the repo, then commit in an isolated worktree.
$stageRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("smkd-publish-stage-{0}" -f [guid]::NewGuid())
$worktreeRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("smkd-publish-worktree-{0}" -f [guid]::NewGuid())
$worktreeAdded = $false
try {
    New-Item -ItemType Directory -Path $stageRoot | Out-Null
    foreach ($path in $selected) {
        $source = Join-Path $repoRoot $path
        $stagedCopy = Join-Path $stageRoot $path
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            $parentDir = Split-Path -Parent $stagedCopy
            if ($parentDir) { New-Item -ItemType Directory -Force -Path $parentDir | Out-Null }
            Copy-Item -LiteralPath $source -Destination $stagedCopy
        } elseif (-not (Test-Path -LiteralPath $source)) {
            # A missing tracked path represents a deletion.
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stagedCopy) | Out-Null
        }
    }

    $branchExists = git show-ref --verify --quiet "refs/heads/$Branch"
    if ($LASTEXITCODE -eq 0) {
        $baseRef = "refs/heads/$Branch"
    } else {
        $remoteRef = git ls-remote --heads $Remote "refs/heads/$Branch"
        if ($LASTEXITCODE -ne 0) { throw "Could not inspect $Remote/$Branch." }
        if ($remoteRef) {
            Invoke-PublishGit @('fetch', '--no-tags', $Remote, "refs/heads/$Branch") "Could not fetch $Remote/$Branch."
            $baseRef = (git rev-parse FETCH_HEAD).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $baseRef) { throw "Could not resolve fetched branch $Remote/$Branch." }
        } else { throw "Target branch '$Branch' does not exist locally or on '$Remote'." }
    }

    Invoke-PublishGit @('worktree', 'add', '--detach', $worktreeRoot, $baseRef) 'Could not create isolated publish worktree.'
    $worktreeAdded = $true
    foreach ($path in $selected) {
        $source = Join-Path $stageRoot $path
        $destination = Join-Path $worktreeRoot $path
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            $parentDir = Split-Path -Parent $destination
            if ($parentDir) { New-Item -ItemType Directory -Force -Path $parentDir | Out-Null }
            Copy-Item -LiteralPath $source -Destination $destination -Force
        } else {
            Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
        }
    }

    Push-Location $worktreeRoot
    try {
        Invoke-PublishGit @('add', '--', $selected) 'Could not stage selected paths in isolated worktree.'
        & git diff --cached --check
        if ($LASTEXITCODE -ne 0) { throw 'Staged diff has whitespace errors.' }
        $stagedPaths = @(git diff --cached --name-only)
        if (@($stagedPaths | Where-Object { $_ -notin $selected }).Count -gt 0) { throw 'Unexpected paths entered the isolated commit.' }
        if ($stagedPaths.Count -eq 0) { throw 'Selected paths have no differences from the destination branch.' }

        $commitArgs = @('commit', '-m', $Message)
        if ($NoVerify) { $commitArgs += '--no-verify' }
        Invoke-PublishGit $commitArgs 'Commit failed in isolated worktree.'
        $commit = git rev-parse HEAD
        if ($Action -eq 'Push') {
            & git push $Remote "HEAD:refs/heads/$Branch"
            if ($LASTEXITCODE -ne 0) {
                $savedRef = "refs/codex/publish/$commit"
                git update-ref $savedRef $commit
                throw "Push failed. Commit is saved locally as $savedRef."
            }
        } else {
            $savedRef = "refs/codex/publish/$commit"
            Invoke-PublishGit @('update-ref', $savedRef, $commit) 'Could not preserve local commit reference.'
        }
    } finally { Pop-Location }

    if ($Action -eq 'Commit') {
        Write-Host "Created local commit $commit (saved under refs/codex/publish/$commit; current branch and checkout unchanged)."
    } else {
        Write-Host "Published $commit to $Remote/$Branch."
    }
} finally {
    if ($worktreeAdded) {
        git worktree remove --force $worktreeRoot 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove temporary worktree: $worktreeRoot" }
    }
    Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
}
