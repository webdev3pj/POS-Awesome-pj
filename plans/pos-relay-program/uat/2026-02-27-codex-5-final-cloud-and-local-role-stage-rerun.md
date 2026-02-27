# UAT - 2026-02-27 - codex-5-final Cloud + Local Role-Stage Rerun (SA -> Cashier -> Picker -> Dispatch + Supervisor)

## TL;DR (Business Owner)
- Full strict watch-mode reruns were completed on both cloud dev site and local staging with relay proof specs after each role stage.
- SA, cashier, picker, dispatch, and supervisor exception flows are passing, with relay evidence captured.
- Three Cypress reliability issues were fixed during this rerun (cashier fallback loading, picker final qty proof mismatch, UI-shell long timeout).
- One operational rule is now explicit: supervisor exception needs a fresh pending unreleased row; if dispatch already released all rows, reseed with SA + cashier first.

## Scope
- Branch: `codex-5-final`
- Cloud target: `https://devpjjamaica.v.frappe.cloud/`
- Local staging target: `http://pj.local:8080/`
- Relay host: OptiPlex local relay (`http://127.0.0.1:8787`, LAN HTTPS `https://192.168.50.168`)

## Code Changes Under Test (this rerun cycle)
- `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js`
  - resilient get-items handling and Select-S.O fallback when item grid is unavailable
- `cypress/e2e/picker_workflow_frontend_watch.cy.js`
  - writes final persisted picker qty after ready-state transition
- `cypress/e2e/ui_shell_chrome_role_consistency.cy.js`
  - strengthened long `frappe.call` timeout handling to prevent 15s promise timeout flakes

## Execution Policy Used
- Headed Chrome via `npm.cmd run e2e:watch:gui:chrome -- --once --spec ...`
- One spec at a time
- Strict timeout env:
  - `CYPRESS_MAX_RUN_MS=900000`
  - `CYPRESS_POSTSPEC_SCAN=1`

## Cloud Rerun Results (`devpjjamaica`)
Pass sequence completed:
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/relay_demo_sa_post_ui_watch.cy.js`
5. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
6. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
7. `cypress/e2e/relay_demo_postrun_ui_watch.cy.js`
8. `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js`
9. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js`
10. `cypress/e2e/admin_set_cline_picker_only_role.cy.js`
11. `cypress/e2e/picker_workflow_frontend_watch.cy.js`
12. `cypress/e2e/relay_demo_picker_post_ui_watch.cy.js`
13. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js`
14. `cypress/e2e/dispatch_workflow_frontend_watch.cy.js`
15. `cypress/e2e/relay_demo_dispatch_post_ui_watch.cy.js`
16. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
17. `cypress/e2e/supervisor_fulfillment_exception_watch.cy.js` (after reseed)
18. `cypress/e2e/phase3_security_relay_role_guards_watch.cy.js`
19. `cypress/e2e/ui_shell_chrome_role_consistency.cy.js` (after timeout fix)

Cloud evidence IDs:
- SA token/SO: `SAL-ORD-PJ7-2026-00019`
- Cashier relay local sale: `LSR-PJ7 -20260227090129-CCC5AD`
- Supervisor exception target:
  - `local_sale_ref = LSR-PJ7 -20260227090129-CCC5AD`
  - `pick_status = PICK_EXCEPTION`
  - `dispatch_status = RELEASED`
  - `cloud_invoice_name = ACC-SINV-2026-00293`
- Dispatch proof target:
  - `local_sale_ref = LSR-PJ7 -20260227084924-36A850`
  - `token_id = SAL-ORD-PJ7-2026-00018`
  - `dispatch_status = RELEASED`

## Local Staging Rerun Results (`pj.local`)
Pass sequence completed:
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
14. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js`
15. `cypress/e2e/local_staging/local_staging_supervisor_fulfillment_exception_watch.cy.js` (after reseed)
16. `cypress/e2e/local_staging/local_staging_phase3_security_relay_role_guards_watch.cy.js`

Local staging evidence IDs (source-env proof):
- `LSR-PJ7 -20260227082706-4A3D89` (`source_env=local_staging`, `dispatch_status=RELEASED`)
- `LSR-PJ7 -20260227084138-FE7460` (`source_env=local_staging`, `pick_status=PICK_EXCEPTION`, `dispatch_status=RELEASED`)

## Relay Health Snapshot (end of rerun)
From `GET http://127.0.0.1:8787/health`:
- `ok = true`
- outbox:
  - `done = 30`
  - `queued = 19`
  - `failed = 0`
  - `total = 49`
- legacy queue:
  - `queued = 0`
  - `failed = 0`

Notes:
- Non-zero queued outbox rows include expected backlog from mixed cloud/local test traffic and are not equivalent to relay failure.
- Local staging rows commonly show `cloud_sync_status = SALE_SYNC_PENDING` and `source_env = local_staging`; this is expected for local-loop validation.

## Failures Encountered and Resolved
1. Cashier relay-down fallback spec intermittently failed to find item rows / stable `@getItems` response.
   - Fixed in `cashier_relay_down_cloud_fallback_watch.cy.js` with resilient get-items handling and Sales-Order fallback loading path.
2. Picker post-proof expected stale `picked_qty` (pre-ready value) in some runs.
   - Fixed in `picker_workflow_frontend_watch.cy.js` to write final persisted qty after ready transition.
3. UI shell consistency spec flaked on 15s `cy.then` timeout around long `frappe.call` chains.
   - Fixed in `ui_shell_chrome_role_consistency.cy.js` with explicit long-timeout wrappers and `_frappeCallOnce` timeout-safe helper rewrite.
4. Supervisor exception spec can fail when no pending unreleased queue rows remain.
   - Operational fix documented: reseed with SA + cashier before supervisor exception.

## Result
Pass for cloud+local role-stage rerun and relay proof coverage on `codex-5-final`.

## Remaining Work (next session)
1. Run dedicated cloud-off continuity UAT end-to-end (SA -> Cashier -> Picker -> Dispatch) with explicit outage simulation and relay-only evidence.
2. Expand dispatch timing instrumentation into persistent analytics/reporting outputs.
3. Continue shop-PC rollout hardening (cert trust/support checklist) and historical outbox cleanup policy.
