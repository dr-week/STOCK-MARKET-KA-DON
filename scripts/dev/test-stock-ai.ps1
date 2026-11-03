<#
.SYNOPSIS
  Runs focused, offline-first stock AI and development-tool tests.
.EXAMPLE
  .\scripts\dev\test-stock-ai.ps1 -Suite ai
  .\scripts\dev\test-stock-ai.ps1 -Suite offline
  .\scripts\dev\test-stock-ai.ps1 -Suite market-data -LiveProvider
  .\scripts\dev\test-stock-ai.ps1 -TestPath stock-signal-bot\backend\app\tests\test_backtest_engine.py -Keyword gap
#>
[CmdletBinding()]
param(
    [ValidateSet("ai", "training", "backtest", "feedback", "paper", "market-data", "integration", "dev-tools", "offline")]
    [string]$Suite = "ai",
    [string[]]$TestPath = @(),
    [string]$Keyword = "",
    [string]$PythonPath = "",
    [switch]$LiveProvider
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backendRoot = Join-Path $repoRoot "stock-signal-bot\backend"
$defaultPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not $PythonPath) {
    $PythonPath = if (Test-Path $defaultPython) {
        $defaultPython
    } else {
        (Get-Command python.exe -ErrorAction Stop).Source
    }
}
if (-not (Test-Path $PythonPath)) {
    throw "Python interpreter not found: $PythonPath"
}

$backendTests = "stock-signal-bot\backend\app\tests"
$suites = @{
    ai = @("$backendTests\test_system_one_model.py", "$backendTests\test_system_one_components.py")
    training = @("$backendTests\test_ai_training.py")
    backtest = @("$backendTests\test_backtest_engine.py", "$backendTests\test_profitability.py", "$backendTests\test_price_action_patterns.py")
    feedback = @("$backendTests\test_feedback_recorder.py", "$backendTests\test_paper_automation.py")
    paper = @("$backendTests\test_paper_trading.py", "$backendTests\test_paper_automation.py", "$backendTests\test_paper_auto_runner.py")
    "market-data" = @("$backendTests\test_market_data_freshness.py", "$backendTests\test_market_history_store.py", "$backendTests\test_provider_replay.py")
    integration = @("$backendTests\test_api_surface_contract.py", "$backendTests\test_groww_integration.py")
    "dev-tools" = @("scripts\dev\tests")
    offline = @(
        "$backendTests\test_system_one_model.py",
        "$backendTests\test_system_one_components.py",
        "$backendTests\test_ai_training.py",
        "$backendTests\test_backtest_engine.py",
        "$backendTests\test_profitability.py",
        "$backendTests\test_price_action_patterns.py",
        "$backendTests\test_feedback_recorder.py",
        "$backendTests\test_paper_automation.py",
        "$backendTests\test_paper_auto_runner.py",
        "$backendTests\test_paper_trading.py",
        "$backendTests\test_market_data_freshness.py",
        "$backendTests\test_market_history_store.py",
        "$backendTests\test_provider_replay.py",
        "$backendTests\test_api_surface_contract.py",
        "$backendTests\test_groww_integration.py",
        "scripts\dev\tests"
    )
}

$paths = if ($TestPath.Count) { $TestPath } else { $suites[$Suite] }
if ($LiveProvider) {
    $paths += "$backendTests\test_live_provider_integration.py"
}
$resolvedPaths = foreach ($path in $paths) {
    $fullPath = if ([IO.Path]::IsPathRooted($path)) { $path } else { Join-Path $repoRoot $path }
    if (-not (Test-Path $fullPath)) {
        throw "Test path not found: $path"
    }
    $fullPath
}

$oldPythonPath = $env:PYTHONPATH
$oldLiveSetting = $env:SMKD_LIVE_PROVIDER_TESTS
$pythonEntries = @($repoRoot, $backendRoot)
if ($oldPythonPath) {
    $pythonEntries += $oldPythonPath -split [IO.Path]::PathSeparator
}
$env:PYTHONPATH = $pythonEntries -join [IO.Path]::PathSeparator
if ($LiveProvider) {
    $env:SMKD_LIVE_PROVIDER_TESTS = "1"
} else {
    Remove-Item Env:SMKD_LIVE_PROVIDER_TESTS -ErrorAction SilentlyContinue
}

$pytestArgs = @("-m", "pytest", "-q") + $resolvedPaths
if ($Keyword) {
    $pytestArgs += @("-k", $Keyword)
}

Write-Host "Running $Suite tests with $PythonPath"
Push-Location $repoRoot
try {
    & $PythonPath @pytestArgs
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
    $env:PYTHONPATH = $oldPythonPath
    if ($null -eq $oldLiveSetting) {
        Remove-Item Env:SMKD_LIVE_PROVIDER_TESTS -ErrorAction SilentlyContinue
    } else {
        $env:SMKD_LIVE_PROVIDER_TESTS = $oldLiveSetting
    }
}
exit $exitCode
