# 00 - AI Agent Start Here (Handoff and Context)

## TL;DR (Business Owner)
- This branch is building a role-based store workflow: SA creates orders/tokens, cashier takes payment, then picker and dispatch complete fulfillment.
- The immediate work is finishing and testing the SA frontend flow end-to-end, including the left sidebar ticket counter/monitor.
- SA must not open/close cash shifts; cashier owns money-related opening/closing.
- The ticket sidebar monitor is now planned to use `POS Profile + business date` (not only opening shift), so SA orders appear even before a cashier opens shift.
- Sales Order series per POS Profile is a near-term follow-up feature; current tests use the default Sales Order series.

## See also
- `README.md`
- `runbooks/optiplex-edge-relay-next-session.md`
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-0-current-state-and-completed-work.md`
- `CHANGELOG_PROGRESS.md`

## Mission and Business Rules
Build and harden a role-based POS workflow with an edge relay so the store can continue operating with local-first behavior while preserving auditability.

Key business rules currently agreed:
- Sales Associate (SA) should create the customer order/token as a `Sales Order` (not a `Sales Invoice`) to preserve invoice numbering integrity.
- Cashier should create/submit the `Sales Invoice` after payment.
- The Sales Invoice series must not be consumed by pre-payment token creation.
- SA attribution on the Sales Order will rely on Frappe `owner` for now.
- SA-stage `sales_partner` capture is deferred and tracked as backlog.

## Current Branch and Status Snapshot
- Branch: `codex-2-cashier`
- Current state: SA Sales Order token + monitor rail are implemented and live-tested; cashier `Select S.O` series/age filtering is implemented and verified on the dev site; role enforcement and full role UI visibility are still incomplete.
- Priority implementation target: `Phase 2` cashier submit hardening (environment-specific relay/cloud outcomes), then Picker/Dispatch UI/E2E coverage.
- Immediate follow-on target: push Cypress hardening/docs updates and expand live E2E coverage beyond SA/Cashier.

### Relay branch note (current next branch)
- Relay-focused follow-on branch exists: `codex-3-edge-relay`
- Use it for OptiPlex/local relay startup and relay-enabled SA/Cashier end-to-end testing
- See `runbooks/optiplex-edge-relay-next-session.md` for zero-context startup steps on the relay host

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

### POS relay/cashier foundation (`Implemented`/`Partial`)
- Relay-enabled payments use `/relay/commit-invoice`.
- Relay-enabled failure path blocks direct cloud fallback.
- Local sale reference display exists.
- Token creation to relay exists as best-effort from invoice draft path (current behavior to be replaced for SA in Phase 1).

### Existing Sales Order support (`Implemented` but not the SA token path)
- POS can search and load submitted unbilled Sales Orders.
- POS can convert Sales Order to Sales Invoice for payment.
- Current SA token popup is still tied to draft Sales Invoice save flow.

### Cypress and OTP login automation (`Local working tree - implemented, not guaranteed committed`)
- Cypress is configured with `npm run e2e:open` and `npm run e2e:run`.
- OTP automation via `otpauth://` and local `.env` exists.
- Cypress login test for Frappe Cloud OTP flow exists.

## What Is Broken / Partial / Deferred
### Partial
- Role-based UI visibility by role across all components.
- Picker and Dispatch front-end operator workflows.
- Customer/item offline UI wiring (partially added locally; needs verification and branch alignment).
- Relay sync parity for some non-sale events.

### Missing (critical)
- Relay authentication for mutating endpoints.
- Server-side relay role authorization (do not trust browser localStorage role).
- SA token as submitted Sales Order (currently invoice-based token generation).

### Deferred (explicit)
- SA-stage `sales_partner` capture on Sales Order token creation.
- Optional explicit custom field for visible SA attribution on Sales Order (owner is sufficient for now).
- SA relay-first/offline token creation until online-first path is stable.

## Immediate Next Recommended Task
Complete and verify `Phase 1 + Phase 1B`: Sales Associate token creation as a submitted `Sales Order` (online-first), SA no-cash POS session bootstrap, and the cross-role ticket sidebar monitor rail for profile/date-scoped pending orders and timing.

Why this is next:
- It resolves a core audit requirement.
- It reduces invoice-series misuse.
- It creates a clear role boundary before deeper relay/auth work.
- It gives operations immediate visibility into bottlenecks (unpaid, paid, picking, picked) and time in status.

## OptiPlex / Relay Host Startup (No Chat Context)
If a new session starts on the OptiPlex relay machine and does not have this conversation context:
- Open `runbooks/optiplex-edge-relay-next-session.md` first
- Checkout/use branch `codex-3-edge-relay`
- Start the local relay and verify `/health`
- Then run the documented Cypress sequence from the main dev machine/browser against the live dev site

## Decision Register
### Accepted
- SA token becomes submitted `Sales Order` in Phase 1 (online-first).
- Cashier prefers `Sales Order -> Sales Invoice`, with direct invoice fallback retained for now.
- SA attribution on Sales Order uses Frappe `owner` for now.
- Slip will include QR + barcode + customer/SA/date/time/grand total/token last4.
- Cypress post-deploy tests can use first available item for SA flow validation (initial automation strategy).
- Add a cross-role ticket sidebar monitor rail (default scope: `POS Profile + business date`, `Mine` filter, hide after dispatch) using polling first; WebSocket deferred.
- Sales Associate must not open/close cash shift; cashier owns cash accountability.
- POS Profile-specific Sales Order naming series is a near-term follow-up (default SO series is acceptable for current testing).

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
  - Phase 1: add SA `create_sales_order_token(...)` API here.
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
- `plans/kilo-codex-v3-branch-accurate-checklist.md`
- `plans/pos-relay-program/README.md`
- `plans/pos-relay-program/01-role-based-workflow-spec.md`
- `plans/pos-relay-program/02-master-implementation-plan.md`
- `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
- `plans/pos-relay-program/phases/*.md`

## How Data Flows (Target Phase 1)
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
### Existing setup (local working tree)
- Commands:
  - `npm run e2e:open`
  - `npm run e2e:run`
- Config files:
  - `cypress.config.cjs`
  - `cypress/e2e/frappe_login_otp.cy.js`
  - `scripts/run-cypress.cjs`
- Local secrets stored in `.env` and ignored by git.

### Agent guidance
- Never commit `.env`.
- Reuse OTP login helper/test flow.
- Add SA E2E test after Phase 1 implementation and after deployment confirmation.

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
