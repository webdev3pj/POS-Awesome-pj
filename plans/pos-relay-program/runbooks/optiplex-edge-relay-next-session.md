# OptiPlex Edge Relay Next-Session Runbook (Fresh Agent / No Chat Context)

## TL;DR (Business Owner)
- This is the first file to open tomorrow on the OptiPlex machine.
- It tells a new AI agent exactly what branch to use, how to start the Edge Relay locally, what to configure in `PJ7 CASHIER`, and what tests to run.
- Goal for tomorrow: prove SA + Cashier flow works against a real local Edge Relay (not just cloud-only UI checks).
- Local relay core endpoints are already smoke-tested on branch `codex-3-edge-relay`.

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
- Branch to use: `codex-3-edge-relay`
- Current relay-focused branch status:
  - SA + Cashier browser flows are already validated in cloud/non-relay-missing scenarios on `codex-2-cashier`
  - `codex-3-edge-relay` starts relay-focused hardening and local relay smoke validation
  - local relay HTTP smoke (`/health`, `/relay/session/open`, `/relay/token/create`, `/relay/commit-invoice`) passed

## Files to Read First (in order)
1. `plans/pos-relay-program/00-ai-agent-start-here.md`
2. `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
3. `plans/pos-relay-program/uat/2026-02-23-local-edge-relay-smoke.md`
4. `plans/pos-relay-program/uat/2026-02-23-dev-site-cashier-watch-mode-cypress.md`
5. `relay/README.md`

## Current Known Good Facts (Do Not Re-Debug First)
- SA flow works on live dev site (Sales Order token + monitor rail)
- Cashier `Select S.O` filtering by POS Profile SO naming series + age works after app fix (`54ef47a`)
- `PJ7 CASHIER` expected SO series for tests: `SAL-ORD-PJ7-.YYYY.-`
- `PJ7 CASHIER` expected `Select S.O Max Age (Days)`: `1`
- Cypress specs exist for:
  - role switching (`cline`)
  - profile preflight/config
  - SA flow
  - cashier flow
  - token-disabled regression (`custom_have_token = 0`)

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
Set-Location 'I:\vscode repos\POS-Awesome-pj\relay'
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m relay.app
```

If `.venv` already exists:
```powershell
Set-Location 'I:\vscode repos\POS-Awesome-pj\relay'
.\.venv\Scripts\python -m relay.app
```

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

### Relay URL notes
- Critical for Frappe Cloud:
  - a raw LAN URL like `http://192.168.50.168:8787` is **not enough** for relay-enabled cashier submit in the current branch.
  - Reason: backend relay connectivity checks run from Frappe Cloud and cannot reach `192.168.x.x`, so POS can show `RELAY DOWN` and block relay submit.
- Browser note (HTTPS page -> HTTP relay):
  - the POS page is served from `https://...frappe.cloud`
  - direct browser `fetch()` to `http://192.168.50.168:8787` may also be blocked as mixed content in Chrome.
- Recommended for tomorrow's live relay test:
  - use a **public HTTPS tunnel URL** (Cloudflare Tunnel / ngrok / equivalent) that forwards to `http://192.168.50.168:8787`
  - set `custom_edge_relay_url` on `PJ7 CASHIER` to that tunnel URL
  - set relay `public_base_url` in the relay setup UI to the same public URL
- LAN-only URL (`http://192.168.50.168:8787`) can still be used for local relay health checks on the OptiPlex itself.

## Tomorrow’s Test Sequence (Recommended)
### 1. Start relay locally and verify `/health`
Do this before opening POS.

### 2. Run Cypress in watch mode (Chrome)
From repo root:
```powershell
Set-Location 'I:\vscode repos\POS-Awesome-pj'
npm.cmd run e2e:open
```
Choose `Chrome`.

### 3. Run specs in this order
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
5. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
6. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js` (regression)

### 4. What to watch for (relay-specific)
- SA token dialog still succeeds
- Cashier `PAY` -> `Submit` path should now prefer relay commit path when relay is configured/reachable
- UI should no longer fail only because relay URL is missing
- Look for relay success messages (local commit / `local_sale_ref`) instead of relay-missing blockers
- Relay dashboard/outbox should show activity after cashier submit attempts

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
- use tunnel/public URL
- set `public_base_url` in relay setup

### E. Relay URL set to local IP but relay-enabled submit still blocked on Frappe Cloud
Symptoms:
- `custom_edge_relay_url` is set (e.g. `http://192.168.50.168:8787`)
- POS still shows relay down / submit blocked

Cause:
- current branch intentionally checks relay connectivity from Frappe Cloud backend
- Frappe Cloud has no route to private LAN IPs (`192.168.x.x`)
- HTTPS page may also block HTTP relay calls (mixed content)

Fix:
- use a public HTTPS tunnel URL for relay access
- set the same URL in POS Profile `Edge Relay URL`
- set relay `public_base_url` to match

### C. Cypress test fails but app likely works
Symptoms:
- selector/timeouts/login OTP flake
- manual UI visibly shows correct flow

Action:
- treat as test issue first
- update Cypress spec, then rerun

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

## What to Update After Tomorrow’s Run
- `plans/pos-relay-program/CHANGELOG_PROGRESS.md`
- `plans/pos-relay-program/uat/` (new dated relay-enabled UAT report)
- `plans/pos-relay-program/00-ai-agent-start-here.md` (status snapshot)

## See Also
- `../00-ai-agent-start-here.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../uat/2026-02-23-local-edge-relay-smoke.md`
- `../../../relay/README.md`
