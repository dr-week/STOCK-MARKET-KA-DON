[CmdletBinding()]
param(
  [int]$Threshold = 250,
  [int]$Top = 30
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sourceRoots = @(
  (Join-Path $repoRoot 'stock-signal-bot/backend/app'),
  (Join-Path $repoRoot 'fast-framework/packages/stock-bot-ui/src'),
  (Join-Path $repoRoot 'scripts/dev')
)
$extensions = @('.py', '.ts', '.tsx', '.js', '.mjs')
$excluded = '\\(node_modules|dist|build|__pycache__|\.venv|coverage)\\'

$modules = foreach ($root in $sourceRoots) {
  if (-not (Test-Path -LiteralPath $root)) { continue }
  Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object {
    $extensions -contains $_.Extension.ToLowerInvariant() -and $_.FullName -notmatch $excluded
  } | ForEach-Object {
    [pscustomobject]@{
      Lines = @(Get-Content -LiteralPath $_.FullName).Count
      File = $_.FullName.Substring($repoRoot.Length + 1)
    }
  }
}

$large = @($modules | Where-Object { $_.Lines -ge $Threshold } | Sort-Object Lines -Descending | Select-Object -First $Top)
Write-Output "Large source modules (threshold: $Threshold lines)"
if ($large.Count -eq 0) {
  Write-Output 'No modules exceed the threshold.'
  exit 0
}
$large | Format-Table Lines, File -AutoSize
Write-Output ''
Write-Output 'Review rule: line count identifies candidates; split only at a responsibility, dependency, and test boundary.'
