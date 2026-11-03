<#
.SYNOPSIS
  Reports documentation affected by changed files using the maintained Python source map.
.PARAMETER DryRun
  Lists affected docs without modifying any files.
.PARAMETER Report
  Generates a JSON status report of documentation synchronization.
#>

param (
    [switch]$DryRun,
    [switch]$Report,
    [string[]]$ChangedFiles = @()
)

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$Arguments = @((Join-Path $PSScriptRoot "docs_tools\check.py"))
if ($ChangedFiles.Count -gt 0) {
    $Arguments += "--files"
    $Arguments += $ChangedFiles
}
if ($Report) { $Arguments += "--json" }
& $Python @Arguments
exit $LASTEXITCODE
