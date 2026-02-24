# UAT - OptiPlex Picker/Dispatch Shared-Shell Relay Local-First Validation

## TL;DR (Business Owner)
- Picker and Dispatch now work in the same POS Awesome shell (role-limited fulfillment workspace) on the dev site.
- Picker can open a paid relay-local sale, edit line-wise picked quantity, and save pick progress/ready status.
- Dispatch can release the same sale and the local relay records the release immediately.
- Local relay persistence is working; cloud sync for picker/dispatch events is still failing with dev-backend `500` errors, so those events remain queued in relay outbox.

## Environment
- Date: `2026-02-24`
- Branch: `codex-4-picker-dispatch`
- Deployed app commit (dev site): `224e842`
- Site: `https://devpjjamaica.v.frappe.cloud/`
- POS Profile: `PJ7 CASHIER`
- Relay host: OptiPlex (`192.168.50.168`)
- Relay local process: Python relay on `127.0.0.1:8787` (restarted during UAT so new storage code loaded)
- Cypress mode: headed Chrome via terminal-driven watch wrapper (`scripts/cypress-gui-watch.cjs`)

## Scope / What Was Tested
- [x] Picker role opens shared-shell fulfillment workspace in POS Awesome
- [x] Relay pick queue loads in picker UI
- [x] Picker line list shows ordered qty, UOM, conversion factor, and picked qty editor
- [x] Picker line-wise quantity edit (decimal) persists to relay local line payload (`payload.picker`)
- [x] Picker status updates local sale (`PICK_IN_PROGRESS` -> `PICKED_READY_FOR_RELEASE`)
- [x] Dispatch role opens shared-shell fulfillment workspace
- [x] Dispatch releases the same local sale
- [x] Relay local sale updates to `dispatch_status = RELEASED`
- [x] Dispatch event is appended locally on relay
- [x] Released row drops out of relay pick queue
- [x] Relay health remains OK after workflow tests

## Important Test Setup Note (Relay Host)
- After deploying `codex-4-picker-dispatch`, the running local relay process on the OptiPlex was still using old Python code.
- The relay process was restarted so the new `relay/relay/storage.py` implementation (picker line payload persistence) would be active.
- Without this restart, picker `line_updates` appeared in `PICK_EVENT` outbox payloads but did **not** persist into `relay_local_sale_lines.payload.picker`.

## Cypress Specs Run (Headed / Watch-Mode Wrapper)
### Ran successfully
- `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js` (local helper spec for this session)
- `cypress/e2e/picker_workflow_frontend_watch.cy.js` (local helper spec for this session)
- `cypress/e2e/dispatch_workflow_frontend_watch.cy.js` (local helper spec for this session)

Notes:
- The picker/dispatch specs above were created/patched locally during this validation session and were **not committed** in this docs-only update.
- They are recorded here so a follow-on AI agent can either commit them or recreate equivalent coverage.

## Test Record (Exact IDs / Evidence)
### Target sale used for Picker + Dispatch
- `local_sale_ref`: `LSR-PJ7 -20260224200538-34917A`
- Related SO token: `SAL-ORD-PJ7-2026-00009`
- Related cloud Sales Invoice (from earlier cashier relay commit): `ACC-SINV-2026-00265`

### Picker line item under test
- Relay line `id`: `5`
- `item_code`: `20.00BSKWF`
- `item_name`: `BLUESONIK FAN18" WALL WITH REMOTE`
- Ordered qty: `1`
- UOM: `Nos`
- Conversion factor: `1`

## Picker Flow Results (Observed)
### UI behavior
- Picker landed in shared-shell fulfillment view (`Picker Queue` + `Fulfillment Detail`) instead of cashier cart/payment layout.
- Line list displayed the expected columns:
  - `Ord Qty`
  - `UOM`
  - `Conv`
  - `Picked Qty`
- `Mark All Picked`, `Start/Save Picking`, `Mark Picked Ready`, and `Flag Exception` actions were visible.

### Relay local persistence (critical proof)
- Picker saved a decimal line-wise pick edit:
  - `picked_qty = 0.5`
- Relay transaction detail (`/api/transactions/<local_sale_ref>`) showed persisted picker payload on the line:
  - `payload.picker.picked_qty = 0.5`
  - `payload.picker.picked_uom = "Nos"`
  - `payload.picker.ordered_uom = "Nos"`
  - `payload.picker.conversion_factor = 1`
  - `payload.picker.picked_stock_qty = 0.5`
  - `payload.picker.pick_status = "PARTIAL"`
- Relay appended a local `PICK_EVENT` with matching `line_updates` payload.

### Picker finalization (same session)
- After `Mark All Picked` + `Mark Picked Ready`:
  - sale `pick_status = PICKED_READY_FOR_RELEASE`
  - line `pick_status = PICKED`
  - relay appended another `PICK_EVENT` with `event_type = PICKED_READY_FOR_RELEASE`

## Dispatch Flow Results (Observed)
### UI behavior
- Dispatch landed in shared-shell fulfillment view (`Dispatch Queue` + `Fulfillment Detail`) instead of cashier layout.
- `Release Goods` action was visible and enabled for the target sale.

### Relay local persistence (critical proof)
- After `Release Goods`, relay transaction detail showed:
  - `dispatch_status = RELEASED`
  - `released_by = cline@pjjamaica.com`
  - `released_at` populated
  - `pick_status` remained `PICKED_READY_FOR_RELEASE`
- Relay appended a local dispatch event:
  - `event_type = RELEASED`
  - payload included line summary and dispatcher metadata

### Queue behavior
- Released sale no longer appeared in relay pick queue (`/relay/pick-queue`) after dispatch release.
- Observed queue count decrease (`5 -> 4`) for `PJ7 CASHIER`.

## Relay Health / Queue Snapshot After UAT
- `/health` -> `ok: true`
- Relay outbox counters (post-test snapshot):
  - `done = 19`
  - `queued = 10`
  - `total = 29`
- Legacy queue counters (separate legacy table/UI):
  - `queued = 0`
  - `processing = 0`
  - `done = 0`
  - `failed = 1`

## What Failed / Pending (Cloud Sync Gap)
Local-first behavior is working, but cloud sync for picker/dispatch events is not yet completing.

Observed relay outbox errors:
- `PICK_EVENT` cloud sync -> `500` on:
  - `posawesome.posawesome.api.posapp.update_relay_picking_status`
- `RELEASE_EVENT` cloud sync -> `500` on:
  - `posawesome.posawesome.api.posapp.release_relay_dispatch`

Impact:
- Picker/Dispatch local operations remain usable and persisted on the relay (good offline behavior).
- Cloud-side fulfillment state parity is not yet achieved for pick/release updates.
- Relay outbox correctly queues/retries these events for later sync once backend endpoints are fixed.

## Handoff Notes for Next AI Agent
### Immediate next technical tasks
1. Fix/implement cloud backend methods:
   - `update_relay_picking_status`
   - `release_relay_dispatch`
2. Re-run picker/dispatch UAT on the same OptiPlex relay after backend deploy.
3. Commit/push the local Cypress picker/dispatch specs (or replace with committed equivalents) for repeatable coverage.
4. Continue Phase 3 auth/authorization hardening (relay mutating endpoints + server-side role checks).

### Operational caution
- When relay Python code changes on this branch, restart the local relay process on the OptiPlex before testing. Deploying the cloud app alone is not enough to update the local relay executable code.

## Links
- `../CHANGELOG_PROGRESS.md`
- `../01-role-based-workflow-spec.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `../phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `../runbooks/optiplex-edge-relay-next-session.md`
- `../runbooks/optiplex-fresh-codex-zero-context-handoff.md`
