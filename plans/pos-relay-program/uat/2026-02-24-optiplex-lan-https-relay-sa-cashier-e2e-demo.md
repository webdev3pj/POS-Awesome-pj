# UAT - OptiPlex LAN HTTPS Relay SA + Cashier End-to-End Demo

## TL;DR (Business Owner)
- The local Edge Relay on the OptiPlex is now working for the real SA -> Cashier workflow on the dev site.
- SA creates a `Sales Order` token, the relay stores it locally, cashier retrieves it, and cashier submit goes to the relay first.
- The relay creates a local sale ID (`LSR-*`) and then syncs the real cloud Sales Invoice (`ACC-SINV-*`).
- We also demonstrated the relay UI pages in Cypress, including 20-second observation pauses on relay proof screens.

## Environment
- Date: `2026-02-24`
- Branch: `codex-3-edge-relay`
- Deployed app commit (dev site): `1c47d36` (with earlier same-session cashier/payment fixes `5522d5f`, `fcc719d`, `fd781cc`)
- Site: `https://devpjjamaica.v.frappe.cloud/`
- POS Profile: `PJ7 CASHIER`
- Relay host: OptiPlex (`192.168.50.168`)
- Relay LAN HTTPS URL: `https://192.168.50.168`
- Cypress mode: `watch mode / Chrome` (headed, terminal-driven wrapper)

## Baseline / Starting Point
- Baseline handoff commit used: `424c79a`
- Current handoff package commit referenced in runbook prompt: `2a3c6c7`
- Relay process startup method used: local OptiPlex relay (`relay/start_relay.bat` equivalent / running relay app on `:8787`) + Caddy reverse proxy (`https://192.168.50.168`)
- Shop PCs certificate trust completed on:
  - OptiPlex host: `Yes` (trusted locally)
  - Other shop PCs: `Pending rollout`

## Profile Configuration Used (`PJ7 CASHIER`)
- `custom_have_token = 1`
- `posa_allow_sales_order = 1`
- `custom_allow_select_sales_order = 1`
- `posa_sales_order_naming_series = SAL-ORD-PJ7-.YYYY.-`
- `posa_sales_order_lookup_max_age_days = 1`
- `custom_edge_relay_url = https://192.168.50.168`
- `posa_edge_relay_connectivity_mode = lan_only_browser_checked`
- `posa_allow_cloud_fallback_when_relay_down = 1`

## What Was Tested (Checklist)
- [x] Relay health reachable over LAN HTTPS (`https://192.168.50.168/health`)
- [x] SA flow with relay configured
- [x] Cashier `Select S.O` filtering still correct
- [x] Cashier relay-enabled submit path
- [x] Relay-down / cloud-up fallback prompt
- [x] Relay-down / cloud-down blocking behavior
- [x] `custom_have_token = 0` regression smoke
- [x] Relay UI demo in Cypress with 20-second observation pause (SA token proof and cashier transaction proof)

## What Passed
- Relay local health and APIs:
  - `/health` -> `ok: true`
  - `/api/outbox` -> counters/rows returned
  - `/api/transactions` -> local sales rows returned
  - `/queue` and `/api/queue` -> legacy queue UI/API reachable
- SA role flow:
  - SA created `Sales Order` token successfully in POS
  - Relay stored token and outbox `TOKEN_CREATED` event
- Cashier role flow:
  - Cashier retrieved SA-created SO via `Select S.O`
  - Payment modes displayed correctly from POS Profile (`Cash`, `Credit Card`, `Cheque`, `Bank Transfer`)
  - Cashier submit succeeded through relay-first path
  - Relay created local sale and synced cloud invoice
- Relay UI observability:
  - Dashboard `/` shows transaction timeline row and outbox counters
  - Transaction detail API shows local sale status + line detail + outbox event
  - Legacy `/queue` page UI update was demonstrated separately in Cypress using an injected legacy queue event

## What Failed
- No blocker in the final validated path.
- One historical (older test) outbox row remains queued from a legacy cloud endpoint path and should be treated as historical noise for demos:
  - `LSR-PJ7 -20260223063408-6D29F5` (`404` legacy sync error)

## Relay Status Behavior (Observed)
### Relay up / cloud up
- POS shows relay/cloud online status chips.
- Cashier submits to relay (`/relay/commit-invoice`) first.
- Relay stores local sale (`LSR-*`) and outbox event immediately.
- Relay sync worker submits to cloud and attaches `cloud_invoice_name`.

### Relay down / cloud up
- Prompt shown: `Yes` (validated by fallback watch spec)
- Cloud fallback worked?: `Yes` (cashier can proceed after explicit confirmation)

### Relay down / cloud down
- Correct block message shown?: `Yes` (validated by fallback watch spec)

## SA Flow Notes (Observed)
- Final demo SA order/token:
  - `Sales Order`: `SAL-ORD-PJ7-2026-00009`
  - Relay token id: `SAL-ORD-PJ7-2026-00009`
- Relay outbox recorded:
  - `event_type = TOKEN_CREATED`
  - `local_ref = SAL-ORD-PJ7-2026-00009`
  - `status = done`
- Relay token endpoint (after cashier payment) confirms token lifecycle:
  - `status = TOKEN_PAID`
  - `consumed_sale_ref = LSR-PJ7 -20260224200538-34917A`

## Cashier Flow Notes (Observed)
- Cashier loaded `SAL-ORD-PJ7-2026-00009` in `Select S.O`, moved to payment screen, and submitted.
- Final relay local sale created:
  - `local_sale_ref = LSR-PJ7 -20260224200538-34917A`
- Relay local sale status:
  - `sale_status = SALE_COMMITTED_LOCAL`
  - `pick_status = PAID_PENDING_PICK`
  - `dispatch_status = PENDING`
  - `cloud_sync_status = SALE_SYNCED_SI_SUBMITTED`
- Cloud invoice synced by relay:
  - `cloud_invoice_name = ACC-SINV-2026-00265`

## Monitor Rail Notes (Observed)
- POS `Order Monitor` remains visible and functional in SA/Cashier flows.
- Relay-specific proof for this UAT focused on relay dashboard/outbox/transaction detail rather than the ERPNext workflow monitor rail.

## Evidence / Artifacts
- Cypress specs run (headed watch mode / Chrome):
  - `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
  - `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
  - `cypress/e2e/sa_workflow_frontend_watch.cy.js`
  - `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
  - `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
  - `cypress/e2e/cashier_relay_down_cloud_fallback_watch.cy.js`
  - `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js`
  - relay demo/spec support:
    - `cypress/e2e/relay_demo_sa_post_ui_watch.cy.js` (20s pause)
    - `cypress/e2e/relay_demo_postrun_ui_watch.cy.js` (20s pause)
    - `cypress/e2e/relay_queue_ui_watch.cy.js` (legacy queue UI update proof)
    - `cypress/e2e/relay_dashboard_hold_20s_watch.cy.js`
  - Note: the relay demo helper specs above were local test helpers used during this OptiPlex validation session and may be committed separately from this docs/UAT update.
- Cypress screenshots (relay UI):
  - `cypress/screenshots/relay_demo_sa_post_ui_watch.cy.js/relay-demo-sa-post-token-json.png`
  - `cypress/screenshots/relay_demo_postrun_ui_watch.cy.js/relay-demo-postrun-dashboard-filtered.png`
  - `cypress/screenshots/relay_demo_postrun_ui_watch.cy.js/relay-demo-postrun-transaction-json.png`
  - `cypress/screenshots/relay_demo_postrun_ui_watch.cy.js/relay-demo-postrun-token-json.png`
  - `cypress/screenshots/relay_queue_ui_watch.cy.js/relay-queue-before-enqueue.png`
  - `cypress/screenshots/relay_queue_ui_watch.cy.js/relay-queue-after-enqueue.png`
  - `cypress/screenshots/relay_dashboard_hold_20s_watch.cy.js/relay-dashboard-hold-before.png`
  - `cypress/screenshots/relay_dashboard_hold_20s_watch.cy.js/relay-dashboard-hold-after-20s.png`
- Relay artifacts / temp evidence files:
  - `cypress/tmp/latest_sa_order.json`
  - `cypress/tmp/latest_cashier_relay_commit.json`
  - `cypress/tmp/latest_cashier_relay_commit_http.json`
  - `cypress/tmp/relay_demo_baseline_counts.json`

## Defects Found (and fixed in this validation cycle)
- Cashier payment screen missing payment modes for SO -> SI path when invoice returned without `payments` rows.
- Vue 2 non-reactive assignment prevented payment UI rerender after seeding payments.
- Cashier relay commit used wrong token/reference in SO -> SI path (truncated invoice suffix instead of full `SAL-ORD-*` token).
- Default/walk-in customer logic incorrectly blocked relay commit in some cases.

## Next Actions
- Commit/push the local Cypress relay-demo specs + cashier spec hardening if these test improvements should remain in branch history.
- Clean up/classify the historical legacy queued outbox row so relay demos are less confusing.
- Move to next milestone:
  - Phase 3 relay auth + server-side role enforcement
  - Picker/Dispatch relay-backed flow validation and Cypress coverage
  - shop-PC certificate trust rollout and deployment checklist execution

## Links
- `../CHANGELOG_PROGRESS.md`
- `../runbooks/optiplex-edge-relay-next-session.md`
- `../runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `../runbooks/shop-pc-lan-relay-setup-non-technical.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
