# 00 - AI Agent Start Here (Handoff and Context)

## TL;DR (Business Owner)
- This branch family is building a role-based store workflow: SA creates orders/tokens, cashier takes payment, then picker and dispatch complete fulfillment.
- SA/Cashier relay-first flow and Picker/Dispatch relay-first flow are now live-tested on the dev site + OptiPlex relay, including cloud parity for picker/dispatch fulfillment status sync.
- The current focus has moved to relay hardening (auth/authorization), committed test coverage cleanup, and rollout/operations cleanup (shop PCs + docs/UAT).
- SA must not open/close cash shifts; cashier owns money-related opening/closing.
- The ticket sidebar monitor is now planned to use `POS Profile + business date` (not only opening shift), so SA orders appear even before a cashier opens shift.
- Sales Order series per POS Profile is implemented and used for cashier `Select S.O` filtering (for `PJ7 CASHIER`, tested with `SAL-ORD-PJ7-.YYYY.-`).

## See also
- `README.md`
- `runbooks/optiplex-edge-relay-next-session.md`
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `runbooks/shop-pc-lan-relay-setup-non-technical.md`
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-0-current-state-and-completed-work.md`
- `CHANGELOG_PROGRESS.md`

## Document Currency (Current vs Historical)
- This is the primary handoff doc for the current branch family and is currently aligned to `codex-4.1-picked-dispatch-relay` (with inherited relay work from `codex-3-edge-relay` and `codex-4-picker-dispatch`).
- Branch progression matters:
  - `kilo-codex-v3` = baseline planning + SA/monitor rollout
  - `codex-2-cashier` = cashier filtering + cashier live UAT
  - `codex-3-edge-relay` = relay-focused validation and OptiPlex runbook execution
  - `codex-4-picker-dispatch` = shared-shell Picker/Dispatch fulfillment workspace + relay line-level pick persistence + local relay UAT
  - `codex-4.1-picked-dispatch-relay` = picker/dispatch cloud sync parity fix + OptiPlex relay autostart hardening + live cloud parity validation
- Historical UAT docs remain branch/date-specific on purpose; do not rewrite them as generic current-state docs.

## Mission and Business Rules
Build and harden a role-based POS workflow with an edge relay so the store can continue operating with local-first behavior while preserving auditability.

Key business rules currently agreed:
- Sales Associate (SA) should create the customer order/token as a `Sales Order` (not a `Sales Invoice`) to preserve invoice numbering integrity.
- Cashier should create/submit the `Sales Invoice` after payment.
- The Sales Invoice series must not be consumed by pre-payment token creation.
- SA attribution on the Sales Order will rely on Frappe `owner` for now.
- SA-stage `sales_partner` capture is deferred and tracked as backlog.

## Current Branch and Status Snapshot
- Current working branch: `codex-4.1-picked-dispatch-relay`
- GitHub handoff baseline for the next OptiPlex session: `424c79a` (`docs(relay): clarify frappe cloud local-lan relay constraints`)
- Current picker/dispatch shared-shell implementation commit: `224e842` (`feat(relay): add shared picker dispatch fulfillment workspace`)
- Current picker/dispatch cloud-parity + OptiPlex autostart fix branch commits:
  - `cdc7038` (`fix(relay): sync fulfillment events and add optiplex autostart`)
  - `5d39f02` (`chore(relay): ignore autostart runtime logs`)
- Inherited validated work:
  - `kilo-codex-v3`: SA Sales Order token flow, no-cash SA session, monitor rail foundation
  - `codex-2-cashier`: cashier `Select S.O` filtering (naming series + age), cashier live E2E coverage, token-disabled regression coverage
- Current state:
  - LAN-only relay mode + prompted cloud fallback are implemented and live-validated (`codex-3-edge-relay` inherited)
  - OptiPlex LAN HTTPS relay (`https://192.168.50.168`) is configured and working
  - relay-enabled SA/Cashier end-to-end flow is live-validated (SA token -> relay local sale -> cloud sync invoice)
  - shared-shell Picker/Dispatch fulfillment workspace is deployed and live-validated on `codex-4-picker-dispatch` for local relay persistence:
    - picker line-wise `picked_qty` edits persist to relay line payloads (`payload.picker`) with UOM/conversion metadata
    - picker status transitions to `PICKED_READY_FOR_RELEASE`
    - dispatch release updates relay `dispatch_status = RELEASED`
  - picker/dispatch cloud sync parity is now live-validated on `codex-4.1-picked-dispatch-relay`:
    - relay outbox `PICK_EVENT` and `RELEASE_EVENT` rows sync to `done`
    - cloud `POS Relay Workflow State` updates to `Picked` / `Released`
  - OptiPlex relay+Caddy auto-start is now implemented and verified using a Windows boot scheduled task (`POSRelayStack_Autostart_OnStart`, `SYSTEM`) with relay LAN HTTPS health checks passing
- Priority implementation/verification target: Phase 3 relay auth/server-side role enforcement, then committed picker/dispatch Cypress coverage cleanup, then rollout hardening and shop-PC trust rollout.
- Frappe Cloud topology note: raw private LAN relay URLs are still not cloud-backend reachable; in LAN-only mode this is expected and treated as diagnostic-only while browser-LAN HTTPS health is the submit gate.

## What Is Already Implemented (Branch-Accurate)
### Relay foundation (`Implemented`)
- Relay Flask app with local SQLite persistence.
- Token/session/local sale/outbox/idempotency/pick/dispatch tables.
- Local-first commit endpoint (`/relay/commit-invoice`) with idempotency.
- Queue/dashboard/outbox/transactions observability endpoints.
- ERPNext accessibility check (`/api/erpnext-access-check`) and `public_base_url` support.
- LAN HTTPS reverse-proxy deployment on OptiPlex via Caddy and browser-reachable relay health over `https://192.168.50.168` (validated).

### POS role foundation (`Implemented`/`Partial`)
- Opening dialog derives a single `cline-*` role from ERPNext roles.
- Ambiguous role/no-role users are blocked when token workflow is enabled.
- Role stored in localStorage as `pos_current_role`.
- Full role-based visibility across POS screens is not complete yet.

### POS SA/Cashier workflow foundation (`Implemented`/`Partial`)
- SA no-cash POS session bootstrap is implemented.
- SA token creation as submitted `Sales Order` is implemented and live-tested (dev site).
- Ticket sidebar workflow monitor rail is implemented and live-tested (read-only v1).
- Relay-enabled payments use `/relay/commit-invoice`.
- LAN-only relay submit gating (browser-LAN relay health) is implemented.
- Cashier prompted cloud fallback when relay is down but cloud is up is implemented (POS Profile toggle controlled).
- Local sale reference display exists.
- Cashier `Select S.O` filtering by POS Profile Sales Order naming series + age is implemented and live-tested.
- Relay-first cashier submit is live-validated end-to-end on the dev site with local relay transaction/outbox evidence and cloud sync completion.

### POS Picker/Dispatch fulfillment workspace (`Implemented`/`Partial`)
- Shared-shell fulfillment panel in POS Awesome for `cline-Picker`, `cline-Dispatch`, `cline-Supervisor` is implemented in `codex-4-picker-dispatch`.
- Relay-backed picker queue/detail/load/update/release UI is deployed and live-tested on the dev site (OptiPlex relay).
- Picker line-wise `picked_qty` editing defaults to ordered qty and persists to relay local line payloads (`relay_local_sale_lines.payload.picker`) with:
  - `ordered_uom`
  - `picked_uom`
  - `conversion_factor`
  - derived `picked_stock_qty`
- Dispatch release updates relay local sale and dispatch event state locally (`RELEASED`).
- Cloud sync for picker/dispatch events is currently `Partial`:
  - `PICK_EVENT` / `RELEASE_EVENT` are correctly queued in relay outbox
  - dev backend endpoints currently return `500`, so cloud parity is pending backend fixes

### Existing and upgraded Sales Order support (`Implemented`)
- POS can search and load submitted unbilled Sales Orders.
- POS can convert Sales Order to Sales Invoice for payment.
- SA token flow now creates submitted `Sales Order` records (instead of consuming a `Sales Invoice` number) in the implemented SA path.

### Cypress and OTP login automation (`Implemented`, committed)
- Cypress is configured with `npm run e2e:open` and `npm run e2e:run`.
- OTP automation via `otpauth://` and local `.env` exists.
- Cypress login test, SA flow, cashier flow, role preflight, POS Profile preflight, and token-disabled regression smoke specs exist (see `cypress/e2e/` and UAT docs).

## What Is Broken / Partial / Deferred
### Partial
- Role-based UI visibility by role across all components.
- Picker and Dispatch front-end operator workflows (`Implemented` core local-first path on `codex-4-picker-dispatch`; UX polish and committed test coverage still partial).
- Customer/item offline UI wiring (partially added locally; needs verification and branch alignment).
- Relay sync parity for non-sale fulfillment events (`PICK_EVENT`, `RELEASE_EVENT`) is now working for fresh picker/dispatch relay outbox events on the dev backend (live-validated on `codex-4.1-picked-dispatch-relay`); historical queued rows from earlier pre-fix runs may still remain.

### Missing (critical)
- Relay authentication for mutating endpoints.
- Server-side relay role authorization (do not trust browser localStorage role).

### Deferred (explicit)
- SA-stage `sales_partner` capture on Sales Order token creation.
- Optional explicit custom field for visible SA attribution on Sales Order (owner is sufficient for now).
- SA relay-first/offline token creation until online-first path is stable.

## Immediate Next Recommended Task
Move to Phase 3 relay auth + server-side role enforcement hardening, then commit/standardize picker/dispatch Cypress helper coverage and continue rollout hardening.

Why this is next:
- SA/Cashier relay-first flow is now proven on the dev site and local OptiPlex relay.
- Picker/Dispatch local-first relay flow and cloud sync parity for fresh fulfillment events are now proven on the OptiPlex/dev site, so the main remaining risk has shifted to trust/auth hardening (Phase 3).
- The biggest remaining security risk is still trust hardening on relay mutating endpoints and role enforcement (Phase 3).
- Shop-PC certificate trust rollout and support instructions are now the main deployment-readiness tasks for store adoption.
- It reduces the gap between successful demo validation and repeatable production-style operation.

## OptiPlex / Relay Host Startup (No Chat Context)
If a new session starts on the OptiPlex relay machine and does not have this conversation context:
- Open `runbooks/optiplex-edge-relay-next-session.md` first
- Then open `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- Checkout/use branch `codex-4.1-picked-dispatch-relay` (unless explicitly asked to hotfix an earlier branch)
- Start the local relay and verify `/health`
- Restart the local relay process if relay Python code changed (for example `relay/relay/storage.py`)
- Copy the local-only `.env` (Cypress secrets) to the repo root if Cypress will run on the OptiPlex
- Relay-enabled SA/Cashier demo is already proven; rerun only if revalidating after new changes
- Next target: Phase 3 auth hardening + commit/standardize picker/dispatch Cypress coverage + rollout docs/checklists

## Decision Register
### Accepted
- SA token becomes submitted `Sales Order` in Phase 1 (online-first).
- Cashier prefers `Sales Order -> Sales Invoice`, with direct invoice fallback retained for now.
- SA attribution on Sales Order uses Frappe `owner` for now.
- Slip will include QR + barcode + customer/SA/date/time/grand total/token last4.
- Cypress post-deploy tests can use first available item for SA flow validation (initial automation strategy).
- Add a cross-role ticket sidebar monitor rail (default scope: `POS Profile + business date`, `Mine` filter, hide after dispatch) using polling first; WebSocket deferred.
- Sales Associate must not open/close cash shift; cashier owns cash accountability.
- POS Profile-specific Sales Order naming series and cashier lookup-age filtering are implemented; verify profile config before testing.

### Deferred
- Capture `sales_partner` during SA stage.
- Add explicit visible Sales Order field for SA user (reporting convenience).
- Relay-first SA token creation (offline-first) until online path is stable.

## Critical File Map
### POS Frontend (Vue)
- `posawesome/public/js/posapp/components/pos/OpeningDialog.vue`
  - Role derivation display/validation and SA no-cash session entry.
- `posawesome/public/js/posapp/components/pos/Invoice.vue`
  - Current token popup/print behavior, save/new flow, held orders, SO selection triggers.
  - Phase 1 primary frontend change point.
- `posawesome/public/js/posapp/components/pos/Pos.vue`
  - POS shell layout; host for cross-role workflow monitor rail.
- `posawesome/public/js/posapp/components/pos/WorkflowTicketRail.vue`
  - Phase 1B read-only ticket sidebar monitor (pending orders for profile/date scope, live polling, timing display).
- `posawesome/public/js/posapp/components/pos/FulfillmentWorkspace.vue`
  - Shared-shell Picker/Dispatch/Supervisor fulfillment panel (relay queue/detail, line-wise pick edits, dispatch release).
- `posawesome/public/js/posapp/components/pos/Payments.vue`
  - Payment submit, relay commit, role-based SA payment block, sales person/partner fields.
- `posawesome/public/js/posapp/components/pos/SalesOrders.vue`
  - Cashier selection of Sales Orders and SO -> SI conversion preload.
- `posawesome/public/js/posapp/components/pos/Navbar.vue`
  - Relay/cloud status chips, future role display.
- `posawesome/public/js/posapp/components/pos/Customer.vue`
- `posawesome/public/js/posapp/components/pos/UpdateCustomer.vue`
- `posawesome/public/js/posapp/components/pos/ItemsSelector.vue`
  - Customer/item offline cache UI wiring areas.

### ERPNext/Frappe Backend
- `posawesome/posawesome/api/posapp.py`
  - POS APIs, relay workflow state helpers, invoice submit, SO search/create-SI-from-SO.
  - SA `create_sales_order_token(...)`, no-cash session bootstrap, and monitor-board APIs are implemented here.
- `posawesome/posawesome/doctype/pos_relay_workflow_state/pos_relay_workflow_state.json`
  - Custom DocType linking token/workflow state (currently invoice-oriented).
  - Phase 1: extend for `sales_order` support.
- `posawesome/posawesome/api/invoice.py`
  - Existing hook that can auto-create SO from SI; must avoid duplicate behavior in new flow.

### Relay (Flask + SQLite)
- `relay/relay/app.py`
  - Relay HTTP endpoints, dashboards, setup endpoints.
- `relay/relay/storage.py`
  - Local schema + persistence + idempotent commit logic.
- `relay/relay/sync_worker.py`
  - Outbox sync to cloud.
- `relay/README.md`
- `relay/SETUP_CHECKLIST_OPTIPLEX.md`

### Planning / Documentation
- `plans/kilo-codex-v3-branch-accurate-checklist.md` (historical baseline checklist)
- `plans/pos-relay-program/README.md`
- `plans/pos-relay-program/01-role-based-workflow-spec.md`
- `plans/pos-relay-program/02-master-implementation-plan.md`
- `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
- `plans/pos-relay-program/phases/*.md`

## How Data Flows (Current SA/Cashier + Picker/Dispatch Relay Baseline)
1. SA opens POS and role is derived from ERPNext (`cline-Sales Associate`).
2. SA builds cart and customer selection.
3. SA clicks `Save/New`.
4. POS calls new backend API to create and submit `Sales Order`.
5. POS shows token slip dialog (SO-backed token) and prints QR/barcode + text details.
6. POS optionally performs best-effort relay token sync (`/relay/token/create`) using SO token id.
7. Cashier later loads SO (prefer `Select S.O`) and converts SO -> SI for payment.
8. Cashier submits payment (cloud or relay-enabled path depending profile and availability).
9. Picker opens the same POS shell in fulfillment mode and updates pick progress line-wise (relay stores local line payload + pick events first).
10. Dispatch opens the same POS shell in fulfillment mode and releases goods (relay stores local dispatch event + release status first).
11. Relay sync worker syncs `PICK_EVENT` / `RELEASE_EVENT` to ERPNext/Frappe cloud (live-validated on `codex-4.1-picked-dispatch-relay` for fresh events; historical pre-fix rows may still remain queued).
12. Ticket sidebar monitor rail shows live status/timing updates for pending orders (profile/date scope, all roles, optional `Mine` filter) as backend parity improves.

## How To Validate
### Code/Docs validation (no deployment needed)
- Confirm new docs and phase docs exist and cross-link correctly.
- Confirm phase statuses reflect code reality.
- Confirm role matrices match UI component behavior.

### Functional validation (after implementation)
- SA cannot pay.
- SA token creates submitted `Sales Order`.
- Token slip prints correct fields and symbols.
- Cashier can load SO and proceed to payment.
- SI is only created during cashier step.
- Ticket sidebar count and rows update as order states move from unpaid -> paid -> picking -> picked and disappear after dispatch release.

### Relay/offline validation
- Relay `/health`, `/api/outbox`, `/queue` reachable.
- Relay commit idempotency repeat returns same local sale ref.
- Picker line-wise updates persist in relay line payloads (`payload.picker`) and remain visible after refresh/reload.
- Dispatch release updates local relay sale status immediately and removes the row from relay pick queue.
- Outbox retries and next attempt scheduling behave as expected.
- Fresh picker/dispatch fulfillment outbox events (`PICK_EVENT`, `RELEASE_EVENT`) now sync successfully to the dev backend after the `codex-4.1-picked-dispatch-relay` fixes; older historical rows created before the fix may still show legacy `500` errors.

## Cypress and OTP Test Setup
### Existing setup (committed)
- Commands:
  - `npm run e2e:open`
  - `npm run e2e:run`
- Config files:
  - `cypress.config.cjs`
  - `cypress/e2e/frappe_login_otp.cy.js`
  - `scripts/run-cypress.cjs`
- Local secrets stored in `.env` and ignored by git.

### Local-only secrets pack (required for a fresh OptiPlex Codex session)
- Copy repo-root `.env` from the main machine to the OptiPlex repo root (do not commit).
- Exact keys required by `cypress.config.cjs`:
  - `CYPRESS_baseUrl`
  - `CYPRESS_username`
  - `CYPRESS_password`
  - `CYPRESS_totpUri`
- Relay runtime credentials/settings are local-only in `relay/data/relay_config.json` (written by relay setup UI; do not commit).

### Agent guidance
- Never commit `.env`.
- Reuse OTP login helper/test flow.
- Add SA E2E test after Phase 1 implementation and after deployment confirmation.
  - Note: SA and cashier E2E specs are now committed and in use; extend them rather than replacing them.

## Deployment Flow (What Agent Can Do vs What User Must Do)
### Agent can do locally
- Edit code/docs/tests.
- Run lint/tests/local Cypress login checks.
- Prepare commits and push branch.
- Provide deployment checklist and post-deploy Cypress commands.

### User/site admin must do
- Deploy branch to Frappe Cloud dev site.
- Run `bench migrate`/restart if required by environment workflow.
- Confirm deployment complete and relay URL/config updates are applied.
- Provide any new credentials/secrets if test users change.

## Safety Rules for Repo Changes
- The worktree may be dirty. Do not revert unrelated user changes.
- Stage and commit only intended files.
- Do not commit `.env`, OTP secrets, API secrets, or relay credentials.
- Prefer non-destructive git commands.
- If `ROLE_IMPLEMENTATION.md` is untracked locally, decide explicitly before staging (do not accidentally publish local-only notes).
- When documenting current state, distinguish committed branch state vs local working tree state.

## Glossary
- `SA`: Sales Associate
- `SO`: Sales Order
- `SI`: Sales Invoice
- `UAT`: User Acceptance Testing
- `ERPNext`: Cloud business system used by POS-Awesome
- `Frappe`: Framework under ERPNext
- `Relay`: Local Windows edge service (Flask + SQLite)
- `Outbox`: Local queue of cloud-sync events
- `Idempotency`: Mechanism ensuring repeated requests do not duplicate the transaction

## Links to All Other Docs
- `README.md`
- `runbooks/optiplex-edge-relay-next-session.md`
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `runbooks/shop-pc-lan-relay-setup-non-technical.md`
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-0-current-state-and-completed-work.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `phases/phase-4-sa-relay-first-offline-token-creation.md`
- `phases/phase-5-uat-deployment-observability-hardening.md`
- `CHANGELOG_PROGRESS.md`

## See also
- `README.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `CHANGELOG_PROGRESS.md`
