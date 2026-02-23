# Phase 2 - Cashier, Picker, Dispatch UI and Role Enforcement (Frontend UX Layer)

## TL;DR (Business Owner)
- This phase finishes the role-based screens so each role sees only what they should.
- It builds on Phase 1/1B, where SA tokens and the sidebar monitor foundation are created.
- The ticket sidebar stays useful across roles, and Phase 2 decides if it remains read-only or gets quick actions later.

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Purpose
Complete the operator-facing role UX so each role sees the right screens/actions and is blocked from the wrong ones at the UI level.

## In Scope
- Role display in navbar
- Role-based visibility/disable rules across POS components
- Picker and Dispatch operator UI workflow completion
- Supervisor UI affordances for exception handling (frontend layer)
- Build on Phase 1B ticket monitor rail for role-aware operational visibility (read-only rail exists first; Phase 2 may add deeper affordances)

## Out of Scope
- Final server-side/relay authorization (Phase 3)
- SA relay-first/offline token creation (Phase 4)
- Production rollout evidence (Phase 5)

## Completed So Far
- Opening dialog role derivation and no/multi-role blocking (`Implemented`).
- Partial SA payment UI blocking in local working tree (`Partial`).
- Cashier relay commit UX foundation and status diagnostics (`Implemented`/`Partial`).
- Phase 1B monitor rail foundation added locally (ticket icon/sidebar, polling, profile/date-scoped pending rows, timing display) pending UAT and refinement.
- Cashier `Select S.O` backend filtering by POS Profile Sales Order naming series + age window implemented (`Implemented`).
- Live dev-site cashier E2E (headed Cypress) verified:
  - `Select S.O` request includes `pos_profile`
  - `PJ7 CASHIER` naming-series/age filtering works
  - cashier can load SA-created SO into payment screen (`Partial`, submit success depends on environment/relay config)
- Regression smoke test added for `custom_have_token = 0` on POS Profile to ensure cashier POS still opens and payment screen is reachable (`Implemented`, Cypress).

## Implementation Tasks
- [ ] Add read-only current role display in `Navbar.vue`.
- [ ] Implement per-role visibility matrix in `Invoice.vue` (Held, Select SO, Return, Save/New, PAY, draft print behavior).
- [ ] Harden `Payments.vue` role gating beyond SA only (picker/dispatch/supervisor UX rules).
- [ ] Implement/complete picker workflow UI for pick queue and pick status actions.
- [ ] Implement/complete dispatch workflow UI for release actions and hold/reason states.
- [ ] Add supervisor UI affordances for exception review/override (without weakening default restrictions).
- [ ] Decide whether the ticket monitor rail remains read-only in Phase 2 or gains role-specific row actions (open details, quick filters, transition shortcuts).
- [ ] Align labels/messages with role terminology used in `01-role-based-workflow-spec.md`.
- [ ] Update role spec statuses after implementation.

## Tests and Verification
- [ ] Role-by-role UI visibility walkthrough using test users.
- [ ] Cypress assertions for hidden/disabled controls by role.
- [x] Regression checks for cashier SO selection filtering (POS Profile series + age) on live dev site.
- [x] Smoke regression: cashier POS/payment screen still works when `custom_have_token = 0`.
- [ ] Full cashier payment submit success under relay-configured or token-disabled submit environment.

## Known Risks
- UI-only blocks can create false sense of security until Phase 3 auth lands.
- Shared components may have side effects when hidden/disabled logic is added.

## Deferred Items
- Relay/server-side authorization enforcement (Phase 3).

## Exit Criteria
- Role visibility matrix in `01-role-based-workflow-spec.md` is mostly `Implemented` for UI-level rules.
- Picker and Dispatch operators can complete their UI workflows without using cashier screens.

## Cross-References
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
