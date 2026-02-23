param(
    [string]$LanIp = "192.168.50.168",
    [int]$RelayPort = 8787,
    [string]$CaddyExe = "caddy",
    [switch]$TrustRoot,
    [switch]$Background
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runDir = Join-Path $scriptDir "run"
$logsDir = Join-Path $scriptDir "logs"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

if (-not (Get-Command $CaddyExe -ErrorAction SilentlyContinue)) {
    throw "Caddy executable '$CaddyExe' not found. Run .\install_caddy.ps1 first."
}

$configPath = Join-Path $runDir "Caddyfile.active"
$configBody = @"
https://$LanIp {
    tls internal
    header {
        Access-Control-Allow-Origin *
        Access-Control-Allow-Methods "GET, POST, OPTIONS"
        Access-Control-Allow-Headers "Content-Type, Authorization"
    }
    @options method OPTIONS
    respond @options 204
    reverse_proxy 127.0.0.1:$RelayPort
}
"@
$configBody | Set-Content -Path $configPath -Encoding UTF8

$outLog = Join-Path $logsDir "caddy.out.log"
$errLog = Join-Path $logsDir "caddy.err.log"

if ($Background) {
    $p = Start-Process -FilePath $CaddyExe `
        -ArgumentList ("run --config `"{0}`"" -f $configPath) `
        -WorkingDirectory $scriptDir `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -PassThru
    Write-Host ("Started Caddy in background. PID={0}" -f $p.Id)
    Start-Sleep -Seconds 1
    if ($TrustRoot) {
        Write-Host "Running: caddy trust --config `"$configPath`""
        & $CaddyExe trust --config $configPath
    }
    Write-Host ("LAN URL: https://{0}" -f $LanIp)
    exit 0
}

if ($TrustRoot) {
    Write-Host "Running: caddy trust --config `"$configPath`""
    & $CaddyExe trust --config $configPath
}

Write-Host ("Starting Caddy foreground. LAN URL: https://{0}" -f $LanIp)
& $CaddyExe run --config $configPath
