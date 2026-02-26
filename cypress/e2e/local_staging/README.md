## Local Staging Cypress Specs (`pj.local:8080`)

These specs are wrappers or local-only flows intended to be run with:

- `CYPRESS_baseUrl=http://pj.local:8080/`

They are kept separate so local staging validation is easy to spot in the repo and can be run before cloud deploy loops.

Primary intent:
- fast local parity checks on `pj.local:8080`
- local-only SA -> Cashier -> Picker -> Dispatch validation before cloud deploy
- local runtime/browser module error detection (the suite now captures browser runtime events and fails fast on severe local module/script load errors)

Recommended local end-to-end order:
1. `local_staging_parity_smoke_watch.cy.js`
2. `admin_set_cline_sa_only_role.cy.js`
3. `local_staging_sa_workflow_frontend_watch.cy.js`
4. `admin_set_cline_cashier_only_role.cy.js`
5. `local_staging_cashier_workflow_frontend_watch.cy.js`
6. `admin_set_cline_picker_only_role.cy.js`
7. `local_staging_picker_workflow_frontend_watch.cy.js`
8. `admin_set_cline_dispatch_only_role.cy.js`
9. `local_staging_dispatch_workflow_frontend_watch.cy.js`
10. `admin_set_cline_supervisor_only_role.cy.js` (optional)
11. `local_staging_supervisor_fulfillment_exception_watch.cy.js` (optional)
12. `local_staging_phase3_security_relay_role_guards_watch.cy.js`

Recommended runner (strict timeout + post-spec scan):

```powershell
$env:CYPRESS_baseUrl='http://pj.local:8080/'
$env:CYPRESS_MAX_RUN_MS='720000'
$env:CYPRESS_POSTSPEC_SCAN='1'
& 'C:\Program Files\nodejs\node.exe' scripts/run-cypress.cjs run --headed --runner-ui --browser chrome --spec cypress/e2e/local_staging/<spec>.cy.js
```
