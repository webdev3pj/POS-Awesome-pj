# UAT - LAN-Only Relay Enabled SA + Cashier (Template)

## TL;DR (Business Owner)
- This report records whether SA and Cashier worked end-to-end using the local Edge Relay on the shop LAN (OptiPlex).
- It should confirm relay status behavior, cashier fallback behavior, and whether the store can continue if the relay goes down.
- Replace this template text with the actual results after testing.

## Environment
- Date:
- Branch:
- Commit:
- Site:
- POS Profile:
- Relay host:
- Relay LAN HTTPS URL:
- Cypress mode: `watch mode / Chrome`

## Baseline / Starting Point
- Baseline handoff commit used:
- Relay process startup method used:
- Shop PCs certificate trust completed on:

## Profile Configuration Used (`PJ7 CASHIER`)
- `custom_have_token =`
- `posa_allow_sales_order =`
- `custom_allow_select_sales_order =`
- `posa_sales_order_naming_series =`
- `posa_sales_order_lookup_max_age_days =`
- `custom_edge_relay_url =`
- `posa_edge_relay_connectivity_mode =`
- `posa_allow_cloud_fallback_when_relay_down =`

## What Was Tested (Checklist)
- [ ] Relay health reachable over LAN HTTPS (`https://192.168.50.168/health`)
- [ ] SA flow with relay configured
- [ ] Cashier `Select S.O` filtering still correct
- [ ] Cashier relay-enabled submit path
- [ ] Relay-down / cloud-up fallback prompt
- [ ] Relay-down / cloud-down blocking behavior
- [ ] `custom_have_token = 0` regression smoke

## What Passed
- 

## What Failed
- 

## Relay Status Behavior (Observed)
### Relay up / cloud up
- 

### Relay down / cloud up
- Prompt shown?:
- Cloud fallback worked?:

### Relay down / cloud down
- Correct block message shown?:

## SA Flow Notes (Observed)
- 

## Cashier Flow Notes (Observed)
- 

## Monitor Rail Notes (Observed)
- 

## Evidence / Artifacts
- Cypress specs run:
  - 
- Screenshots/videos:
  - 
- Relay dashboard/outbox observations:
  - 

## Defects Found
- 

## Next Actions
- 

## Links
- `../CHANGELOG_PROGRESS.md`
- `../runbooks/optiplex-edge-relay-next-session.md`
- `../runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
