# OptiPlex Fresh Codex Zero-Context Handoff

## TL;DR (Business Owner)
- This is the handoff document for a brand-new Codex session on the OptiPlex with no prior chat context.
- It includes the exact branch, baseline commit, what is already working, what still needs to be built, and the exact order to work in.
- It also explains how to handle secrets safely: copy local `.env` and relay config files, but do not commit them.
- Main target: make relay-enabled SA + Cashier work on LAN-only mode with correct status checking and cloud fallback when relay is down.

## Current Branch / Baseline
- Working branch: `codex-3-edge-relay`
- GitHub baseline commit for this handoff: `424c79a`
- Baseline commit message: `docs(relay): clarify frappe cloud local-lan relay constraints`

## Important Historical Commits (Context, not rollback)
- `54ef47a` - cashier `Select S.O` lookup/profile fix + token-off regression test addition
- `c19798c` - POS Profile SO naming series + SO lookup max-age filtering
- `ecfd053` - SA SO token item `delivery_warehouse` fix
- `44880b9` - docs normalization (current vs historical labeling)

## What Is Already Working (Verified)
- SA flow on live dev site:
  - no-cash SA session entry
  - SA creates submitted `Sales Order` token
  - token dialog/print path
  - workflow monitor rail visibility
- Cashier flow on live dev site:
  - `Select S.O` filtering by POS Profile SO naming series + age
  - loading SA-created SO into cashier payment screen
- POS Profile SO naming series and max-age config fields exist and are in use.
- Cypress watch-mode automation exists for:
  - login + OTP
  - role switching (`cline`)
  - POS Profile preflight/config
  - SA flow
  - cashier flow
  - token-disabled regression
- Relay local acceptance tests and local HTTP smoke were run successfully.

## What Is Not Finished (Tomorrow’s Build Target)
- LAN-only relay mode (browser-LAN relay status should be the real submit gate)
- Relay-down -> cloud fallback prompt (when cloud is up)
- OptiPlex HTTPS reverse proxy automation (Caddy on Windows)
- One-time shop-PC certificate trust scripts and non-technical guide
- Relay-enabled live Cypress validation for SA + Cashier on the dev site using the real OptiPlex relay

## Non-Negotiable Security Rule (Read First)
- Do **not** put passwords, OTP URIs, API keys, or relay secrets into Git commits/docs.
- Use a two-layer setup:
  - GitHub docs (safe, no secrets)
  - local-only secrets files copied to the OptiPlex

## Local-Only Secrets Pack (What must exist on the OptiPlex)
### 1. Cypress secrets (`.env` in repo root)
File (local only, do not commit):
- `I:\vscode repos\POS-Awesome-pj\.env`

Exact env vars required by `cypress.config.cjs`:
```dotenv
CYPRESS_baseUrl=
CYPRESS_username=
CYPRESS_password=
CYPRESS_totpUri=
```

Action:
- Copy the existing `.env` from the main machine to the OptiPlex repo root.

### 2. Relay runtime config (local relay UI writes this)
File (local only, do not commit):
- `relay/data/relay_config.json`

Key values expected (written by relay setup UI):
- `frappe_base_url`
- `api_key`
- `api_secret`
- `relay_host`
- `relay_port`
- `public_base_url`
- `site_name`
- `offline_mode`
- `poll_seconds`
- `allowed_subnet`

Action:
- Prefer configuring via relay setup UI on the OptiPlex instead of hand-editing JSON.

### 3. Optional relay process secret
Optional env var:
- `RELAY_SECRET`

Notes:
- If unset, relay uses default `pos-relay-secret`.
- If used, keep it local-only (Windows env var or local ignored file).

## Exact Starter Prompt for Codex on the OptiPlex (Copy/Paste)
```text
Open and follow this file first:
plans/pos-relay-program/runbooks/optiplex-edge-relay-next-session.md

Then open:
plans/pos-relay-program/runbooks/optiplex-fresh-codex-zero-context-handoff.md

Work only on branch codex-3-edge-relay.
Baseline GitHub commit for this handoff is 424c79a.

Current verified status:
- SA flow works on the dev site (SO token + monitor rail)
- Cashier Select S.O filtering by naming series + age works
- Local relay acceptance + HTTP smoke passed

Build target for this session:
1) Start and verify local Edge Relay on this OptiPlex
2) Add LAN-only relay mode support (browser-LAN relay status is submit gate)
3) Add cashier prompt fallback to cloud when relay is down but cloud is up
4) Add Caddy-based LAN HTTPS reverse proxy automation on Windows
5) Add one-time shop-PC certificate trust scripts + non-technical guide
6) Configure PJ7 CASHIER for LAN-only relay mode
7) Run Cypress in watch mode (Chrome) for SA + Cashier + relay fallback tests
8) Update docs/UAT and push changes

Security:
- Do not commit .env, OTP URI, passwords, relay API secrets, or relay local config.
- Copy the local .env from the main machine if needed.

Repo hygiene:
- Do not touch unrelated local changes unless explicitly asked.
- Keep docs labeled Current vs Historical.
```

## Frappe Cloud `PJ7 CASHIER` Profile (Relay Pilot Target Config)
Set/verify on the dev site:
- `custom_have_token = 1`
- `posa_allow_sales_order = 1`
- `custom_allow_select_sales_order = 1`
- `posa_sales_order_naming_series = SAL-ORD-PJ7-.YYYY.-`
- `posa_sales_order_lookup_max_age_days = 1`
- `custom_edge_relay_url = https://192.168.50.168` (target LAN HTTPS URL after Caddy setup)

Planned new fields to implement/configure:
- `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
- `posa_allow_cloud_fallback_when_relay_down = 1`

## Implementation Priorities (Decision Complete)
### 1. LAN-only relay mode
- Add POS Profile mode field (`cloud_checked` / `lan_only_browser_checked`)
- Expand relay status API response (cloud diagnostics + mode metadata)
- Add browser relay `/health` checks in `Navbar.vue`
- Use effective relay status in `Payments.vue` submit gating

### 2. Relay-down -> cloud fallback
- Add POS Profile toggle `posa_allow_cloud_fallback_when_relay_down`
- Emit/consume `cloud_status_changed`
- Prompt cashier and submit to cloud on confirmation when relay is down but cloud is up
- Keep workflow monitor updated via ERPNext workflow state (no relay backfill in this phase)

### 3. OptiPlex LAN HTTPS
- Add `relay/windows_https/` scripts for Caddy setup, cert export, autostart, and shop-PC cert installation
- Use `https://192.168.50.168` as target LAN URL
- Keep relay Flask on `http://127.0.0.1:8787`

## Cypress Run Order (Watch Mode, Chrome)
Run from repo root:
```powershell
Set-Location 'I:\vscode repos\POS-Awesome-pj'
npm.cmd run e2e:open
```

Spec order:
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
5. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
6. `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js` *(to add)*
7. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js`

## What to Update and Push After the OptiPlex Session
- `plans/pos-relay-program/CHANGELOG_PROGRESS.md`
- `plans/pos-relay-program/00-ai-agent-start-here.md`
- `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
- `plans/pos-relay-program/uat/<date>-lan-only-relay-enabled-sa-cashier.md`
- relevant phase docs (`phase-0`, `phase-2`, and phase docs touched by actual implementation)

## See Also
- `optiplex-edge-relay-next-session.md`
- `shop-pc-lan-relay-setup-non-technical.md`
- `../00-ai-agent-start-here.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
