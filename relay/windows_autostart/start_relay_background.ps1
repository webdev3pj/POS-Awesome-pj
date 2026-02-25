param(
    [int]$RelayPort = 8787
)

$ErrorActionPreference = "Stop"

function Test-RelayHealth {
    param([int]$Port)
    try {
        $resp = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $Port) -TimeoutSec 3
        return [bool]($resp -and $resp.ok -eq $true)
    } catch {
        return $false
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$relayDir = Split-Path -Parent $scriptDir
$logsDir = Join-Path $scriptDir "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$configPath = Join-Path $relayDir "data\\relay_config.json"
if (-not $PSBoundParameters.ContainsKey("RelayPort") -and (Test-Path $configPath)) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        if ($cfg -and $cfg.relay_port) {
            $RelayPort = [int]$cfg.relay_port
        }
    } catch {
        Write-Warning ("Could not parse relay config for relay_port: {0}" -f $_.Exception.Message)
    }
}

if (Test-RelayHealth -Port $RelayPort) {
    Write-Host ("Relay already healthy on http://127.0.0.1:{0}" -f $RelayPort)
    exit 0
}

$pythonExe = Join-Path $relayDir ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw ("Relay virtualenv python not found: {0}" -f $pythonExe)
}

$outLog = Join-Path $logsDir "relay.out.log"
$errLog = Join-Path $logsDir "relay.err.log"

$p = Start-Process -FilePath $pythonExe `
    -ArgumentList "-m relay.app" `
    -WorkingDirectory $relayDir `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

Start-Sleep -Seconds 3

if (Test-RelayHealth -Port $RelayPort) {
    Write-Host ("Relay started. PID={0}. Port={1}" -f $p.Id, $RelayPort)
    exit 0
}

Write-Warning ("Relay process started (PID={0}) but /health is not responding yet. Check logs: {1}, {2}" -f $p.Id, $outLog, $errLog)
exit 1
