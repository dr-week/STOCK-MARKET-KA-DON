param(
    [Parameter(Position = 0)]
    [string]$Message = "",

    [switch]$Publish
)

$ErrorActionPreference = 'Stop'
$repoRoot = (git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repoRoot) {
    throw 'Run this script from inside the SMKD Git repository.'
}
Set-Location -LiteralPath $repoRoot

# These are intentionally the only root-repository paths this helper stages.
# Add new source/documentation roots here when the project layout changes.
$allowedRoots = @(
    'README.md', 'DOCS.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'AGENTS.md',
    '.gitignore', '.gitmodules', 'package.json', 'pnpm-lock.yaml',
    'capacitor.config.json', 'android', 'desktop', 'docs', 'launcher',
    'scripts', 'stock-signal-bot', '.github'
)

$tracked = @(git diff --name-only --diff-filter=ACDMRTUXB)
$staged = @(git diff --cached --name-only --diff-filter=ACDMRTUXB)
$untracked = @(git ls-files --others --exclude-standard)
$candidates = @($tracked + $staged + $untracked | Sort-Object -Unique)

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
        Write-Host 'Excluded local/runtime/submodule changes:'
        $excluded | ForEach-Object { Write-Host "  - $_" }
    }
    exit 0
}

Write-Host 'Files eligible for publish:'
$selected | ForEach-Object { Write-Host "  + $_" }
if ($excluded.Count -gt 0) {
    Write-Host 'Excluded files (will not be uploaded):'
    $excluded | ForEach-Object { Write-Host "  - $_" }
}

if (-not $Publish) {
    Write-Host ''
    Write-Host 'Preview only. Review the list, then run:'
    Write-Host '  pnpm publish:now -- "docs: update setup guide"'
    exit 0
}

if (-not $Message.Trim()) {
    throw 'Provide a short commit message. Example: pnpm publish:now -- "docs: update setup guide"'
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

$branch = (git branch --show-current).Trim()
if (-not $branch) { throw 'Cannot publish from a detached HEAD.' }
git push origin $branch
if ($LASTEXITCODE -ne 0) { throw "Push failed. Commit is local on '$branch'; inspect Git status and retry after resolving the push error." }

Write-Host "Published commit to origin/$branch."
