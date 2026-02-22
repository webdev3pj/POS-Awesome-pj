# 2026-02-22 Dev Site SA Watch-Mode Cypress Run

## TL;DR (Business Owner)
- This file records the Sales Associate frontend test run on the live dev site using Cypress watch mode (Chrome).
- It is the evidence log for what worked, what failed, and what needs fixing next.
- This specific file is prepared in advance and should be updated immediately after the actual watch-mode run.

## Environment
- Site: `https://devpjjamaica.v.frappe.cloud/`
- Branch: `kilo-codex-v3`
- Browser: `Chrome` (Cypress watch mode / interactive)
- Cypress command: `npm.cmd run e2e:open`
- POS Profile under test: `PJ7 CASHIER`

## Branch + Commit + Deploy Confirmation
- Branch deployed: `kilo-codex-v3`
- Commit deployed: `TBD`
- Deploy confirmation timestamp: `TBD`
- Migrate/restart completed: `TBD`

## Role Setup Used
- Test user: `cline`
- Operational `cline-*` role setup during test:
  - `cline-Sales Associate`: `TBD`
  - Other `cline-*` roles disabled during test: `TBD`
- Non-operational/admin roles preserved: `TBD`

## Scope of This Run
- SA login + OTP
- SA POS entry (no cash opening shift for SA)
- SA token creation (`Sales Order`, not `Sales Invoice`)
- Token dialog/slip visibility
- Ticket sidebar counter + expanded monitor rail row
- SA blocked actions (payment / cashier cash controls)

## What Passed
- `TBD`

## What Failed
- `TBD`

## Watch-Mode Observations (What Was Seen Clicking)
- `TBD`

## Screenshots / Cypress Artifacts
- Cypress screenshots: `TBD`
- Cypress videos (if enabled): `TBD`
- Manual screenshots/notes: `TBD`

## Data Verification (ERPNext / POS)
- Sales Order created: `TBD`
- Sales Invoice created at SA step (should be No): `TBD`
- SO owner = SA (`cline`): `TBD`
- Workflow state row exists with `business_date` + timing fields: `TBD`
- Monitor row status on create (expected `Unpaid`): `TBD`

## Defects Found
- `TBD`

## Next Actions
1. `TBD`
2. `TBD`
3. `TBD`

## Links
- `../phases/phase-1-sa-sales-order-token-online-first.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
