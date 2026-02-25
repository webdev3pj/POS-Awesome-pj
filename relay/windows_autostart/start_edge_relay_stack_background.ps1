param(
    [string]$LanIp = "",
    [int]$RelayPort = 8787,
    [string]$CaddyExe = "",
    [string]$CaddyAppData = "",
    [string]$CaddyLocalAppData = ""
)

$ErrorActionPreference = "Stop"

function Test-RelayHealthHttp {
    param([int]$Port)
    try {
        $resp = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $Port) -TimeoutSec 3
        return [bool]($resp -and $resp.ok -eq $true)
    } catch {
        return $false
    }
}

function Test-RelayHealthHttpsLan {
    param([string]$Ip)
    if ([string]::IsNullOrWhiteSpace($Ip)) { return $false }
    try {
        $prevCallback = [System.Net.ServicePointManager]::ServerCertificateValidationCallback
        try {
            # Startup task may run as SYSTEM, which may not trust the local Caddy root
            # in the same user store. This health probe is local-only, so bypass trust here.
            [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
            $resp = Invoke-RestMethod -Uri ("https://{0}/health" -f $Ip) -TimeoutSec 3
            return [bool]($resp -and $resp.ok -eq $true)
        } finally {
            [System.Net.ServicePointManager]::ServerCertificateValidationCallback = $prevCallback
        }
    } catch {
        return $false
    }
}

function Get-LanIpFromConfig {
    param([string]$ConfigPath)
    if (-not (Test-Path $ConfigPath)) { return "" }
    try {
        $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
        if ($cfg -and $cfg.public_base_url) {
            $uri = [Uri]([string]$cfg.public_base_url)
            return [string]$uri.Host
        }
    } catch {
        Write-Warning ("Could not derive LAN IP from relay_config.json public_base_url: {0}" -f $_.Exception.Message)
    }
    return ""
}

function Test-Blocking443Listener {
    param([string]$Ip)
    $listeners = Get-NetTCPConnection -LocalPort 443 -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) { return $false }

    foreach ($l in $listeners) {
        $addr = [string]$l.LocalAddress
        if ($addr -in @("0.0.0.0", "::", "::0", $Ip)) {
            return $true
        }
    }
    return $false
}

function Test-CaddyLanListener {
    param([string]$Ip)

    $listeners = Get-NetTCPConnection -LocalPort 443 -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) { return $false }

    foreach ($l in $listeners) {
        $addr = [string]$l.LocalAddress
        if ($addr -notin @("0.0.0.0", "::", "::0", $Ip)) {
            continue
        }

        try {
            $procId = [int]$l.OwningProcess
            $p = Get-Process -Id $procId -ErrorAction Stop
            if ([string]::Equals([string]$p.ProcessName, "caddy", [System.StringComparison]::OrdinalIgnoreCase)) {
                return $true
            }
        } catch {
            continue
        }
    }

    return $false
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$relayDir = Split-Path -Parent $scriptDir
$relayConfigPath = Join-Path $relayDir "data\\relay_config.json"

if (-not $PSBoundParameters.ContainsKey("LanIp") -or [string]::IsNullOrWhiteSpace($LanIp)) {
    $LanIp = Get-LanIpFromConfig -ConfigPath $relayConfigPath
    if ([string]::IsNullOrWhiteSpace($LanIp)) {
        $LanIp = "192.168.50.168"
    }
}

if (-not $PSBoundParameters.ContainsKey("RelayPort") -and (Test-Path $relayConfigPath)) {
    try {
        $cfg = Get-Content $relayConfigPath -Raw | ConvertFrom-Json
        if ($cfg -and $cfg.relay_port) {
            $RelayPort = [int]$cfg.relay_port
        }
    } catch {}
}

$relayStarter = Join-Path $scriptDir "start_relay_background.ps1"
if (-not (Test-Path $relayStarter)) {
    throw ("Missing relay starter script: {0}" -f $relayStarter)
}

Write-Host ("Starting/ensuring relay on port {0}..." -f $RelayPort)
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $relayStarter -RelayPort $RelayPort

if (-not (Test-RelayHealthHttp -Port $RelayPort)) {
    throw "Relay /health is not reachable after relay start attempt."
}

if (Test-RelayHealthHttpsLan -Ip $LanIp) {
    Write-Host ("LAN HTTPS relay already healthy at https://{0}" -f $LanIp)
    exit 0
}

if (Test-CaddyLanListener -Ip $LanIp) {
    Write-Warning ("Caddy is already listening for LAN IP {0} on :443, but HTTPS health probe did not succeed in this startup context. Treating as started." -f $LanIp)
    exit 0
}

$blocking443 = Test-Blocking443Listener -Ip $LanIp
if ($blocking443) {
    Write-Warning ("Port 443 already has a blocking listener for LAN IP {0} (or all interfaces), and LAN HTTPS relay /health did not respond. Leaving existing listener untouched." -f $LanIp)
    exit 1
}

$caddyStarter = Join-Path $relayDir "windows_https\\start_caddy_lan_https.ps1"
if (-not (Test-Path $caddyStarter)) {
    throw ("Missing Caddy starter script: {0}" -f $caddyStarter)
}

Write-Host ("Starting Caddy LAN HTTPS proxy for https://{0} -> 127.0.0.1:{1}" -f $LanIp, $RelayPort)
$caddyArgs = @(
    "-NoProfile",
    "-ExecutionPolicy","Bypass",
    "-File",$caddyStarter,
    "-LanIp",$LanIp,
    "-RelayPort",$RelayPort,
    "-Background"
)
if (-not [string]::IsNullOrWhiteSpace($CaddyExe)) {
    $caddyArgs += @("-CaddyExe", $CaddyExe)
}
if (-not [string]::IsNullOrWhiteSpace($CaddyAppData)) {
    $caddyArgs += @("-CaddyAppData", $CaddyAppData)
}
if (-not [string]::IsNullOrWhiteSpace($CaddyLocalAppData)) {
    $caddyArgs += @("-CaddyLocalAppData", $CaddyLocalAppData)
}
& powershell.exe @caddyArgs

Start-Sleep -Seconds 3

if (Test-RelayHealthHttpsLan -Ip $LanIp) {
    Write-Host ("LAN HTTPS relay healthy at https://{0}" -f $LanIp)
    exit 0
}

if (Test-CaddyLanListener -Ip $LanIp) {
    Write-Warning ("Caddy listener is up for LAN IP {0} on :443, but HTTPS health probe did not succeed in this startup context. Treating as started." -f $LanIp)
    exit 0
}

Write-Warning ("Caddy start attempted, but https://{0}/health is not responding yet. Check relay/windows_https/logs/*" -f $LanIp)
exit 1
