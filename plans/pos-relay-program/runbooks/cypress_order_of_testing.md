# Cypress Order Of Testing (OptiPlex Relay Host)

## Purpose
- Define one repeatable test order so any new agent can prove role workflows and relay persistence stage-by-stage.
- This machine (OptiPlex) is both:
  - Cypress runner host
  - local Edge Relay host (`127.0.0.1:8787`, LAN HTTPS `https://192.168.50.168`)

## Non-Negotiable Rules
- Use headed watch-mode wrapper, one spec at a time.
- Use strict timeout for every spec run.
- After each role workflow, run the relay-dashboard proof spec for that role stage.
- Do not continue if relay `/health` is not `ok: true`.

## Preflight
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj'
Invoke-RestMethod http://127.0.0.1:8787/health | ConvertTo-Json -Depth 6
```

Expected:
- `"ok": true`

## Standard Runner Command
```powershell
$env:CYPRESS_MAX_RUN_MS='900000'
$env:CYPRESS_POSTSPEC_SCAN='1'
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/<spec>.cy.js
```

## Cloud Dev Site Order (`https://devpjjamaica.v.frappe.cloud/`)
Set once before the run:
```powershell
$env:CYPRESS_baseUrl='https://devpjjamaica.v.frappe.cloud/'
```

Run in this exact order:
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/relay_demo_sa_post_ui_watch.cy.js`
5. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
6. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
7. `cypress/e2e/relay_demo_postrun_ui_watch.cy.js`
8. `cypress/e2e/admin_set_cline_picker_only_role.cy.js`
9. `cypress/e2e/picker_workflow_frontend_watch.cy.js`
10. `cypress/e2e/relay_demo_picker_post_ui_watch.cy.js`
11. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js`
12. `cypress/e2e/dispatch_workflow_frontend_watch.cy.js`
13. `cypress/e2e/relay_demo_dispatch_post_ui_watch.cy.js`

Optional hardening:
14. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
15. `cypress/e2e/supervisor_fulfillment_exception_watch.cy.js`
16. `cypress/e2e/phase3_security_relay_role_guards_watch.cy.js`
17. `cypress/e2e/ui_shell_chrome_role_consistency.cy.js`

Cashier attribution post-check (after step 7):
1. Open `cypress/tmp/latest_cashier_relay_commit.json` and copy `cloudInvoiceName`.
2. In Desk, open `Sales Invoice` list and open that exact invoice.
3. Verify cashier attribution field (for example `custom_cashier`) matches the cashier login (`cline@pjjamaica.com` in current UAT).

Supervisor reseed rule (important):
- If step 15 fails with `pending unreleased queue row: expected undefined to be an object`, the queue was already fully released by dispatch.
- Reseed before re-running step 15:
  1. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
  2. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
  3. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
  4. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
  5. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
  6. `cypress/e2e/supervisor_fulfillment_exception_watch.cy.js`

## Local Staging Order (`http://pj.local:8080/`)
Set once before the run:
```powershell
$env:CYPRESS_baseUrl='http://pj.local:8080/'
```

Run in this exact order:
1. `cypress/e2e/local_staging/local_staging_parity_smoke_watch.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/local_staging/local_staging_sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/local_staging/local_staging_relay_demo_sa_post_ui_watch.cy.js`
5. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
6. `cypress/e2e/local_staging/local_staging_cashier_workflow_frontend_watch.cy.js`
7. `cypress/e2e/local_staging/local_staging_relay_demo_cashier_post_ui_watch.cy.js`
8. `cypress/e2e/admin_set_cline_picker_only_role.cy.js`
9. `cypress/e2e/local_staging/local_staging_picker_workflow_frontend_watch.cy.js`
10. `cypress/e2e/local_staging/local_staging_relay_demo_picker_post_ui_watch.cy.js`
11. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js`
12. `cypress/e2e/local_staging/local_staging_dispatch_workflow_frontend_watch.cy.js`
13. `cypress/e2e/local_staging/local_staging_relay_demo_dispatch_post_ui_watch.cy.js`

Optional hardening:
14. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
15. `cypress/e2e/local_staging/local_staging_supervisor_fulfillment_exception_watch.cy.js`
16. `cypress/e2e/local_staging/local_staging_phase3_security_relay_role_guards_watch.cy.js`

Supervisor reseed rule (important):
- If step 15 fails with `pending unreleased queue row: expected undefined to be an object`, the queue was already fully released by dispatch.
- Reseed before re-running step 15:
  1. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
  2. `cypress/e2e/local_staging/local_staging_sa_workflow_frontend_watch.cy.js`
  3. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
  4. `cypress/e2e/local_staging/local_staging_cashier_workflow_frontend_watch.cy.js`
  5. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
  6. `cypress/e2e/local_staging/local_staging_supervisor_fulfillment_exception_watch.cy.js`

## Dedicated Local Cloud-Off UAT (`pj.local`, relay-only evidence)
Use this when you need explicit Wi-Fi/cloud-unavailable continuity proof while relay remains reachable.

1. Backup relay config and switch relay cloud target to an unreachable endpoint:
```powershell
Copy-Item -Force .\relay\data\relay_config.json .\cypress\tmp\relay_config.pre_cloud_off_uat.json
$cfg = Get-Content .\relay\data\relay_config.json -Raw | ConvertFrom-Json
$cfg.frappe_base_url = 'http://10.255.255.1:65534'
$cfg.site_name = 'cloud-off-sim'
($cfg | ConvertTo-Json -Depth 8) | Set-Content .\relay\data\relay_config.json -Encoding Ascii
Invoke-RestMethod http://127.0.0.1:8787/health | ConvertTo-Json -Depth 6
```
Expected:
- relay `/health` stays `ok: true`
- `frappe_base_url` shows `http://10.255.255.1:65534`

2. Run the same local staging order (steps 1-13 above).
3. Build one consolidated relay-only evidence snapshot:
```powershell
$sa = Get-Content .\cypress\tmp\latest_sa_order.json -Raw | ConvertFrom-Json
$cash = Get-Content .\cypress\tmp\latest_cashier_relay_commit.json -Raw | ConvertFrom-Json
$pick = Get-Content .\cypress\tmp\latest_picker_update.json -Raw | ConvertFrom-Json
$disp = Get-Content .\cypress\tmp\latest_dispatch_release.json -Raw | ConvertFrom-Json
$ref = [string]$disp.local_sale_ref
$health = Invoke-RestMethod http://127.0.0.1:8787/health
$tx = Invoke-RestMethod ("http://127.0.0.1:8787/api/transactions/{0}" -f [uri]::EscapeDataString($ref))
$outbox = Invoke-RestMethod http://127.0.0.1:8787/api/outbox
$matched = @($outbox.rows | Where-Object { [string]$_.local_ref -eq $ref })
$result = [ordered]@{
  captured_at = (Get-Date).ToString('s')
  relay_health = $health
  sa = @{ sales_order = $sa.salesOrder; token_id = $sa.tokenId; created_at = $sa.createdAt }
  cashier = @{ local_sale_ref = $cash.localSaleRef; sale_status = $cash.relaySaleRow.sale_status; cloud_sync_status = $cash.relaySaleRow.cloud_sync_status }
  picker = @{ local_sale_ref = $pick.local_sale_ref; pick_status = $pick.pick_status; picked_qty = $pick.picked_qty }
  dispatch = @{ local_sale_ref = $disp.local_sale_ref; dispatch_status = $disp.dispatch_status; released_at = $disp.released_at }
  transaction_snapshot = @{
    sale_status = $tx.sale.sale_status
    pick_status = $tx.sale.pick_status
    dispatch_status = $tx.sale.dispatch_status
    cloud_sync_status = $tx.sale.cloud_sync_status
    cloud_sync_error = $tx.sale.cloud_sync_error
  }
  matched_outbox_events = @($matched | Select-Object event_type,status,retries,last_error,created_at,updated_at)
}
$result | ConvertTo-Json -Depth 8 | Set-Content .\cypress\tmp\local_staging_cloud_off_full_chain_evidence.json -Encoding Ascii
```
4. Restore relay config:
```powershell
Copy-Item -Force .\cypress\tmp\relay_config.pre_cloud_off_uat.json .\relay\data\relay_config.json
Invoke-RestMethod http://127.0.0.1:8787/health | ConvertTo-Json -Depth 6
```

## Stage Evidence Files (produced by specs)
- SA: `cypress/tmp/latest_sa_order.json`
- Cashier: `cypress/tmp/latest_cashier_relay_commit.json`
- Picker: `cypress/tmp/latest_picker_update.json`
- Dispatch: `cypress/tmp/latest_dispatch_release.json`
- Picker->Dispatch handoff: `cypress/tmp/picker_dispatch_target.json`
- Dedicated cloud-off consolidated evidence: `cypress/tmp/local_staging_cloud_off_full_chain_evidence.json`

## What “Pass” Means For Relay Proof
- SA proof: token/SO id from `latest_sa_order.json` resolves on relay (`/relay/token/<token>`).
- Cashier proof: `localSaleRef` from `latest_cashier_relay_commit.json` is visible on relay dashboard and `/api/transactions/<local_sale_ref>`.
- Picker proof: same `localSaleRef` shows `pick_status=PICKED_READY_FOR_RELEASE` and line payload has picker data.
- Dispatch proof: same `localSaleRef` shows `dispatch_status=RELEASED` and latest dispatch event is `RELEASED`.
