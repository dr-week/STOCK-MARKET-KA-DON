<#
.SYNOPSIS
  Checks the local SMKD API, frontend, CORS, and served frontend assets.
.EXAMPLE
  npm run doctor:integration
.EXAMPLE
  .\scripts\dev\check-smkd-integration.ps1 -BackendUrl http://127.0.0.1:8000 -FrontendUrl http://127.0.0.1:5173
#>
[CmdletBinding()]
param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$FrontendUrl = "http://127.0.0.1:5173"
)

$ErrorActionPreference = "Stop"
$failures = [System.Collections.Generic.List[string]]::new()

function Get-CheckedResponse {
    param([string]$Label, [string]$Uri, [hashtable]$Headers = @{})
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -Headers $Headers -TimeoutSec 5
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            throw "HTTP $($response.StatusCode)"
        }
        Write-Host "[PASS] $Label (HTTP $($response.StatusCode))" -ForegroundColor Green
        return $response
    } catch {
        $script:failures.Add("$Label - $($_.Exception.Message)")
        Write-Host "[FAIL] $Label - $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

$backendBase = $BackendUrl.TrimEnd("/")
$frontendBase = $FrontendUrl.TrimEnd("/")
$health = Get-CheckedResponse "Backend health" "$backendBase/health"
$openApiResponse = Get-CheckedResponse "Backend OpenAPI" "$backendBase/openapi.json"

if ($health) {
    try {
        $healthBody = $health.Content | ConvertFrom-Json
        if ($healthBody.status -ne "ok") { throw "Expected status 'ok', received '$($healthBody.status)'." }
    } catch {
        $failures.Add("Backend health payload - $($_.Exception.Message)")
        Write-Host "[FAIL] Backend health payload - $($_.Exception.Message)" -ForegroundColor Red
    }

    $cors = Get-CheckedResponse "Frontend-to-backend CORS" "$backendBase/health" @{
        Origin = $frontendBase
    }
    if ($cors -and $cors.Headers["Access-Control-Allow-Origin"] -ne $frontendBase) {
        $failures.Add("CORS does not allow $frontendBase.")
        Write-Host "[FAIL] CORS does not allow $frontendBase." -ForegroundColor Red
    } elseif ($cors) {
        Write-Host "[PASS] CORS allows $frontendBase" -ForegroundColor Green
    }
}

if ($openApiResponse) {
    try {
        $openApi = $openApiResponse.Content | ConvertFrom-Json
        foreach ($route in @("/api/scan", "/api/stock/{symbol}")) {
            if (-not $openApi.paths.PSObject.Properties.Name.Contains($route)) {
                throw "Required API route is missing: $route"
            }
        }
        Write-Host "[PASS] Required scan and stock API routes are published" -ForegroundColor Green
    } catch {
        $failures.Add("Backend API contract - $($_.Exception.Message)")
        Write-Host "[FAIL] Backend API contract - $($_.Exception.Message)" -ForegroundColor Red
    }
}

$frontend = Get-CheckedResponse "Frontend page" "$frontendBase/"
if ($frontend) {
    $assets = [regex]::Matches($frontend.Content, '(?:src|href)="([^"]+\.(?:js|css))"') |
        ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -notmatch '^https?://' }
    if (-not $assets) {
        $failures.Add("Frontend page contains no local JavaScript or CSS assets.")
        Write-Host "[FAIL] Frontend page contains no local JavaScript or CSS assets." -ForegroundColor Red
    }
    foreach ($asset in $assets) {
        $assetUri = [System.Uri]::new("$frontendBase/", $asset).AbsoluteUri
        $null = Get-CheckedResponse "Frontend asset $asset" $assetUri
    }
}

if ($failures.Count) {
    Write-Host "`nIntegration check failed ($($failures.Count) issue(s))." -ForegroundColor Red
    Write-Host "Start/restart the API with: npm run dev:backend"
    Write-Host "Start/restart the UI with: npm run dev:ui"
    exit 1
}

Write-Host "`nSMKD backend/frontend integration checks passed." -ForegroundColor Green
