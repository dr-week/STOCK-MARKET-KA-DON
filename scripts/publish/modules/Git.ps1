function Invoke-PublishGit([string[]]$Arguments, [string]$Failure) {
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw $Failure }
}

function Get-PublishRepoRoot {
    $root = (git rev-parse --show-toplevel).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $root) { throw 'Run inside the SMKD Git repository.' }
    return $root
}
