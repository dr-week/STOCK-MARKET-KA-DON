param(
    [Parameter(Mandatory = $true)][string]$BackendSource,
    [Parameter(Mandatory = $true)][string]$RuntimeDir,
    [Parameter(Mandatory = $true)][string]$AppVersion
)

$ErrorActionPreference = 'Stop'
$uvVersion = '0.13.7'
$uvSha256 = '0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021'
$venvDir = Join-Path $RuntimeDir 'venv'
$pythonExe = Join-Path $venvDir 'Scripts\python.exe'
$marker = Join-Path $RuntimeDir 'runtime-version.txt'
$uvExe = Join-Path $RuntimeDir 'tools\uv.exe'

# Tauri returns extended Windows paths (\\?\C:\...) that PowerShell's file
# provider cannot use directly with Join-Path. The normal DOS path is safe here.
if ($BackendSource.StartsWith('\\?\')) { $BackendSource = $BackendSource.Substring(4) }
if ($RuntimeDir.StartsWith('\\?\')) { $RuntimeDir = $RuntimeDir.Substring(4) }
$backendLock = Join-Path $BackendSource 'requirements-lock.txt'

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

if ((Test-Path $pythonExe) -and (Test-Path $marker) -and ((Get-Content $marker -Raw).Trim() -eq $AppVersion)) {
    Write-Output 'Backend environment is already ready.'
    exit 0
}

Write-Output 'Preparing the private SMKD backend environment.'
if (-not (Test-Path -LiteralPath $backendLock)) {
    throw 'The packaged backend files are missing from the application.'
}

if (-not (Test-Path $uvExe)) {
    $toolsDir = Split-Path -Parent $uvExe
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
    $download = Join-Path $RuntimeDir "uv-$uvVersion-windows-x64.zip"
    $extractDir = Join-Path $RuntimeDir "uv-extract-$PID"
    $uri = "https://github.com/astral-sh/uv/releases/download/$uvVersion/uv-x86_64-pc-windows-msvc.zip"
    Write-Output 'Downloading the pinned Python environment manager.'
    Invoke-WebRequest -Uri $uri -OutFile $download
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($download)
    try {
        $actualHash = [System.BitConverter]::ToString($sha256.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
    if ($actualHash -ne $uvSha256) { throw 'The downloaded environment manager failed its SHA-256 check.' }
    Expand-Archive -LiteralPath $download -DestinationPath $extractDir -Force
    $uvFile = Get-ChildItem -LiteralPath $extractDir -Filter 'uv.exe' -Recurse | Select-Object -First 1
    if (-not $uvFile) { throw 'The downloaded environment manager archive did not contain uv.exe.' }
    Copy-Item -LiteralPath $uvFile.FullName -Destination $uvExe -Force
    Remove-Item -LiteralPath $download, $extractDir -Recurse -Force
}

$env:UV_PYTHON_INSTALL_DIR = Join-Path $RuntimeDir 'python'
$env:UV_CACHE_DIR = Join-Path $RuntimeDir 'cache'
$env:UV_PYTHON_DOWNLOADS = 'automatic'

Write-Output 'Downloading a private Python runtime if needed.'
& $uvExe python install 3.14
if ($LASTEXITCODE -ne 0) { throw "Private Python download failed with exit code $LASTEXITCODE." }
& $uvExe venv --clear --python 3.14 --managed-python $venvDir
if ($LASTEXITCODE -ne 0) { throw "Python environment creation failed with exit code $LASTEXITCODE." }

Write-Output 'Installing the locked backend dependencies.'
& $uvExe pip sync --python $pythonExe $backendLock
if ($LASTEXITCODE -ne 0) { throw "Backend dependency setup failed with exit code $LASTEXITCODE." }

Write-Output 'Removing the temporary package-download cache.'
& $uvExe cache clean
if ($LASTEXITCODE -ne 0) { throw "Temporary package-cache cleanup failed with exit code $LASTEXITCODE." }

Set-Content -LiteralPath $marker -Value $AppVersion -Encoding ascii
Write-Output 'Private backend environment is ready.'
