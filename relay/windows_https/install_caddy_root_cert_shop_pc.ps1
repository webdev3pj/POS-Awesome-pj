param(
    [Parameter(Mandatory = $true)]
    [string]$CertPath,
    [switch]$CurrentUserOnly
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CertPath)) {
    throw "Certificate file not found: $CertPath"
}

$storeLocation = if ($CurrentUserOnly) { "CurrentUser" } else { "LocalMachine" }

try {
    Import-Certificate -FilePath $CertPath -CertStoreLocation ("Cert:\{0}\Root" -f $storeLocation) | Out-Null
    Write-Host ("Imported certificate into {0}\Root store." -f $storeLocation)
} catch {
    if ($CurrentUserOnly) {
        throw
    }
    Write-Warning "LocalMachine import failed (likely needs Administrator). Retrying CurrentUser..."
    Import-Certificate -FilePath $CertPath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
    Write-Host "Imported certificate into CurrentUser\Root store."
}

Write-Host "Close and reopen Chrome on this PC after trust installation."
