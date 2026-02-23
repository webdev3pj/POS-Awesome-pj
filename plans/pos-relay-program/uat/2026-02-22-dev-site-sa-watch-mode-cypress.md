# 2026-02-22 Dev Site SA Watch-Mode Cypress Run

## TL;DR (Business Owner)
- OTP login automation works on the live dev site, but the SA workflow spec still has intermittent OTP/login flake (test issue).
- The app-side SA workflow now works through Sales Order token creation and opens the Sales Order Token dialog.
- The ticket sidebar monitor rail is visible and updating, but the Cypress SA spec still needs stabilization to finish all rail assertions consistently.
- A real backend bug was found and fixed: SA Sales Order token items were missing `delivery_warehouse` (fixed in commit `ecfd053`).
- Preflight automation now sets `cline` to SA-only and validates/configures `PJ7 CASHIER` for token + Sales Order testing.
- Next step is Cypress spec hardening (login/session reuse + modal timing), then rerun and record final pass/fail on the monitor rail assertions.

## Environment
- Site: `https://devpjjamaica.v.frappe.cloud/`
- Branch: `kilo-codex-v3`
- Browser: `Chrome` (Cypress headed/watch-visible runs)
- Cypress commands used:
  - `npm.cmd run e2e:run -- --headed --browser chrome --spec cypress/e2e/admin_set_cline_sa_only_role.cy.js`
  - `npm.cmd run e2e:run -- --headed --browser chrome --spec cypress/e2e/sa_workflow_frontend_watch.cy.js`
- POS Profile under test: `PJ7 CASHIER`

## Branch + Commit + Deploy Confirmation
- Branch deployed: `kilo-codex-v3`
- Commits deployed during this test cycle:
  - `172c149` (opening dialog translation hotfix)
  - `9a89012` (role fixtures)
  - `ecfd053` (SA token delivery warehouse fix)
- Deploy confirmation: user-confirmed redeploys during iterative test cycle
- Migrate/restart completed: `Not explicitly confirmed each time` (site behavior indicates code updates took effect)

## Role Setup Used
- Test user: `cline`
- Operational `cline-*` role setup during test:
  - `cline-Sales Associate`: `Enabled by Cypress preflight`
  - Other `cline-*` roles: `Disabled by Cypress preflight`
- Non-operational/admin roles preserved: `Yes`

## Scope of This Run
- SA login + OTP
- SA POS entry (no cash opening shift for SA)
- SA token creation (`Sales Order`, not `Sales Invoice`)
- Token dialog/slip visibility
- Ticket sidebar counter + expanded monitor rail row
- SA blocked actions (payment / cashier cash controls)

## What Passed
- `cypress/e2e/frappe_login_otp.cy.js` (earlier in same test cycle)
  - Login + OTP automation succeeded.
  - Cypress reached Frappe Desk/home successfully.
- `cypress/e2e/admin_set_cline_sa_only_role.cy.js` (local improved version; not pushed yet)
  - Resolved `cline-Sales Associate` from installed role fixtures.
  - Set `cline` to SA-only among `cline-*` roles.
  - Verified/updated `PJ7 CASHIER` flags:
    - `custom_have_token = 1`
    - `posa_allow_sales_order = 1`
    - `custom_allow_select_sales_order = 1`
  - Verified required POS Profile basics (company, warehouse, selling price list, payment rows).
  - Verified backend `get_items(...)` returns items for `PJ7 CASHIER`.
- `cypress/e2e/sa_workflow_frontend_watch.cy.js` now reaches and verifies substantial app behavior:
  - SA no-cash session dialog appears with role label
  - SA session starts without opening cash amounts
  - items load in POS
  - SA adds item to cart
  - `Save/New` triggers SA Sales Order token creation
  - `Sales Order Token` dialog appears (with SO number / token / customer / SA / total)
  - print action is triggered (Cypress popup stub confirms `window.open` call)
  - monitor rail is present and visibly populated behind the token dialog in successful app runs

## What Failed (Current)
- `cypress/e2e/sa_workflow_frontend_watch.cy.js` final result still `FAIL` due to Cypress-spec instability, not a clear app regression:
  - intermittent OTP verification rejection (`Invalid Login. Try again.`) causing login flake in this spec
  - token dialog modal/print timing causing the rail visibility assertions to race against the still-open modal
  - selector/timing hardening is still in progress for the Frappe modal close path

## Watch-Mode Observations (What Was Seen Clicking)
- SA opening dialog shows `Role: Sales Associate` and no-cash session guidance.
- SA can submit the `Start POS Session` dialog without entering opening amounts.
- `PJ7 CASHIER` item list loads and item selection works.
- Token creation succeeded and the token dialog showed:
  - token last4 (large)
  - full SO number
  - customer
  - sales associate
  - date/time
  - grand total
- Order Monitor rail is visible in the left sidebar and shows pending orders/count in the background.
- Relay warnings were visible (`Relay Not Configured` / offline continuity unavailable) but did not block SA token creation.

## Screenshots / Cypress Artifacts
- Cypress screenshots include evidence of:
  - token dialog displayed successfully
  - monitor rail visible behind token dialog
  - intermediate test failures (OTP flake / modal-close timing)
- Screenshot paths (examples):
  - `cypress/screenshots/sa_workflow_frontend_watch.cy.js/... (failed).png`
  - `cypress/screenshots/admin_set_cline_sa_only_role.cy.js/... (failed or passed reruns may not create screenshot)`

## Data Verification (ERPNext / POS)
- Sales Order created: `Yes` (observed via token dialog in multiple reruns)
- Sales Invoice created at SA step (should be No): `No` (SA flow stops at token creation dialog; payment not used)
- SO owner = SA (`cline`): `Expected but not directly desk-verified in this run`
- Workflow state row exists with `business_date` + timing fields: `Monitor board API responses and visible rail rows indicate state rows exist`; direct DocType inspection not completed in this run
- Monitor row status on create (expected `Unpaid`): `Observed in rail UI`

## Defects Found
- Fixed in code during this cycle: SA `Sales Order` token items missing `delivery_warehouse`, causing ERPNext validation error `Delivery warehouse required for stock item ...`.
  - Fix commit: `ecfd053`
- Remaining issue is test automation reliability (Cypress spec):
  - intermittent OTP retry/login flake in `sa_workflow_frontend_watch.cy.js`
  - token dialog close/print timing needs cleaner post-print handling before rail assertions
- Previously fixed in code this cycle:
  - opening dialog API translation typo (`NameError: '_' is not defined`) fixed in `172c149`

## Next Actions
1. Stabilize `cypress/e2e/sa_workflow_frontend_watch.cy.js` login by reusing deterministic authenticated session setup (or `cy.session`).
2. Simplify token-dialog handling in the spec: assert dialog content, then close explicitly without depending on print-side effects.
3. Rerun SA spec and complete rail assertions (`Order Monitor`, `Mine` filter, row fields).
4. Push local Cypress spec improvements + updated docs to GitHub after the spec is stable.

## Links
- `../phases/phase-1-sa-sales-order-token-online-first.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
