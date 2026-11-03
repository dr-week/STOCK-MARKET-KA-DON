function Read-PublishConfig([string]$Path, [string]$RepoRoot) {
    if (-not [System.IO.Path]::IsPathRooted($Path)) { $Path = Join-Path $RepoRoot $Path }
    if (-not (Test-Path -LiteralPath $Path)) { return @{} }
    try {
        $configObject = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        $settings = @{}
        foreach ($property in $configObject.PSObject.Properties) { $settings[$property.Name] = $property.Value }
        return $settings
    } catch {
        throw "Invalid publisher JSON config '$Path': $($_.Exception.Message)"
    }
}

function Get-PublishPreset($ConfigData, [string]$Name) {
    if (-not $Name) { return $null }
    $property = if ($ConfigData.presets) { $ConfigData.presets.PSObject.Properties[$Name] } else { $null }
    if (-not $property) {
        $available = if ($ConfigData.presets) { @($ConfigData.presets.PSObject.Properties.Name) -join ', ' } else { '(none configured)' }
        throw "Unknown preset '$Name'. Available presets: $available"
    }
    return $property.Value
}
