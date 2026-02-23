# 00 - AI Agent Start Here (Handoff and Context)

## TL;DR (Business Owner)
- This branch is building a role-based store workflow: SA creates orders/tokens, cashier takes payment, then picker and dispatch complete fulfillment.
- SA and cashier frontend flows are already live-tested on the dev site (with relay-missing warnings in that environment).
- The current focus is making the same SA/Cashier flow work cleanly with a real Edge Relay running on the OptiPlex/local server.
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
- This is the primary handoff doc for the current branch family and is currently aligned to `codex-3-edge-relay`.
- Branch progression matters:
  - `kilo-codex-v3` = baseline planning + SA/monitor rollout
  - `codex-2-cashier` = cashier filtering + cashier live UAT
  - `codex-3-edge-relay` = relay-focused validation and OptiPlex runbook execution
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
- Current working branch: `codex-3-edge-relay`
- GitHub handoff baseline for the next OptiPlex session: `424c79a` (`docs(relay): clarify frappe cloud local-lan relay constraints`)
- Inherited validated work:
  - `kilo-codex-v3`: SA Sales Order token flow, no-cash SA session, monitor rail foundation
  - `codex-2-cashier`: cashier `Select S.O` filtering (naming series + age), cashier live E2E coverage, token-disabled regression coverage
- Current state: SA and cashier flows are validated on the dev site in non-relay-configured conditions; local relay acceptance + HTTP smoke are passing; next step is LAN-only relay hardening (status gating + fallback) and then live relay-enabled SA/Cashier testing from the OptiPlex/local relay host.
- Priority implementation/verification target: relay-enabled end-to-end SA/Cashier flow and submit outcomes, then Picker/Dispatch UI/E2E coverage.
- Frappe Cloud topology note: do not assume a raw LAN relay URL (`http://192.168.x.x:8787`) will work for relay-enabled submit in current behavior; current target is LAN-only mode (browser-LAN relay status as submit gate) with LAN HTTPS on the OptiPlex.

## What Is Already Implemented (Branch-Accurate)
### Relay foundation (`Implemented`)
- Relay Flask app with local SQLite persistence.
- Token/session/local sale/outbox/idempotency/pick/dispatch tables.
- Local-first commit endpoint (`/relay/commit-invoice`) with idempotency.
- Queue/dashboard/outbox/transactions observability endpoints.
- ERPNext accessibility check (`/api/erpnext-access-check`) and `public_base_url` support.

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
- Relay-enabled failure path blocks direct cloud fallback.
- Local sale reference display exists.
- Cashier `Select S.O` filtering by POS Profile Sales Order naming series + age is implemented and live-tested.

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
- Picker and Dispatch front-end operator workflows.
- Customer/item offline UI wiring (partially added locally; needs verification and branch alignment).
- Relay sync parity for some non-sale events.

### Missing (critical)
- Relay authentication for mutating endpoints.
- Server-side relay role authorization (do not trust browser localStorage role).
- Relay-enabled end-to-end cashier submit proof on the live dev site (with a configured reachable relay) is still pending.

### Deferred (explicit)
- SA-stage `sales_partner` capture on Sales Order token creation.
- Optional explicit custom field for visible SA attribution on Sales Order (owner is sufficient for now).
- SA relay-first/offline token creation until online-first path is stable.

## Immediate Next Recommended Task
Implement the `codex-3-edge-relay` LAN-only relay mode + cloud fallback package on the OptiPlex track, then validate relay-enabled SA + Cashier in headed Cypress.

Why this is next:
- SA/Cashier cloud-side behavior is already proven well enough for the next milestone.
- Relay-enabled cashier submit behavior is the highest-value remaining uncertainty.
- The current blocker is Frappe Cloud-to-LAN relay reachability assumptions in status gating.
- LAN-only mode + prompted cloud fallback reduces cashier downtime when relay is unavailable.
- It directly prepares the OptiPlex/live-relay testing session.
- It informs Phase 3 auth hardening with real deployment behavior.

## OptiPlex / Relay Host Startup (No Chat Context)
If a new session starts on the OptiPlex relay machine and does not have this conversation context:
- Open `runbooks/optiplex-edge-relay-next-session.md` first
- Then open `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- Checkout/use branch `codex-3-edge-relay`
- Start the local relay and verify `/health`
- Copy the local-only `.env` (Cypress secrets) to the repo root if Cypress will run on the OptiPlex
- Implement LAN-only mode + cloud fallback + LAN HTTPS reverse-proxy automation (current target)
- Configure `PJ7 CASHIER` relay URL/mode/fallback settings and run the documented Cypress sequence

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

## How Data Flows (Current SA/Cashier Baseline + Next Relay Focus)
1. SA opens POS and role is derived from ERPNext (`cline-Sales Associate`).
2. SA builds cart and customer selection.
3. SA clicks `Save/New`.
4. POS calls new backend API to create and submit `Sales Order`.
5. POS shows token slip dialog (SO-backed token) and prints QR/barcode + text details.
6. POS optionally performs best-effort relay token sync (`/relay/token/create`) using SO token id.
7. Cashier later loads SO (prefer `Select S.O`) and converts SO -> SI for payment.
8. Cashier submits payment (cloud or relay-enabled path depending profile and availability).
9. Relay/cashier workflow state continues through pick and dispatch.
10. Ticket sidebar monitor rail shows live status/timing updates for pending orders (profile/date scope, all roles, optional `Mine` filter).

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
- Outbox retries and next attempt scheduling behave as expected.

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
