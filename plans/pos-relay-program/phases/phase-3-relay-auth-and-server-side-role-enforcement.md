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
- For the latest relay runtime verification, use `../uat/2026-02-23-local-edge-relay-smoke.md`.

## Purpose
Harden the trust boundary so relay and backend authorization do not rely on browser localStorage or client-provided role claims.

## In Scope
- Relay authentication for mutating endpoints
- Relay role authorization by action
- Consistent auth/authorization errors
- ERPNext/Frappe backend role checks on sensitive endpoints
- Audit logging of user/device/role for critical transitions

## Out of Scope
- SA offline-first token creation (Phase 4)
- Final production rollout/UAT closeout (Phase 5)

## Completed So Far
- Relay stores session role field and action payload metadata (`Partial` foundation).
- Browser/pos role derivation exists (`UI only`, not trusted authorization).

## Implementation Tasks
- [ ] Define trusted relay identity model (device token, signed payload, or equivalent).
- [ ] Implement relay auth middleware/check for mutating `/relay/*` endpoints.
- [ ] Implement per-endpoint role authorization rules (SA/Cashier/Picker/Dispatch/Supervisor).
- [ ] Standardize error responses (`NOT_AUTHORIZED`, `AUTH_REQUIRED`, role mismatch).
- [ ] Add server-side role validation in ERPNext/Frappe APIs where role-bound actions occur.
- [ ] Log role/user/device identifiers on token, commit, pick, release actions.
- [ ] Add tests for spoofed role payload attempts and missing auth.
- [ ] Update `01-role-based-workflow-spec.md` and `03-offline-edge-relay-and-windows-service-spec.md` with final trust model.

## Tests and Verification
- [ ] Automated tests for unauthorized/forbidden relay requests.
- [ ] Positive tests for each allowed role/action pair.
- [ ] Manual verification that bypassing UI controls cannot invoke forbidden actions.

## Known Risks
- Breaking active store devices if auth rollout is not coordinated.
- Key/session management complexity on mixed LAN/public relay access patterns.

## Deferred Items
- Additional cryptographic signing/hardware-bound trust (if not needed for initial production launch).

## Exit Criteria
- Relay rejects unauthorized mutating requests.
- Role spoofing from browser payloads no longer authorizes forbidden actions.
- Permission model is documented and test-covered.

## Cross-References
- `../01-role-based-workflow-spec.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
