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

## 2026-02-24 - LAN-only relay + cloud fallback implemented and live-validated on OptiPlex (SA -> Cashier -> Relay -> Cloud)
- Branch: `codex-3-edge-relay`
- Summary: Implemented the LAN-only relay submit-gating + cashier cloud-fallback package, fixed cashier relay commit/payment-screen regressions, configured OptiPlex LAN HTTPS relay via Caddy, and completed headed Cypress watch-mode live validation on the dev site proving SA token storage and cashier relay-first local sale commit with relay UI evidence.
- What changed:
  - Implemented LAN-only relay connectivity mode (browser-LAN health check as submit gate) and relay-down prompted cloud fallback toggle in POS Profile-backed relay logic.
  - Added/used POS Profile relay controls:
    - `posa_edge_relay_connectivity_mode`
    - `posa_allow_cloud_fallback_when_relay_down`
  - Added OptiPlex LAN HTTPS relay reverse proxy + certificate tooling (Caddy) and non-technical shop PC trust runbook guidance.
  - Fixed cashier relay flow regressions across multiple commits (deployed during this session):
    - derive relay token from SO line-item when top-level token fields are blank (`1c47d36`)
    - render/seed payment modes correctly on SO -> SI cashier payment screen (`5522d5f`, `fcc719d`, `fd781cc`)
  - Added/used headed Cypress watch-mode relay demo specs to show local relay dashboard/token/transaction detail and `/queue` UI updates with explicit 20-second observation pauses (local test artifacts/specs used for UAT demonstration).
  - Updated plan docs and added a new dated UAT report for the completed relay demo/evidence set.
- What was verified:
  - Dev site deployed + migrated with relay mode fields available.
  - `PJ7 CASHIER` configured for LAN HTTPS relay and fallback:
    - `custom_edge_relay_url = https://192.168.50.168`
    - `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
    - `posa_allow_cloud_fallback_when_relay_down = 1`
  - Local relay health on OptiPlex:
    - `http://127.0.0.1:8787/health` -> `ok: true`
    - `https://192.168.50.168/health` -> `ok: true`
  - Full headed Cypress watch-mode coverage (Chrome) passes on current deployed app:
    - admin profile config
    - SA role preflight
    - SA workflow
    - cashier role preflight
    - cashier workflow
    - relay-down/cloud-fallback workflow
    - token-disabled regression smoke
  - Full demo (Cypress, headed) proving relay data lifecycle:
    - SA creates `Sales Order`/token `SAL-ORD-PJ7-2026-00009`
    - Relay stores token and emits `TOKEN_CREATED` outbox event (`done`)
    - Cashier loads the SO, pays, and relay commits local sale `LSR-PJ7 -20260224200538-34917A`
    - Relay transaction detail shows:
      - `sale_status = SALE_COMMITTED_LOCAL`
      - `pick_status = PAID_PENDING_PICK`
      - `dispatch_status = PENDING`
      - `cloud_sync_status = SALE_SYNCED_SI_SUBMITTED`
      - `cloud_invoice_name = ACC-SINV-2026-00265`
    - Relay token state transitions to `TOKEN_PAID` with `consumed_sale_ref` set to the new local sale ref
    - Relay dashboard (`/`) shows the local sale row and v2 outbox counters updating
  - Legacy queue UI (`/queue`) can be shown updating live via Cypress when a legacy queue event is enqueued; documented distinction from v2 relay outbox/transactions used by SA/Cashier local-first flow.
- What remains:
  - Commit/push Cypress relay demo specs + cashier spec hardening if these test improvements should be retained in the branch (currently local-only).
  - Clear or formally classify the one historical legacy queue/outbox failure row (`LSR-PJ7 -20260223063408-6D29F5`, old `404` path) so dashboards are cleaner for business demos.
  - Continue with next milestone work:
    - Phase 3 relay auth + server-side role enforcement hardening
    - Picker/Dispatch relay-backed UI/E2E coverage
    - shop-PC certificate trust rollout + rollout checklist execution
- Links:
  - `uat/2026-02-24-optiplex-lan-https-relay-sa-cashier-e2e-demo.md`
  - `runbooks/optiplex-edge-relay-next-session.md`
  - `runbooks/shop-pc-lan-relay-setup-non-technical.md`
  - `03-offline-edge-relay-and-windows-service-spec.md`

## 2026-02-23 - OptiPlex zero-context handoff package docs (LAN-only mode + cloud fallback implementation handoff)
- Branch: `codex-3-edge-relay`
- Summary: Added a zero-context relay-host handoff package so a fresh Codex session on the OptiPlex can start immediately, with exact branch/baseline commit, local-only secret file requirements, LAN-only relay mode implementation target, and non-technical shop-PC setup guidance.
- What changed:
  - Added `runbooks/optiplex-fresh-codex-zero-context-handoff.md` (fresh Codex takeover guide with exact baseline commit `424c79a`, copy-paste starter prompt, local-only secrets pack requirements, and implementation priorities).
  - Added `runbooks/shop-pc-lan-relay-setup-non-technical.md` (plain-English one-time certificate trust steps for SA/Cashier/Picker/Dispatch PCs).
  - Added `uat/2026-02-24-lan-only-relay-enabled-sa-cashier-template.md` (template for tomorrow's relay-enabled UAT evidence).
  - Updated current docs/runbooks to include:
    - exact GitHub baseline commit for OptiPlex handoff (`424c79a`)
    - exact Cypress env var names (`CYPRESS_baseUrl`, `CYPRESS_username`, `CYPRESS_password`, `CYPRESS_totpUri`)
    - explicit local-only secrets handling (`.env`, `relay/data/relay_config.json`)
    - current-vs-planned distinction for tunnel-based current behavior vs LAN-only mode target
- What was verified:
  - Handoff docs reference the current branch (`codex-3-edge-relay`) and the correct baseline commit (`424c79a`).
  - Cypress env var names in docs match `cypress.config.cjs`.
  - Relay config keys documented match `relay/relay/storage.py` defaults.
- What remains:
  - Implement LAN-only relay mode (browser-LAN health submit gate).
  - Implement cashier relay-down -> cloud fallback prompt (per POS Profile toggle).
  - Add OptiPlex Caddy reverse-proxy automation and shop-PC cert install scripts.
  - Run relay-enabled SA/Cashier Cypress UAT and fill the new UAT template.
- Links:
  - `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
  - `runbooks/shop-pc-lan-relay-setup-non-technical.md`
  - `uat/2026-02-24-lan-only-relay-enabled-sa-cashier-template.md`

## 2026-02-23 - OptiPlex relay startup + PJ7 CASHIER relay URL configured (local relay validated; headed Cypress pending)
- Branch: `codex-3-edge-relay`
- Summary: Executed the OptiPlex runbook startup steps on the relay host, verified local relay health/queue/outbox and local commit behavior, configured relay cloud connection settings, and updated `PJ7 CASHIER` to use the LAN relay URL on the dev site.
- What changed:
  - Started the local relay on the OptiPlex (`relay/.venv` created, dependencies installed, `relay.selftest` passed, `relay.app` running on `:8787`).
  - Configured relay runtime settings (`frappe_base_url`, API token, `public_base_url`, subnet/port) via the relay setup flow.
  - Updated dev-site POS Profile `PJ7 CASHIER` `custom_edge_relay_url` to the OptiPlex LAN relay URL (`http://192.168.50.168:8787`) using Frappe API token auth.
  - Re-enabled `PJ7 CASHIER.custom_have_token = 1` (it was `0` at session start, which would block relay token-mode testing).
- What was verified:
  - Relay local endpoints:
    - `GET /` -> `200`
    - `GET /queue` -> `200`
    - `GET /health` -> `ok: true`
    - `GET /api/outbox` -> JSON returned
  - Relay local commit smoke on the running server:
    - `POST /relay/session/open`
    - `POST /relay/token/create`
    - `POST /relay/commit-invoice`
    - idempotent replay returns same `local_sale_ref`
  - Relay transaction persisted locally with:
    - `sale_status = SALE_COMMITTED_LOCAL`
    - `cloud_sync_status = SALE_SYNC_PENDING`
    - generated `local_sale_ref`
  - Dev-site API token auth works (used to update POS Profile settings).
  - Relay best-effort access check endpoint reports the configured LAN URL reachable from the relay host (`/api/erpnext-access-check`).
- What remains:
  - Run the headed Chrome Cypress watch-mode SA + Cashier flow from the main machine against the live dev site while the OptiPlex relay is running.
  - Verify real cashier POS submit hits relay commit path and capture the live `local_sale_ref` from a browser-driven run (not only local API smoke).
  - Optionally provide a tunnel/public URL if backend/cloud-side relay reachability diagnostics are required (LAN URL is browser/LAN-only).
- Links:
  - `uat/2026-02-23-optiplex-relay-start-profile-config.md`
  - `runbooks/optiplex-edge-relay-next-session.md`
  - `03-offline-edge-relay-and-windows-service-spec.md`

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

## 2026-02-23 - Relay topology docs clarified for Frappe Cloud + local LAN relay
- Branch: `codex-3-edge-relay`
- Summary: Documented the current-branch limitation of using a raw private LAN relay URL (e.g. `192.168.50.x`) from a Frappe Cloud POS page and added the recommended tunnel/public-URL pattern.
- What changed:
  - Added explicit note that backend relay connectivity checks run from Frappe Cloud and cannot reach private LAN IPs.
  - Added mixed-content warning for `https://...frappe.cloud` -> `http://192.168.x.x:8787` browser calls.
  - Documented exact cloud config location: POS Profile `Edge Relay URL` (`custom_edge_relay_url`) and relay `public_base_url`.
  - Updated OptiPlex runbook to require a public/tunnel URL for relay-enabled submit testing.
- What remains:
  - Live relay-enabled SA/Cashier testing against a real tunnel/public relay URL on the OptiPlex.
- Links:
  - `runbooks/optiplex-edge-relay-next-session.md`
  - `03-offline-edge-relay-and-windows-service-spec.md`
  - `00-ai-agent-start-here.md`

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
