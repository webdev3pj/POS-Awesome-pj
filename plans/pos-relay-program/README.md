# POS Relay Program Docs (Active Planning Set)

## TL;DR (Business Owner)
- These are the active program docs for the POS role workflow and offline relay work across the branch progression (`kilo-codex-v3` -> `codex-2-cashier` -> `codex-3-edge-relay`).
- The current top priority is relay-enabled validation of the already-implemented SA + Cashier flow (using the local Edge Relay on the OptiPlex).
- A live ticket-style sidebar monitor is being added so staff can track order status and delays.
- SA should not open/close cash shifts; cashier owns cash opening/closing.
- Use `00-ai-agent-start-here.md` first if you want the fastest summary of what is done and what is next.
- If working from the OptiPlex/relay machine with no chat context, use `runbooks/optiplex-edge-relay-next-session.md`.
- If starting a completely fresh Codex session on the OptiPlex, also use `runbooks/optiplex-fresh-codex-zero-context-handoff.md`.

## Purpose
This folder is the active planning and handoff set for the POS token/edge relay program.

It is branch-aware, not single-branch-only:
- `kilo-codex-v3` = original branch-accurate baseline and early SA/monitor rollout
- `codex-2-cashier` = cashier filtering/payment-path work and live cashier UAT
- `codex-3-edge-relay` = current branch for relay-focused validation and OptiPlex runbook execution

It consolidates:
- what is already implemented,
- what is partially implemented,
- what is still planned,
- how role-based workflow should work,
- how the edge relay/offline system works,
- and how an engineer or AI coding agent can take over safely.

## Current Branch, Lineage, and Scope
- Current working branch: `codex-3-edge-relay`
- Prior milestone branch (cashier UAT): `codex-2-cashier`
- Historical baseline branch: `kilo-codex-v3`
- Repo: `POS-Awesome-pj`
- Scope: role-based POS workflow + edge relay offline continuity + phased implementation/UAT/deployment

## Document Currency Labels (How to Read Status Correctly)
- `Current`: reflects the current program state and latest verified work on the active branch family (`codex-3-edge-relay` plus inherited commits).
- `Historical baseline`: intentionally tied to `kilo-codex-v3` and kept for traceability.
- `Historical UAT`: evidence captured on a specific date/branch (do not relabel as "current branch" later).
- `Stale note`: known outdated wording preserved temporarily inside a detailed checklist/table; check `CHANGELOG_PROGRESS.md` and UAT docs for the latest verified status.

## How To Use These Docs
1. Start with `00-ai-agent-start-here.md` for a fast operational handoff.
2. Read `01-role-based-workflow-spec.md` to understand what each role can/cannot do and see.
3. Read `02-master-implementation-plan.md` for the full phased roadmap.
4. Read `03-offline-edge-relay-and-windows-service-spec.md` for relay/offline storage and Windows service operations.
5. Use `phases/` docs for current execution state and phase-specific tasks.
6. Append progress to `CHANGELOG_PROGRESS.md` after each meaningful implementation or verification pass.
7. On the OptiPlex relay host, use `runbooks/optiplex-edge-relay-next-session.md` as the local operator/AI handoff entry point.
8. For shop PC one-time setup (non-technical), use `runbooks/shop-pc-lan-relay-setup-non-technical.md`.

## Document Map
- `00-ai-agent-start-here.md`: AI coding agent handoff, status snapshot, file map, next steps.
- `01-role-based-workflow-spec.md`: detailed role visibility/action matrix and implementation status.
- `02-master-implementation-plan.md`: end-to-end phased implementation plan and dependencies.
- `03-offline-edge-relay-and-windows-service-spec.md`: relay data model, sync semantics, Windows operations.
- `phases/phase-0-current-state-and-completed-work.md`: current branch-family baseline + completed work so far (explicitly labels historical vs current).
- `phases/phase-1-sa-sales-order-token-online-first.md`: SA token via submitted Sales Order (online-first).
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`: role UI completion and workflow UX.
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`: trust boundary/auth/authorization hardening.
- `phases/phase-4-sa-relay-first-offline-token-creation.md`: SA offline-first creation via relay.
- `phases/phase-5-uat-deployment-observability-hardening.md`: UAT, rollout, monitoring, hardening.
- `CHANGELOG_PROGRESS.md`: progress ledger across dates/commits (historical record; latest entry is the operational truth).
- `runbooks/optiplex-edge-relay-next-session.md`: zero-context startup guide for relay-host sessions (OptiPlex).
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`: full zero-context Codex takeover guide with exact branch/commit/env-var requirements.
- `runbooks/shop-pc-lan-relay-setup-non-technical.md`: one-time certificate trust steps for shop PCs (plain-English operator guide).

## Phase Map (High Level)
- Phase 0: Baseline and completed work documentation (branch-family snapshot + explicit historical/current labeling)
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

## Status Snapshot (February 23, 2026)
- SA flow is implemented and live-tested on the dev site up to the SA handoff boundary (`Sales Order` token creation + monitor visibility).
- Cashier `Select S.O` filtering by POS Profile Sales Order naming series + age is implemented and live-tested.
- Cashier flow is validated through SO load into payment/submit path (full relay-enabled submit success still depends on relay configuration testing).
- Relay local-first foundation is substantial and local relay acceptance + HTTP smoke checks are passing on `codex-3-edge-relay`.
- The current focus is relay-enabled SA/Cashier validation on the OptiPlex/local relay host.
- Relay auth and server-side role enforcement remain the major security gap (Phase 3).

## Source Documents Used (Context)
- `../../LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/POS_token_and_edge_relay.md`
- `../../LLM_DEVELOPMENTS/POS_TOKEN_and_EDGE_RELAY/ROLE_IMPLEMENTATION.md` (local context doc; may have drift)
- `../kilo-codex-v3-branch-accurate-checklist.md` (historical baseline checklist for `kilo-codex-v3`)
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
- `runbooks/optiplex-edge-relay-next-session.md`
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `runbooks/shop-pc-lan-relay-setup-non-technical.md`
