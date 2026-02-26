# UAT - Local Staging (`pj.local`) SA -> Cashier -> Picker -> Dispatch + Dispatch Monitor

## Date
- 2026-02-26

## Branch / Commit Under Test
- Branch: `codes-4.3-dispatch`
- Base dispatch monitor commit inherited: `d73fd42`
- Local staging deploy/test hardening and local deploy fixes: working tree changes on `codes-4.3-dispatch` (committed after this UAT entry)

## Scope
- Validate local Docker staging site (`http://pj.local:8080`) as a practical pre-cloud deploy loop.
- Prove local SA -> Cashier -> Picker -> Dispatch flow works end-to-end again after local deploy/runtime compatibility fixes.
- Validate dispatch monitor UX improvements (SLA/queue sorting/timing timeline) on local staging.
- Verify relay/local state and clean local relay outbox demo noise from local-staging cloud-sync attempts.

## Environment
- Local staging site: `http://pj.local:8080`
- Local relay: `http://127.0.0.1:8787` (LAN HTTPS also available)
- Browser: Cypress headed Chrome
- Cypress runner discipline:
  - one spec at a time
  - strict timeout (`CYPRESS_MAX_RUN_MS`)
  - post-spec scan enabled (`CYPRESS_POSTSPEC_SCAN=1`)

## Key Local Fixes Validated
- Local `pj.local` POS module/runtime failures resolved:
  - `Module POSAwesome not found`
  - `Vuetify is not defined`
- Local backend `create_sales_invoice_from_order` 500 fixed:
  - prior root cause: `ModuleNotFoundError: No module named 'posawesome.overrides'`
  - fixed by local Docker deploy compatibility shim (`posawesome.overrides` nested-package symlink)
- Browser runtime/console capture now persists local runtime errors to `cypress/tmp/browser_runtime_events/...` and local parity smoke fails fast on severe local module/script load issues

## Local Staging Cypress Results (all on `pj.local`)
- `cypress/e2e/local_staging/local_staging_parity_smoke_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_sa_only_role.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_sa_workflow_frontend_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_cashier_only_role.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_cashier_workflow_frontend_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_picker_only_role.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_picker_workflow_frontend_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_dispatch_workflow_frontend_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_supervisor_fulfillment_exception_watch.cy.js` ✅
- `cypress/e2e/local_staging/local_staging_phase3_security_relay_role_guards_watch.cy.js` ✅

## End-to-End Proof (fresh local SA -> Cashier -> Picker -> Dispatch)
### SA
- Sales Order / token created on local staging:
  - `SAL-ORD-PJ7-2026-00005`

### Cashier (relay-first local commit)
- Relay local sale created:
  - `LSR-PJ7 -20260226223509-4BBF19`
- Relay transaction row snapshot (captured from `cypress/tmp/latest_cashier_relay_commit.json`):
  - `sale_status = SALE_COMMITTED_LOCAL`
  - `pick_status = PAID_PENDING_PICK`
  - `dispatch_status = PENDING`
  - `source_env = local_staging`
  - `source_origin = http://pj.local:8080`

### Picker
- Picker targeted same local sale:
  - `LSR-PJ7 -20260226223509-4BBF19`
- Picker line edit + status path verified via relay detail/outbox:
  - partial pick (`picked_qty = 0.5`)
  - picked ready (`PICKED_READY_FOR_RELEASE`)
  - UOM/conversion factor persisted in line `payload.picker`

### Dispatch
- Dispatch targeted same local sale and released it:
  - `dispatch_status = RELEASED`
  - `released_by = cline@pjjamaica.com`
  - `released_at` populated
- Relay transaction detail confirmed after dispatch:
  - `pick_status = PICKED_READY_FOR_RELEASE`
  - `dispatch_status = RELEASED`
  - `cloud_sync_status = SALE_SYNC_PENDING` (expected on local staging cloud-sync mismatch path)
  - `source_env = local_staging`

## Dispatch Monitor UX (local staging validation)
Validated visible dispatch monitor elements:
- queue summary cards:
  - `Ready`
  - `Picking`
  - `Exceptions`
  - `Avg Wait (Ready)`
  - `Oldest Open`
  - `Over SLA`
- queue row badges:
  - pick/dispatch status chips
  - SLA chip (`SLA: OK|Watch|High`)
  - age + current-phase timing labels
- detail panel:
  - `Phase Timeline (Dispatch Monitor)`
  - `Current Phase`
  - `Current Phase Age`
  - `Open Age`
  - `SLA`
  - timing summaries (for example `Paid -> Released (Total)`)

## Relay / Queue / Outbox Observations
- Local relay health remained stable during the full local suite:
  - `/health` -> `ok: true`
- Legacy queue (`/queue`) remained clean by end of run:
  - `queued=0`, `processing=0`, `done=0`, `failed=0`
- Local relay outbox initially accumulated 4 queued rows for the local-staging sale due cloud sync attempts:
  - `SALE_COMMITTED` -> cloud `417` on `submit_invoice`
  - subsequent `PICK_EVENT` / `RELEASE_EVENT` waiting for cloud invoice linkage
- These rows were local-staging demo noise (not a relay crash) and were cleaned after evidence capture using relay storage cleanup tooling (targeted by `local_ref`):
  - cleaned `4` queued rows for `LSR-PJ7 -20260226223509-4BBF19`
- Final relay state after cleanup:
  - outbox `queued=0`, `failed=0`

## Errors/Warnings Seen During UAT (and classification)
### Local browser/runtime (fixed during this cycle)
- `Module POSAwesome not found` (local Docker asset/module serving mismatch) -> fixed
- `Vuetify is not defined` (local legacy asset shim path issue) -> fixed

### Local backend (fixed during this cycle)
- `ModuleNotFoundError: No module named 'posawesome.overrides'` on `create_sales_invoice_from_order` -> fixed via local deploy nested-package root-module shim

### Local backend (non-blocking/transient)
- `QueryDeadlockError` / `tabSeries` during `delete_sales_invoice` cleanup path (local staging test cleanup race)
  - classified as transient cleanup deadlock, not relay failure
  - did not block final local SA->Dispatch proof after rerun

## Artifacts / Evidence (local)
- `cypress/tmp/latest_sa_order.json`
- `cypress/tmp/latest_cashier_relay_commit.json`
- `cypress/tmp/picker_dispatch_target.json`
- `cypress/tmp/supervisor_exception_target.json`
- `cypress/tmp/local_staging_parity_smoke.json`
- `cypress/tmp/local_staging_posapp_window_debug.json`
- `cypress/tmp/browser_runtime_events/` (runtime/console/resource error capture)

## Conclusion
- Local staging (`pj.local`) is restored as a viable pre-cloud deploy validation loop for POS/relay frontend workflows.
- Local SA -> Cashier -> Picker -> Dispatch flow is functioning end-to-end again on local staging.
- Dispatch monitor SLA/timeline UI improvements are rendering and test-validated locally.
- Next step: deploy `codes-4.3-dispatch` to cloud dev site and rerun dispatch/supervisor (then broader cloud regression as needed).
