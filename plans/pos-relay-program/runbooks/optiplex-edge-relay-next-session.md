# OptiPlex Edge Relay Next-Session Runbook (Fresh Agent / No Chat Context)

## TL;DR (Business Owner)
- This is the first file to open on the OptiPlex machine.
- It tells a new AI agent exactly what branch to use, how to start the Edge Relay locally, what to configure in `PJ7 CASHIER`, and what tests to run.
- Relay-enabled SA + Cashier flow is already proven on the OptiPlex/dev site, and Picker/Dispatch relay-first flow (including cloud fulfillment sync parity) is proven and rerun-validated through `codex-5-final`; next sessions should build on that proof (cloud-off continuity + analytics), or rerun demos/UAT when validating new changes.
- Local relay core endpoints are already smoke-tested and the relay-host runbook process is established from `codex-3-edge-relay` forward.
- For a completely fresh Codex session, also open `optiplex-fresh-codex-zero-context-handoff.md`.

## Purpose
Provide a zero-context startup guide for a new AI coding agent session on the OptiPlex (Windows relay host), including:
- branch and docs to read first
- relay startup steps
- local health checks
- Frappe Cloud POS Profile config reminders
- Cypress test sequence to validate SA/Cashier relay behavior
- common failure modes and how to classify them

## Branch and Starting Point
- Repo: `POS-Awesome-pj`
- Branch to use (current): `codex-5-final`
- GitHub baseline commit for this handoff/runbook: `424c79a`
- Current relay-focused branch status:
  - SA + Cashier browser flows are already validated in cloud/non-relay-missing scenarios on `codex-2-cashier`
  - `codex-3-edge-relay` now includes relay-focused hardening (LAN-only mode + cloud fallback), OptiPlex LAN HTTPS setup, and live relay-enabled SA/Cashier validation
  - `codex-4-picker-dispatch` adds shared-shell Picker/Dispatch/Supervisor fulfillment workspace + relay line-wise picker payload persistence and has been live-validated locally on OptiPlex/dev site for picker/dispatch state changes
  - `codex-4.1-picked-dispatch-relay` fixes picker/dispatch cloud fulfillment sync parity and OptiPlex relay autostart (boot task) and has been live-validated on OptiPlex/dev site
  - `0b8f772` adds Phase 3 baseline relay/client-key + server-side role guards and commits helper/security Cypress specs
  - `6767d0f` fixes a live cashier regression where relay submit could send an empty role (relay rejected with `RELAY_ROLE_REQUIRED`)
  - `ce5f84d` + `6cf64aa` fix fulfillment-role navbar relay-status chip races so picker/dispatch/supervisor top-bar relay chips match actual relay usage
  - `df1ac0c` adds offline continuity fallback paths (relay token search + relay workflow monitor fallback + SA/cashier relay token/SO fallback); explicit cloud-off proof still pending
  - `d73fd42` (`codex-4.2-dispatch`) adds dispatch monitoring timers/phase timeline UX
  - `codes-4.3-dispatch` restores and validates local Docker staging (`pj.local:8080`) as a pre-cloud deploy loop:
    - local deploy compatibility fixes for current repo layout
    - separate local-staging Cypress suite under `cypress/e2e/local_staging/`
    - local SA->Cashier->Picker->Dispatch + supervisor + local relay-guard specs passing on `pj.local`
    - dispatch monitor SLA sorting/timing/detail-panel polish validated locally
  - `codex-5-final` completes strict reruns on both cloud and local:
    - SA -> Cashier -> Picker -> Dispatch role-stage suites with relay proof specs after each stage
    - supervisor exception and phase3 security reruns
    - Cypress hardening fixes for cashier fallback, picker final persisted qty proof, and long UI-shell role-consistency timeout stability
  - local relay HTTP smoke (`/health`, `/relay/session/open`, `/relay/token/create`, `/relay/commit-invoice`) passed
  - headed Cypress relay demo proof completed:
    - SA token/SO `SAL-ORD-PJ7-2026-00009`
    - relay local sale `LSR-PJ7 -20260224200538-34917A`
    - cloud invoice via relay sync `ACC-SINV-2026-00265`
  - headed Cypress picker/dispatch fulfillment validation completed (local relay persistence + cloud parity proof):
    - picker line-wise `picked_qty` decimal edit persisted in relay `payload.picker`
    - sale moved to `PICKED_READY_FOR_RELEASE`
    - dispatch release set `dispatch_status = RELEASED`
    - fresh relay outbox `PICK_EVENT` / `RELEASE_EVENT` now sync to cloud (`done`) after `codex-4.1-picked-dispatch-relay` fixes
    - cloud `POS Relay Workflow State` reflects `Picked` / `Released` for the tested invoice (`ACC-SINV-2026-00260`)

## Files to Read First (in order)
1. `plans/pos-relay-program/00-ai-agent-start-here.md`
2. `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
3. `plans/pos-relay-program/uat/2026-02-23-local-edge-relay-smoke.md`
4. `plans/pos-relay-program/uat/2026-02-23-dev-site-cashier-watch-mode-cypress.md`
5. `plans/pos-relay-program/uat/2026-02-24-optiplex-picker-dispatch-shared-shell-relay-local-first.md`
6. `plans/pos-relay-program/runbooks/optiplex-fresh-codex-zero-context-handoff.md`
7. `relay/README.md`
8. `plans/pos-relay-program/uat/2026-02-26-local-staging-sa-cashier-picker-dispatch-and-dispatch-monitor.md`
9. `cypress/e2e/local_staging/README.md`
10. `plans/pos-relay-program/runbooks/cypress_order_of_testing.md`

## Local-Only Secrets Pack (Required Before Cypress)
### Repo root `.env` (copy from main machine, do not commit)
File:
- `C:\vs code repos\POS-Awesome-pj\.env`

Exact keys required by `cypress.config.cjs`:
```dotenv
CYPRESS_baseUrl=
CYPRESS_username=
CYPRESS_password=
CYPRESS_totpUri=
```

Action:
- Copy the current `.env` from the main machine to the OptiPlex repo root.
- Do not commit it.

### Relay local runtime config (created by relay setup UI)
File:
- `relay/data/relay_config.json`

This stores local relay credentials/settings (`frappe_base_url`, `api_key`, `api_secret`, `public_base_url`, etc.) and must remain local-only.

## Current Known Good Facts (Do Not Re-Debug First)
- SA flow works on live dev site (Sales Order token + monitor rail)
- Cashier `Select S.O` filtering by POS Profile SO naming series + age works after app fix (`54ef47a`)
- LAN-only relay mode + cashier prompted cloud fallback are implemented and validated on `codex-3-edge-relay`
- OptiPlex LAN HTTPS relay (`https://192.168.50.168`) works locally after certificate trust (Caddy reverse proxy)
- `PJ7 CASHIER` expected SO series for tests: `SAL-ORD-PJ7-.YYYY.-`
- `PJ7 CASHIER` expected `Select S.O Max Age (Days)`: `1`
- Cypress specs exist for:
  - role switching (`cline`)
  - profile preflight/config
  - SA flow
  - cashier flow
  - relay-down/cloud-fallback flow
  - token-disabled regression (`custom_have_token = 0`)
- Relay observability distinction:
  - `/queue` = legacy queue UI (`relay_queue`)
  - SA/Cashier/Picker/Dispatch local-first relay flow is primarily visible in dashboard `/` + `/api/outbox` + `/api/transactions`

## OptiPlex Local Relay Startup (Windows)
### Option A (preferred for convenience)
- Double-click: `relay/start_relay.bat`

What it should do:
- create/use Python environment
- install `relay/requirements.txt`
- run relay self-test
- start relay app on port `8787`
- open browser to local relay UI

### Option B (manual, PowerShell)
From repo root:
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj\relay'
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m relay.app
```

If `.venv` already exists:
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj\relay'
.\.venv\Scripts\python -m relay.app
```

### Important restart rule after relay code changes
- If you change or deploy branch code that affects `relay/relay/*.py` (for example `relay/relay/storage.py`), restart the local relay process on the OptiPlex before testing.
- Cloud deploy alone does not update the local Python relay process.

### Current autostart model on this OptiPlex (verified)
- The OptiPlex now has a boot-time scheduled task:
  - `POSRelayStack_Autostart_OnStart`
- It starts the relay + Caddy LAN HTTPS stack on boot (runs as `SYSTEM`) using scripts in `relay/windows_autostart/`.
- If a future session suspects the relay did not restart correctly after a reboot:
  - check task result in admin PowerShell (`Get-ScheduledTaskInfo`)
  - verify both:
    - `http://127.0.0.1:8787/health`
    - `https://192.168.50.168/health`

## Relay Health Checks (Must Pass Before POS Testing)
Open in browser or use PowerShell:
- `http://127.0.0.1:8787/`
- `http://127.0.0.1:8787/health`
- `http://127.0.0.1:8787/api/outbox`

PowerShell quick checks:
```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
Invoke-RestMethod http://127.0.0.1:8787/api/outbox
```

Expected minimum:
- `/health` returns JSON with `"ok": true`

## Frappe Cloud POS Profile Setup for Relay Test (`PJ7 CASHIER`)
On the dev site, verify/set:
- `custom_have_token = 1`
- `posa_allow_sales_order = 1`
- `custom_allow_select_sales_order = 1`
- `posa_sales_order_naming_series = SAL-ORD-PJ7-.YYYY.-`
- `posa_sales_order_lookup_max_age_days = 1`
- `custom_edge_relay_url = <reachable relay URL>`

Where to set this in the site frontend (ERPNext/Frappe Desk):
- Open `POS Profile` -> `PJ7 CASHIER`
- Set the field labeled `Edge Relay URL` (backend fieldname: `custom_edge_relay_url`)
- Save

Fallback (not preferred for this workflow):
- site config key `posa_edge_relay_url` in `site_config.json` (used only when POS Profile field is blank)

### Relay URL notes (current behavior + LAN-only mode)
- Historical baseline (pre-LAN-only mode):
  - a raw LAN URL like `http://192.168.50.168:8787` was not enough for relay-enabled cashier submit because cloud backend relay checks could block submit.
- Current validated mode on this branch:
  - use LAN HTTPS `https://192.168.50.168` with POS Profile LAN-only relay mode
  - browser-LAN relay health is the submit gate
  - cloud backend relay reachability for a private LAN URL is diagnostic-only
- Browser note (HTTPS page -> HTTP relay):
  - the POS page is served from `https://...frappe.cloud`
  - direct browser `fetch()` to `http://192.168.50.168:8787` may also be blocked as mixed content in Chrome.
- If cloud-side relay diagnostics must also pass from outside the LAN:
  - use a public HTTPS tunnel URL (Cloudflare Tunnel / ngrok / equivalent)
  - set `custom_edge_relay_url` and relay `public_base_url` to that same URL
- For the current validated LAN-only deployment path:
  - use LAN HTTPS relay URL (`https://192.168.50.168`) after reverse-proxy + certificate trust setup
  - set the same LAN HTTPS URL in POS Profile `Edge Relay URL` and relay `public_base_url`
- LAN-only URL (`http://192.168.50.168:8787`) can still be used for local relay health checks on the OptiPlex itself.

### Current Relay-Focused Status / Next Target
- Completed on `codex-3-edge-relay`:
  - LAN-only relay mode (`browser-LAN` relay health is submit gate)
  - Cashier prompted cloud fallback when relay is down but cloud is up
  - OptiPlex HTTPS reverse-proxy (Caddy) + shop-PC certificate trust guidance
  - Live headed Cypress validation proving SA -> relay token and cashier -> relay local sale -> cloud sync
- Completed on `codex-4-picker-dispatch` (OptiPlex/dev-site local-first validation):
  - shared-shell Picker/Dispatch fulfillment workspace loads in POS Awesome for fulfillment roles
  - picker line-wise pick updates persist to relay line payloads (`payload.picker`) with UOM/conversion metadata
  - dispatch release updates relay local sale and dispatch events
- Completed on `codex-5-final`:
  - strict cloud + local staging rerun matrix is complete with watch-mode Cypress and hard timeouts
  - relay dashboard/transaction proof specs are passing after every role-stage workflow
  - UI-shell cross-role consistency spec is stable after timeout hardening
- Next recommended work:
  - Execute dedicated cloud-off continuity UAT across SA -> Cashier -> Picker -> Dispatch while relay remains reachable
  - Capture relay-only evidence for token visibility, SO retrieval, cashier submit behavior, and fulfillment status propagation under cloud outage
  - Expand dispatch timing/phase analytics persistence and reporting
  - Start dispatch monitoring/timing-first UX and relay phase timing instrumentation (business optimization focus)
  - Simplify picker default UX path (order-level actions first) while keeping line-item editing available for exceptions/wire/UOM cases
  - shop-PC certificate trust rollout and support docs cleanup

## Local staging pre-cloud loop (now available)
- Local Docker staging site on this OptiPlex: `http://pj.local:8080`
- Local staging deploy script (repo root):
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-staging\deploy_posawesome_to_pj_local.ps1
```
- Local-staging Cypress specs are separated and labeled under:
  - `cypress/e2e/local_staging/`
- Use the same strict Cypress discipline (one spec at a time, hard timeout, post-spec scan) with:
  - `CYPRESS_baseUrl=http://pj.local:8080/`

## Next Session Test Sequence (Recommended)
### 1. Start relay locally and verify `/health`
Do this before opening POS.

### 2. Run Cypress in watch mode (Chrome)
Preferred on OptiPlex (visible Chrome, one spec at a time):
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj'
& 'C:\Program Files\nodejs\node.exe' scripts\cypress-gui-watch.cjs --once --browser chrome --spec cypress/e2e/<spec>.cy.js
```

Alternative (manual Cypress runner UI):
```powershell
Set-Location 'C:\vs code repos\POS-Awesome-pj'
npm.cmd run e2e:open
```
Choose `Chrome`.

### 2A. Cypress execution discipline on OptiPlex (required)
- Run one spec at a time with a strict command timeout (do not leave runs hanging).
- Check in between runs and confirm the prior Cypress process has exited.
- If a run hangs, kill only Cypress-related orphan `node.exe` and Cypress-launched Chrome processes before retrying.
- For relay-dependent specs, verify both:
  - UI state (`Relay Online (LAN)` / relay-down banners / cloud chip)
  - actual relay/API state (`/health`, `/api/outbox`, `/api/transactions`, target `LSR-*`)

### 3. Core relay regression specs (SA/Cashier + fallback)
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/relay_demo_sa_post_ui_watch.cy.js` (SA relay proof)
5. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
6. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
7. `cypress/e2e/relay_demo_postrun_ui_watch.cy.js` (cashier relay proof)
8. `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js`
9. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js` (regression)

Relay UI/API sync checks expected during these runs:
- `sa_workflow_frontend_watch.cy.js`: SA UI state aligns with token creation + relay outbox `TOKEN_CREATED` evidence
- `cashier_workflow_frontend_watch.cy.js`: relay UI chip/banner state aligns with relay `/health`, `SESSION_OPEN`, `SALE_COMMITTED`, and local sale/outbox evidence
- `cashier_relay_down_cloud_fallback_watch.cy.js`: relay-down UI state is intentional and must match the relay-down simulation

### 4. Picker/Dispatch validation sequence (after deploying fulfillment/auth changes on `codex-5-final` or descendants)
Run in headed mode (manual + Cypress helpers as available). Current status: local relay persistence and cloud parity for fresh fulfillment events are validated; use this sequence after UI/auth/backend changes:
1. Set `cline` role to `Picker` and open POS
2. Confirm shared-shell fulfillment panel loads (not cashier cart/payment layout)
3. Open a relay local sale row and verify:
   - line list visible
   - `ordered qty`, `UOM`, `conversion factor`, `ordered stock qty` shown
   - `picked qty` defaults to ordered qty
4. Edit at least one line picked qty (decimal/wire-style value where possible) and save pick update
5. Verify relay transaction detail (`/api/transactions/<local_sale_ref>`) shows persisted `payload.picker` line data and `PICK_EVENT` outbox/pick event entries
6. Set `cline` role to `Dispatch` and open POS
7. Confirm dispatch queue/release-ready filtering and release action
8. Verify relay transaction detail + dispatch events after release
9. Confirm relay outbox `PICK_EVENT` / `RELEASE_EVENT` cloud sync completes for fresh events and cloud relay workflow state updates to `Picked` / `Released`

Strict role-by-role sequence including relay proof specs after each stage now lives in:
- `plans/pos-relay-program/runbooks/cypress_order_of_testing.md`

### 5. Optional visual relay demo sequence (Cypress + local relay pages)
Run this when you need business-owner proof of relay local storage/status screens:
1. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
2. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
3. Open local relay token proof page (`/relay/token/<SO token>`) and pause for observation (manual or local demo spec, if present)
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
5. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
6. Open local relay transaction proof page (`/api/transactions/<local_sale_ref>` or dashboard `/` filtered to `local_sale_ref`) and pause for observation (manual or local demo spec, if present)

### 6. What to watch for (relay-specific)
- SA token dialog still succeeds
- Cashier `PAY` -> `Submit` path should prefer relay commit path when relay is configured/reachable
- In LAN-only mode, relay submit should not be blocked solely because cloud backend cannot reach a private LAN relay URL
- Look for relay success messages (`local_sale_ref`) and relay transaction/outbox evidence after cashier submit
- Watch relay dashboard `/` `Outbox Counters (v2 Local-First)` and `Transaction Timeline (Local Sales)` for SA/Cashier local-first activity
- For Picker/Dispatch, watch relay transaction detail + outbox rows (`PICK_EVENT`, `RELEASE_EVENT`) and distinguish:
  - local relay status success (expected)
  - cloud sync completion for fresh events (expected after the `codex-4.1-picked-dispatch-relay` parity fixes and retained in `codex-5-final`)
- Historical outbox rows from pre-fix runs may still show old `500`/`417` errors; use fresh timestamps/local refs when validating.
- Remember `/queue` is the legacy queue UI and may remain idle while v2 outbox/transaction views update

## If Something Fails (How to Classify Quickly)
### A. Relay not reachable from POS browser
Symptoms:
- relay URL errors / timeouts in POS UI
- no requests visible in relay console/logs

Check:
- `custom_edge_relay_url` is correct
- Windows firewall
- correct IP/port
- relay process actually running

### B. Frappe Cloud backend says relay unreachable, but POS browser works
Symptoms:
- POS local relay calls may still work
- backend diagnostics say relay unreachable

Cause:
- cloud cannot reach LAN URL

Fix:
- in current LAN-only mode, treat cloud-side relay reachability as diagnostic-only and confirm browser-LAN HTTPS relay health/status instead
- use a tunnel/public URL only if you require cloud-side/backend relay diagnostics to pass
- set `public_base_url` in relay setup

### C. Cypress test fails but app likely works
Symptoms:
- selector/timeouts/login OTP flake
- manual UI visibly shows correct flow

Action:
- treat as test issue first
- update Cypress spec, then rerun

### E. Picker/Dispatch local relay state updates, but cloud sync stays queued
Symptoms:
- Picker/Dispatch actions succeed in POS
- relay `/api/transactions/<local_sale_ref>` shows updated local pick/release status
- relay `/api/outbox` shows `PICK_EVENT` / `RELEASE_EVENT` with retries and `last_error` `500`

Cause:
- Cloud backend endpoints for relay fulfillment sync not implemented/fixed yet in deployed app

Check:
- `last_error` in relay outbox rows
- endpoint names in error:
  - `update_relay_picking_status`
  - `release_relay_dispatch`

Action:
- Treat local-first relay workflow as working
- Capture evidence in UAT
- Fix backend endpoints, redeploy, rerun picker/dispatch validation

### D. Relay local DB schema errors
Symptoms:
- sqlite errors mentioning missing columns

Context:
- local persistent `relay/data/relay.db` may be old

Action:
- for tests, use isolated temp DB approach (already implemented in `relay/tests/test_offline_workflow.py`)
- for local runtime, back up and reset relay DB only if necessary (do not delete casually without confirming)

## Commands for Local Relay Smoke (Optional Fast Debug)
Run from `relay/` if needed to confirm relay logic independent of POS UI:
```powershell
python -m unittest tests.test_offline_workflow -v
```

This now uses an isolated temp DB per test and should not fail due to stale local `relay/data/relay.db`.

## What a New AI Agent Should Avoid
- Do not revert unrelated local changes in:
  - `posawesome/public/js/posapp/components/pos/Customer.vue`
  - `posawesome/public/js/posapp/components/pos/ItemsSelector.vue`
  - `posawesome/public/js/posapp/components/pos/UpdateCustomer.vue`
  - `relay/relay/storage.py`
- Do not assume relay failures are app bugs before checking local relay process + URL + firewall
- Do not trust cached browser assets after deploy; hard-refresh before declaring deploy broken
- Do not commit `.env`, OTP URI, relay API keys, or `relay/data/relay_config.json`

## What to Update After the Next Run
- `plans/pos-relay-program/CHANGELOG_PROGRESS.md`
- `plans/pos-relay-program/uat/` (new dated relay-enabled UAT report)
- `plans/pos-relay-program/00-ai-agent-start-here.md` (status snapshot)
- `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md` (if relay behavior/ops notes change)
- `plans/pos-relay-program/runbooks/shop-pc-lan-relay-setup-non-technical.md` (if trust steps change)

## See Also
- `../00-ai-agent-start-here.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `./optiplex-fresh-codex-zero-context-handoff.md`
- `./shop-pc-lan-relay-setup-non-technical.md`
- `../uat/2026-02-23-local-edge-relay-smoke.md`
- `../../../relay/README.md`

