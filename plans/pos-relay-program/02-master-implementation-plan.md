# 02 - Master Implementation Plan (Phased, End-to-End)

## TL;DR (Business Owner)
- We are delivering the workflow in phases so we fix audit-critical issues first without breaking the store.
- Phase 1/1B is the immediate business priority: SA creates `Sales Order` tokens, plus a live sidebar monitor for pending orders.
- SA should be able to work without opening a cash shift; cashier still owns cash opening/closing.
- The sidebar monitor should show orders by `POS Profile + business date` so SA orders appear even before a cashier opens shift.
- Profile-specific Sales Order numbering and cashier `Select S.O` age filtering are now implemented and verified in live dev-site cashier testing.

## See also
- `README.md`
- `00-ai-agent-start-here.md`
- `01-role-based-workflow-spec.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-0-current-state-and-completed-work.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `phases/phase-4-sa-relay-first-offline-token-creation.md`
- `phases/phase-5-uat-deployment-observability-hardening.md`
- `CHANGELOG_PROGRESS.md`

## Purpose
Provide the decision-complete implementation roadmap from the original `kilo-codex-v3` baseline through the current `codex-3-edge-relay` branch toward a production-ready role-based POS workflow with edge relay offline continuity.

## Document Currency
- This is the long-lived roadmap and phase-ordering document. It intentionally preserves plan structure from earlier branches.
- Current implementation evidence and branch-specific progress should always be checked in:
  - `CHANGELOG_PROGRESS.md`
  - `uat/*.md`
  - `00-ai-agent-start-here.md`
- Where this plan says "Phase X" but work is already complete, treat the phase section as design intent + scope history and use the changelog/UAT docs for verification status.

## Business Objective
Deliver a reliable, auditable, role-based retail workflow where:
- SA creates token/order,
- Cashier converts and collects payment,
- Picker picks,
- Dispatch releases,
- Supervisor handles exceptions,
- and the store can keep operating during cloud outages using the edge relay.

## Non-Goals (Current Program)
- Rebuilding ERPNext POS from scratch.
- Replacing all existing POS-Awesome flows at once.
- Implementing scanner-device fleet management in the same phase as SA token conversion.
- Final production security hardening before the workflow is functionally proven in UAT.

## Current State Summary (Branch-Accurate)
### Strengths (`Implemented` / `Partial`)
- Relay local-first commit and idempotency foundation exists.
- POS profile relay gating and relay status diagnostics exist.
- Role derivation foundation exists (single `cline-*` at opening dialog).
- SA no-cash session, SA Sales Order token flow, and read-only ticket monitor rail are implemented and dev-site UAT verified.
- Cashier relay commit path is functional at foundation level.
- SO search and SO -> SI conversion support exists, and cashier `Select S.O` series/age filtering is implemented and dev-site UAT verified.
- Cypress OTP login, SA flow, cashier flow, and token-disabled regression specs are committed and actively used.
- Local edge relay acceptance tests and local HTTP smoke are passing on `codex-3-edge-relay`.

### Gaps (`Planned` / `Deferred`)
- Full role-specific UI visibility is incomplete.
- Relay auth/server-side role authorization missing.
- Relay-enabled live dev-site SA/Cashier proof (with a real reachable Edge Relay) is still pending.
- SA relay-first/offline token creation deferred until online path stabilizes.

## Architecture Overview (Program Target)
### Core systems
- POS Browser (POS-Awesome Vue frontend)
- ERPNext/Frappe backend (`posapp.py` APIs + DocTypes)
- Edge Relay (Flask + SQLite + sync worker)

### Target workflow split
- SA: create submitted SO + token slip
- Cashier: SO -> SI payment (prefer), relay local commit when relay-enabled
- Picker: relay pick queue/status updates
- Dispatch: relay release workflow
- Supervisor: exception approvals/void/override (phased)

## Phase Plan
## Phase 0 - Current State Baseline and Completed Work Documentation
Goal:
- Freeze a branch-accurate baseline and capture completed work so new contributors do not repeat discovery.

Key outputs:
- This docs program (`plans/pos-relay-program/*`)
- Cross-links from existing docs/checklists
- Progress ledger entries

Dependencies:
- None (documentation only)

Exit criteria:
- Docs exist, cross-linked, pushed, and usable by human or AI agent.

## Phase 1 - SA Token as Submitted Sales Order (Online-First)
Goal:
- Replace SA invoice-based token generation with submitted Sales Order token creation.

Business decisions locked:
- SA token uses submitted `Sales Order`.
- SA attribution uses `owner` for now.
- SA-stage `sales_partner` capture deferred.
- Cashier prefers `SO -> SI`; direct invoice fallback remains.
- SA online-first only in this phase.

Primary changes:
- New backend API in `posapp.py` to create/submit SO from POS cart.
- Extend `POS Relay Workflow State` to support SO-first record linkage.
- Update `Invoice.vue` SA `Save/New` path to call SO token API.
- Token slip print with QR/barcode + required fields.
- Best-effort relay token sync after SO creation.
- Guard duplicate SO auto-creation behavior in `api/invoice.py` path when SI originates from SO.

Dependencies:
- Existing role derivation and SO conversion support.

Exit criteria:
- SA token creates submitted SO and no SI number is consumed.
- Cashier can still bill from SO.
- Token slip prints required fields.

## Phase 1B - Workflow Monitor Rail (Ticket Sidebar, Profile + Business Date Scope)
Goal:
- Give all roles a live read-only sidebar monitor to track pending orders and time spent in each workflow state.

Business decisions locked:
- Monitor is visible to all roles (including SA).
- Default scope is `POS Profile + business date`; `POS Opening Shift` is optional metadata, not the primary visibility key.
- Expanded panel supports a `Mine` filter based on Sales Order `owner` (SA attribution).
- Rows disappear after dispatch release by default.
- WebSocket is deferred; v1 uses polling + local event-trigger refresh.

Primary changes:
- Extend `POS Relay Workflow State` with timing fields (`order_taken_at`, `paid_at`, `pick_started_at`, `picked_at`, `status_changed_at`) and SO linkage support.
- Add/maintain `business_date` on workflow state rows for monitor scoping before cashier shift open.
- Add backend monitor API returning row details + summary counts for the sidebar.
- Add `WorkflowTicketRail.vue` and mount it in `Pos.vue` as a collapsible ticket-style left rail.
- Emit refresh events after local actions (SA token create, cashier payment success; picker/dispatch later as UI is completed).

Dependencies:
- Phase 1 SO-first workflow state support (required so unpaid SA orders appear before cashier payment).
- SA no-cash POS session bootstrap (so SA can create orders before cashier shift open).

Exit criteria:
- Collapsed ticket icon shows pending count.
- Expanded panel shows customer, SA, order taken time, current status, time in status, grand total for the selected profile/date scope.
- Rows update via polling and disappear after dispatch release.

## Phase 2 - Role UI Completion (Cashier / Picker / Dispatch / Supervisor UX)
Goal:
- Make the operator experience match role boundaries visually and behaviorally.

Primary changes:
- Role display in Navbar.
- Component-level visibility/disable rules across Invoice/Payments/SalesOrders/etc.
- Picker and Dispatch workflow screens/buttons aligned to role.
- Supervisor UI for exception/override actions (where scope allows before Phase 3 hard auth).

Dependencies:
- Phase 1 preferably complete (to stabilize SA/Cashier boundary first).

Exit criteria:
- Role matrices in `01-role-based-workflow-spec.md` have UI states mostly `Implemented`.

## Phase 3 - Relay Authentication and Server-Side Role Enforcement
Goal:
- Harden trust boundary so relay does not trust browser role payloads or unauthenticated mutation requests.

Primary changes:
- Relay mutating endpoint authentication.
- Trusted identity model (device/session/signed payload or equivalent).
- Action authorization by role on relay endpoints.
- Consistent auth error codes and logs.
- ERPNext-side role checks on sensitive APIs.

Dependencies:
- Phase 2 role matrix stable enough to know intended permissions.

Exit criteria:
- Relay blocks unauthorized action attempts even if browser UI is bypassed.

## Phase 4 - SA Relay-First Offline Token Creation (Offline-First)
Goal:
- Allow SA token/order creation while cloud ERPNext is unavailable, then sync to cloud SO later.

Primary changes:
- Relay local order/token storage for SA stage (SO-like local record or explicit local SO queue).
- Cloud sync event for SO creation.
- Conflict handling and reconciliation rules.
- POS UX for offline SA token creation and later cloud reference update.

Dependencies:
- Phase 1 SO data model and slip format stable.
- Phase 3 auth model preferred before broad offline write expansion.

Exit criteria:
- SA can continue token creation offline with clear operator messaging and later SO sync.

## Phase 5 - UAT, Deployment, Observability, Hardening
Goal:
- Produce deployment evidence and operational runbooks for production confidence.

Primary changes:
- Full UAT pass for all roles.
- Cypress E2E coverage expansion (SA token flow, cashier SO->SI, selected relay diagnostics).
- Deployment runbooks and rollback steps.
- Observability and operational checks (relay dashboard/outbox/transactions/health).

Dependencies:
- Functional phases complete enough for real scenario testing.

Exit criteria:
- UAT evidence documented, defects triaged, and deployment checklist validated.

## Phase Boundaries and Dependencies (Execution Order)
1. Phase 0 must precede implementation scaling (documentation baseline).
2. Phase 1 precedes serious business pilot because it fixes the invoice-series audit issue.
3. Phase 1B follows Phase 1 immediately because operational timing visibility depends on SO-first workflow state and is business-critical.
4. Phase 2 and Phase 3 can overlap partially, but role matrices should stabilize before finalizing auth rules.
5. Phase 4 should not start until the Phase 1 online path is proven in UAT.
6. Phase 5 spans the end of each phase but culminates after Phase 4.

## Frontend Changes by Component (Planned Across Phases)
### `OpeningDialog.vue`
- Keep ERPNext-derived role model.
- Improve role display messaging and validation feedback.
- Phase 1B: support non-cash session bootstrap for SA/picker/dispatch/supervisor and keep cashier opening shift flow for cash accountability.

### `Pos.vue`
- Phase 1B: mount `WorkflowTicketRail.vue` (left sidebar ticket monitor).
- Phase 1B: tolerate `pos_opening_shift = null/virtual` and carry `session_business_date` for monitor scope.

### `WorkflowTicketRail.vue` (new)
- Phase 1B: read-only cross-role monitor panel (default profile/date scope, pending count badge, `Mine` filter, timing display).
- Phase 2+: optional row actions and deeper role-specific affordances if needed.

### `Navbar.vue`
- Add read-only role chip (Phase 2).
- Keep relay/cloud status chips.
- Phase 1B: hide/block cash close-shift action for SA.

### `Invoice.vue`
- Phase 1: SA `Save/New` -> submitted SO token path + QR/barcode slip.
- Phase 2: role-specific visibility cleanup (Held, Select SO, Return, Print actions).
- Phase 4: offline SA token via relay-first flow.

### `Payments.vue`
- Preserve SA block.
- Maintain cashier relay commit path.
- Phase 2/3: role UX + authorization error handling.

### `SalesOrders.vue`
- Cashier-preferred SO retrieval path.
- Phase 2: role visibility and search/filter UX hardening.

### `Customer.vue`, `UpdateCustomer.vue`, `ItemsSelector.vue`
- Continue online + relay cache fallback integration.
- Phase 2: role visibility and edit restrictions.
- Phase 4: offline SA creation path alignment.

## Backend Changes by API / DocType
### `posawesome/posawesome/api/posapp.py`
- Phase 1: add SA `create_sales_order_token(...)` API.
- Phase 1+: enhance relay workflow state helpers for SO-first linkage.
- Phase 1B: add `bootstrap_pos_session(...)` (non-cash role session) and `get_relay_workflow_monitor_board(...)` API; maintain workflow timestamps and `business_date`.
- Phase 3: add role checks on sensitive APIs.

### `POS Relay Workflow State` DocType
- Phase 1: add `sales_order` link field and support SO-first lifecycle.
- Phase 1B: add workflow timing fields and `business_date` for monitor scope (`pos_opening_shift` remains optional metadata).
- Keep `sales_invoice` for cashier completion stage.

### `posawesome/posawesome/api/invoice.py`
- Phase 1: prevent duplicate SO creation when SI already originates from SO.

## Relay Changes by Endpoint / Storage
### Current strength
- `relay/commit-invoice`, token/session/pick/dispatch/outbox foundations exist.

### Planned changes
- Phase 1: minimal/no schema change (best-effort relay token sync using SO token id).
- Phase 1B: no relay schema dependency for v1 monitor (ERPNext workflow state is the source); document future relay/offline monitor implications.
- Phase 3: auth + server-side role enforcement.
- Phase 4: SA relay-first order/token creation and cloud SO sync workflow.

## Security and Trust Boundary Plan
### Current risk
- Role in browser (`localStorage`) and payload can be spoofed.
- Relay mutating endpoints lack robust auth.

### Plan
- Phase 3 introduces authenticated relay mutation calls and server-side authorization.
- UI blocks remain UX aids only; server/relay become source of truth.

## Deployment Plan (Frappe Cloud + Relay)
### Application deployment
- Push branch to GitHub.
- Deploy branch to dev cloud site.
- Run migrations/restart as required by the hosting workflow.

### Relay deployment / ops
- Validate relay config (`public_base_url`, API credentials, allowed subnet, port).
- Verify `/health`, `/api/outbox`, `/queue`, `/api/transactions`, `/api/erpnext-access-check`.

### Configuration alignment
- POS Profile `custom_have_token` and `custom_edge_relay_url` must match the intended relay mode and URL.
- `POS Profile.posa_sales_order_naming_series` and `posa_sales_order_lookup_max_age_days` are implemented; verify profile values before cashier UAT (e.g. `PJ7 CASHIER`).

## UAT Plan (High Level)
### SA
- Enter POS without opening cash shift, build cart, create token/SO, print slip, confirm SI not created.
- Confirm ticket sidebar row appears as `Unpaid` with timer and SA name using profile/date scope.

### Cashier
- Load SO, pay, create SI, confirm relay/cloud behavior.
- Confirm ticket sidebar row updates to `Paid`.

### Picker
- Pick queue and pick update transitions.
- Confirm ticket sidebar row updates to `Picking` / `Picked`.

### Dispatch
- Release only after allowed states.
- Confirm row removal from default sidebar list after release.

### Supervisor
- Exception and override workflows (when implemented).

## Cypress Automation Strategy
### Existing baseline
- OTP login automation to live Frappe Cloud dev site.
- SA and cashier headed/watch-mode specs are committed and were used for live dev-site verification.

### Planned additions
- Phase 2/5: expand role-visibility regression tests and extend cashier flow to relay-enabled submit success.
- Phase 5: add Picker/Dispatch/Supervisor E2E coverage as workflows/UI become stable.

### Practical constraint
- Live-site tests require stable test data and environment readiness; use first available item initially, then evolve to dedicated test fixtures.

## Risks and Rollback Controls
### Key risks
- Breaking existing cashier invoice flow while changing SA token path.
- DocType changes impacting existing workflow state assumptions.
- Relay auth changes breaking field devices if rollout is not phased.

### Mitigations
- Phase 1 keeps direct invoice fallback and reuses existing SO->SI conversion.
- Document and test both legacy and new paths.
- Deploy to dev site first and validate with Cypress + manual UAT.

### Rollback
- Feature-gate new SA SO token path behind profile/role checks during rollout.
- Keep legacy invoice path available for cashier/non-SA fallback until stable.

## Acceptance Criteria by Phase (Condensed)
- Phase 0: docs complete, pushed, usable.
- Phase 1: SA token creates submitted SO, slip prints required fields, cashier SO->SI works.
- Phase 1B: ticket sidebar monitor rail shows pending count + profile/date-scoped rows with timing.
- Phase 2: role UI visibility aligns with spec for all roles.
- Phase 3: relay/server reject unauthorized actions.
- Phase 4: SA can create token/order offline and sync to cloud later.
- Phase 5: UAT evidence and deployment runbooks completed.

## See also
- `01-role-based-workflow-spec.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `phases/phase-5-uat-deployment-observability-hardening.md`
