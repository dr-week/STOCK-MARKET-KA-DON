<#
.SYNOPSIS
  Manages SMKD change transactions and task checkpoints.
.DESCRIPTION
  Initializes a task transaction, records baseline git status, copies original files,
  and verifies completion against allowed paths and test outputs.
#>

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "log-cmd", "record-failure", "verify", "status")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [string]$TaskId,

    [Parameter(Mandatory=$false)]
    [string]$Objective,

    [Parameter(Mandatory=$false)]
    [string[]]$AllowedPaths = @(),

    [Parameter(Mandatory=$false)]
    [string]$Command,

    [Parameter(Mandatory=$false)]
    [int]$ExitCode = 0,

    [Parameter(Mandatory=$false)]
    [string]$OutputLog = "",

    [Parameter(Mandatory=$false)]
    [string]$Fingerprint = "",

    [Parameter(Mandatory=$false)]
    [string]$Status = "IN_PROGRESS"
)

$RuntimeBase = Join-Path $PSScriptRoot "..\..\.runtime\tasks"

function Init-Task {
    param ($Id, $Obj, $Paths)
    $TaskDir = Join-Path $RuntimeBase $Id
    $BeforeDir = Join-Path $TaskDir "before"
    New-Item -ItemType Directory -Force -Path $BeforeDir | Out-Null

    $GitStatus = git status --porcelain
    Set-Content -Path (Join-Path $TaskDir "git-status-before.txt") -Value $GitStatus

    git diff > (Join-Path $TaskDir "diff-before.patch")

    # Save original copies of allowed files if they exist
    foreach ($p in $Paths) {
        if (Test-Path $p) {
            $dest = Join-Path $BeforeDir ([System.IO.Path]::GetFileName($p))
            Copy-Item -Path $p -Destination $dest -Force
        }
    }

    $TaskData = @{
        task_id = $Id
        status = "IN_PROGRESS"
        objective = $Obj
        allowed_paths = $Paths
        created_at = (Get-Date -Format "o")
        completed_steps = @()
        failed_step = $null
        retry_counts = @{}
        test_results = @{}
        next_action = "Execute task procedure"
    }
    $TaskData | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $TaskDir "task.json")
    Write-Output "Task transaction initialized at: $TaskDir"
}

function Log-Command {
    param ($Id, $Cmd, $Code, $Log)
    $TaskDir = Join-Path $RuntimeBase $Id
    $CmdEntry = @{
        timestamp = (Get-Date -Format "o")
        command = $Cmd
        exit_code = $Code
        output_snippet = if ($Log.Length -gt 500) { $Log.Substring(0, 500) } else { $Log }
    }
    $Line = $CmdEntry | ConvertTo-Json -Compress
    Add-Content -Path (Join-Path $TaskDir "commands.jsonl") -Value $Line
}

function Record-Failure {
    param ($Id, $Fp, $Cmd, $Log)
    $TaskDir = Join-Path $RuntimeBase $Id
    $TaskJsonPath = Join-Path $TaskDir "task.json"
    if (-not (Test-Path $TaskJsonPath)) { return }

    $TaskData = Get-Content $TaskJsonPath -Raw | ConvertFrom-Json -AsHashtable
    $CurrentCount = 0
    if ($TaskData.retry_counts.ContainsKey($Fp)) {
        $CurrentCount = [int]$TaskData.retry_counts[$Fp]
    }
    $CurrentCount += 1
    $TaskData.retry_counts[$Fp] = $CurrentCount
    $TaskData.failed_step = @{
        fingerprint = $Fp
        command = $Cmd
        attempt = $CurrentCount
        timestamp = (Get-Date -Format "o")
    }

    if ($CurrentCount -ge 2) {
        $TaskData.next_action = "Repeated failure recorded for $Fp. Review logs if useful."
        Write-Warning "Repeated failure recorded for '$Fp'; editing and retries remain available."
    }

    $TaskData | ConvertTo-Json -Depth 5 | Set-Content -Path $TaskJsonPath
}

function Verify-Task {
    param ($Id)
    $TaskDir = Join-Path $RuntimeBase $Id
    $TaskJsonPath = Join-Path $TaskDir "task.json"
    if (-not (Test-Path $TaskJsonPath)) { 
        Write-Error "Task $Id not found."
        return
    }

    $TaskData = Get-Content $TaskJsonPath -Raw | ConvertFrom-Json
    git diff > (Join-Path $TaskDir "diff-after.patch")

    # Scope check
    $CurrentStatus = git status --porcelain
    Set-Content -Path (Join-Path $TaskDir "git-status-after.txt") -Value $CurrentStatus

    $TaskData.status = "VERIFIED"
    $TaskData | ConvertTo-Json -Depth 5 | Set-Content -Path $TaskJsonPath
    Write-Output "Task $Id verified. Diff and state recorded in $TaskDir"
}

switch ($Action) {
    "start" { Init-Task -Id $TaskId -Obj $Objective -Paths $AllowedPaths }
    "log-cmd" { Log-Command -Id $TaskId -Cmd $Command -Code $ExitCode -Log $OutputLog }
    "record-failure" { Record-Failure -Id $TaskId -Fp $Fingerprint -Cmd $Command -Log $OutputLog }
    "verify" { Verify-Task -Id $TaskId }
    "status" {
        $TaskJson = Join-Path $RuntimeBase "$TaskId\task.json"
        if (Test-Path $TaskJson) { Get-Content $TaskJson } else { Write-Output "No task found for $TaskId" }
    }
}
