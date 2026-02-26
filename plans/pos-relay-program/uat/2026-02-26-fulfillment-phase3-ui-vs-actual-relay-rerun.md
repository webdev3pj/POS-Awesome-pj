# UAT - 2026-02-26 - Fulfillment UI-vs-Actual Relay Sync Rerun (Picker / Dispatch / Supervisor)

## TL;DR (Business Owner)
- We reran the fulfillment role flows (Picker, Dispatch, Supervisor) on the live dev site using strict Cypress timeouts and explicit checks that the UI relay/cloud chips match actual relay behavior.
- A real UI mismatch was caught first (fulfillment screen was using relay APIs while the top bar only showed `Cloud Online`), then fixed with navbar relay-status race/recovery patches.
- After deploying the fixes, Picker, Dispatch, and Supervisor fulfillment flows all passed and relay outbox events synced to `done`.

## Scope of this UAT
- Branch: `codex-4.1-picked-dispatch-relay`
- Live target site: `https://devpjjamaica.v.frappe.cloud/`
- Local relay: OptiPlex relay (`http://127.0.0.1:8787`, LAN HTTPS `https://192.168.50.168`)
- Focus:
  - fulfillment-role relay/cloud status chip correctness (UI vs actual)
  - picker line-wise qty persistence
  - dispatch release
  - supervisor exception + override release

## Commits under test (relevant)
- `0b8f772` - Phase 3 baseline relay/client-key + server-side role guards
- `6767d0f` - frontend fallback role from Frappe when local role missing
- `ce5f84d` - navbar relay-status fast-boot race fix
- `6cf64aa` - navbar relay poll recovery if profile event is missed

## Cypress execution policy used (strict)
- Headed Chrome (`scripts/cypress-gui-watch.cjs`)
- One spec at a time (`--once`)
- Strict per-spec Cypress config overrides:
  - `defaultCommandTimeout=15000`
  - `requestTimeout=15000`
  - `responseTimeout=30000`
  - `pageLoadTimeout=60000`
- Shell command timeout applied to every run (prevents silent hangs)

## Specs Run (this UAT slice)
1. `cypress/e2e/admin_set_cline_picker_only_role.cy.js` ✅
2. `cypress/e2e/picker_workflow_frontend_watch.cy.js` ✅ (after `6cf64aa` deploy)
3. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js` ✅
4. `cypress/e2e/dispatch_workflow_frontend_watch.cy.js` ✅
5. `cypress/e2e/admin_set_cline_supervisor_only_role.cy.js` ✅
6. `cypress/e2e/supervisor_fulfillment_exception_watch.cy.js` ✅

## What failed before the fix (and why it mattered)
- `picker_workflow_frontend_watch.cy.js` initially failed on the new helper assertion:
  - `UI relay online chip visible: expected false to equal true`
- At the same time, the picker screen was clearly calling relay APIs:
  - `/relay/pick-queue`
  - `/api/transactions/<LSR>`
- This proved a real UI-vs-actual mismatch:
  - actual relay path was active
  - top bar did not show relay status
- Root cause:
  - navbar relay polling depended on POS profile registration event timing
  - navbar could miss the event and never start relay polling

## Fix verification (UI-vs-actual in sync)
- After `ce5f84d` + `6cf64aa` deploy:
  - fulfillment-role top bar shows relay/cloud chips consistently
  - helper assertion passes:
    - relay `/health` returns `ok: true`
    - UI shows `Relay Online (LAN)`
    - UI shows `Cloud Online`
    - no relay-down banner shown during normal fulfillment runs

## Evidence IDs from this rerun
### Picker/Dispatch target (normal path)
- Local sale ref (`LSR`): `LSR-PJ7 -20260226045846-70265E`
- Token / Sales Order: `SAL-ORD-PJ7-2026-00012`
- Cloud invoice: `ACC-SINV-2026-00279`

### Supervisor exception/override target
- Local sale ref (`LSR`): `LSR-PJ7 -20260226022457-7123CC`
- Token / Sales Order: `SAL-ORD-PJ7-2026-00011`
- Cloud invoice: `ACC-SINV-2026-00277`

## Relay proof (normal picker/dispatch path)
Transaction: `LSR-PJ7 -20260226045846-70265E`

Verified on relay transaction detail (`/api/transactions/<LSR>`):
- `sale_status = SALE_COMMITTED_LOCAL`
- `pick_status = PICKED_READY_FOR_RELEASE`
- `dispatch_status = RELEASED`
- `released_by = cline@pjjamaica.com`
- `cloud_invoice_name = ACC-SINV-2026-00279`

Line persistence proof (`payload.picker`) on relay line:
- `ordered_uom = Nos`
- `picked_uom = Nos`
- `conversion_factor = 1`
- `picked_qty` persisted (partial then picked in sequence)
- `picked_stock_qty` persisted

Relay outbox proof (`/api/outbox`, fresh rows):
- `PICK_EVENT` (`PICK_IN_PROGRESS`, partial `picked_qty=0.5`) -> `done`
- `PICK_EVENT` (`PICKED_READY_FOR_RELEASE`, picked `picked_qty=1`) -> `done`
- `RELEASE_EVENT` (`cline-Dispatch`, `allow_partial=false`) -> `done`

## Relay proof (supervisor exception + override path)
Transaction: `LSR-PJ7 -20260226022457-7123CC`

Verified on relay transaction detail:
- `sale_status = SALE_COMMITTED_LOCAL`
- `pick_status = PICK_EXCEPTION`
- `dispatch_status = RELEASED`
- `released_by = cline@pjjamaica.com`
- `cloud_invoice_name = ACC-SINV-2026-00277`

Supervisor exception / override outbox proof:
- `PICK_EVENT` (`PICK_IN_PROGRESS`, role `cline-Supervisor`) -> `done`
- `PICK_EVENT` (`PICK_EXCEPTION`, role `cline-Supervisor`) -> `done`
- `RELEASE_EVENT` (role `cline-Supervisor`, `allow_partial=true`) -> `done`

## Relay health snapshot after rerun
From `GET /health` on local relay:
- `ok = true`
- outbox counts:
  - `done = 45`
  - `queued = 0`
  - `failed = 0`
  - `total = 45`
- legacy queue counts:
  - `failed = 1` (historical artifact; not the local-first v2 outbox path)

## Result
✅ Pass (for this fulfillment validation slice)

What is now proven:
- Picker, Dispatch, and Supervisor flows work on the live dev site with relay local-first behavior
- UI relay/cloud status chips are now in sync with actual relay behavior during fulfillment flows
- Relay outbox fulfillment events for the tested runs sync to cloud successfully (`done`)

## Remaining follow-up (not covered by this UAT slice)
- Run the remaining Phase 3 signoff rerun slice on the latest deployed build:
  - SA/Cashier + fallback + `phase3_security_relay_role_guards_watch.cy.js`
- Live-validate `df1ac0c` offline continuity fallbacks:
  - relay monitor/sidebar fallback
  - SA token creation relay fallback
  - cashier `Select S.O` relay token search/load fallback
  - prefer cloud-site forced-cloud-failure first, then `pj.local:8080` for true cloud-off simulation
- Start dispatch monitoring/timing-first UX and relay phase timing instrumentation

## Notes / Artifacts
- Cypress helper used for UI-vs-actual checks (currently local/uncommitted at time of run):
  - `cypress/e2e/_helpers/relay_ui_sync.js`
- Latest Cypress temp artifacts used for IDs:
  - `cypress/tmp/latest_sa_order.json`
  - `cypress/tmp/latest_cashier_relay_commit.json`
  - `cypress/tmp/picker_dispatch_target.json`
  - `cypress/tmp/supervisor_exception_target.json`
