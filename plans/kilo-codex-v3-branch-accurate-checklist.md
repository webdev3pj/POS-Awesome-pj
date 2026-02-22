# kilo-codex-v3 Branch-Accurate Relay Implementation Checklist

## TL;DR (Business Owner)
- This is the branch-specific checklist for what is already built vs what is still missing.
- The current business priority is finishing and testing the SA frontend workflow (Sales Order token + sidebar monitor).
- SA should not open/close cash shifts; cashier owns cash accountability.
- The sidebar monitor is moving to `POS Profile + business date` scope so SA orders show up before cashier opens shift.
- Use the `plans/pos-relay-program/` docs for full details and step-by-step implementation/testing.

## Active Program Docs (Read This First)
- Use the phased docs set in `plans/pos-relay-program/` as the current planning and handoff source of truth.
- Start with `plans/pos-relay-program/00-ai-agent-start-here.md` for status, next steps, and file map.
- Use `plans/pos-relay-program/01-role-based-workflow-spec.md` for detailed per-role visibility/action rules.
- Use `plans/pos-relay-program/02-master-implementation-plan.md` for the full multi-phase roadmap.
- Use `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md` for relay/offline/Windows operations.

## Purpose
- This checklist converts the generic deep research report into a repo-specific execution checklist for branch `kilo-codex-v3`.
- It separates what is already implemented from what is still pending, so work can be prioritized correctly.
- It uses the actual current stack and routes in this branch (Flask relay on port `8787`, not FastAPI examples on `8088`).

## Section 1: Already Implemented (Confirmed in `kilo-codex-v3`)

### A. POS profile gating and backend workflow hooks
- [x] Relay/token behavior is gated by POS Profile flag `custom_have_token`.
- [x] POS Profile supports per-profile relay URL `custom_edge_relay_url`.
- [x] POS backend exposes relay connectivity and workflow methods:
  - `get_relay_connectivity_status`
  - `get_relay_workflow_state`
  - `update_relay_picking_status`
  - `release_relay_dispatch`
  - `submit_invoice`

### B. Role foundation (ERPNext-side role derivation)
- [x] Five `cline-*` roles exist in `posawesome/fixtures/role.json`.
- [x] Opening dialog derives role from ERPNext user roles (not user-selected).
- [x] Opening dialog blocks ambiguous role assignments (multiple `cline-*` roles).
- [x] Opening dialog blocks no-role users when token workflow is enabled.
- [x] Derived role is stored in `localStorage` as UI session state (`pos_current_role`).

### C. POS frontend relay-first behavior (enabled profiles)
- [x] `Payments.vue` routes relay-enabled invoice submit through relay endpoint `/relay/commit-invoice`.
- [x] Relay-enabled flow returns and displays `local_sale_ref`.
- [x] Direct-cloud fallback is disabled when relay-enabled commit fails.
- [x] `Invoice.vue` performs best-effort draft-stage token creation to relay (`/relay/token/create`).
- [x] `Navbar.vue` shows relay/cloud diagnostics including:
  - `RELAY DOWN (Offline continuity unavailable)`
  - `OFFLINE MODE (Relay Active)`
  - cloud/internet status chip diagnostics

### D. Relay API surface (actual routes in this branch)
- [x] Health and ops endpoints:
  - `GET /health`
  - `GET /queue` (HTML)
  - `GET /api/queue`
  - `GET /api/metrics`
  - `GET /api/outbox`
- [x] Transaction observability endpoints (v3):
  - `GET /api/transactions`
  - `GET /api/transactions/<local_sale_ref>`
- [x] ERPNext accessibility check endpoint (v3):
  - `GET /api/erpnext-access-check`
- [x] Relay flow endpoints:
  - `POST /relay/token`
  - `POST /relay/token/create`
  - `GET /relay/token/<token_id>`
  - `POST /relay/token/<token_id>/void`
  - `POST /relay/session/open`
  - `GET /relay/session/current`
  - `POST /relay/session/close`
  - `POST /relay/customer/upsert`
  - `GET /relay/customer/search`
  - `GET /relay/items/search`
  - `POST /relay/items/refresh`
  - `POST /relay/items/refresh-from-cloud`
  - `POST /relay/commit-invoice`
  - `GET /relay/pick-queue`
  - `POST /relay/pick/update`
  - `POST /relay/dispatch/release`
  - `POST /relay/submit-invoice` (legacy/edge-first path retained)

### E. Relay local-first persistence and idempotent commit foundation
- [x] SQLite relay storage includes local-sale, token, session, idempotency, pick/dispatch, and outbox tables.
- [x] `commit_invoice_atomic` enforces required idempotency key and stores replay responses.
- [x] Double-pay prevention path exists at relay storage layer (token consume + idempotency handling).
- [x] Outbox queue supports retries and `next_attempt_at` backoff scheduling.
- [x] Sync worker processes `SALE_COMMITTED`, `PICK_EVENT`, and `RELEASE_EVENT`.
- [x] Sync worker marks `TOKEN_CREATED`, `SESSION_OPEN`, `SESSION_CLOSE` as intentional no-op cloud ack (partial parity).

### F. Offline cache foundation
- [x] Relay customer upsert/search endpoints exist.
- [x] Relay item cache search and refresh endpoints exist.
- [x] `offline_sync.py` helper exists for item refresh from cloud.

### G. Tests and docs already present
- [x] Relay acceptance test suite exists (`relay/tests/test_offline_workflow.py`) covering 5 relay API-level scenarios.
- [x] Handoff doc includes v2 implementation progress snapshot and known limitations.
- [x] Handoff doc includes ERPNext-to-relay accessibility requirement and `public_base_url` guidance.

### H. Additional v3 changes outside core checklist
- [x] Relay dashboard now includes transaction observability (list/detail view and summary).
- [x] Relay setup/dashboard expose `public_base_url`.
- [x] POS commission hooks were fixed/refactored (`run_all_commissions`) in this branch.

## Section 2: Must Fix Next (Priority-Ordered Gaps)

### P0. Security and trust boundary implementation (not just design)
- [ ] Implement actual relay request authentication for mutating endpoints (current code does not implement `X-Relay-Token` / `RELAY_AUTH_TOKEN`).
- [ ] Define and implement the real identity model the relay will trust for user identity (device token, signed user payload, ERPNext-backed session, or equivalent).
- [ ] Enforce server-side role authorization in relay endpoints (do not trust `pos_current_role` from localStorage or client payload role).
- [ ] Add clean authorization error codes (`NOT_AUTHORIZED`, role mismatch, no-role, multi-role) and consistent response format.

### P0. Deployment alignment and cloud reachability validation
- [ ] Deploy branch `kilo-codex-v3` to the target cloud app/site.
- [ ] Run `bench migrate` and restart services on the cloud site.
- [ ] Verify cloud methods resolve and are callable:
  - `get_relay_connectivity_status`
  - `get_relay_workflow_state`
  - `update_relay_picking_status`
  - `release_relay_dispatch`
  - `submit_invoice`
- [ ] Configure relay `public_base_url` to a cloud-reachable URL (HTTPS tunnel/VPN/public route).
- [ ] Set POS Profile `custom_edge_relay_url` to the cloud-reachable relay URL for backend diagnostics.
- [ ] Validate relay `/health` from cloud path using relay `/api/erpnext-access-check`.

### P1. POS UI role enforcement and role-based visibility
- [ ] Show current derived role in `Navbar.vue` (read-only display).
- [ ] Ship and UAT the ticket-style workflow monitor rail (Phase 1B):
  - left sidebar ticket icon + pending count badge
  - profile/date-scoped pending orders list (`POS Profile + business date`; opening shift optional metadata)
  - `Mine` filter by Sales Order owner (SA attribution)
  - timing display (`order_taken_at` / time-in-status)
  - hide rows after dispatch release
- [ ] Implement/verify SA no-cash POS session entry (cash opening remains cashier-only).
- [ ] Near-term follow-up: add POS Profile-specific Sales Order naming series setting (`posa_sales_order_naming_series`) for per-profile SO numbering; current testing uses default SO series.
- [ ] Implement role-based UI visibility/disable rules using derived role:
  - Sales Associate
  - Cashier
  - Picker
  - Dispatch
  - Supervisor
- [ ] Block forbidden UI actions early (UX), while keeping server-side enforcement as source of truth.
- [ ] Add/define supervisor override UI flows (discount/exception approvals) if required for this rollout.

### P1. Offline continuity UX wiring for customer and item search/create
- [ ] Wire `Customer.vue` / related POS customer flows to relay endpoints during cloud outage or relay-first mode:
  - `GET /relay/customer/search`
  - `POST /relay/customer/upsert`
- [ ] Wire `ItemsSelector.vue` (and related item selection flows) to relay item cache:
  - `GET /relay/items/search`
  - refresh path when appropriate
- [ ] Define fallback behavior matrix for enabled profile:
  - relay reachable + cloud down
  - relay down + cloud up
  - relay down + cloud down
- [ ] Validate profile-disabled path remains unchanged.

### P1. Sync parity and cloud reconciliation hardening
- [ ] Extend outbox cloud mapping and reconciliation beyond current phase-1 parity:
  - `TOKEN_CREATED`
  - `SESSION_OPEN`
  - `SESSION_CLOSE`
  - fuller pick/release cloud parity if required
- [ ] Add replay-safe cloud lookup/correlation for timeout/conflict cases across all synced event types.
- [ ] Standardize cloud idempotency correlation fields (sale + pick + release + session).
- [ ] Add poison-event handling / operator-visible triage path for repeated failures.

### P2. Relay audit and role traceability enhancements
- [ ] Add role audit fields where still missing (token creator role, pick/dispatch actor role, supervisor action role).
- [ ] Add supervisor approval audit record format (who, when, why, what changed).
- [ ] Confirm session open/close events are durably recorded and visible in outbox/dashboard.

### P2. Operational hardening and observability polish
- [ ] Add structured request logging (endpoint, user/device, local_sale_ref/event_id, status, latency).
- [ ] Add explicit metrics/alerts for outbox backlog age and repeated failure counts.
- [ ] Harden health/connectivity checks against transient false positives/negatives.
- [ ] Finalize Windows service/firewall packaging for production rollout (auto-start + Private profile firewall rules).

### P2. Documentation cleanup (branch accuracy)
- [ ] Update `LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/ROLE_IMPLEMENTATION.md` to reflect:
  - role is derived from ERPNext roles (not user-selected)
  - current completed vs pending status
- [ ] Update generic deep research checklist to actual branch routes and stack:
  - Flask (not FastAPI prompt assumptions)
  - port `8787` default
  - actual route names (`/relay/commit-invoice`, `/relay/pick/update`, etc.)
- [ ] Update handoff markdown/PDF after next implementation cycle and UAT results.

## Section 3: UAT + Deployment Evidence Checklist (What Must Be Collected)

### A. Environment and deployment proof
- [ ] Record branch and commit used for cloud deployment (`kilo-codex-v3`, commit SHA).
- [ ] Record cloud deploy timestamp, migrate timestamp, and restart timestamp.
- [ ] Capture evidence that new Frappe methods are available (successful API calls or logs).
- [ ] Capture relay config snapshot (redacted):
  - `frappe_base_url`
  - `public_base_url`
  - relay host/port
  - poll interval

### B. Relay reachability and diagnostics proof
- [ ] Relay local health reachable: `http://127.0.0.1:8787/health`.
- [ ] Relay dashboard reachable: `http://127.0.0.1:8787`.
- [ ] Relay outbox/transactions pages reachable:
  - `/api/outbox`
  - `/api/transactions`
- [ ] `GET /api/erpnext-access-check` returns success against configured `public_base_url`.
- [ ] POS navbar shows expected relay/cloud chips with correct diagnostics.

### C. Core acceptance flows (store LAN / multi-device or multi-session)
- [ ] Test 1: Multi-device offline sale flow (SA -> Cashier -> Picker -> Dispatch).
- [ ] Test 2: Multi-cashier same profile concurrent sessions with separate tokens.
- [ ] Test 3: Double-pay prevention (same token, second cashier blocked).
- [ ] Test 4: Idempotency replay returns same `local_sale_ref`.
- [ ] Test 5: Sync recovery after outage with no duplicate cloud invoices.

### D. Additional role and policy tests (branch-specific gaps)
- [ ] User with multiple `cline-*` roles is blocked at opening dialog.
- [ ] User with no `cline-*` role is blocked when token workflow is enabled.
- [ ] User with no `cline-*` role is allowed legacy mode when token workflow is disabled.
- [ ] Relay-enabled profile blocks commit when relay is down (direct-cloud fallback disabled in relay path).
- [ ] Profile-disabled behavior remains legacy-compatible.

### E. Data integrity and sync evidence
- [ ] For each acceptance test sale, capture:
  - relay `local_sale_ref`
  - local sale status, pick status, dispatch status
  - outbox events and final statuses
  - cloud invoice name (when synced)
- [ ] Verify no duplicate local sale for same token.
- [ ] Verify no duplicate cloud invoice for same local sale / correlation id.
- [ ] Verify pick/release events reconcile as intended (or document intentional local-only behavior).

### F. Logs and screenshots to archive
- [ ] Relay dashboard screenshots (health, queue/outbox, transactions detail).
- [ ] POS screenshots (chips, submit success with `local_sale_ref`, relay-down blocking message).
- [ ] Relay logs covering one full offline->online recovery cycle.
- [ ] Cloud-side logs or API responses proving method availability and invoice creation.

### G. Sign-off criteria
- [ ] Security model for relay request auth and role enforcement is documented and approved.
- [ ] Critical P0 and P1 checklist items are complete (or explicitly deferred with rationale).
- [ ] Known limitations are documented in handoff markdown with operator impact.
- [ ] Final docs updated and pushed with implementation changes.
