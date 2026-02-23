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

## Document Currency
- This phase doc is the current baseline snapshot for the active branch family, not just `kilo-codex-v3`.
- Historical branch snapshots remain in `CHANGELOG_PROGRESS.md` and UAT docs by date/branch.
- This doc should answer: "What is committed now?" and "What is only local/unrelated?"

## Purpose
Capture a branch-accurate baseline and completed work so future engineering work starts from facts, not rediscovery.

## In Scope
- Current branch-family implementation status (`codex-3-edge-relay`, with inherited `codex-2-cashier` / `kilo-codex-v3` work)
- Local working tree notable work (only if clearly labeled as uncommitted and out-of-scope)
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
- SA no-cash POS session bootstrap and cashier-only cash opening behavior.
- SA token flow now creates submitted `Sales Order` tokens (audit-safe SI series handling).
- Ticket sidebar workflow monitor rail (profile/date scope, read-only, `Mine` filter) is implemented.
- Cashier relay commit path via `/relay/commit-invoice`.
- SO search and SO -> SI conversion support in POS.
- Cashier `Select S.O` filtering by POS Profile Sales Order naming series + age window is implemented.
- POS Profile custom fields for:
  - `posa_sales_order_naming_series`
  - `posa_sales_order_lookup_max_age_days`
- Cypress OTP login + SA/Cashier watch-mode specs + token-disabled regression smoke are committed.
- Relay acceptance tests use isolated temp DB/config and local relay HTTP smoke is documented/passing.

### Local uncommitted work currently present (`Out of scope unless intentionally staged`)
- Unrelated POS UI edits:
  - `posawesome/public/js/posapp/components/pos/Customer.vue`
  - `posawesome/public/js/posapp/components/pos/ItemsSelector.vue`
  - `posawesome/public/js/posapp/components/pos/UpdateCustomer.vue`
- Unrelated relay storage edits:
  - `relay/relay/storage.py`
- Local artifacts / scratch files:
  - `POS_Relay_End_to_End_Plan_with_Workflow_Exceptions_and_Edge_Cases.pdf`
  - `attendance.db`
  - `cypress/tmp/`

Rule:
- Do not assume any item in this section is part of the branch state.

### Documentation assets now present
- `plans/kilo-codex-v3-branch-accurate-checklist.md`
- `plans/pos-relay-program/*` (this docs program)
- `plans/pos-relay-program/uat/*` (branch/date-specific UAT evidence)
- `plans/pos-relay-program/runbooks/optiplex-edge-relay-next-session.md` (zero-context relay-host startup)
- Historical/context docs under `LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/`

## Implementation Tasks (Phase 0 Closeout)
- [x] Keep the baseline docs updated as branch state changes. *(continuing maintenance task)*
- [x] Mark local working tree items as committed once they are actually committed/pushed. *(ongoing; current uncommitted items listed explicitly above)*
- [ ] Continue linking future implementation PR/commit IDs in `../CHANGELOG_PROGRESS.md`.

## Tests and Verification
- Documentation verification:
  - [ ] All cross-links resolve.
  - [x] Phase/top-level docs explicitly label current vs historical/baseline context.
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
- Current vs historical/stale labeling is explicit enough for a zero-context handoff.

## Cross-References
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
