param(
    [string]$DestinationDir = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $DestinationDir) {
    $DestinationDir = Join-Path $scriptDir "export"
}
New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null

$candidatePaths = @(
    (Join-Path $env:APPDATA "Caddy\pki\authorities\local\root.crt"),
    (Join-Path $env:ProgramData "Caddy\pki\authorities\local\root.crt")
)

$rootCertPath = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $rootCertPath) {
    throw "Caddy local root certificate not found. Start Caddy with tls internal first."
}

$destPath = Join-Path $DestinationDir "caddy-local-root.crt"
Copy-Item -Force -Path $rootCertPath -Destination $destPath

Write-Host ("Exported Caddy local root cert to: {0}" -f $destPath)
