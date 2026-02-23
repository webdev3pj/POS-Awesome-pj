# CHANGELOG / Progress Ledger

## TL;DR (Business Owner)
- This file is the running history of what changed, what was tested, and what remains.
- Check the latest dated entry to see the current implementation/testing status.
- It is the fastest way to know whether something is planned, local-only, or actually verified.

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

Note:
- Entries are intentionally historical and preserve the branch/date context they were recorded under.
- Do not rewrite older entries to match the current branch name.

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
  - Added `WorkflowTicketRail.vue` and mounted it in `Pos.vue` (ticket icon, badge count, expandable monitor, `Mine` filter, polling).
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

## 2026-02-22 - SA no-cash session + profile/date monitor scope implementation (local, pending deploy/UAT)
- Branch: `kilo-codex-v3`
- Summary: Updated Phase 1B implementation locally so SA can enter POS without cash opening and the ticket monitor rail scopes by `POS Profile + business date` instead of requiring a cashier shift.
- What changed:
  - Added `bootstrap_pos_session(...)` in `posawesome/posawesome/api/posapp.py` for non-cash role sessions (SA/picker/dispatch/supervisor) while keeping cashier on opening shift flow.
  - Updated opening dialog and POS shell (`OpeningDialog.vue`, `Pos.vue`) to support no-cash sessions and virtual/no-opening-shift session payloads.
  - Updated ticket monitor API and `WorkflowTicketRail.vue` to use default `POS Profile + business date` scope and keep `pos_opening_shift` optional metadata.
  - Added `business_date` to `POS Relay Workflow State` DocType and workflow-state helper updates for monitor scoping and timing continuity.
  - Added SA close-shift UI guard/hide behavior in `Navbar.vue`.
  - Added Cypress watch-mode SA workflow spec draft (`cypress/e2e/sa_workflow_frontend_watch.cy.js`) for post-deploy validation.
  - Updated docs with business-owner TL;DR sections and recorded near-term follow-up for POS Profile-specific Sales Order series (use default series for current tests).
- What was verified:
  - Code review of local diffs completed.
  - Runtime UAT pending deploy + migrate.
- What remains:
  - Commit/push these changes.
  - Deploy + migrate dev site.
  - Set `cline` to SA-only operational role for SA watch-mode test.
  - Run Cypress in watch mode (Chrome) and document results in a UAT report.
- Links:
  - `phases/phase-1-sa-sales-order-token-online-first.md`
  - `00-ai-agent-start-here.md`
  - `02-master-implementation-plan.md`

## 2026-02-22 - Dev-site Cypress watch/headed runs (login pass, SA blocked by missing roles)
- Branch: `kilo-codex-v3`
- Summary: Ran Cypress against the live dev site in visible Chrome mode and CLI-headed mode; login passed, but SA workflow testing is blocked by missing `cline-*` roles on the site.
- What changed:
  - Executed `admin_set_cline_sa_only_role.cy.js`, `frappe_login_otp.cy.js`, and `sa_workflow_frontend_watch.cy.js` against `https://devpjjamaica.v.frappe.cloud/`.
  - Improved `admin_set_cline_sa_only_role.cy.js` to auto-detect SA role name and fail with explicit available `cline-*` role list.
  - Identified and fixed opening dialog API `NameError: '_' is not defined` (translation helper typo) and pushed hotfix commit `172c149`.
  - Updated UAT evidence doc with actual run outcomes and blockers.
- What was verified:
  - OTP login automation works on the live dev site.
  - Dev site currently returns no `cline-*` roles (`Available cline-* roles: (none)`), blocking role assignment and SA flow.
  - SA spec reaches POS opening dialog and correctly surfaces “no assigned role” blocker.
- What remains:
  - Ensure `cline-*` roles exist on the site (fixtures/migrate).
  - Rerun role preflight spec to set `cline` to SA-only.
  - Rerun SA workflow + ticket rail spec after role setup.
- Links:
  - `uat/2026-02-22-dev-site-sa-watch-mode-cypress.md`
  - `phases/phase-1-sa-sales-order-token-online-first.md`
  - `01-role-based-workflow-spec.md`

## 2026-02-23 (Codex / Redeploy Trigger)
- Branch: `codex-2-cashier`
- What changed:
  - Docs-only commit to force a fresh Frappe Cloud deploy/restart while investigating stale cashier frontend assets (`Select S.O` request missing `pos_profile`).
- What remains:
  - Redeploy and re-run cashier Cypress spec to confirm `search_orders` request includes `pos_profile` and naming-series filtering is active.

## 2026-02-23 - Dev-site cashier Cypress run (series/age filtering verified; token-disabled regression added)
- Branch: `codex-2-cashier`
- Summary: Completed live headed Cypress verification of the cashier `Select S.O` filtering flow after fixing the real app issue (`Invoice.vue` initial lookup omitted `pos_profile`). Added a regression smoke test to prove POS still works when `custom_have_token` is disabled.
- What changed:
  - Deployed app fix commit `54ef47a`:
    - `Invoice.vue` now passes `pos_profile` in cashier `search_orders` calls
    - backend `search_orders(...)` infers `pos_profile` from active cashier opening shift if request omits it
  - Added Cypress smoke spec `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js` (local/pending push at time of run)
  - Hardened cashier Cypress specs locally for login, row selection, payment button selectors, and submit outcome assertions.
- What was verified:
  - `PJ7 CASHIER` POS Profile configured to `SAL-ORD-PJ7-.YYYY.-` and `Select S.O Max Age (Days) = 1`
  - SA flow creates a fresh Sales Order token for cashier pickup
  - Cashier `Select S.O` request now includes `pos_profile`
  - `Select S.O` results are filtered by naming series and age for `PJ7 CASHIER`
  - Cashier can load the SA-created SO into payment flow and reach submit/validation stage
  - Token-disabled regression smoke test passes and restores `custom_have_token`
- What remains:
  - Push local Cypress hardening + docs updates to GitHub
  - Prove full cashier submit success under a relay-configured or token-disabled submit scenario (current environment shows relay warnings)
  - Expand E2E coverage to Picker/Dispatch/Supervisor
- Links:
  - `uat/2026-02-23-dev-site-cashier-watch-mode-cypress.md`
  - `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
  - `00-ai-agent-start-here.md`

## 2026-02-23 - Local edge relay acceptance + HTTP smoke on new relay branch
- Branch: `codex-3-edge-relay`
- Summary: Started relay-focused hardening branch and validated SA/Cashier relay core endpoints locally using both automated acceptance tests and a real local HTTP smoke server.
- What changed:
  - Updated `relay/tests/test_offline_workflow.py` to use an isolated temporary SQLite DB/config per test run and disable the background sync loop during tests.
  - This avoids false failures from stale local `relay/data/relay.db` schemas (e.g. missing newer columns such as `relay_cashier_sessions.role`).
- What was verified:
  - Relay acceptance suite passes locally (`5/5`) on isolated temp DB.
  - Local HTTP smoke using a real relay server process/thread succeeded for:
    - `GET /health`
    - `POST /relay/session/open`
    - `POST /relay/token/create`
    - `POST /relay/commit-invoice`
  - `commit-invoice` returned `SALE_COMMITTED_LOCAL` with a valid `local_sale_ref`.
- What remains:
  - Deploy `codex-3-edge-relay` and test SA/Cashier flow against a real Edge Relay URL (LAN/tunnel) from the live dev site.
  - Validate cashier submit outcomes end-to-end with relay configured (not just UI guards / relay-missing warnings).
  - Expand relay-focused E2E coverage for pick/release transitions if needed.

## 2026-02-23 - OptiPlex zero-context startup runbook added
- Branch: `codex-3-edge-relay`
- What changed:
  - Added `plans/pos-relay-program/runbooks/optiplex-edge-relay-next-session.md` with:
    - exact relay startup commands (Windows)
    - health checks
    - `PJ7 CASHIER` relay/profile settings
    - Cypress run order
    - troubleshooting classification
    - no-chat-context handoff guidance for a fresh AI session on the relay host
  - Linked the runbook from:
    - `plans/pos-relay-program/README.md`
    - `plans/pos-relay-program/00-ai-agent-start-here.md`
    - `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`

## 2026-02-23 - Documentation currency normalization (current vs historical labeling)
- Branch: `codex-3-edge-relay`
- Summary: Normalized top-level/phase docs to clearly label what is current, historical baseline, or historical UAT evidence, and updated branch snapshots to the current branch family.
- What changed:
  - Updated `README.md` with branch lineage and document currency label rules.
  - Updated `00-ai-agent-start-here.md` current branch snapshot to `codex-3-edge-relay` and aligned status to SA/Cashier verified work + relay local smoke.
  - Updated role spec / master plan / phase docs with explicit currency notes and corrected stale statements (SO naming-series status, SA SO token status, UAT references).
  - Labeled `plans/kilo-codex-v3-branch-accurate-checklist.md` as a historical baseline checklist.
- What was verified:
  - Docs-only normalization pass completed on current branch.
  - Current vs historical labeling now appears in top-level docs and phase docs.
- What remains:
  - Continue keeping phase checklists in sync as relay-enabled live validation progresses.
  - Update UAT docs and phase statuses after OptiPlex relay-enabled SA/Cashier testing.
- Links:
  - `README.md`
  - `00-ai-agent-start-here.md`
  - `phases/phase-0-current-state-and-completed-work.md`

## 2026-02-22 - Dev-site SA Cypress reruns progressed to token creation (app bug fixed, spec still flaky)
- Branch: `kilo-codex-v3`
- Summary: Continued live dev-site Cypress headed runs after role fixture deployment; SA workflow now reaches Sales Order token creation and monitor rail visibility. Identified and fixed a real backend issue (`delivery_warehouse` missing on SA-created Sales Order items).
- What changed:
  - Added local Cypress preflight hardening in `cypress/e2e/admin_set_cline_sa_only_role.cy.js`:
    - sets `cline` to SA-only among `cline-*`
    - verifies/sets `PJ7 CASHIER` token/SO flags
    - validates POS Profile basics and backend `get_items(...)` returns items
  - Added local Cypress SA spec hardening in `cypress/e2e/sa_workflow_frontend_watch.cy.js`:
    - SA no-cash session submit handling
    - item-feed request wait + placeholder row filtering
    - cart/non-empty verification before `Save/New`
    - Frappe modal token dialog selector support
    - OTP retry-once handling (still flaky intermittently)
  - Fixed backend SA token bug in `posawesome/posawesome/api/posapp.py`:
    - set `delivery_warehouse`/`warehouse` on Sales Order items using row or POS Profile warehouse fallback
    - pushed as commit `ecfd053`
  - Updated UAT report with latest observed results and blockers.
- What was verified:
  - `admin_set_cline_sa_only_role.cy.js` passes against live site after role fixture deployment.
  - `PJ7 CASHIER` backend `get_items(...)` returns items.
  - SA flow reaches POS, adds item, and `Save/New` opens `Sales Order Token` dialog.
  - Monitor rail visible with pending rows/count behind token dialog.
  - SA path no longer fails with `Delivery warehouse required for stock item ...` after deploy of `ecfd053`.
- What remains:
  - Stabilize SA spec login (intermittent OTP `Invalid Login. Try again.` flake).
  - Finalize token modal close handling in spec and complete rail assertions (`Order Monitor`, `Mine`, row fields).
  - Push local Cypress spec changes + docs to GitHub once stable.
- Links:
  - `uat/2026-02-22-dev-site-sa-watch-mode-cypress.md`
  - `phases/phase-1-sa-sales-order-token-online-first.md`
  - `01-role-based-workflow-spec.md`
