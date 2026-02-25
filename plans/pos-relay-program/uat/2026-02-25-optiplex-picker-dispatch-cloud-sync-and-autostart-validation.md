# UAT - OptiPlex Picker/Dispatch Cloud Sync Parity + Relay Autostart Validation

## TL;DR (Business Owner)
- Picker and Dispatch shared-shell workflows still work in POS Awesome (headed Cypress watch mode).
- Fresh relay outbox fulfillment events now sync to cloud successfully:
  - `PICK_EVENT` -> `done`
  - `RELEASE_EVENT` -> `done`
- Cloud `POS Relay Workflow State` now reflects the picker/dispatch status updates (`Picked`, `Released`) for the tested invoice.
- OptiPlex relay + Caddy LAN HTTPS auto-start is now configured and verified using a Windows boot scheduled task.

## Environment
- Date: `2026-02-25`
- Branch: `codex-4.1-picked-dispatch-relay`
- Deployed app commit (dev site): `5d39f02` (includes backend parity fix commit `cdc7038`)
- Site: `https://devpjjamaica.v.frappe.cloud/`
- POS Profile: `PJ7 CASHIER`
- Relay host: OptiPlex (`192.168.50.168`)
- Relay local process: Python relay on `127.0.0.1:8787`
- Relay LAN HTTPS: `https://192.168.50.168`
- Cypress mode: headed Chrome via terminal-driven watch wrapper (`scripts/cypress-gui-watch.cjs`)

## Scope / What Was Tested
- [x] OptiPlex relay/Caddy boot autostart task startup and health checks
- [x] Picker shared-shell workflow (watch mode / headed Cypress)
- [x] Dispatch shared-shell workflow (watch mode / headed Cypress)
- [x] Relay local transaction/outbox proof for fresh picker/dispatch events
- [x] Cloud fulfillment parity proof (ERPNext `POS Relay Workflow State`)

## What Changed in This Validation Cycle
- Relay sync worker now enriches fulfillment events (`PICK_EVENT`, `RELEASE_EVENT`) using `local_sale_ref` to include:
  - `sales_invoice`
  - `pos_profile`
- Relay sync worker normalizes relay picker statuses to cloud endpoint statuses:
  - `PICK_IN_PROGRESS` -> `In Progress`
  - `PICKED_READY_FOR_RELEASE` -> `Picked`
- Cloud fulfillment endpoints now accept relay-provided `pos_profile` fallback when target `Sales Invoice.pos_profile` is blank.
- OptiPlex startup scripts and scheduled task support were added/validated for relay + Caddy stack startup.

## OptiPlex Autostart Validation (Windows)
### Scheduled task
- Task name: `POSRelayStack_Autostart_OnStart`
- Trigger: boot/startup
- Run identity: `SYSTEM`

### What was verified
- Admin PowerShell verification confirmed:
  - `LastTaskResult = 0` after final startup-script fix
- Relay stack health after task run:
  - `http://127.0.0.1:8787/health` -> `ok: true`
  - `https://192.168.50.168/health` -> `ok: true`

### Notes
- Startup scripts account for:
  - Tailscale `:443` listener false positives
  - Caddy cert-store path consistency under `SYSTEM`
  - local HTTPS health-check trust differences during startup verification

## Cypress Specs Run (Headed / Watch-Mode Wrapper)
### Passed
- `cypress/e2e/admin_set_cline_picker_only_role.cy.js` ✅
- `cypress/e2e/picker_workflow_frontend_watch.cy.js` ✅
- `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js` ✅
- `cypress/e2e/dispatch_workflow_frontend_watch.cy.js` ✅

### Run notes
- `admin_set_cline_dispatch_only_role.cy.js` failed once due a login/OTP flake (stayed on `/login`) and passed on immediate rerun.
- Picker/Dispatch helper specs remain local-only in this session (not committed in this docs update).

## Test Record (Exact IDs / Evidence)
### Target local sale (picker/dispatch validation)
- `local_sale_ref`: `LSR-PJ7 -20260224190636-3B0FD9`
- Related SO token: `SAL-ORD-PJ7-2026-00007`
- Cloud Sales Invoice: `ACC-SINV-2026-00260`

## Relay Local Proof (Fresh Events)
Relay transaction detail (`/api/transactions/LSR-PJ7 -20260224190636-3B0FD9`) shows:
- local picker and dispatch event history present
- line payload `picker` data persisted (ordered/picked qty, UOM, conversion factor, derived stock qty)
- sale status fields reflect fulfillment progression:
  - `pick_status = PICKED_READY_FOR_RELEASE`
  - `dispatch_status = RELEASED`
  - `released_by = cline@pjjamaica.com`
  - `released_at` populated

Fresh relay outbox rows for the same `local_sale_ref`:
- `PICK_EVENT` (`PARTIAL`) -> `status = done`
- `PICK_EVENT` (`PICKED_READY_FOR_RELEASE`) -> `status = done`
- `RELEASE_EVENT` -> `status = done`

Observed cloud reference on these fulfillment outbox rows:
- `cloud_ref = mrqofelbgo` (cloud `POS Relay Workflow State` doc name)

## Cloud Parity Proof (ERPNext/Frappe)
Direct cloud query (`/api/resource/POS Relay Workflow State`) for `sales_invoice = ACC-SINV-2026-00260` returned:
- `name = mrqofelbgo`
- `pos_profile = PJ7 CASHIER`
- `token_status = Paid`
- `picking_status = Picked`
- `dispatch_status = Released`
- `exceptions_note = ""`
- `released_by = cline@pjjamaica.com`
- `released_at` populated

This confirms relay fulfillment events are now updating cloud workflow state for fresh runs.

## Relay Health / Outbox Snapshot After Validation
- `/health` -> `ok: true`
- Relay outbox counters (observed after fresh picker/dispatch sync validation):
  - `done = 22`
  - `queued = 15`
  - `total = 37`

### Important note on queued rows
- Remaining queued outbox rows are historical artifacts from pre-fix runs (older `500`/`417` failures), not the fresh picker/dispatch events from this validation.
- Use fresh timestamps and `local_ref` values when demoing current parity behavior.

## Defects Resolved in This Cycle
- Relay fulfillment outbox payloads lacked `sales_invoice`/`pos_profile` enrichment from `local_sale_ref`
- Relay picker status names (`PICK_*`) did not match cloud endpoint status vocabulary (`In Progress`, `Picked`, etc.)
- Cloud fulfillment endpoints rejected relay-created invoices with blank `Sales Invoice.pos_profile`
- OptiPlex relay/Caddy startup after reboot was not automatic and required task/script hardening

## Remaining Work (Next Priorities)
1. Phase 3 relay auth + server-side role authorization (shared-shell safety)
2. Commit/push local picker/dispatch Cypress helper specs if they should be part of branch history
3. Expand fulfillment UAT coverage:
   - exception path (`PICK_EXCEPTION`)
   - dispatch hold/reason/override
   - supervisor override flows
4. Cleanup/classify historical queued outbox rows to reduce demo noise

## Links
- `../CHANGELOG_PROGRESS.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `../phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `../runbooks/optiplex-edge-relay-next-session.md`
- `../runbooks/optiplex-fresh-codex-zero-context-handoff.md`
