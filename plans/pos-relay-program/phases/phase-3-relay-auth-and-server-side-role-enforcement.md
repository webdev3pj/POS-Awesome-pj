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
- Most items here remain design/implementation tasks, not verified behavior.
- For the latest relay runtime verification, use:
  - `../uat/2026-02-23-local-edge-relay-smoke.md`
  - `../uat/2026-02-24-optiplex-lan-https-relay-sa-cashier-e2e-demo.md`

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
- Live relay-enabled SA/Cashier behavior is validated, which provides concrete action paths to lock down in this phase (`TOKEN_CREATED`, `SESSION_OPEN`, `SALE_COMMITTED`).

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
- [ ] Implement relay auth middleware/check for mutating `/relay/*` endpoints.
- [ ] Implement per-endpoint role authorization rules (SA/Cashier/Picker/Dispatch/Supervisor).
- [ ] Standardize error responses (`NOT_AUTHORIZED`, `AUTH_REQUIRED`, role mismatch).
- [ ] Add server-side role validation in ERPNext/Frappe APIs where role-bound actions occur.
- [ ] Log role/user/device identifiers on token, commit, pick, release actions.
- [ ] Log override reason + approver identity for supervisor-only exception paths.
- [ ] Add tests for spoofed role payload attempts and missing auth.
- [ ] Update `01-role-based-workflow-spec.md` and `03-offline-edge-relay-and-windows-service-spec.md` with final trust model.

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
