param(
    [string]$TaskName = "POSRelayStack_Autostart",
    [switch]$RunNow,
    [switch]$SystemStartup
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-RunKeyAutostart {
    param(
        [string]$Name,
        [string]$CommandLine
    )
    $runKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    if (-not (Test-Path $runKey)) {
        New-Item -Path $runKey -Force | Out-Null
    }
    Set-ItemProperty -Path $runKey -Name $Name -Value $CommandLine -Type String
}

function Get-StableCaddyExePath {
    param([string]$RelayRoot)
    $localCopy = Join-Path $RelayRoot "windows_https\\run\\caddy.exe"
    if (Test-Path $localCopy) {
        return $localCopy
    }
    $cmd = Get-Command caddy.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { return "" }

    $src = $cmd.Source
    $dstDir = Split-Path -Parent $localCopy
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    }

    try {
        Copy-Item -Path $src -Destination $localCopy -Force
        return $localCopy
    } catch {
        Write-Warning ("Could not copy caddy.exe to local run folder. Using source path instead. Error: {0}" -f $_.Exception.Message)
        return $src
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$starter = Join-Path $scriptDir "start_edge_relay_stack_background.ps1"
if (-not (Test-Path $starter)) {
    throw ("Missing starter script: {0}" -f $starter)
}
$relayRoot = Split-Path -Parent $scriptDir
$caddyExePath = Get-StableCaddyExePath -RelayRoot $relayRoot
$starterArgs = ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $starter)
if (-not [string]::IsNullOrWhiteSpace($caddyExePath)) {
    $starterArgs += (' -CaddyExe "{0}"' -f $caddyExePath)
}
$currentAppData = [string]$env:APPDATA
$currentLocalAppData = [string]$env:LOCALAPPDATA
if (-not [string]::IsNullOrWhiteSpace($currentAppData)) {
    $starterArgs += (' -CaddyAppData "{0}"' -f $currentAppData)
}
if (-not [string]::IsNullOrWhiteSpace($currentLocalAppData)) {
    $starterArgs += (' -CaddyLocalAppData "{0}"' -f $currentLocalAppData)
}

if ($SystemStartup) {
    if (-not (Test-IsAdmin)) {
        throw "System startup task installation requires an Administrator PowerShell session."
    }

    if ($TaskName -eq "POSRelayStack_Autostart") {
        $TaskName = "POSRelayStack_Autostart_OnStart"
    }

    Write-Host "Installing system-startup (ONSTART) autostart task for relay + Caddy..."
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $starterArgs
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT20S"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Start POS relay + Caddy stack at system startup" -Force | Out-Null
    Write-Host ("Scheduled task '{0}' installed (ONSTART as SYSTEM)." -f $TaskName)

    if ($RunNow) {
        Write-Host ("Running task '{0}' now..." -f $TaskName)
        Start-ScheduledTask -TaskName $TaskName
    }

    Write-Host "Done."
    exit 0
}

Write-Host "Installing user-logon autostart task for relay + Caddy..."
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $starterArgs
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$registeredTask = $false
try {
    if (Test-IsAdmin) {
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
    } else {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Start POS relay + Caddy stack at user logon" -Force | Out-Null
    }
    $registeredTask = $true
    Write-Host ("Scheduled task '{0}' installed (ONLOGON)." -f $TaskName)
} catch {
    Write-Warning ("Scheduled Task registration failed ({0}). Falling back to HKCU Run autostart." -f $_.Exception.Message)
    $runCommand = ("powershell.exe {0}" -f $starterArgs)
    Set-RunKeyAutostart -Name $TaskName -CommandLine $runCommand
    Write-Host ("HKCU Run autostart entry '{0}' installed." -f $TaskName)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Note: current shell is not elevated. Autostart is configured for user logon, not pre-logon system startup."
    Write-Host "If you later run this script as Administrator, use Task Scheduler/Service for true ONSTART behavior."
}

if ($RunNow) {
    if ($registeredTask) {
        Write-Host ("Running task '{0}' now..." -f $TaskName)
        Start-ScheduledTask -TaskName $TaskName
    } else {
        Write-Host "Running starter script now (HKCU Run fallback mode)..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $starter
    }
}

Write-Host "Done."
