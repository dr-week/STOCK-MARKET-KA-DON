$ErrorActionPreference = 'Stop'

$runtimeGuid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$registryPaths = @(
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$runtimeGuid",
    "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$runtimeGuid",
    "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$runtimeGuid"
)

function Test-WebView2Runtime {
    foreach ($path in $registryPaths) {
        try {
            $versionText = (Get-ItemProperty -LiteralPath $path -Name pv -ErrorAction Stop).pv
            $version = [version]::MinVersion
            if ([version]::TryParse([string]$versionText, [ref]$version) -and $version -gt [version]'0.0.0.0') {
                return $true
            }
        } catch {
            continue
        }
    }
    return $false
}

if (Test-WebView2Runtime) {
    Write-Output 'WebView2 Runtime is available.'
    exit 0
}

$installer = Join-Path $env:TEMP "smkd-webview2-$PID.exe"
try {
    Write-Output 'Downloading the Microsoft WebView2 bootstrapper.'
    Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $installer

    $signature = Get-AuthenticodeSignature -FilePath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike 'CN=Microsoft Corporation,*') {
        throw 'The downloaded WebView2 bootstrapper does not have a valid Microsoft signature.'
    }

    Write-Output 'Installing WebView2 silently for the current user.'
    $process = Start-Process -FilePath $installer -ArgumentList '/silent', '/install' -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0 -and -not (Test-WebView2Runtime)) {
        throw "The WebView2 installer returned exit code $($process.ExitCode)."
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(60)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-WebView2Runtime) {
            Write-Output 'WebView2 Runtime is ready.'
            exit 0
        }
        Start-Sleep -Seconds 2
    }
    throw 'WebView2 installation completed without a registered runtime.'
} finally {
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
}
