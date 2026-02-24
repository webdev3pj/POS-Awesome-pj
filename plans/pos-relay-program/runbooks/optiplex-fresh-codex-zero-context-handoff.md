# OptiPlex Fresh Codex Zero-Context Handoff

## TL;DR (Business Owner)
- This is the handoff document for a brand-new Codex session on the OptiPlex with no prior chat context.
- It includes the exact branch, baseline commit, what is already working, what still needs to be built, and the exact order to work in.
- It also explains how to handle secrets safely: copy local `.env` and relay config files, but do not commit them.
- Main target (updated): build on the now-working relay-enabled SA + Cashier flow and the newly validated local-first Picker/Dispatch fulfillment flow (fix cloud sync parity, add auth hardening, finalize rollout support), or rerun demos/UAT after new changes.

## Current Branch / Baseline
- Working branch (current): `codex-4-picker-dispatch`
- GitHub baseline commit for this handoff: `424c79a`
- Baseline commit message: `docs(relay): clarify frappe cloud local-lan relay constraints`

## Important Historical Commits (Context, not rollback)
- `54ef47a` - cashier `Select S.O` lookup/profile fix + token-off regression test addition
- `c19798c` - POS Profile SO naming series + SO lookup max-age filtering
- `ecfd053` - SA SO token item `delivery_warehouse` fix
- `44880b9` - docs normalization (current vs historical labeling)
- `1c47d36` - cashier relay token derivation fix for SO -> SI path (critical relay commit fix)
- `5522d5f` - cashier payment modes render correctly in SO -> SI payment screen
- `224e842` - shared-shell picker/dispatch fulfillment workspace + relay line-wise picker payload persistence (current branch milestone)

## What Is Already Working (Verified)
- SA flow on live dev site:
  - no-cash SA session entry
  - SA creates submitted `Sales Order` token
  - token dialog/print path
  - workflow monitor rail visibility
- Cashier flow on live dev site:
  - `Select S.O` filtering by POS Profile SO naming series + age
  - loading SA-created SO into cashier payment screen
  - payment mode rows render from POS Profile (Cash/Credit Card/Cheque/Bank Transfer)
- POS Profile SO naming series and max-age config fields exist and are in use.
- Cypress watch-mode automation exists for:
  - login + OTP
  - role switching (`cline`)
  - POS Profile preflight/config
  - SA flow
  - cashier flow
  - relay-down/cloud-fallback flow
  - token-disabled regression
- Relay local acceptance tests and local HTTP smoke were run successfully.
- LAN-only relay mode (browser-LAN relay status as submit gate) is implemented.
- Cashier relay-down -> cloud fallback prompt (cloud-up case) is implemented and validated.
- OptiPlex LAN HTTPS relay (`https://192.168.50.168`) via Caddy is set up and validated locally.
- Full relay-enabled dev-site Cypress validation is complete:
  - SA creates SO token -> relay stores token/outbox event
  - cashier retrieves SO and submits via relay -> relay creates local sale (`LSR-*`) and syncs cloud SI (`ACC-SINV-*`)
- Business-owner relay UI demo (Cypress) was completed with 20-second observation pauses on:
  - relay token detail (after SA submit)
  - relay transaction detail (after cashier submit)
- Picker/Dispatch shared-shell local-first flow is now live-validated on `codex-4-picker-dispatch` (OptiPlex + dev site):
  - Picker opens fulfillment workspace, edits line-wise `picked_qty`, and relay persists `payload.picker` with UOM/conversion data
  - Picker marks sale `PICKED_READY_FOR_RELEASE`
  - Dispatch releases the same sale and relay sets `dispatch_status = RELEASED`
  - Released sale drops out of relay pick queue

## What Is Not Finished (Next Build Targets)
- Cloud backend parity for relay fulfillment sync endpoints:
  - `update_relay_picking_status` (`PICK_EVENT`) currently returns `500`
  - `release_relay_dispatch` (`RELEASE_EVENT`) currently returns `500`
- Phase 3 relay auth for mutating endpoints
- Server-side relay role authorization (do not trust browser localStorage role)
- Commit/push picker/dispatch Cypress helper specs (used locally for UAT but not yet committed)
- Shop-PC certificate trust rollout on non-OptiPlex devices (SA/Cashier/Picker/Dispatch PCs)
- Cleanup/classification of one historical legacy queued outbox failure row (older smoke-test artifact)

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

Work only on branch codex-4-picker-dispatch (unless explicitly told to hotfix an older branch).
Baseline GitHub commit for this handoff is 424c79a (historical relay LAN-only baseline reference).

Current verified status:
- SA flow works on the dev site (SO token + monitor rail)
- Cashier Select S.O filtering by naming series + age works
- Local relay acceptance + HTTP smoke passed
- LAN-only relay mode + cloud fallback are implemented
- Relay-enabled SA + Cashier flow has been proven live against the OptiPlex relay (LAN HTTPS)
- Shared-shell Picker/Dispatch local-first flow has been proven live against the OptiPlex relay
  - picker line-wise qty persistence (`payload.picker`)
  - dispatch release local relay state
  - cloud fulfillment sync endpoints still return 500 in dev backend

Choose one session target (based on task):
1) Start and verify local Edge Relay on this OptiPlex
2) If validating a new change: rerun Cypress in watch mode (Chrome) for SA + Cashier + relay fallback tests
3) If business demo is needed: run the relay demo sequence (includes relay UI pauses)
4) Work next milestone items: fix picker/dispatch cloud sync endpoints, then relay auth/server-side role enforcement
5) Update docs/UAT and push changes

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
- `custom_edge_relay_url = https://192.168.50.168`
- `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
- `posa_allow_cloud_fallback_when_relay_down = 1`

## Implementation Priorities (Updated)
### Completed in this branch cycle
- LAN-only relay mode + browser-LAN submit gating
- Relay-down -> cloud fallback prompt/toggle
- OptiPlex LAN HTTPS (Caddy) + shop-PC cert installer guidance
- Relay-enabled SA/Cashier live Cypress validation and relay UI demonstration
- Shared-shell Picker/Dispatch fulfillment workspace deployed and relay-local UAT validated (line-wise pick persistence + dispatch release)

### Next priorities
1. Fix cloud backend fulfillment relay sync endpoints (`update_relay_picking_status`, `release_relay_dispatch`)
2. Relay auth and server-side role enforcement (Phase 3)
3. Commit/reuse picker/dispatch Cypress specs for repeatable UAT
4. Rollout/ops hardening (shop PC trust rollout, support checklists, historical queue cleanup)

## Cypress Run Order (Watch Mode, Chrome)
Run from repo root:
```powershell
Set-Location 'I:\vscode repos\POS-Awesome-pj'
npm.cmd run e2e:open
```

Spec order (core regression):
1. `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
2. `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
3. `cypress/e2e/sa_workflow_frontend_watch.cy.js`
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
5. `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
6. `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js`
7. `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js`

Relay visual demo add-on (optional, local relay pages in Cypress):
1. Show relay token proof page after SA submit (`/relay/token/<SO token>`) and pause for observation (manual or local demo spec, if present)
2. Show relay transaction proof page after cashier submit (`/api/transactions/<local_sale_ref>` or dashboard `/` filtered to local sale) and pause for observation (manual or local demo spec, if present)

## What to Update and Push After the OptiPlex Session
- `plans/pos-relay-program/CHANGELOG_PROGRESS.md`
- `plans/pos-relay-program/00-ai-agent-start-here.md`
- `plans/pos-relay-program/03-offline-edge-relay-and-windows-service-spec.md`
- `plans/pos-relay-program/runbooks/optiplex-edge-relay-next-session.md`
- `plans/pos-relay-program/runbooks/shop-pc-lan-relay-setup-non-technical.md`
- `plans/pos-relay-program/uat/<date>-*.md`
- relevant phase docs touched by actual implementation/testing

## See Also
- `optiplex-edge-relay-next-session.md`
- `shop-pc-lan-relay-setup-non-technical.md`
- `../00-ai-agent-start-here.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
