# CHANGELOG / Progress Ledger

## How to use
Append a new dated entry after each significant implementation, validation, or deployment event.

Entry format:
- Date (absolute)
- Branch
- Summary
- What changed
- What was verified
- What remains
- Links

---

## 2026-02-22 - Docs program initialized (planning and handoff set)
- Branch: `kilo-codex-v3`
- Summary: Created phased relay program docs and AI-agent handoff structure in `plans/pos-relay-program/`.
- What changed:
  - Added README, AI handoff, role spec, master plan, offline relay/Windows service spec.
  - Added phase docs (`phase-0` through `phase-5`).
  - Added centralized progress ledger.
  - Added cross-reference updates to existing docs/checklists (tracked files; local untracked role doc handled separately if staged).
- What was verified:
  - Paths and file structure created.
  - Documents cross-reference each other.
- What remains:
  - Implement Phase 1 (SA token as submitted Sales Order, online-first).
  - Deploy and run Cypress post-deploy tests.
- Links:
  - `README.md`
  - `00-ai-agent-start-here.md`
  - `phases/phase-1-sa-sales-order-token-online-first.md`

## 2026-02-22 - Phase 1 / 1B local implementation in progress (SO token + monitor rail foundation)
- Branch: `kilo-codex-v3`
- Summary: Implemented local working-tree changes for SA Sales Order token path, SO-first workflow-state timing fields, and a new ticket-style workflow monitor rail (Phase 1B foundation).
- What changed:
  - Added `create_sales_order_token(...)` API in `posawesome/posawesome/api/posapp.py` to create/submit SA Sales Orders and return token-slip metadata.
  - Added SO-first + timing-aware relay workflow-state helper logic and `get_relay_workflow_monitor_board(...)` API in `posawesome/posawesome/api/posapp.py`.
  - Updated `POS Relay Workflow State` DocType JSON for `sales_order`, shift scoping, and timing fields (`order_taken_at`, `paid_at`, `pick_started_at`, `picked_at`, `status_changed_at`) and made `sales_invoice` optional at initial creation.
  - Added duplicate Sales Order guard in `posawesome/posawesome/api/invoice.py` when SI already originates from SO.
  - Updated `Invoice.vue` SA `Save/New` flow toward SO token creation and token slip printing (QR/barcode) and relay best-effort token sync.
  - Added `WorkflowTicketRail.vue` and mounted it in `Pos.vue` (ticket icon, badge count, expandable current-shift monitor, `Mine` filter, polling).
  - Emitted `workflow_monitor_refresh_requested` from SA token creation and payment success paths.
  - Updated docs to introduce Phase 1B ticket monitor rail requirement and tracking.
- What was verified:
  - Code-level review completed; no deploy/UAT yet.
  - Local syntax checks still pending for this implementation batch.
- What remains:
  - Finish/verify end-to-end SA SO token runtime behavior on dev site.
  - Run migrations for DocType field changes.
  - UAT monitor rail behavior (count, filters, timing updates, row removal after dispatch).
  - Add Cypress coverage for SA token + ticket rail (post-deploy).
- Links:
  - `phases/phase-1-sa-sales-order-token-online-first.md`
  - `01-role-based-workflow-spec.md`
  - `02-master-implementation-plan.md`
