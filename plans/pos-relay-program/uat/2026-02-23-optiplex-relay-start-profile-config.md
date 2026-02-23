# 2026-02-23 OptiPlex Relay Start + PJ7 CASHIER Relay URL Config (codex-3-edge-relay)

## TL;DR (Business Owner)
- The Edge Relay is now running locally on the OptiPlex and responding on port `8787`.
- `PJ7 CASHIER` on the dev site is configured to use the OptiPlex LAN relay URL (`http://192.168.50.168:8787`).
- Relay local commit behavior was validated on the live local relay process (including idempotent replay and `local_sale_ref` generation).
- The headed Chrome Cypress SA + Cashier relay-enabled run is still pending because it must be executed from the main machine (watch mode) with UI login credentials/OTP.

## Scope (This Session)
- OptiPlex relay-host startup and local verification
- Dev-site POS Profile relay URL configuration (`PJ7 CASHIER`)
- Local relay commit smoke on the running relay process
- Documentation update / handoff prep for the main-machine Cypress run

## Environment
- Repo: `POS-Awesome-pj`
- Branch: `codex-3-edge-relay`
- Host: OptiPlex (Windows)
- Relay bind: `0.0.0.0:8787`
- Relay LAN URL used for POS browser testing: `http://192.168.50.168:8787`
- Dev site: `https://devpjjamaica.v.frappe.cloud/`

## What Was Done
### 1. Started local Edge Relay on the OptiPlex (`PASS`)
- Created relay venv: `relay/.venv`
- Installed `relay/requirements.txt`
- Ran self-test:
  - `python -m relay.selftest` -> `SELFTEST_OK`
- Started relay app (`python -m relay.app`) and confirmed the process was listening on port `8787`

### 2. Verified local relay health / queue / outbox (`PASS`)
- `GET /health` returned JSON with `ok: true`
- `GET /api/outbox` returned JSON counts/rows
- `GET /` returned HTTP `200`
- `GET /queue` returned HTTP `200`

Observed initial local status:
- queue counts: empty
- outbox counts: empty

### 3. Configured relay runtime for dev site (`PASS`)
Configured relay setup with:
- `frappe_base_url = https://devpjjamaica.v.frappe.cloud`
- API token auth (user-provided API key/secret; not reproduced here)
- `public_base_url = http://192.168.50.168:8787`
- `relay_host = 0.0.0.0`
- `relay_port = 8787`
- `allowed_subnet = 192.168.50.0/24`

Verified via `GET /health`:
- `frappe_base_url` persisted
- `public_base_url` persisted
- relay host/port/subnet values correct

### 4. Verified dev-site API token auth (`PASS`)
- Confirmed Frappe API token authentication against the dev site using:
  - `frappe.auth.get_logged_user`
- Token was able to read and update `POS Profile` documents (sufficient for relay URL/profile preflight config)

### 5. Updated `PJ7 CASHIER` POS Profile relay URL (`PASS`)
Updated on dev site:
- `custom_edge_relay_url = http://192.168.50.168:8787`

Also verified/confirmed current relay-test profile fields:
- `custom_have_token = 1` (re-enabled in this session; it was `0` at start)
- `posa_allow_sales_order = 1`
- `custom_allow_select_sales_order = 1`
- `posa_sales_order_naming_series = SAL-ORD-PJ7-.YYYY.-`
- `posa_sales_order_lookup_max_age_days = 1`

Note:
- `custom_have_token` being `0` at session start would have blocked relay token-mode behavior in the POS. This was corrected.

### 6. Local relay commit smoke on the running relay process (`PASS`)
Executed against the live local relay service (not unit-test client):
- `POST /relay/session/open`
- `POST /relay/token/create`
- `POST /relay/commit-invoice`
- Replayed the same `POST /relay/commit-invoice` with the same `idempotency_key`

Verified:
- first commit succeeded and returned a `local_sale_ref`
- replay returned `idempotent_replay = true`
- replay returned the same `local_sale_ref`
- `GET /relay/pick-queue` shows queued work after commit
- `GET /api/outbox` shows `SESSION_OPEN`, `TOKEN_CREATED`, and `SALE_COMMITTED` events queued

Local transaction verification:
- `sale_status = SALE_COMMITTED_LOCAL`
- `cloud_sync_status = SALE_SYNC_PENDING`
- `paid = 1`
- Example `local_sale_ref` observed in this session:
  - `LSR-PJ7 -20260223063408-6D29F5`
  - Note: current formatter preserves a space after `PJ7` (from the POS Profile identifier); behavior observed and documented, not changed in this session.

## Relay URL for Dev Site / POS Browser
Use this LAN URL for the current OptiPlex relay session:
- `http://192.168.50.168:8787`

If the POS browser runs on a different machine on the same LAN:
- this URL should be used in `PJ7 CASHIER.custom_edge_relay_url`

If backend/cloud-side relay reachability checks must pass from ERPNext/Frappe Cloud:
- use a public/tunnel URL instead of a LAN URL
- update both:
  - relay `public_base_url`
  - `PJ7 CASHIER.custom_edge_relay_url`

## What Is Not Yet Proven in This Session
- Headed Chrome Cypress watch-mode SA + Cashier flow against the live dev site with relay enabled
- Real browser-driven cashier submit reaching relay commit path and emitting a `local_sale_ref` in the live POS UI
- Backend/cloud reachability from ERPNext to relay via public/tunnel URL (LAN URL only configured in this session)

## Blocker / Handoff Note (Main Machine Cypress Run)
The runbook requires the headed watch-mode run from the main machine. This OptiPlex session did not have the UI login credentials / OTP environment (`CYPRESS_username`, `CYPRESS_password`, `CYPRESS_totpUri`) needed to execute the existing Cypress specs here.

Run from the main machine while this OptiPlex relay remains running:
```powershell
Set-Location 'I:\vscode repos\POS-Awesome-pj'
npm.cmd run e2e:open
```
Choose `Chrome`, then run in this order:
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
5. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
6. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js` (regression; will likely flip token mode and restore)

Important for this relay-enabled run:
- verify `PJ7 CASHIER.custom_edge_relay_url` still points to the OptiPlex LAN URL before starting
- after the final regression spec, confirm `custom_have_token` is restored to `1` if continuing relay tests

## Suggested Evidence to Capture in the Main-Machine Run
- POS banners/chips showing relay reachable (or relay status changes)
- Cashier submit result path when relay is enabled
- Relay dashboard `/` and `/api/outbox` before/after cashier submit
- `local_sale_ref` shown in POS UI and/or relay transaction list
- Any relay-side logs/errors if browser submit fails

## Links
- `../CHANGELOG_PROGRESS.md`
- `../runbooks/optiplex-edge-relay-next-session.md`
- `../00-ai-agent-start-here.md`
- `./2026-02-23-local-edge-relay-smoke.md`
- `./2026-02-23-dev-site-cashier-watch-mode-cypress.md`
