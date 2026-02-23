param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Test-CaddyInstalled {
    return [bool](Get-Command caddy -ErrorAction SilentlyContinue)
}

if ((Test-CaddyInstalled) -and -not $Force) {
    Write-Host "Caddy is already installed."
    exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget is required to install Caddy automatically."
}

Write-Host "Installing Caddy via winget..."
winget install --id CaddyServer.Caddy -e --accept-source-agreements --accept-package-agreements

if (-not (Test-CaddyInstalled)) {
    throw "Caddy install completed but 'caddy' command is still not available in PATH."
}

Write-Host "Caddy installation complete."
