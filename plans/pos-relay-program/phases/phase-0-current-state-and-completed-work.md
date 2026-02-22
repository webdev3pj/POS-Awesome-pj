# Phase 0 - Current State and Completed Work

## TL;DR (Business Owner)
- This document is the baseline snapshot: what is already in the branch vs what exists only locally on a developer machine.
- It prevents confusion about what is truly deployed and what is still being prepared.
- Use it to check whether a feature is committed/pushed before testing or deployment.

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Purpose
Capture a branch-accurate baseline and completed work so future engineering work starts from facts, not rediscovery.

## In Scope
- Current branch implementation status (`kilo-codex-v3`)
- Local working tree notable work (if not yet committed)
- Known documentation drift
- Immediate next priorities

## Out of Scope
- New feature implementation
- Security hardening execution
- UAT evidence collection (belongs mainly to Phase 5)

## Completed So Far
### Committed branch capabilities (`Implemented` / `Partial`)
- Relay local-first foundation (tokens, sessions, local sales, pick/dispatch, outbox, idempotency).
- Relay dashboards and observability APIs, including transactions endpoints.
- Relay `public_base_url` support and ERPNext accessibility check endpoint.
- POS relay profile gating via `custom_have_token` and `custom_edge_relay_url`.
- POS relay/cloud connectivity status indicators in Navbar.
- Role derivation in opening dialog from ERPNext `cline-*` roles.
- Cashier relay commit path via `/relay/commit-invoice`.
- SO search and SO -> SI conversion support in POS.

### Local working tree work observed (`Partial`, confirm/commit intentionally)
- Cypress + OTP login automation setup (`package.json`, `cypress.config.cjs`, `cypress/`, `scripts/run-cypress.cjs`, `.env.example`).
- SA UI hardening and offline customer/item fallback changes in POS components (`Invoice.vue`, `Payments.vue`, `Customer.vue`, `ItemsSelector.vue`, `UpdateCustomer.vue`).
- Additional role and relay-related edits in `posapp.py`, `OpeningDialog.vue`, `relay/relay/storage.py`.

Note:
- These local changes are intentionally not assumed committed unless verified in git history.
- Docs should explicitly distinguish branch state from local uncommitted work.

### Documentation assets now present
- `plans/kilo-codex-v3-branch-accurate-checklist.md`
- `plans/pos-relay-program/*` (this docs program)
- Historical/context docs under `LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/`

## Implementation Tasks (Phase 0 Closeout)
- [ ] Keep the baseline docs updated as branch state changes.
- [ ] Mark local working tree items as committed once they are actually committed/pushed.
- [ ] Link any future implementation PR/commit IDs in `../CHANGELOG_PROGRESS.md`.

## Tests and Verification
- Documentation verification:
  - [ ] All cross-links resolve.
  - [ ] Phase docs use consistent status labels.
- Code reality spot-checks used for this baseline:
  - `posawesome/posawesome/api/posapp.py`
  - `posawesome/public/js/posapp/components/pos/*.vue`
  - `relay/relay/app.py`
  - `relay/relay/storage.py`

## Known Risks
- Baseline can drift quickly if code changes land but docs are not updated.
- Local working tree changes can be mistaken for committed branch features.
- Historical docs may conflict with branch reality if copied verbatim.

## Deferred Items
- None (this phase is a documentation baseline, not a functional feature phase).

## Exit Criteria
- Branch-accurate baseline documented.
- Local working tree work clearly labeled as uncommitted/partial where applicable.
- New docs program pushed to branch and discoverable by other contributors.

## Cross-References
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
