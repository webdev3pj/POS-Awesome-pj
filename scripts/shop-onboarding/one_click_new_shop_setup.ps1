param(
    [string]$ConfigPath = "",
    [string]$ApiKey = "",
    [string]$ApiSecret = "",
    [switch]$SkipRelayChecks,
    [switch]$SkipShopPcPackage,
    [switch]$WhatIf
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ("[STEP] " + $Message) -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host ("[OK]   " + $Message) -ForegroundColor Green
}

function Write-WarnMsg([string]$Message) {
    Write-Host ("[WARN] " + $Message) -ForegroundColor Yellow
}

function Write-Fail([string]$Message) {
    Write-Host ("[FAIL] " + $Message) -ForegroundColor Red
}

function Has-Prop($Object, [string]$Name) {
    if ($null -eq $Object) { return $false }
    return $null -ne $Object.PSObject.Properties[$Name]
}

function Get-Prop($Object, [string]$Name, $DefaultValue = $null) {
    if (-not (Has-Prop $Object $Name)) { return $DefaultValue }
    $value = $Object.PSObject.Properties[$Name].Value
    if ($null -eq $value) { return $DefaultValue }
    return $value
}

function Resolve-AbsolutePath([string]$BasePath, [string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $BasePath
    }
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }
    return [System.IO.Path]::GetFullPath((Join-Path $BasePath $PathValue))
}

function Invoke-RelayHealthCheck([string]$Url) {
    Write-Step ("Relay health check: " + $Url)
    if ($WhatIf) {
        Write-WarnMsg "WhatIf mode: skipping network call."
        return
    }
    $resp = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 12
    if ($null -eq $resp) {
        throw ("Relay health returned empty response for: " + $Url)
    }
    if (Has-Prop $resp "ok" -and -not [bool]$resp.ok) {
        throw ("Relay health returned ok=false for: " + $Url)
    }
    Write-Ok ("Relay health passed: " + $Url)
}

function Invoke-FrappeMethod([string]$SiteUrl, [hashtable]$Headers, [string]$MethodName, [hashtable]$Args) {
    $uri = "$SiteUrl/api/method/$MethodName"
    $body = $Args | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $Headers -ContentType "application/json" -Body $body -TimeoutSec 45
}

function Get-PosProfileDoc([string]$SiteUrl, [hashtable]$Headers, [string]$ProfileName) {
    $resp = Invoke-FrappeMethod -SiteUrl $SiteUrl -Headers $Headers -MethodName "frappe.client.get" -Args @{
        doctype = "POS Profile"
        name    = $ProfileName
    }
    if ($null -eq $resp -or -not (Has-Prop $resp "message") -or $null -eq $resp.message) {
        throw ("Could not load POS Profile: " + $ProfileName)
    }
    return $resp.message
}

function Set-PosProfileField([string]$SiteUrl, [hashtable]$Headers, [string]$ProfileName, [string]$FieldName, $Value) {
    if ($WhatIf) {
        Write-WarnMsg ("WhatIf: would set {0}.{1} = {2}" -f $ProfileName, $FieldName, $Value)
        return
    }
    Invoke-FrappeMethod -SiteUrl $SiteUrl -Headers $Headers -MethodName "frappe.client.set_value" -Args @{
        doctype   = "POS Profile"
        name      = $ProfileName
        fieldname = $FieldName
        value     = $Value
    } | Out-Null
}

function Compare-FieldValue($CurrentValue, $DesiredValue, [bool]$Numeric) {
    if ($Numeric) {
        return ([int]$CurrentValue) -eq ([int]$DesiredValue)
    }
    return ([string]$CurrentValue).Trim() -eq ([string]$DesiredValue).Trim()
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$defaultConfig = Join-Path $PSScriptRoot "shop_onboarding_config.json"
$exampleConfig = Join-Path $PSScriptRoot "shop_onboarding_config.example.json"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = if (Test-Path $defaultConfig) { $defaultConfig } else { $exampleConfig }
}
$ConfigPath = Resolve-AbsolutePath -BasePath (Get-Location).Path -PathValue $ConfigPath

if (-not (Test-Path $ConfigPath)) {
    throw ("Config file not found: " + $ConfigPath)
}

Write-Step ("Loading config: " + $ConfigPath)
$config = Get-Content -Raw -Path $ConfigPath | ConvertFrom-Json

$siteUrl = ([string](Get-Prop $config "site_url" "")).Trim().TrimEnd("/")
if ([string]::IsNullOrWhiteSpace($siteUrl)) {
    throw "Config missing site_url."
}

$relayUrl = ([string](Get-Prop $config "relay_url" "https://192.168.50.168")).Trim().TrimEnd("/")
if ([string]::IsNullOrWhiteSpace($relayUrl)) {
    $relayUrl = "https://192.168.50.168"
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = [string]$env:FRAPPE_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiSecret)) {
    $ApiSecret = [string]$env:FRAPPE_API_SECRET
}
if ([string]::IsNullOrWhiteSpace($ApiKey) -or [string]::IsNullOrWhiteSpace($ApiSecret)) {
    throw "Missing Frappe API credentials. Set FRAPPE_API_KEY and FRAPPE_API_SECRET env vars or pass -ApiKey/-ApiSecret."
}

$authHeaders = @{
    "Authorization" = ("token {0}:{1}" -f $ApiKey, $ApiSecret)
    "Accept"        = "application/json"
}

if (-not $SkipRelayChecks) {
    $relayHealthUrls = @()
    if (Has-Prop $config "relay_health_urls") {
        $relayHealthUrls = @((Get-Prop $config "relay_health_urls" @()))
    }
    if ($relayHealthUrls.Count -eq 0) {
        $relayHealthUrls = @(
            "http://127.0.0.1:8787/health",
            ($relayUrl + "/health")
        )
    }

    foreach ($healthUrl in $relayHealthUrls) {
        if ([string]::IsNullOrWhiteSpace([string]$healthUrl)) { continue }
        Invoke-RelayHealthCheck -Url ([string]$healthUrl)
    }
}

Write-Step ("Checking API auth on " + $siteUrl)
if ($WhatIf) {
    Write-WarnMsg "WhatIf mode: skipping Frappe API auth check."
} else {
    $userResp = Invoke-FrappeMethod -SiteUrl $siteUrl -Headers $authHeaders -MethodName "frappe.auth.get_logged_user" -Args @{}
    $loggedUser = [string](Get-Prop $userResp "message" "")
    if ([string]::IsNullOrWhiteSpace($loggedUser)) {
        throw "Frappe API auth check failed: empty user."
    }
    Write-Ok ("Authenticated as: " + $loggedUser)
}

$profiles = @((Get-Prop $config "profiles" @()))
if ($profiles.Count -eq 0) {
    throw "Config has no profiles[] entries."
}

$numericFields = @(
    "custom_have_token",
    "posa_allow_sales_order",
    "custom_allow_select_sales_order",
    "posa_sales_order_lookup_max_age_days",
    "posa_allow_cloud_fallback_when_relay_down"
)

$summaryRows = @()

foreach ($profile in $profiles) {
    $profileName = [string](Get-Prop $profile "name" "")
    if ([string]::IsNullOrWhiteSpace($profileName)) {
        throw "Each profiles[] item must include non-empty 'name'."
    }

    Write-Step ("Configuring POS Profile: " + $profileName)
    $isCashier = [bool](Get-Prop $profile "cashier_profile" $false)

    $desired = [ordered]@{}
    $desired["custom_have_token"] = [int](Get-Prop $profile "custom_have_token" 1)
    $desired["custom_edge_relay_url"] = [string](Get-Prop $profile "custom_edge_relay_url" $relayUrl)
    $desired["posa_edge_relay_connectivity_mode"] = [string](Get-Prop $profile "posa_edge_relay_connectivity_mode" "lan_only_browser_checked")
    $desired["posa_allow_cloud_fallback_when_relay_down"] = [int](Get-Prop $profile "posa_allow_cloud_fallback_when_relay_down" ($(if ($isCashier) { 1 } else { 0 })))

    if ($isCashier -or (Has-Prop $profile "posa_allow_sales_order")) {
        $desired["posa_allow_sales_order"] = [int](Get-Prop $profile "posa_allow_sales_order" ($(if ($isCashier) { 1 } else { 0 })))
    }
    if ($isCashier -or (Has-Prop $profile "custom_allow_select_sales_order")) {
        $desired["custom_allow_select_sales_order"] = [int](Get-Prop $profile "custom_allow_select_sales_order" ($(if ($isCashier) { 1 } else { 0 })))
    }
    if (Has-Prop $profile "posa_sales_order_lookup_max_age_days") {
        $desired["posa_sales_order_lookup_max_age_days"] = [int](Get-Prop $profile "posa_sales_order_lookup_max_age_days" 1)
    } elseif ($isCashier) {
        $desired["posa_sales_order_lookup_max_age_days"] = 1
    }

    $seriesValue = [string](Get-Prop $profile "posa_sales_order_naming_series" "")
    if (-not [string]::IsNullOrWhiteSpace($seriesValue)) {
        $desired["posa_sales_order_naming_series"] = $seriesValue
    }

    $doc = $null
    if (-not $WhatIf) {
        $doc = Get-PosProfileDoc -SiteUrl $siteUrl -Headers $authHeaders -ProfileName $profileName
    } else {
        Write-WarnMsg "WhatIf mode: skipping profile fetch/update."
    }

    $updatedFields = @()
    foreach ($pair in $desired.GetEnumerator()) {
        $field = [string]$pair.Key
        $desiredValue = $pair.Value
        $isNumeric = $numericFields -contains $field

        if ($WhatIf) {
            $updatedFields += $field
            continue
        }

        if (-not (Has-Prop $doc $field)) {
            Write-WarnMsg ("Skipping missing field on site: {0}.{1}" -f $profileName, $field)
            continue
        }

        $currentValue = Get-Prop $doc $field $null
        if (Compare-FieldValue -CurrentValue $currentValue -DesiredValue $desiredValue -Numeric:$isNumeric) {
            continue
        }

        Set-PosProfileField -SiteUrl $siteUrl -Headers $authHeaders -ProfileName $profileName -FieldName $field -Value $desiredValue
        $updatedFields += $field
    }

    if (-not $WhatIf) {
        $doc = Get-PosProfileDoc -SiteUrl $siteUrl -Headers $authHeaders -ProfileName $profileName
    }

    $summaryRows += [pscustomobject]@{
        profile_name = $profileName
        cashier_profile = $isCashier
        updated_fields = if ($updatedFields.Count -gt 0) { ($updatedFields -join ", ") } else { "(none)" }
        relay_url = if ($WhatIf) { [string]$desired["custom_edge_relay_url"] } else { [string](Get-Prop $doc "custom_edge_relay_url" "") }
        have_token = if ($WhatIf) { [int]$desired["custom_have_token"] } else { [int](Get-Prop $doc "custom_have_token" 0) }
        fallback_when_relay_down = if ($WhatIf) { [int]$desired["posa_allow_cloud_fallback_when_relay_down"] } else { [int](Get-Prop $doc "posa_allow_cloud_fallback_when_relay_down" 0) }
    }

    Write-Ok ("Profile configured: " + $profileName)
}

if (-not $SkipShopPcPackage) {
    $outputDirRaw = [string](Get-Prop $config "shop_pc_package_output_dir" "scripts/shop-onboarding/output/shop-pc-package")
    $outputDir = Resolve-AbsolutePath -BasePath $repoRoot -PathValue $outputDirRaw
    $sourceDir = Join-Path $repoRoot "relay\windows_https\export"
    $requiredFiles = @(
        "SHOP-PC-ONE-CLICK-SETUP.bat",
        "install_shop_pc_relay_cert.bat",
        "install_shop_pc_relay_cert.ps1",
        "caddy-local-root.crt"
    )

    Write-Step ("Preparing shop PC one-click package: " + $outputDir)
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

    foreach ($fileName in $requiredFiles) {
        $src = Join-Path $sourceDir $fileName
        if (-not (Test-Path $src)) {
            throw ("Required package file missing: " + $src)
        }
        Copy-Item -Path $src -Destination (Join-Path $outputDir $fileName) -Force
    }

    $posUrl = [string](Get-Prop $config "pos_url" ($siteUrl + "/app/posapp"))
    $instructions = @(
        "SHOP PC ONE-CLICK SETUP",
        "1) On each PC, double-click SHOP-PC-ONE-CLICK-SETUP.bat and click Yes for admin prompt.",
        "2) Wait for success message; browser will open relay health page.",
        ("3) Open POS URL and confirm Relay Online (LAN): " + $posUrl),
        ("Relay URL: " + $relayUrl)
    )
    $instructions | Set-Content -Path (Join-Path $outputDir "INSTALL-STEPS.txt") -Encoding Ascii
    Write-Ok ("Shop PC package ready: " + $outputDir)
}

$reportDir = Join-Path $PSScriptRoot "output"
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$reportPath = Join-Path $reportDir "latest_shop_onboarding_report.json"

$report = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    site_url = $siteUrl
    relay_url = $relayUrl
    what_if = [bool]$WhatIf
    profiles = $summaryRows
}
$report | ConvertTo-Json -Depth 20 | Set-Content -Path $reportPath -Encoding Ascii

Write-Host ""
Write-Host "========== ONE-CLICK SHOP SETUP SUMMARY ==========" -ForegroundColor Magenta
$summaryRows | Format-Table -AutoSize | Out-String | Write-Host
Write-Host ("Report: " + $reportPath) -ForegroundColor Gray
Write-Host "Done." -ForegroundColor Green
