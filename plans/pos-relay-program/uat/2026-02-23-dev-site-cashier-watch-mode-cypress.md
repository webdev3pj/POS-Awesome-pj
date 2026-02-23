# 2026-02-23 Dev Site Cashier Watch-Mode Cypress Run

## TL;DR (Business Owner)
- Cashier `Select S.O` filtering is now working for `PJ7 CASHIER` using the POS Profile Sales Order naming series and age limit.
- We fixed the real cashier bug: the cashier order lookup was not sending `pos_profile`, so wholesale orders appeared.
- Sales Associate can create a fresh Sales Order token, and Cashier can pick it up in `Select S.O` and continue into the payment screen.
- Cashier flow now reaches payment submit and the expected validation/submit guard stage on your live site.
- A new regression test confirms POS still works when `custom_have_token` is turned off on the POS Profile (and restores the setting after the test).
- Relay is still not configured on the profile, so full relay-backed submit success is not proven in this run.

## Environment
- Site: `https://devpjjamaica.v.frappe.cloud/`
- Branch: `codex-2-cashier`
- Browser: `Chrome` (Cypress headed/watch-visible runs)
- POS Profile under test: `PJ7 CASHIER`
- Test user: `cline`

## Branch + Commit + Deploy Confirmation
- Branch deployed: `codex-2-cashier`
- Key app commits under test:
  - `c19798c` - POS Profile SO series + Select S.O age filter feature
  - `54ef47a` - cashier `Select S.O` lookup fix (`pos_profile` passed + backend fallback) and token-disabled smoke test
- Deploy confirmation: user-confirmed deploys during the test cycle

## Role Setup Used
- `cline-Sales Associate` enabled for SA order creation step (via Cypress preflight)
- `cline-Cashier` enabled for cashier flow step (via Cypress preflight)
- Other `cline-*` operational roles disabled for each role-specific spec
- Non-operational/admin roles preserved

## Cypress Specs Run (Headed Chrome)
- `cypress/e2e/admin_configure_pj7_cashier_profile.cy.js`
- `cypress/e2e/admin_set_cline_sa_only_role.cy.js`
- `cypress/e2e/sa_workflow_frontend_watch.cy.js`
- `cypress/e2e/admin_set_cline_cashier_only_role.cy.js`
- `cypress/e2e/cashier_workflow_frontend_watch.cy.js`
- `cypress/e2e/cashier_token_disabled_profile_smoke.cy.js`

## What Passed
### POS Profile preflight (`PASS`)
- `PJ7 CASHIER` configured/verified with:
  - `posa_sales_order_naming_series = SAL-ORD-PJ7-.YYYY.-`
  - `posa_sales_order_lookup_max_age_days = 1`
  - token/SO flags enabled for token-mode tests (`custom_have_token = 1`, `posa_allow_sales_order = 1`, `custom_allow_select_sales_order = 1`)

### SA flow (`PASS`)
- SA role entry works
- SA creates a fresh Sales Order token
- Token dialog appears
- Monitor rail remains visible and updates

### Cashier role preflight (`PASS`)
- `cline` switched to Cashier-only among `cline-*`

### Cashier flow (`PASS` for current scope)
- Cashier opens/enters POS and reaches `Select S.O`
- `search_orders` request now includes `pos_profile`
- `Select S.O` list is filtered by:
  - `PJ7 CASHIER` Sales Order naming series (`SAL-ORD-PJ7-.YYYY.-`)
  - age limit (`1` day)
- Cashier can select the SA-created SO and load it into the invoice/payment screen
- Cashier reaches submit path and expected UI validation/submit guard behavior

### Token-disabled regression (`PASS`)
- New smoke test disables `custom_have_token` on `PJ7 CASHIER`
- Cashier POS still opens and reaches payment screen (non-token mode path not broken)
- Test restores `custom_have_token` to its original value afterward

## What Was Fixed (App vs Test)
### App fix (deployed)
- `54ef47a` fixed cashier order lookup path:
  - `Invoice.vue` now sends `pos_profile` to `search_orders`
  - backend `search_orders(...)` falls back to active open shift `pos_profile` if request omits it

### Cypress-only hardening (local during run)
- Cashier role preflight login hardened (OTP/login flake mitigation)
- Cashier SO row selection fixed in `Select S.O` dialog
- Cashier payment button selector fixed
- Cashier submit outcome assertions broadened to match live validation text
- Token-disabled smoke test cleanup hook fixed (restores profile flag without failing if already logged in)

## What Failed / Not Proven Yet
- Full cashier invoice submit success is not proven in this run because the POS Profile still shows relay warnings (`Relay Not Configured` / relay down banners).
- Picker, Dispatch, and Supervisor frontend flows are not covered in this cashier run.
- Relay-auth/server-side role enforcement remains a separate pending phase.

## Watch-Mode / Headed Observations
- `Select S.O` popup behavior is now correct enough for cashier workflow progression.
- Monitor rail stays visible during cashier payment flow and shows the pending order state.
- Cashier payment UI reached submit; one live run produced `The amount paid is not complete`, which is a normal business validation and confirms the flow reached the correct layer.

## Next Actions
1. Push Cypress script hardening + docs updates to GitHub (no app deploy required for docs/tests-only changes).
2. If relay submit success must be proven, configure a valid Edge Relay URL (or disable token mode for a pure cloud cashier submit test).
3. Start Picker/Dispatch UI E2E coverage (role preflight + monitor state transitions).

## Links
- `../phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `../CHANGELOG_PROGRESS.md`
- `../00-ai-agent-start-here.md`
