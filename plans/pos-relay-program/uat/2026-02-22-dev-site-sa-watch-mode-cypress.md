# 2026-02-22 Dev Site SA Watch-Mode Cypress Run

## TL;DR (Business Owner)
- Cypress login + OTP automation works on the live dev site.
- SA workflow test is currently blocked because the site has **no `cline-*` roles installed** (the app correctly shows “User has no assigned role”).
- The preflight Cypress role-setting spec cannot assign SA role because the `cline-Sales Associate` role document does not exist on the site.
- The deployed POS opening dialog API error (`NameError: '_' is not defined`) was identified and fixed in code (`172c149`), then redeployed before this run.
- Next step is environment/data setup: ensure role fixtures/migrations create the `cline-*` roles on the dev site, then rerun the SA workflow test.

## Environment
- Site: `https://devpjjamaica.v.frappe.cloud/`
- Branch: `kilo-codex-v3`
- Browser: `Chrome` (Cypress watch mode / interactive)
- Cypress command: `npm.cmd run e2e:open`
- POS Profile under test: `PJ7 CASHIER`

## Branch + Commit + Deploy Confirmation
- Branch deployed: `kilo-codex-v3`
- Commit deployed: `172c149` (user-confirmed redeploy before rerun)
- Deploy confirmation timestamp: `2026-02-22` (exact time not recorded)
- Migrate/restart completed: `Unknown / not explicitly confirmed`

## Role Setup Used
- Test user: `cline`
- Operational `cline-*` role setup during test:
  - `cline-Sales Associate`: `Not possible (role document missing on site)`
  - Other `cline-*` roles disabled during test: `Not possible (no cline-* roles found)`
- Non-operational/admin roles preserved: `Not modified (preflight blocked before save)`

## Scope of This Run
- SA login + OTP
- SA POS entry (no cash opening shift for SA)
- SA token creation (`Sales Order`, not `Sales Invoice`)
- Token dialog/slip visibility
- Ticket sidebar counter + expanded monitor rail row
- SA blocked actions (payment / cashier cash controls)

## What Passed
- `cypress/e2e/frappe_login_otp.cy.js`
  - Login + OTP automation succeeded.
  - Cypress reached Frappe Desk/home successfully.
- Cypress headed Chrome runs were executed successfully from local machine (visible browser session).

## What Failed
- `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
  - Failed with explicit precondition error:
  - `No Sales Associate cline role exists on this site. Available cline-* roles: (none)`
- `cypress/e2e/sa_workflow_frontend_watch.cy.js`
  - Failed at the opening dialog role assertion (`Role:` not found).
  - UI showed backend message:
  - `User has no assigned role. Please contact admin to assign a role...`
  - Because no role exists, SA-specific mode and SA flow assertions cannot proceed.

## Watch-Mode Observations (What Was Seen Clicking)
- Login visibly completed with OTP automation and landed on Desk.
- Opening POS (`/app/posapp`) showed the opening dialog.
- Dialog displayed a red warning banner indicating no assigned role.
- Dialog still showed cashier-style opening amount table (expected when no derived role is available).
- SA-specific role label (`Role: Sales Associate`) did not appear because the site returned no role.

## Screenshots / Cypress Artifacts
- Cypress screenshots:
  - `cypress/screenshots/admin_set_cline_sa_only_role.cy.js/... (failed).png`
  - `cypress/screenshots/sa_workflow_frontend_watch.cy.js/... (failed).png`
- Cypress videos (if enabled): `TBD`
- Manual screenshots/notes: Cypress headed Chrome windows were visible during execution.

## Data Verification (ERPNext / POS)
- Sales Order created: `No (SA flow blocked before token creation)`
- Sales Invoice created at SA step (should be No): `No test execution reached this step`
- SO owner = SA (`cline`): `Not tested (no SO created)`
- Workflow state row exists with `business_date` + timing fields: `Not tested (no SO created)`
- Monitor row status on create (expected `Unpaid`): `Not tested (no SO created)`

## Defects Found
- Environment/config blocker: `cline-*` roles are missing entirely on the dev site (fixtures/migrations not present or not applied).
- Functional blocker for SA UAT: without `cline-Sales Associate`, the SA no-cash session path cannot be exercised.
- Previously found and fixed in code: opening dialog API translation typo causing `NameError: '_' is not defined` (fixed in `172c149`).

## Next Actions
1. Ensure `cline-*` role fixtures exist on the dev site (`cline-Sales Associate`, `cline-Cashier`, `cline-Picker`, `cline-Dispatch`, `cline-Supervisor`) and rerun migrate if needed.
2. Rerun `cypress/e2e/admin_set_cline_sa_only_role.cy.js` to set `cline` to SA-only among operational roles.
3. Rerun `cypress/e2e/sa_workflow_frontend_watch.cy.js` and continue SA flow verification (token creation + ticket rail).

## Links
- `../phases/phase-1-sa-sales-order-token-online-first.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
