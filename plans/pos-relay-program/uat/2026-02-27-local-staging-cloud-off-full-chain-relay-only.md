# UAT - Local Staging Cloud-Off Full-Chain (Relay-Only Evidence)

- Date: 2026-02-27
- Branch: `codex-5-final`
- Repo path: `C:\vs code repos\POS-Awesome-pj`
- Local staging base URL: `http://pj.local:8080/`
- Relay URL: `http://127.0.0.1:8787`
- Goal: prove SA -> Cashier -> Picker -> Dispatch continuity with cloud unavailable, using relay evidence as source of truth.

## Cloud-Off Simulation Setup
- Backed up relay config: `cypress/tmp/relay_config.pre_cloud_off_uat.json`
- Temporary relay cloud target set to unreachable endpoint:
  - `frappe_base_url = http://10.255.255.1:65534`
  - `site_name = cloud-off-sim`
- Verified relay remained online:
  - `GET /health` returned `ok: true` and reflected unreachable `frappe_base_url`.

## Cypress Execution Mode
- Headed watch-mode wrapper (`--once`) with strict timeout:
  - `scripts/cypress-gui-watch.cjs`
  - `CYPRESS_MAX_RUN_MS=720000`
  - `CYPRESS_POSTSPEC_SCAN=1`
  - `CYPRESS_baseUrl=http://pj.local:8080/`

## Spec Order and Results
1. `cypress/e2e/admin_set_cline_sa_only_role.cy.js` - pass
2. `cypress/e2e/local_staging/local_staging_sa_workflow_frontend_watch.cy.js` - pass
3. `cypress/e2e/local_staging/local_staging_relay_demo_sa_post_ui_watch.cy.js` - pass
4. `cypress/e2e/admin_set_cline_cashier_only_role.cy.js` - pass
5. `cypress/e2e/local_staging/local_staging_cashier_workflow_frontend_watch.cy.js` - pass
6. `cypress/e2e/local_staging/local_staging_relay_demo_cashier_post_ui_watch.cy.js` - pass
7. `cypress/e2e/admin_set_cline_picker_only_role.cy.js` - pass
8. `cypress/e2e/local_staging/local_staging_picker_workflow_frontend_watch.cy.js` - pass
9. `cypress/e2e/local_staging/local_staging_relay_demo_picker_post_ui_watch.cy.js` - pass
10. `cypress/e2e/admin_set_cline_dispatch_only_role.cy.js` - pass
11. `cypress/e2e/local_staging/local_staging_dispatch_workflow_frontend_watch.cy.js` - pass
12. `cypress/e2e/local_staging/local_staging_relay_demo_dispatch_post_ui_watch.cy.js` - pass

## Relay-Only Evidence (Single Chain)
- SA token/Sales Order:
  - `SAL-ORD-PJ7-2026-00015`
  - source artifact: `cypress/tmp/latest_sa_order.json`
- Cashier relay commit:
  - `local_sale_ref = LSR-PJ7 -20260227154400-600CB9`
  - `sale_status = SALE_COMMITTED_LOCAL`
  - `cloud_sync_status = SALE_SYNC_PENDING`
  - source artifact: `cypress/tmp/latest_cashier_relay_commit.json`
- Picker persisted state:
  - `pick_status = PICKED_READY_FOR_RELEASE`
  - `first_line_id = 22`
  - `picked_qty = 1`
  - source artifact: `cypress/tmp/latest_picker_update.json`
- Dispatch persisted state:
  - `dispatch_status = RELEASED`
  - `released_by = cline@pjjamaica.com`
  - source artifact: `cypress/tmp/latest_dispatch_release.json`

Transaction detail proof (`GET /api/transactions/<local_sale_ref>`) for `LSR-PJ7 -20260227154400-600CB9`:
- `sale_status = SALE_COMMITTED_LOCAL`
- `pick_status = PICKED_READY_FOR_RELEASE`
- `dispatch_status = RELEASED`
- `cloud_sync_status = SALE_SYNC_PENDING`
- `source_env = local_staging`
- pick events include:
  - `PICK_IN_PROGRESS`
  - `PICKED_READY_FOR_RELEASE`
- dispatch events include:
  - `RELEASED`

Outbox proof (`GET /api/outbox` filtered by local ref):
- `SALE_COMMITTED` row for this `LSR-*` is `queued` with cloud connect timeout against `10.255.255.1:65534`.
- `PICK_EVENT` and `RELEASE_EVENT` rows for this `LSR-*` are `queued` with expected cloud-wait errors.

Consolidated artifact:
- `cypress/tmp/local_staging_cloud_off_full_chain_evidence.json`

## Screenshots
- SA relay proof:
  - `cypress/screenshots/local_staging_relay_demo_sa_post_ui_watch.cy.js/relay-demo-sa-post-dashboard.png`
  - `cypress/screenshots/local_staging_relay_demo_sa_post_ui_watch.cy.js/relay-demo-sa-post-token-json.png`
- Picker relay proof:
  - `cypress/screenshots/local_staging_relay_demo_picker_post_ui_watch.cy.js/relay-demo-picker-post-dashboard-filtered.png`
  - `cypress/screenshots/local_staging_relay_demo_picker_post_ui_watch.cy.js/relay-demo-picker-post-transaction-json.png`
- Dispatch relay proof:
  - `cypress/screenshots/local_staging_relay_demo_dispatch_post_ui_watch.cy.js/relay-demo-dispatch-post-dashboard-filtered.png`
  - `cypress/screenshots/local_staging_relay_demo_dispatch_post_ui_watch.cy.js/relay-demo-dispatch-post-transaction-json.png`

## Post-Run Cleanup
- Restored relay config from backup (`cypress/tmp/relay_config.pre_cloud_off_uat.json`).
- Confirmed relay health returned to normal base URL:
  - `frappe_base_url = https://devpjjamaica.v.frappe.cloud`
  - `ok: true`

## Conclusion
- Dedicated local staging cloud-off full-chain continuity is verified.
- Next step is cloud dev staging replay of this exact chain and evidence model after deploy confirmation.
