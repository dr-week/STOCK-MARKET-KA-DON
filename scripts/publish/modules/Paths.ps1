function Normalize-PublishPaths([string[]]$Paths) {
    return @($Paths | ForEach-Object { $_.Replace('\', '/').Trim().Trim('/') } | Where-Object { $_ })
}

function Test-PublishPathMatch([string]$Path, [string[]]$Rules) {
    foreach ($rule in $Rules) {
        if ($rule -match '[*?\[]') {
            if ($Path -like $rule) { return $true }
        } elseif ($Path -eq $rule -or $Path.StartsWith("$rule/", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Select-PublishPaths(
    [string[]]$Candidates,
    [string[]]$AllowedRoots,
    [string[]]$BlockedPatterns,
    [string[]]$Include,
    [string[]]$Exclude
) {
    $selected = @()
    $excluded = @()
    foreach ($path in $Candidates) {
        $safeRoot = Test-PublishPathMatch $path $AllowedRoots
        $blocked = $false
        foreach ($pattern in $BlockedPatterns) {
            if ($path -match $pattern) { $blocked = $true; break }
        }
        if ($Include.Count -gt 0 -and -not (Test-PublishPathMatch $path $Include)) { $safeRoot = $false }
        if ($Exclude.Count -gt 0 -and (Test-PublishPathMatch $path $Exclude)) { $safeRoot = $false }
        if ($safeRoot -and -not $blocked) { $selected += $path } else { $excluded += $path }
    }
    return @{ Selected = $selected; Excluded = $excluded }
}
