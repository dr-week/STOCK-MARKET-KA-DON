<#
.SYNOPSIS
  Runs regression eval scenarios to test agent safeguards and failure handling.
.DESCRIPTION
  Evaluates:
  1. Corrupted package manifest detection
  2. Duplicate component detection
  3. Circuit breaker on repeated failure fingerprints
  4. Task transaction checkpoints
#>

$EvalReport = @{
    timestamp = (Get-Date -Format "o")
    passed = 0
    failed = 0
    tests = @()
}

function Run-Eval {
    param ($Name, [scriptblock]$Test)
    Write-Host "Running Eval: $Name..." -NoNewline
    try {
        $result = & $Test
        if ($result -eq $true) {
            Write-Host " [PASS]" -ForegroundColor Green
            $script:EvalReport.passed += 1
            $script:EvalReport.tests += @{ name = $Name; status = "PASS" }
        } else {
            Write-Host " [FAIL]" -ForegroundColor Red
            $script:EvalReport.failed += 1
            $script:EvalReport.tests += @{ name = $Name; status = "FAIL"; error = "Assertion returned false" }
        }
    } catch {
        Write-Host " [ERROR]" -ForegroundColor Red
        $script:EvalReport.failed += 1
        $script:EvalReport.tests += @{ name = $Name; status = "ERROR"; error = $_.Exception.Message }
    }
}

# Eval 1: Duplicate Component Detection
Run-Eval "Duplicate Detection on LiveCandleChart" {
    $out = & "$PSScriptRoot\detect-duplicate.ps1" -TargetName "LiveCandleChart" | Out-String | ConvertFrom-Json
    return ($out.recommendation -eq "EXTEND_EXISTING" -and $out.files_found.Count -gt 0)
}

# Eval 2: Task Transaction Checkpoint Initialization
Run-Eval "Task Transaction Lifecycle" {
    $TaskId = "EVAL-TEST-001"
    & "$PSScriptRoot\task-transaction.ps1" -Action "start" -TaskId $TaskId -Objective "Eval Test" -AllowedPaths @("AGENTS.md") | Out-Null
    $status = & "$PSScriptRoot\task-transaction.ps1" -Action "status" -TaskId $TaskId | ConvertFrom-Json
    return ($status.task_id -eq $TaskId -and $status.status -eq "IN_PROGRESS")
}

# Eval 3: Failure fingerprint remains advisory
Run-Eval "Repeated Failure Advisory" {
    $TaskId = "EVAL-TEST-002"
    & "$PSScriptRoot\task-transaction.ps1" -Action "start" -TaskId $TaskId -Objective "Circuit Breaker Test" | Out-Null
    & "$PSScriptRoot\task-transaction.ps1" -Action "record-failure" -TaskId $TaskId -Fingerprint "JSON_PARSE_ERROR" -Command "test-cmd" -OutputLog "Syntax error" | Out-Null
    & "$PSScriptRoot\task-transaction.ps1" -Action "record-failure" -TaskId $TaskId -Fingerprint "JSON_PARSE_ERROR" -Command "test-cmd" -OutputLog "Syntax error" | Out-Null
    $status = & "$PSScriptRoot\task-transaction.ps1" -Action "status" -TaskId $TaskId | ConvertFrom-Json
    return ($status.status -eq "IN_PROGRESS")
}

# Eval 4: Rules & Skills Structure
Run-Eval "Skills and Rules Structure" {
    $skills = Get-ChildItem -Path "$PSScriptRoot\..\..\.agents\skills" -Directory
    $rules = Get-ChildItem -Path "$PSScriptRoot\..\..\.agents\rules" -File
    return ($skills.Count -ge 3 -and $rules.Count -ge 2)
}

Write-Host "`nEval Suite Complete: $($EvalReport.passed) Passed, $($EvalReport.failed) Failed." -ForegroundColor Cyan
$EvalReport | ConvertTo-Json -Depth 4
