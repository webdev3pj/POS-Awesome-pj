# One-Click New Shop Setup

This folder automates new-shop relay rollout for multiple POS Profiles plus shop-PC installer packaging.

## What it does
- Checks local relay health (`127.0.0.1` and LAN HTTPS).
- Configures all listed POS Profiles on your Frappe site.
- Generates a ready-to-share shop-PC one-click package.
- Writes an onboarding report JSON.

## One-time prerequisites
1. Set API credentials in PowerShell (current session):
```powershell
$env:FRAPPE_API_KEY='YOUR_API_KEY'
$env:FRAPPE_API_SECRET='YOUR_API_SECRET'
```
2. Copy the example config and edit profile names:
```powershell
Copy-Item .\scripts\shop-onboarding\shop_onboarding_config.example.json .\scripts\shop-onboarding\shop_onboarding_config.json
notepad .\scripts\shop-onboarding\shop_onboarding_config.json
```

## Run (easy mode)
- Double-click:
  - `scripts\shop-onboarding\ONE-CLICK-NEW-SHOP-SETUP.bat`

## Run (PowerShell mode)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\shop-onboarding\one_click_new_shop_setup.ps1 -ConfigPath .\scripts\shop-onboarding\shop_onboarding_config.json
```

## Output
- Report:
  - `scripts\shop-onboarding\output\latest_shop_onboarding_report.json`
- Shop-PC package folder:
  - `scripts\shop-onboarding\output\shop-pc-package\`
  - includes `SHOP-PC-ONE-CLICK-SETUP.bat` + relay cert installer files

