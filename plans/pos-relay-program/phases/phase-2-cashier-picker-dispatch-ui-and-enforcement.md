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

## Document Currency
- This is the active phase doc for remaining cashier/picker/dispatch/supervisor UX work.
- Cashier filtering, LAN-only relay status semantics, cloud fallback UX, and relay-first cashier SO-load/payment-path coverage are implemented and verified on `codex-3-edge-relay`.
- `codex-4-picker-dispatch` introduced a shared-shell Picker/Dispatch/Supervisor fulfillment workspace wired to relay pick/release APIs and was live-validated on the dev site/OptiPlex relay for local-first picker/dispatch state updates.
- `codex-4.1-picked-dispatch-relay` completes live cloud parity validation for fresh picker/dispatch relay outbox events (`PICK_EVENT`, `RELEASE_EVENT`) on the dev site.
- `codex-4.1-picked-dispatch-relay` also adds committed fulfillment/security Cypress helper specs and Phase 3 baseline guard code; fulfillment-role retesting now includes strict UI-vs-actual-state assertions (relay/cloud chips/banners vs relay APIs) and has been rerun successfully after navbar relay-status sync fixes (`ce5f84d`, `6cf64aa`).
- Remaining tasks in this file are primarily Picker/Dispatch/Supervisor UX polish (especially simplification), visibility-matrix cleanup across shared components, and repeatable Cypress coverage/reruns.
- Use `../CHANGELOG_PROGRESS.md` and the cashier UAT doc for the latest verified cashier status.

## Purpose
Complete the operator-facing role UX so each role sees the right screens/actions and is blocked from the wrong ones at the UI level.

## In Scope
- Single-shell role strategy within POS Awesome (same app UI, role-limited capabilities)
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
- SA payment UI blocking is implemented and live-tested (`Implemented` for SA boundary; broader role gating remains `Partial`).
- Cashier relay commit UX foundation and status diagnostics (`Implemented`/`Partial`).
- Phase 1B monitor rail foundation is implemented and dev-site UAT verified (read-only v1); refinement remains open.
- Cashier `Select S.O` backend filtering by POS Profile Sales Order naming series + age window implemented (`Implemented`).
- Live dev-site cashier E2E (headed Cypress) verified:
  - `Select S.O` request includes `pos_profile`
  - `PJ7 CASHIER` naming-series/age filtering works
  - cashier can load SA-created SO into payment screen (`Partial`, submit success depends on environment/relay config)
- Regression smoke test added for `custom_have_token = 0` on POS Profile to ensure cashier POS still opens and payment screen is reachable (`Implemented`, Cypress).
- OptiPlex handoff package docs added for next relay-focused cashier validation pass (`Implemented`, docs).
- LAN-only relay mode cashier UX semantics implemented (browser-LAN relay health as submit gate) and live-validated on the OptiPlex/dev site.
- Cashier prompted cloud fallback when relay is down but cloud is reachable implemented and validated (Cypress watch mode).
- Relay-first cashier submit path live-validated end-to-end with local relay transaction/outbox evidence and cloud sync completion.
- Shared-shell Picker/Dispatch/Supervisor fulfillment workspace added in `Pos.vue` (`Implemented` for local-first relay path on `codex-4-picker-dispatch`; cloud sync parity still pending):
  - role-default fulfillment panel replaces cashier cart/payment layout for fulfillment roles
  - relay pick queue + relay transaction detail views
  - picker line list with editable `picked_qty` (defaults to ordered qty)
  - UOM/conversion factor and derived stock qty display for line-level picking (wire-friendly decimals)
  - dispatch release action wired to relay release endpoint
- Relay storage now persists line-level pick results in local sale line payloads (`relay_local_sale_lines.payload.picker`) during `/relay/pick/update` so picker edits survive refresh/offline usage (`Implemented`, OptiPlex/dev-site live UAT verified after local relay restart).
- Live picker/dispatch relay-local UAT on `codex-4-picker-dispatch` verified:
  - Picker shared-shell queue/detail loads
  - decimal line-wise `picked_qty` edit persists (`0.5` test case) with UOM/conversion metadata
  - picker transitions `PICK_IN_PROGRESS` -> `PICKED_READY_FOR_RELEASE`
  - Dispatch shared-shell release updates `dispatch_status = RELEASED`
  - released row disappears from relay pick queue
- Cloud parity for fresh picker/dispatch relay outbox events is now live-validated on `codex-4.1-picked-dispatch-relay` (relay outbox rows move to `done`; cloud `POS Relay Workflow State` updates to `Picked` / `Released`). Historical queued rows from pre-fix runs may still remain and should be treated as legacy artifacts during demos.

## Recommended UX Direction (Same POS Awesome Shell for All Roles)
- Use one POS Awesome UI shell for all roles (same navigation, same relay/cloud status chips, same monitor rail).
- Change what the operator can *see/edit/do* based on role, instead of launching separate apps.
- Default role landing/panel recommendations:
  - SA: cart + customer + `Save/New` token flow (payment controls disabled/hidden)
  - Cashier: cart + `Select S.O` + payment flow
  - Picker: pick queue / order detail / line pick actions (read-only pricing/payment)
  - Dispatch: release queue / release confirmation / hold reasons (read-only payment)
  - Supervisor: read-all + override/exception tools with explicit audit prompts
- All operator state transitions should sync through the offline relay first when relay-backed flows are used (pick/release events recorded locally and synced via relay outbox).

### Picker simplification direction (business feedback, 2026-02-26)
- Keep the line-item list visible (required for accuracy and wire/UOM handling).
- Keep line-wise `picked_qty` editing available.
- Default every line `picked_qty` to ordered qty.
- Make the normal picker path mostly order-level buttons:
  - `Start/Save Picking`
  - `Mark Picked Ready`
  - `Flag Exception`
- Treat line edits as exception/measurement handling, not the primary path for every order.
- Do not mutate the billed invoice lines; picker edits update relay fulfillment data only.

## Implementation Tasks
- [ ] Add read-only current role display in `Navbar.vue`.
- [ ] Implement per-role visibility matrix in `Invoice.vue` (Held, Select SO, Return, Save/New, PAY, draft print behavior).
- [ ] Harden `Payments.vue` role gating beyond SA only (picker/dispatch/supervisor UX rules).
- [ ] Implement/complete picker workflow UI for pick queue and pick status actions (within the shared POS shell). `Partial`: shared-shell relay-backed picker workflow is deployed and locally UAT-validated on `codex-4-picker-dispatch`; remaining work is UX polish/simplification (pick ticket print/reprint, clearer default order-level path, line notes/reason presets, supervisor exception paths) and repeatable committed test reruns.
- [ ] Implement/complete dispatch workflow UI for release actions and hold/reason states (within the shared POS shell). `Partial`: relay-backed release action and queue filtering are deployed and locally UAT-validated on `codex-4-picker-dispatch`; remaining work is hold/reason/override refinements and committed test coverage.
- [ ] Add supervisor UI affordances for exception review/override (without weakening default restrictions). `Partial`: shared-shell supervisor fulfillment exception/override workflow exists and is now live-rerun validated on the dev site; UX polish and explicit reason/hold flows remain.
- [ ] Decide whether the ticket monitor rail remains read-only in Phase 2 or gains role-specific row actions (open details, quick filters, transition shortcuts).
- [ ] Design and implement role-specific default views/panels in the shared POS shell (SA/Cashier/Picker/Dispatch/Supervisor) without duplicating app routes unnecessarily. `Partial`: Picker/Dispatch/Supervisor now route to shared fulfillment panel in `Pos.vue`; SA/Cashier/UI-polish work remains.
- [x] Wire picker/dispatch UI actions to relay-backed endpoints (`/relay/pick-queue`, `/relay/pick/update`, `/relay/dispatch/release`) so offline relay remains the operational source. Live-validated on OptiPlex/dev-site (`codex-4-picker-dispatch`) for local relay state changes; cloud sync parity for fresh events is now verified on `codex-4.1-picked-dispatch-relay`.
- [ ] Align labels/messages with role terminology used in `01-role-based-workflow-spec.md`.
- [ ] Update role spec statuses after implementation.

## Tests and Verification
- [ ] Role-by-role UI visibility walkthrough using test users.
- [ ] Cypress assertions for hidden/disabled controls by role.
- [x] Add/standardize Cypress assertions that UI relay/cloud status chips/banners match actual relay/API state in each relay-dependent workflow spec. Local helper/spec hardening exists (currently uncommitted at the time of this note); live rerun caught and validated fixes for a real navbar relay-chip sync race (`ce5f84d`, `6cf64aa`).
- [ ] Enforce strict per-spec Cypress timeout + orphan-process cleanup discipline in runbooks and repeatable test scripts (OptiPlex operational rule).
- [x] Regression checks for cashier SO selection filtering (POS Profile series + age) on live dev site.
- [x] Smoke regression: cashier POS/payment screen still works when `custom_have_token = 0`.
- [x] Full cashier payment submit success under relay-configured submit environment (relay local sale + cloud sync evidence captured).
- [x] LAN-only relay mode status/fallback Cypress coverage (relay down + cloud up / cloud down cases).
- [x] Picker UI workflow Cypress coverage (queue -> pick update -> status changes reflected in relay/UI) exists and is committed on `codex-4.1-picked-dispatch-relay`; rerun/flake-hardening validation on current deploy is in progress.
- [x] Dispatch UI workflow Cypress coverage (release path reflected in relay/UI) exists and is committed on `codex-4.1-picked-dispatch-relay`; hold/reason variants remain untested and current rerun/flake-hardening validation is in progress.
- [x] Manual/headed UAT on OptiPlex/dev site for shared-shell picker/dispatch workspace (`codex-4-picker-dispatch`) including line-wise picked quantity persistence and UOM/conversion-factor display. Follow-on `codex-4.1-picked-dispatch-relay` validation confirmed cloud parity for fresh fulfillment events.
- [x] Cloud parity validation for picker/dispatch events (`PICK_EVENT` / `RELEASE_EVENT` sync completion and cloud-state update confirmation) on `codex-4.1-picked-dispatch-relay` using headed Cypress watch mode + relay/cloud API evidence.
- [x] Supervisor exception/override Cypress coverage live validation on the current deployed Phase 3 build (`supervisor_fulfillment_exception_watch.cy.js`) completed in headed watch mode with relay/UI/API evidence (2026-02-26 rerun).

## Known Risks
- UI-only blocks can create false sense of security until Phase 3 auth lands.
- Shared components may have side effects when hidden/disabled logic is added.
- Relay/cloud status semantics can confuse operators if LAN-only mode diagnostics and submit gating are not clearly distinguished in the UI.
- Fulfillment operators may still misread success if historical queued outbox rows (older pre-fix events) are visible during demos; UI/runbooks should clarify how to identify fresh events by timestamp/local ref and distinguish local status from cloud sync counters.
- A single-shell role strategy improves training and consistency, but increases the importance of strict backend/relay authorization and comprehensive hidden/disabled control tests.
- Picker workspace can feel too complex if line-level controls dominate the normal path; Phase 2 UX polish should prioritize a simpler default order-level flow with line edits as needed.

## Deferred Items
- Relay/server-side authorization enforcement (Phase 3).

## Exit Criteria
- Role visibility matrix in `01-role-based-workflow-spec.md` is mostly `Implemented` for UI-level rules.
- Picker and Dispatch operators can complete their UI workflows inside the shared POS shell without using cashier screens.
- Relay-backed pick/release actions visibly update local relay state and survive cloud interruptions (with later sync).
- Cloud parity for picker/dispatch events is either verified or clearly documented as local-first queued behavior during rollout/UAT.

## Cross-References
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
