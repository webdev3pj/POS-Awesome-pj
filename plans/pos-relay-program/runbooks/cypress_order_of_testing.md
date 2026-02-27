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

## Stage Evidence Files (produced by specs)
- SA: `cypress/tmp/latest_sa_order.json`
- Cashier: `cypress/tmp/latest_cashier_relay_commit.json`
- Picker: `cypress/tmp/latest_picker_update.json`
- Dispatch: `cypress/tmp/latest_dispatch_release.json`
- Picker->Dispatch handoff: `cypress/tmp/picker_dispatch_target.json`

## What “Pass” Means For Relay Proof
- SA proof: token/SO id from `latest_sa_order.json` resolves on relay (`/relay/token/<token>`).
- Cashier proof: `localSaleRef` from `latest_cashier_relay_commit.json` is visible on relay dashboard and `/api/transactions/<local_sale_ref>`.
- Picker proof: same `localSaleRef` shows `pick_status=PICKED_READY_FOR_RELEASE` and line payload has picker data.
- Dispatch proof: same `localSaleRef` shows `dispatch_status=RELEASED` and latest dispatch event is `RELEASED`.
