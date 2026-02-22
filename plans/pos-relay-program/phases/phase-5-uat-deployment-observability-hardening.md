# Phase 5 - UAT, Deployment, Observability, and Hardening

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Purpose
Turn the implemented role/relay workflow into a deployable, supportable operating system with evidence, test coverage, and runbooks.

## In Scope
- UAT plans and evidence capture
- Dev -> production deployment checklists
- Observability/monitoring validation
- Cypress E2E coverage expansion
- Rollback and operational hardening

## Out of Scope
- New major feature development unless required to fix UAT-critical defects

## Completed So Far
- Relay dashboard/queue/outbox/transactions operational visibility foundation exists.
- Cypress OTP login automation exists in local working tree.
- Relay setup and OptiPlex checklist docs exist in `relay/`.

## Implementation Tasks
- [ ] Build role-by-role UAT scripts and evidence templates.
- [ ] Run dev-site UAT for SA -> Cashier -> Picker -> Dispatch end-to-end flows.
- [ ] Expand Cypress coverage:
  - SA token SO creation
  - Cashier SO -> SI path
  - selected role visibility assertions
- [ ] Validate relay observability endpoints and operator runbooks.
- [ ] Finalize deployment checklist for Frappe Cloud + relay config alignment.
- [ ] Add rollback procedure per phase/feature gate.
- [ ] Record defects and stabilization fixes in `../CHANGELOG_PROGRESS.md`.

## Tests and Verification
- [ ] Cypress `e2e:open` visual runs on live dev site after each major change.
- [ ] Cypress `e2e:run` headless regression baseline.
- [ ] Manual UAT evidence with screenshots/log notes.
- [ ] Relay outage/cloud outage simulations with expected operator messaging.

## Known Risks
- Live-site data variability causing flaky E2E tests.
- Environment/config drift between dev and production relay setups.
- Operational documentation lagging behind late changes.

## Deferred Items
- Long-term production observability improvements (centralized logging, external monitoring) if not required for initial rollout.

## Exit Criteria
- UAT evidence exists for each role and key failure mode.
- Deployment and rollback docs are complete and used successfully on dev rollout.
- Cypress regression suite covers critical operator flows and is runnable by one command.

## Cross-References
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
