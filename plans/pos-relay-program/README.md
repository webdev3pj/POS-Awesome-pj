# POS Relay Program Docs (Active Planning Set)

## Purpose
This folder is the active, branch-accurate planning and handoff set for the POS token/edge relay program on `kilo-codex-v3`.

It consolidates:
- what is already implemented,
- what is partially implemented,
- what is still planned,
- how role-based workflow should work,
- how the edge relay/offline system works,
- and how an engineer or AI coding agent can take over safely.

## Current Branch and Scope
- Branch: `kilo-codex-v3`
- Repo: `POS-Awesome-pj`
- Scope: role-based POS workflow + edge relay offline continuity + phased implementation/UAT/deployment

## How To Use These Docs
1. Start with `00-ai-agent-start-here.md` for a fast operational handoff.
2. Read `01-role-based-workflow-spec.md` to understand what each role can/cannot do and see.
3. Read `02-master-implementation-plan.md` for the full phased roadmap.
4. Read `03-offline-edge-relay-and-windows-service-spec.md` for relay/offline storage and Windows service operations.
5. Use `phases/` docs for current execution state and phase-specific tasks.
6. Append progress to `CHANGELOG_PROGRESS.md` after each meaningful implementation or verification pass.

## Document Map
- `00-ai-agent-start-here.md`: AI coding agent handoff, status snapshot, file map, next steps.
- `01-role-based-workflow-spec.md`: detailed role visibility/action matrix and implementation status.
- `02-master-implementation-plan.md`: end-to-end phased implementation plan and dependencies.
- `03-offline-edge-relay-and-windows-service-spec.md`: relay data model, sync semantics, Windows operations.
- `phases/phase-0-current-state-and-completed-work.md`: branch-accurate baseline + completed work so far.
- `phases/phase-1-sa-sales-order-token-online-first.md`: SA token via submitted Sales Order (online-first).
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`: role UI completion and workflow UX.
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`: trust boundary/auth/authorization hardening.
- `phases/phase-4-sa-relay-first-offline-token-creation.md`: SA offline-first creation via relay.
- `phases/phase-5-uat-deployment-observability-hardening.md`: UAT, rollout, monitoring, hardening.
- `CHANGELOG_PROGRESS.md`: progress ledger across dates/commits.

## Phase Map (High Level)
- Phase 0: Baseline and completed work documentation (current branch + local working tree snapshot)
- Phase 1: Sales Associate token becomes submitted Sales Order (online-first)
- Phase 2: Cashier/Picker/Dispatch/Supervisor role UX visibility and operator workflows
- Phase 3: Relay auth + server-side role enforcement (trust boundary hardening)
- Phase 4: SA relay-first/offline token creation and SO sync to cloud
- Phase 5: UAT, deployment evidence, observability, runbooks, hardening

## Definitions
- `Token`: The identifier used to move a customer order through SA -> Cashier -> Picker -> Dispatch stages.
- `SO`: Sales Order (intended SA-created audit record in Phase 1).
- `SI`: Sales Invoice (created/submitted by cashier after payment).
- `Relay`: Local Windows-hosted Flask service that supports offline continuity and local-first commit.
- `Outbox`: Relay table/queue that stores events awaiting cloud sync.
- `Local Sale Ref`: Relay-generated local payment commit reference (e.g. `LSR-*`).

## Status Snapshot (February 22, 2026)
- Relay local-first foundation exists and is substantial.
- Role derivation foundation exists in POS Opening dialog.
- Cashier relay commit path is the most complete implemented role flow.
- SA payment is blocked in UI (local working tree), but SA token is still invoice-based in committed branch.
- SA token must be converted to submitted Sales Order in Phase 1.
- Relay auth and server-side role enforcement are still missing (critical).

## Source Documents Used (Context)
- `../../LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/POS_token_and_edge_relay.md`
- `../../LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/ROLE_IMPLEMENTATION.md` (local context doc; may have drift)
- `../kilo-codex-v3-branch-accurate-checklist.md`
- `../kilo-codex-v2-offline-continuity-checklist.md`
- Actual code in `posawesome/` and `relay/`

## Change Discipline
- Keep these docs branch-accurate.
- Mark items explicitly as `Implemented`, `Partial`, `Planned`, or `Deferred`.
- Prefer appending to `CHANGELOG_PROGRESS.md` and updating the relevant phase doc rather than rewriting all docs.
- Preserve historical notes in `LLM_DEVELOPMENTS/...`; use this folder for operational truth.

## See Also
- `00-ai-agent-start-here.md`
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `CHANGELOG_PROGRESS.md`
