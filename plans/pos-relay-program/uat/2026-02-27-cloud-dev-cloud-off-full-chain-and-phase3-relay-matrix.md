# 2026-02-27 Cloud Dev Cloud-Off Full Chain + Phase 3 Relay Matrix

## Scope
- Environment under test:
  - Frappe Cloud dev site: `https://devpjjamaica.v.frappe.cloud/`
  - OptiPlex local relay service: `http://127.0.0.1:8787`
  - OptiPlex LAN relay URL: `https://192.168.50.168`
- Branch: `codex-5-final`
- Cloud deploy baseline for browser/UI flows:
  - deployed latest branch state including `a9072cd`
- Additional local relay code under validation:
  - legacy relay write-endpoint role-guard extension in `relay/relay/app.py`
  - expanded security matrix in `cypress/e2e/phase3_security_relay_role_guards_watch.cy.js`

## Test Intent
1. Prove cloud-dev continuity with cloud intentionally unavailable to the relay.
2. Prove the live role chain still works relay-first and relay-only:
   - Sales Associate
   - Cashier
   - Picker
   - Dispatch
3. Close the relay-side Phase 3 negative matrix for both v2 and legacy relay write endpoints.

## Cloud-Off Simulation Setup
- Relay config during this run:
  - `frappe_base_url = http://10.255.255.1:65534`
  - result: relay could not reach cloud by design
- Relay health still passed:
  - `/health -> ok: true`
  - relay accepted browser writes locally
  - outbox items remained queued/retrying while cloud target was unreachable

## Fresh Evidence IDs
- SA token / Sales Order: `SAL-ORD-PJ7-2026-00027`
- Cashier local sale: `LSR-PJ7 -20260227233006-CE7913`
- Local invoice payload name: `ACC-SINV-2026-00311`
- Picker first-line persisted update:
  - line id: `29`
  - picked qty: `0.5`
  - ordered UOM: `Nos`
  - picked UOM: `Nos`
  - conversion factor: `1`
- Dispatch release:
  - `dispatch_status = RELEASED`
  - `released_by = cline@pjjamaica.com`
  - `released_at = 2026-02-27T23:36:16Z`

## Cypress Execution Policy
- Mode: headed watch mode (Chrome)
- Strict timeout env:
  - `CYPRESS_MAX_RUN_MS=900000`
  - `CYPRESS_POSTSPEC_SCAN=1`

## Specs Run
### Cloud-Off Role Chain on Live OptiPlex Relay (`127.0.0.1:8787`)
1. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
2. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
3. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
4. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
5. `cypress/e2e/relay_demo_postrun_ui_watch.cy.js`
6. `cypress/e2e/admin_set_cline_picker_only_role.cy.js`
7. `cypress/e2e/picker_workflow_frontend_watch.cy.js`
8. `cypress/e2e/relay_demo_picker_post_ui_watch.cy.js`
9. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js`
10. `cypress/e2e/dispatch_workflow_frontend_watch.cy.js`
11. `cypress/e2e/relay_demo_dispatch_post_ui_watch.cy.js`

Result:
- All 11 specs passed.

### Phase 3 Relay Matrix
1. `cypress/e2e/phase3_security_relay_role_guards_watch.cy.js`

Relay targets used:
- v2 checks validated first against the live relay service on `127.0.0.1:8787`
- full matrix (including legacy endpoints) validated against a patched parallel relay instance on `127.0.0.1:8788`

Reason for split:
- the live listener on `8787` is owned by a protected service/elevated context
- the non-admin Codex shell could not hot-reload or terminate that listener
- a parallel user-owned process on `8788` was used to validate the newly-patched legacy routes without disturbing the continuity run

Result:
- Phase 3 relay matrix passed.

## What Was Proven
### Sales Associate
- Created a fresh Sales Order/token on cloud dev.
- The token ID was captured to `cypress/tmp/latest_sa_order.json`.

### Cashier
- Opened relay session successfully.
- Submitted through relay, not direct cloud submit.
- Relay created a new local sale row:
  - `LSR-PJ7 -20260227233006-CE7913`
- Relay commit response:
  - `sale_status = SALE_COMMITTED_LOCAL`
  - `cloud_sync_status = SALE_SYNC_PENDING`
- Because cloud target was intentionally unreachable, sync did not complete, which is the expected cloud-off result.

### Picker
- Opened the fulfillment queue from the same cloud dev POS shell.
- Updated line-level picked quantity to `0.5`.
- Relay persisted the picker payload in local sale line data (`payload.picker`).
- Relay transaction detail showed:
  - line partial pick state
  - pick events queued for later cloud sync

### Dispatch
- Released the same local sale.
- Relay persisted:
  - `dispatch_status = RELEASED`
  - release event metadata with dispatcher identity
- Relay dashboard and transaction JSON both reflected the release.

## Relay API / Dashboard Evidence
- `cypress/tmp/latest_cashier_relay_commit_http.json`
- `cypress/tmp/latest_picker_update.json`
- `cypress/tmp/latest_dispatch_release.json`
- `cypress/screenshots/relay_demo_postrun_ui_watch.cy.js/*`
- `cypress/screenshots/relay_demo_picker_post_ui_watch.cy.js/*`
- `cypress/screenshots/relay_demo_dispatch_post_ui_watch.cy.js/*`

Key relay transaction facts for `LSR-PJ7 -20260227233006-CE7913`:
- `sale_status = SALE_COMMITTED_LOCAL`
- `pick_status = PICKED_READY_FOR_RELEASE`
- `dispatch_status = RELEASED`
- `cloud_sync_status = SALE_SYNC_PENDING`
- outbox contains:
  - `SALE_COMMITTED`
  - `PICK_EVENT`
  - `RELEASE_EVENT`
- queued/outstanding errors are expected because cloud was intentionally unreachable

## Phase 3 Matrix Details
### Negative cases now covered
- Missing role rejected
- Wrong role rejected

Covered endpoints:
- v2:
  - `/relay/session/open`
  - `/relay/token/create`
  - `/relay/commit-invoice`
  - `/relay/pick/update`
  - `/relay/dispatch/release`
- legacy:
  - `/relay/token`
  - `/relay/pick`
  - `/relay/release`
  - `/relay/submit-invoice`

### Allowed-role passthrough checks
- cashier session open accepted
- cashier commit-invoice moved past auth gate to payload validation
- sales associate token create accepted

## Findings
1. Cashier spec first failed when it reused a stale already-paid token (`SAL-ORD-PJ7-2026-00026`).
   - This was a test-sequencing issue, not a relay regression.
   - Reseeding with a fresh SA token (`SAL-ORD-PJ7-2026-00027`) resolved it.
2. Live relay service on `8787` could not be hot-reloaded from the current non-admin shell.
   - New legacy-route guards were therefore validated on `8788`.
   - v2 live service behavior remained validated on the real service.

## Remaining Before Final Normal Cloud Rerun
1. Restore relay `frappe_base_url` from cloud-off simulation back to the real dev site.
2. Run the normal cloud-available rerun:
   - SA
   - Cashier
   - relay-down/cloud-up fallback
   - Picker
   - Dispatch
   - Supervisor
   - relay proof specs after each stage
3. If full backend trust-model closure is required before production signoff, add explicit negative tests for cloud fulfillment sync methods:
   - `update_relay_picking_status`
   - `release_relay_dispatch`
