$ErrorActionPreference = 'Stop'

$tauriRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$sourceExe = Join-Path $tauriRoot 'src-tauri\target\release\smkd-windows.exe'
$sourceBackend = Join-Path $tauriRoot 'bundle\backend'
$sourceBootstrap = Join-Path $PSScriptRoot 'prepare_backend.ps1'
$sourceWebViewBootstrap = Join-Path $PSScriptRoot 'ensure_webview.ps1'
$destination = Join-Path $tauriRoot 'portable'

foreach ($required in @($sourceExe, (Join-Path $sourceBackend 'requirements-lock.txt'), $sourceBootstrap, $sourceWebViewBootstrap)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Portable launcher input is missing: $required"
    }
}

$resolvedDestination = [System.IO.Path]::GetFullPath($destination)
if (-not $resolvedDestination.StartsWith($tauriRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Portable output must stay inside the Tauri project: $resolvedDestination"
}
if (Test-Path -LiteralPath $resolvedDestination) {
    Remove-Item -LiteralPath $resolvedDestination -Recurse -Force
}

New-Item -ItemType Directory -Path $resolvedDestination | Out-Null
Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $resolvedDestination 'Stock Market Ka Don.exe')
Copy-Item -LiteralPath $sourceBackend -Destination (Join-Path $resolvedDestination 'backend') -Recurse
New-Item -ItemType Directory -Path (Join-Path $resolvedDestination 'bootstrap') | Out-Null
Copy-Item -LiteralPath $sourceBootstrap -Destination (Join-Path $resolvedDestination 'bootstrap\prepare_backend.ps1')
Copy-Item -LiteralPath $sourceWebViewBootstrap -Destination (Join-Path $resolvedDestination 'bootstrap\ensure_webview.ps1')

Write-Output "Portable launcher ready: $resolvedDestination"
Write-Output 'Run Stock Market Ka Don.exe from this folder. No Python or Node installation is required.'
