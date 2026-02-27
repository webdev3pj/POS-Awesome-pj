# New Shop One-Click Setup (Multi-POS Profile)

## Goal
Bring a new shop live with relay-first POS using one script on OptiPlex and one-click installer on each shop PC.

## Prerequisites
1. OptiPlex relay host is running.
2. Relay health works:
   - `http://127.0.0.1:8787/health`
   - `https://192.168.50.168/health`
3. You have Frappe API key/secret with permission to update `POS Profile`.

## Step 1: Run one-click onboarding on OptiPlex
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj'
$env:FRAPPE_API_KEY='YOUR_API_KEY'
$env:FRAPPE_API_SECRET='YOUR_API_SECRET'
Copy-Item .\scripts\shop-onboarding\shop_onboarding_config.example.json .\scripts\shop-onboarding\shop_onboarding_config.json
notepad .\scripts\shop-onboarding\shop_onboarding_config.json
powershell -ExecutionPolicy Bypass -File .\scripts\shop-onboarding\one_click_new_shop_setup.ps1 -ConfigPath .\scripts\shop-onboarding\shop_onboarding_config.json
```

What this script does:
1. Checks relay health.
2. Updates each profile listed in config (`custom_have_token`, relay URL, connectivity mode, fallback policy, and cashier SO settings if configured).
3. Builds shop-PC setup package:
   - `scripts\shop-onboarding\output\shop-pc-package\`
4. Writes report:
   - `scripts\shop-onboarding\output\latest_shop_onboarding_report.json`

## Step 2: One-click setup on every shop PC
From the package folder, run:
- `SHOP-PC-ONE-CLICK-SETUP.bat`

Then check:
1. `https://192.168.50.168/health` opens without cert warning.
2. Open POS and confirm top chip: `Relay Online (LAN)`.

## Step 3: Smoke-test each profile
For each profile in config:
1. Login with role user.
2. Confirm role UI matches profile purpose:
   - SA: token/SO creation
   - Cashier: payment/submit
   - Picker: queue + pick actions
   - Dispatch: queue + release actions
3. Run one transaction and confirm relay dashboard updates.

## Recommended defaults per profile type
1. Cashier profile:
   - `custom_have_token = 1`
   - `custom_edge_relay_url = https://192.168.50.168`
   - `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
   - `posa_allow_cloud_fallback_when_relay_down = 1`
   - `posa_allow_sales_order = 1`
   - `custom_allow_select_sales_order = 1`
2. Picker/Dispatch/Supervisor profile:
   - `custom_have_token = 1`
   - `custom_edge_relay_url = https://192.168.50.168`
   - `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
   - `posa_allow_cloud_fallback_when_relay_down = 0` (or business choice)

## Rollback
If onboarding fails:
1. Fix config and rerun same script.
2. Review report JSON and console warnings for missing fields/permissions.
3. Do not proceed to shop PCs until relay and profile checks pass.

