param(
    [string]$RelayHealthUrl = "https://192.168.50.168/health"
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Relaunch-AsAdmin {
    param([string]$ScriptPath, [string]$RelayHealthUrl)
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ('"{0}"' -f $ScriptPath),
        "-RelayHealthUrl", ('"{0}"' -f $RelayHealthUrl)
    ) -join " "
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $args | Out-Null
}

function Write-Step([string]$Text) {
    Write-Host ("[SHOP-PC SETUP] " + $Text) -ForegroundColor Cyan
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$certPath = Join-Path $scriptDir "caddy-local-root.crt"

if (-not (Test-Path $certPath)) {
    Write-Host "Certificate file not found: $certPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-IsAdmin)) {
    Write-Step "Requesting Administrator permission..."
    Relaunch-AsAdmin -ScriptPath $MyInvocation.MyCommand.Path -RelayHealthUrl $RelayHealthUrl
    exit 0
}

Write-Step "Importing local relay certificate into Trusted Root..."
& certutil.exe -addstore -f Root $certPath | Out-Host

Write-Step "Testing relay health URL: $RelayHealthUrl"
try {
    $resp = Invoke-WebRequest -Uri $RelayHealthUrl -UseBasicParsing -TimeoutSec 10
    if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
        Write-Host "SUCCESS: Relay health page is reachable and trusted." -ForegroundColor Green
        Write-Host "This PC is ready for the LAN relay." -ForegroundColor Green
        try {
            Start-Process $RelayHealthUrl | Out-Null
        } catch {}
        exit 0
    }
    Write-Host ("WARNING: Relay responded with HTTP " + $resp.StatusCode) -ForegroundColor Yellow
    exit 2
}
catch {
    Write-Host "Relay health test failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "If the OptiPlex relay is running and this PC is on the same LAN, re-run this script or contact IT." -ForegroundColor Yellow
    exit 3
}
