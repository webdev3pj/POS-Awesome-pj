# UAT - Quotation Role / Validity / Reprice / Relay-Local Sync

- Date: 2026-03-01
- Branch: `codex-5-final`
- Base commit at test prep: `f8ce4d8`
- Scope:
  - role-aware quotation actions (SA/Cashier profile toggles)
  - quotation validity hard-stop
  - reprice preview + confirm on delta
  - relay-local create/search/convert when cloud unavailable
  - outbox sync (`QUOTE_UPSERT`) and idempotent cloud upsert behavior

## Implementation Covered
- Profile fields:
  - `posa_allow_sa_quotation`
  - `posa_allow_cashier_quotation`
  - `posa_quotation_validity_days`
- Cloud APIs (`posawesome/posawesome/api/posapp.py`):
  - `create_quotation_token`
  - `search_quotations`
  - `quotation_reprice_preview`
  - `convert_quotation_to_sales_order_token`
  - relay-sync idempotency key support via `Quotation.custom_relay_quote_id`
- Relay:
  - quote tables in `relay/relay/storage.py`:
    - `relay_quotes`
    - `relay_quote_lines`
  - quote endpoints in `relay/relay/app.py`
  - sync mapping in `relay/relay/sync_worker.py`:
    - `QUOTE_UPSERT`
    - cloud quote ref writeback (`set_local_quote_cloud_synced`)
- Frontend:
  - `Invoice.vue` quote actions + fallback behavior
  - `Quotations.vue` dialog (search, stale/expiry chips, reprice preview, convert)
  - `Pos.vue` dialog mount
- Cypress:
  - `quotation_role_visibility_watch.cy.js`
  - `quotation_create_reprice_convert_watch.cy.js`
  - `quotation_expiry_hard_stop_watch.cy.js`
  - `quotation_relay_local_offline_sync_watch.cy.js`
  - local wrappers under `cypress/e2e/local_staging/`

## Execution Status
- Cloud run status: `Pending deploy`
- Local staging run status: `Pending deploy parity`
- Pre-deploy signal:
  - branch compiles and fixtures parse, but cloud runtime tests must wait for deploy of this branch code.

## Run Commands (after deploy)
```powershell
$env:CYPRESS_MAX_RUN_MS='900000'
$env:CYPRESS_POSTSPEC_SCAN='1'
$env:CYPRESS_baseUrl='https://devpjjamaica.v.frappe.cloud/'
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/quotation_role_visibility_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/quotation_create_reprice_convert_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/quotation_expiry_hard_stop_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/quotation_relay_local_offline_sync_watch.cy.js
```

```powershell
$env:CYPRESS_MAX_RUN_MS='900000'
$env:CYPRESS_POSTSPEC_SCAN='1'
$env:CYPRESS_baseUrl='http://pj.local:8080/'
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_quotation_role_visibility_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_quotation_create_reprice_convert_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_quotation_expiry_hard_stop_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_quotation_relay_local_offline_sync_watch.cy.js
```

## Pass Criteria
- SA/Cashier quote actions respect profile toggles.
- Expired quotations cannot be converted.
- Reprice delta is shown and conversion requires explicit confirm.
- Relay-local quote conversion produces token and is visible in relay state.
- `QUOTE_UPSERT` sync does not create duplicate cloud quotations on retry.

## Open Items
- Complete cloud and local post-deploy executions.
- Attach real evidence IDs (`quote_name`, `token_id`, `local_sale_ref`, outbox event ids, cloud refs).
