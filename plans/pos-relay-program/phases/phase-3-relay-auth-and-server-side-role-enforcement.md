# Phase 3 - Relay Authentication and Server-Side Role Enforcement

## TL;DR (Business Owner)
- This phase is the security hardening phase.
- It prevents users/devices from faking roles or calling relay actions they should not use.
- UI restrictions are not enough without this phase.

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Document Currency
- This is a current planning doc (Phase 3 is not complete).
- `codex-4.1-picked-dispatch-relay` now includes a Phase 3 baseline implementation (`0b8f772`) plus frontend follow-up fixes from live deploy testing:
  - `6767d0f` (relay role fallback for empty local role)
  - `ce5f84d` / `6cf64aa` (navbar relay-status polling/profile-registration race fixes so UI relay chips reflect actual fulfillment relay usage)
- This doc now tracks a mixed state: baseline auth/authorization is implemented in code, while full live regression/negative coverage and rollout hardening remain open.
- For the latest relay runtime verification, use:
  - `../uat/2026-02-23-local-edge-relay-smoke.md`
  - `../uat/2026-02-24-optiplex-lan-https-relay-sa-cashier-e2e-demo.md`
  - `../uat/2026-02-24-optiplex-picker-dispatch-shared-shell-relay-local-first.md`

## Purpose
Harden the trust boundary so relay and backend authorization do not rely on browser localStorage or client-provided role claims.

This phase is especially important because the recommended UX direction is a **single POS Awesome shell for all roles** with role-limited actions. In that model, UI hiding/disabling improves operator ergonomics, but only server/relay authorization makes it safe.

## In Scope
- Relay authentication for mutating endpoints
- Relay role authorization by action
- Consistent auth/authorization errors
- ERPNext/Frappe backend role checks on sensitive endpoints
- Audit logging of user/device/role for critical transitions
- Role spoofing prevention for shared-shell UI requests (same browser app, different operator roles)

## Out of Scope
- SA offline-first token creation (Phase 4)
- Final production rollout/UAT closeout (Phase 5)

## Completed So Far
- Relay stores session role field and action payload metadata (`Partial` foundation).
- Browser/pos role derivation exists (`UI only`, not trusted authorization).
- Phase 3 baseline relay hardening is implemented in branch code on `codex-4.1-picked-dispatch-relay` (`0b8f772`):
  - relay mutating-endpoint role guards (cashier/picker/dispatch/supervisor paths)
  - optional relay client-key auth plumbing (`X-Relay-Client-Key`)
  - server-side role enforcement on key POS/relay workflow APIs in `posapp.py`
  - committed Cypress security/fulfillment helper specs for repeatable validation
- Live dev-site testing exposed and fixed a real integration regression (`6767d0f`): cashier relay submit could send an empty role when local role state was missing; frontend now falls back to Frappe-derived role before relay calls.
- Live relay-enabled SA/Cashier behavior is validated, which provides concrete action paths to lock down in this phase (`TOKEN_CREATED`, `SESSION_OPEN`, `SALE_COMMITTED`).
- Shared-shell Picker/Dispatch/Supervisor fulfillment workspace is now implemented on `codex-4-picker-dispatch` and live-validated locally (OptiPlex relay + dev site) while calling relay pick/release endpoints from the same POS shell (`/relay/pick/update`, `/relay/dispatch/release`), increasing the urgency of relay auth/authorization before wider rollout.
- Picker line-wise fulfillment payloads are now persisted in relay local line payloads (`payload.picker`) and included in relay outbox `PICK_EVENT` payloads (`Implemented` local-first behavior, live UAT verified), but role trust remains client-provided until this phase is completed.
- Live dev-site/OptiPlex UAT now confirms picker and dispatch actions execute through the relay and sync fresh outbox fulfillment events (`PICK_EVENT`, `RELEASE_EVENT`) to the cloud after the `codex-4.1-picked-dispatch-relay` parity fix. This increases operational pressure to complete this phase's auth/authorization controls before wider rollout because the fulfillment path is now more end-to-end complete.

## Target Trust Model (Recommended)
- Keep one POS Awesome UI shell for all roles.
- Treat browser-provided role (`pos_current_role`) as *display hint only*.
- Relay and ERPNext APIs must authorize using a trusted identity source (device/session token + authenticated user context, or equivalent).
- Every mutating workflow action must be checked server-side/relay-side against the allowed role matrix.

## Role/Action Authorization Priority (Recommended Order)
1. Cashier commit/payment actions (highest financial risk)
2. Token creation / token void (SA/Supervisor)
3. Picker updates (inventory/fulfillment operational risk)
4. Dispatch release (goods release risk)
5. Supervisor overrides (sensitive exception path)

## Implementation Tasks
- [ ] Define trusted relay identity model (device token, signed payload, or equivalent).
- [ ] Implement relay auth middleware/check for mutating `/relay/*` endpoints. `Partial`: baseline guard + optional client-key plumbing implemented on `codex-4.1-picked-dispatch-relay`; rollout policy and stronger trust model still pending.
- [ ] Implement per-endpoint role authorization rules (SA/Cashier/Picker/Dispatch/Supervisor). `Partial`: baseline role guards implemented; full validation matrix and edge-case coverage still pending.
- [ ] Standardize error responses (`NOT_AUTHORIZED`, `AUTH_REQUIRED`, role mismatch).
- [ ] Add server-side role validation in ERPNext/Frappe APIs where role-bound actions occur. `Partial`: key workflow APIs updated; complete coverage/audit review still pending.
- [ ] Log role/user/device identifiers on token, commit, pick, release actions.
- [ ] Log override reason + approver identity for supervisor-only exception paths.
- [ ] Add tests for spoofed role payload attempts and missing auth.
- [ ] Update `01-role-based-workflow-spec.md` and `03-offline-edge-relay-and-windows-service-spec.md` with final trust model.

Implementation note (current dev-site state, not a substitute for this phase):
- Picker/dispatch relay outbox cloud-sync parity for fresh events is now working on `codex-4.1-picked-dispatch-relay` (`update_relay_picking_status`, `release_relay_dispatch`), including relay-provided `pos_profile` fallback handling for relay-created Sales Invoices with blank `pos_profile`.
- Phase 3 is still required to ensure only authorized roles can invoke picker/dispatch/cashier mutating actions and to prevent spoofed role payloads in the shared-shell UI model.

## Minimum Relay Authorization Matrix (Phase 3 baseline)
- `SA` (and optionally `Supervisor`):
  - allow token create
  - deny payment commit
  - deny pick/release actions
- `Cashier` (and optionally `Supervisor`):
  - allow session open/close (cashier workflow)
  - allow relay commit-invoice
  - deny picker/dispatch transitions by default
- `Picker` (and optionally `Supervisor`):
  - allow pick queue read + pick updates
  - deny payment commit / dispatch release
- `Dispatch` (and optionally `Supervisor`):
  - allow release actions
  - deny payment commit / pick updates unless explicitly allowed by policy
- `Supervisor`:
  - allow approved override endpoints only (do not implicitly allow all actions without audit logging)

## Tests and Verification
- [ ] Automated tests for unauthorized/forbidden relay requests.
- [ ] Positive tests for each allowed role/action pair.
- [ ] Manual verification that bypassing UI controls cannot invoke forbidden actions.
- [ ] Negative tests from shared-shell UI contexts (e.g. Picker browser attempts cashier submit, Dispatch browser attempts pick update with forged role payload).
- [ ] Add negative tests covering the new shared-shell fulfillment workspace (e.g. forged picker/dispatch payloads from `FulfillmentWorkspace.vue` context).
- [ ] Add negative tests specifically for cloud fulfillment sync endpoints (`update_relay_picking_status`, `release_relay_dispatch`) to ensure role spoofing is rejected after the `codex-4.1-picked-dispatch-relay` endpoint parity fix.
- [ ] Complete live dev-site rerun on deployed `0b8f772` + `6767d0f` using strict per-spec Cypress timeouts and UI-vs-actual relay status assertions in relay-dependent specs.

Current validation status note (2026-02-26):
- `cashier_workflow_frontend_watch.cy.js` and `phase3_security_relay_role_guards_watch.cy.js` both passed on the deployed dev site after `6767d0f`.
- Fulfillment rerun (Picker/Dispatch/Supervisor) with strict UI-vs-actual relay assertions is now passing on the deployed dev site after navbar relay-status fixes `ce5f84d` + `6cf64aa`.
- Remaining recommended rerun for Phase 3 signoff is the full SA/Cashier + fallback + security spec slice on the latest deployed build under the same strict timeout policy.
- Local-staging parity note (`codes-4.3-dispatch`): `cypress/e2e/local_staging/local_staging_phase3_security_relay_role_guards_watch.cy.js` now runs against `pj.local:8080` as a pre-cloud deploy smoke and passed during the 2026-02-26 local SA->Dispatch rerun after local Docker deploy/runtime fixes.

## Known Risks
- Breaking active store devices if auth rollout is not coordinated.
- Key/session management complexity on mixed LAN/public relay access patterns.
- Over-broad supervisor permissions can undermine auditability if overrides are not explicit and reason-coded.

## Deferred Items
- Additional cryptographic signing/hardware-bound trust (if not needed for initial production launch).

## Exit Criteria
- Relay rejects unauthorized mutating requests.
- Role spoofing from browser payloads no longer authorizes forbidden actions.
- Permission model is documented and test-covered.
- Shared-shell role UX is safe to operate because backend/relay authorization matches the documented role matrix.

## Cross-References
- `../01-role-based-workflow-spec.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
