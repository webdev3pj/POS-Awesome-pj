# UAT - Sales Order Age Policy (Cloud + Local)

- Date: 2026-03-01
- Branch: `codex-5-final`
- Base commit at test prep: `f8ce4d8`
- Scope:
  - profile-driven stale policy (`max age`, `allow stale`, `history days`)
  - consistency across:
    - cloud `search_orders(...)`
    - relay `/relay/tokens/search`
    - cashier selection UI
    - picker/dispatch stale visibility chips

## Implementation Covered
- Backend:
  - `posawesome/posawesome/api/posapp.py`
    - `search_orders(...)` now returns:
      - `order_age_days`
      - `is_stale`
      - stale policy metadata
- Relay:
  - `relay/relay/storage.py` `list_relay_tokens(...)` stale-policy support
  - `relay/relay/app.py` `/relay/tokens/search` stale-policy query params
- Frontend:
  - `SalesOrders.vue` stale chips + age column
  - `Invoice.vue` stale-policy args for cloud + relay lookup
  - `FulfillmentWorkspace.vue` stale warn-only chips in picker/dispatch detail and queue
- Cypress:
  - `cypress/e2e/cashier_sales_order_age_policy_watch.cy.js`
  - `cypress/e2e/fulfillment_stale_visibility_watch.cy.js`
  - local wrappers under `cypress/e2e/local_staging/`

## Execution Status
- Cloud run status: `Pending deploy`
- Local staging run status: `Pending deploy parity`
- Pre-deploy signal captured:
  - first cloud run of `cashier_sales_order_age_policy_watch.cy.js` fails on expected mismatch:
    - deployed cloud API response does not yet include `order_age_days` (indicates old server code)

## Run Commands (after deploy)
```powershell
$env:CYPRESS_MAX_RUN_MS='900000'
$env:CYPRESS_POSTSPEC_SCAN='1'
$env:CYPRESS_baseUrl='https://devpjjamaica.v.frappe.cloud/'
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/cashier_sales_order_age_policy_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/fulfillment_stale_visibility_watch.cy.js
```

```powershell
$env:CYPRESS_MAX_RUN_MS='900000'
$env:CYPRESS_POSTSPEC_SCAN='1'
$env:CYPRESS_baseUrl='http://pj.local:8080/'
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_cashier_sales_order_age_policy_watch.cy.js
npm.cmd run e2e:watch:gui:chrome -- --once --spec cypress/e2e/local_staging/local_staging_fulfillment_stale_visibility_watch.cy.js
```

## Pass Criteria
- Strict mode (`allow_stale=0`): stale SO excluded in cloud + relay search.
- Warn mode (`allow_stale=1`): stale SO included with `is_stale=1` and UI warning chips.
- Picker/Dispatch stale state visible without blocking fulfillment actions.
- Relay fallback returns stale metadata aligned with profile policy.

## Open Items
- Complete cloud deploy and execute the two cloud specs.
- Execute local staging wrappers after local deploy parity.
- Attach artifact JSON and screenshots after passing runs.
