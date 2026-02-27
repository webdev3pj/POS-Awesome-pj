# Shop PC LAN Relay Setup (Non-Technical, One-Time)

## Fastest New-Shop Setup (Owner, 10-minute path)
On the OptiPlex, use the one-click onboarding script for multiple POS profiles:
1. Set API credentials in PowerShell:
```powershell
$env:FRAPPE_API_KEY='YOUR_API_KEY'
$env:FRAPPE_API_SECRET='YOUR_API_SECRET'
```
2. Edit the profile list once:
```powershell
Copy-Item .\scripts\shop-onboarding\shop_onboarding_config.example.json .\scripts\shop-onboarding\shop_onboarding_config.json
notepad .\scripts\shop-onboarding\shop_onboarding_config.json
```
3. Run one-click setup:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\shop-onboarding\one_click_new_shop_setup.ps1 -ConfigPath .\scripts\shop-onboarding\shop_onboarding_config.json
```
4. Use generated package on each shop PC:
   - `scripts\shop-onboarding\output\shop-pc-package\SHOP-PC-ONE-CLICK-SETUP.bat`

This automates:
- relay health checks
- POS profile configuration (multiple profiles)
- shop-PC installer package generation
- readiness report output

## TL;DR (Business Owner / Shop Staff)
- Do this **once** on each shop PC (SA, Cashier, Picker, Dispatch).
- Run the relay certificate installer as **Administrator**.
- Open `https://192.168.50.168/health` in Chrome.
- If it opens without a browser warning, that PC is ready to use the local relay over LAN HTTPS.
- This setup path was validated on the OptiPlex/dev-site relay demo on `2026-02-24`; remaining work is rolling it out on the other shop PCs.

## Why this is needed (plain English)
- Your POS page comes from Frappe Cloud (`https://...frappe.cloud`).
- The local relay is in the shop on your LAN.
- To let the browser talk safely to the local relay, we will use a local HTTPS address:
  - `https://192.168.50.168`
- Each shop PC needs to trust the local relay certificate one time.

## What you need before starting
- The OptiPlex relay machine is running and the relay HTTPS setup was completed by Codex/IT.
- You have the file:
  - `install_shop_pc_relay_cert.bat`
- (Codex/IT note: this is exported/generated from the OptiPlex relay HTTPS setup package; staff should receive the file directly and should not browse repo folders)
- You are logged into Windows with rights to approve an Administrator prompt.

## One-Time Setup Steps (per PC)
1. Close Chrome and any open POS tabs.
2. Double-click `install_shop_pc_relay_cert.bat`.
3. If Windows shows a permission prompt, click **Yes**.
4. Wait for the script to finish (it should show a success message).
5. Open Chrome.
6. Visit:
   - `https://192.168.50.168/health`
7. Confirm:
   - no red security warning
   - a small JSON page appears (relay health response)

If this works, the PC is ready.

## Quick extra check in POS (optional, after cert trust is installed)
After Codex/IT confirms the POS Profile relay URL is set:
1. Open the POS page (`https://...frappe.cloud`)
2. Wait for the POS status chips at the top
3. Confirm you can see:
   - `Relay Online (LAN)` (green)

If the POS page works but does not show `Relay Online (LAN)`, tell Codex/IT.

## What the staff member does NOT need to do
- No command line
- No browser settings
- No developer tools
- No tunnel setup
- No manual certificate import steps (the script handles it)

## If you see a browser warning or error
### Case 1: Security / certificate warning
Do this:
1. Close Chrome
2. Re-run `install_shop_pc_relay_cert.bat` as Administrator
3. Try `https://192.168.50.168/health` again

If still failing:
- Ask Codex/IT to check that the OptiPlex relay HTTPS setup completed and the correct certificate was exported.

### Case 2: Page does not load / timeout
Possible causes:
- OptiPlex relay is not running
- Shop PC not on the same LAN
- Windows firewall/network issue

What to tell Codex/IT:
- “This PC cannot open `https://192.168.50.168/health`.”

## Quick checklist for managers
- [ ] SA PC ready
- [ ] Cashier PC ready
- [ ] Picker PC ready
- [ ] Dispatch PC ready

## If you are rolling out multiple POS Profiles (simple manager steps)
Do this once after PC trust setup is complete:
1. Ask Codex/IT to open each live POS Profile and set:
   - `custom_have_token = 1`
   - `custom_edge_relay_url = https://192.168.50.168`
2. For cashier profiles only, confirm cloud fallback toggle is enabled:
   - `posa_allow_cloud_fallback_when_relay_down = 1`
3. For each role/profile pair, open POS and confirm:
   - top status chip shows `Relay Online (LAN)`
   - role sees the expected screen (SA token flow, cashier payment flow, picker queue, dispatch queue)
4. Run one test transaction and ask Codex/IT to confirm it appears on relay dashboard and relay API.

## Notes for Codex/IT (do not ask staff to do this)
- The certificate installer is generated/maintained from `relay/windows_https/install_shop_pc_relay_cert.ps1` and `relay/windows_https/install_shop_pc_relay_cert.bat`.
- Exported installer/cert artifacts for distribution may be staged under `relay/windows_https/export/` on the OptiPlex.
- If relay LAN HTTPS moves to a hostname (fallback plan), update this document and the health-check URL accordingly.
