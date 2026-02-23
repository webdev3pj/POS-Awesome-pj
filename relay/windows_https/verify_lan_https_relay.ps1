param(
    [string]$RelayUrl = "https://192.168.50.168"
)

$ErrorActionPreference = "Stop"

$healthUrl = ($RelayUrl.TrimEnd("/") + "/health")
Write-Host ("Checking {0}" -f $healthUrl)

try {
    $resp = Invoke-RestMethod -Uri $healthUrl -Method Get
    if (-not $resp.ok) {
        throw "Relay responded but did not report ok=true"
    }
    Write-Host "LAN HTTPS relay health check passed."
    $resp | ConvertTo-Json -Depth 6
} catch {
    Write-Error $_
    exit 1
}
