# 01 - Role-Based Workflow Specification (Detailed)

## TL;DR (Business Owner)
- This file defines exactly what each role should be able to see and do in POS.
- SA can build orders/tokens and monitor status, but must not take payment or manage cash shifts.
- Cashier owns payment and cash opening/closing.
- Recommended UX direction: all roles use the same POS Awesome shell, but each role is limited to the actions/screens they are allowed to use.
- The left ticket monitor sidebar is visible to all roles and is planned/scoped around `POS Profile + business date`.
- UI blocks improve safety, but real security still requires server/relay authorization (Phase 3).

## See also
- `README.md`
- `00-ai-agent-start-here.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `CHANGELOG_PROGRESS.md`

## Purpose
Define the intended role-based POS workflow in operational detail and map each rule to implementation status across the active branch family (`kilo-codex-v3` baseline -> `codex-2-cashier` -> `codex-3-edge-relay` -> `codex-4-picker-dispatch`).

This document is the authoritative reference for:
- what each role can see,
- what each role can do,
- what must be blocked,
- what is enforced in UI vs server,
- and which phase delivers missing pieces.

## Status Labels
- `Implemented`: behavior exists and is expected to work in code (subject to UAT).
- `Partial`: some pieces exist, but flow is incomplete or not fully enforced.
- `Planned`: design agreed, not implemented yet.
- `Deferred`: intentionally postponed and tracked.
- `Local-only`: observed in an uncommitted working tree change, not part of the current branch state.

## Document Currency
- This spec is the role/permission source of truth, but some detailed row notes were originally written during `kilo-codex-v3` and `codex-2-cashier` implementation passes.
- Treat inline notes that mention `dev-site UAT` or a branch name as evidence markers.
- Treat `CHANGELOG_PROGRESS.md` and UAT docs as the authoritative timeline for what was verified and when.

## Role Derivation and Ambiguity Rules
### Source of truth
- ERPNext/Frappe user roles (single `cline-*` role expected).
- POS Opening dialog derives the runtime role and stores it in local storage as `pos_current_role`.

### Valid runtime roles
- `cline-Sales Associate`
- `cline-Cashier`
- `cline-Picker`
- `cline-Dispatch`
- `cline-Supervisor`

### Ambiguity/no-role rules
- If token workflow is enabled and user has no `cline-*` role: block opening (`Implemented`).
- If user has multiple `cline-*` roles: block opening (`Implemented`).
- If exactly one `cline-*` role: allow and store role (`Implemented`).

### Security note
- Browser role (`pos_current_role`) is UI state only.
- Final authorization must be server-side and relay-side (`Partial` on `codex-4.1-picked-dispatch-relay`; Phase 3 baseline guards are implemented, full hardening/coverage remains).

## Workflow Overview by Role
### Sales Associate (SA)
Primary job:
- Build customer cart, produce token/order, hand customer to cashier.

Must not do:
- Take payment.
- Submit Sales Invoice.
- Perform pick/dispatch release.

### Cashier
Primary job:
- Load token/order, collect payment, create/submit Sales Invoice.

Must not do:
- Perform picker-only or dispatch-only state transitions without authorization.

### Picker
Primary job:
- Pick paid orders, update pick status, flag exceptions.

### Dispatch / Gatekeeper
Primary job:
- Verify release conditions and release goods.

### Supervisor
Primary job:
- Approve exceptions, overrides, and sensitive actions.

## Recommended Operator UX Strategy (Single POS Awesome Shell)
### Recommendation
- Use one POS Awesome UI shell for all roles (same app, same navbar, same status chips, same monitor rail).
- Limit actions, editability, and default panels by role instead of creating separate apps.

### Why this is the best fit here
- Lower training cost: staff learn one UI layout.
- Lower maintenance cost: fewer duplicated flows/components.
- Better observability consistency: relay/cloud status and monitor rail appear in one place.
- Better offline continuity: all roles can operate against the same relay-backed local state model.

### Non-negotiable constraint
- Because all roles share the same UI shell, backend/relay authorization (Phase 3) is mandatory.
- Hidden/disabled controls are UX guardrails, not security.

## Relay-First Sync Principle for All Roles (Operational Rule)
- If a workflow action affects store operations, it should be representable in local relay state first, then synced to cloud via relay outbox when applicable.
- Current proven flow:
  - SA token create -> relay token + `TOKEN_CREATED`
  - Cashier payment commit -> relay local sale + `SALE_COMMITTED`
- Remaining role flows should follow the same pattern:
  - Picker updates -> relay pick events / sale line status updates (then sync)
  - Dispatch release -> relay dispatch events / release status updates (then sync)

## Component Visibility Matrix (Intended Behavior)
Status tags in the last column reflect the current program branch family state; evidence detail lives in UAT docs and `CHANGELOG_PROGRESS.md`.

### `OpeningDialog.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Derived role display | Visible | Visible | Visible | Visible | Visible | `Implemented` |
| Role self-selection | No | No | No | No | No | `Implemented` |
| Block no/multi role when relay token workflow enabled | Yes | Yes | Yes | Yes | Yes | `Implemented` |
| Start POS without cash opening table (non-cash roles) | Yes | No | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |
| Require cash opening amounts/table (cashier only) | No | Yes | No | No | No | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |

### `Navbar.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Relay/cloud status chips | Visible | Visible | Visible | Visible | Visible | `Implemented` |
| Read-only current role display | Visible | Visible | Visible | Visible | Visible | `Planned` (Phase 2) |
| Role-specific shortcuts/actions | Minimal | Cashier-focused | Pick-focused | Dispatch-focused | Supervisor-focused | `Planned` (Phase 2) |

### `WorkflowTicketRail.vue` (left sidebar ticket monitor)
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| See collapsed ticket icon + pending count | Visible | Visible | Visible | Visible | Visible | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |
| Expand monitor panel for profile/date scope (opening shift optional metadata) | Yes | Yes | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |
| View customer, SA name, order taken time, current status, time in status, grand total | Yes | Yes | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |
| Filter rows by `Mine` (SA owner) | Yes | Yes | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) |
| See dispatched rows by default | No | No | No | No | No | `Implemented` (default hidden; API excludes released rows) |
| Row actions (open/approve/transition) | No | No | No | No | No | `Deferred` (read-only v1, Phase 2+) |

### `Invoice.vue` (cart/token screen)
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Add/remove items | Yes | Yes | Limited/No | No | Optional | `Partial` |
| Select/update customer | Yes | Yes | Read-only | Read-only | Yes | `Partial` |
| `Save/New` token/order | Yes | Optional | No | No | Optional | `Implemented` (SA SO token path live-tested; cashier/non-SA behavior still `Partial`) |
| `PAY` button visible | Visible but disabled | Visible enabled | Hidden/disabled | Hidden/disabled | Optional | `Partial` (SA disable exists locally; full role gating pending) |
| `Select S.O` | No (preferred hidden) | Yes | No | No | Optional | `Partial` (Phase 2 role visibility) |
| Held invoices | No (preferred hidden) | Yes | No | No | Optional | `Planned` (Phase 2) |

### `Payments.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Open payment screen | No | Yes | No | No | Supervisor-only for overrides | `Partial` (SA block implemented locally; other role gating pending) |
| Enter payment amounts | No | Yes | No | No | Limited | `Planned` (server-side auth in Phase 3) |
| Submit invoice (cloud) | No | Yes | No | No | Limited | `Partial` |
| Submit invoice via relay | No | Yes | No | No | Limited | `Partial` |
| Set sales person/partner commission fields | Deferred for SA stage | Yes (cashier screen) | No | No | Optional | `Implemented` (cashier side), `Deferred` (SA stage) |

### `SalesOrders.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Search submitted unbilled Sales Orders | No (preferred hidden) | Yes | No | No | Optional | `Partial` (exists; role visibility pending) |
| Load SO into POS for payment conversion | No | Yes | No | No | Optional | `Implemented` (cashier workflow support exists) |

### `Customer.vue` / `UpdateCustomer.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Search/select customer | Yes | Yes | Read-only/No | No | Yes | `Partial` |
| Create/update customer online | Yes | Yes | No | No | Yes | `Partial` |
| Create/update customer via relay fallback | Yes | Yes | No | No | Yes | `Partial` (`Local-only` changes exist; not part of current branch state) |

### `ItemsSelector.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Search items online | Yes | Yes | Limited | No | Yes | `Implemented` |
| Search items via relay cache fallback | Yes | Yes | Limited | No | Yes | `Partial` (`Local-only` changes exist; not part of current branch state) |

## Allowed / Blocked Action Matrix (UI + Backend + Relay)
### Action matrix
| Action | SA | Cashier | Picker | Dispatch | Supervisor | UI Status | Server/Relay Status |
|---|---|---|---|---|---|---|---|
| Start POS session (non-cash roles allowed without opening cash) | Yes | Yes | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) | `Partial` |
| Open cash shift / enter opening amounts | No | Yes | No | No | No | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) | `Partial` |
| Close cash shift | No | Yes | No | No | Conditional | `Partial` (SA hidden/blocked locally; broader role rules pending) | `Partial` |
| View ticket monitor rail (read-only) | Yes | Yes | Yes | Yes | Yes | `Implemented` (dev-site UAT verified on `codex-2-cashier`; inherited) | `N/A` |
| Create token/order | Yes | Optional | No | No | Optional | `Implemented` (SA SO token path verified) | `Partial` (server/relay auth still pending) |
| Print token slip | Yes | Optional | No | No | Optional | `Implemented` (token dialog + explicit `Print Token Slip` CTA live-validated; browser PDF artifact proof completed on cloud dev) | `N/A` |
| Render QR/barcode token slip | Yes | Optional | No | No | Optional | `Partial` (browser/PDF render verified; raw QR cashier lookup unsupported today, barcode/SO retrieval proven; physical printer/scanner signoff still pending) | `N/A` |
| Take payment | No | Yes | No | No | Conditional | `Partial` | `Planned` (Phase 3 auth) |
| Submit SI | No | Yes | No | No | Conditional | `Partial` | `Partial` |
| Void token | No | No | No | No | Yes | `Planned` | `Partial` (relay endpoint exists; auth missing) |
| Pick update | No | No | Yes | No | Yes | `Implemented` (shared-shell relay path live-validated on `codex-4-picker-dispatch` / `codex-4.1-picked-dispatch-relay`) | `Partial` (auth/trust pending; cloud parity now verified for fresh events) |
| Dispatch release | No | No | No | Yes | Yes | `Implemented` (shared-shell relay path live-validated on `codex-4-picker-dispatch` / `codex-4.1-picked-dispatch-relay`) | `Partial` (auth/trust pending; cloud parity now verified for fresh events) |
| Override exceptions | No | No | No | Limited | Yes | `Planned` | `Planned` |

## Current Implementation Notes by Role
### Sales Associate (`cline-Sales Associate`)
Status: `Implemented` (SA boundary) / `Partial` (full multi-role integration)

What exists:
- Role derivation and storage in opening dialog (`Implemented`).
- SA payment block in UI is implemented and dev-site UAT verified.
- SA SO token API + frontend save path are implemented and dev-site UAT verified.
- SA can see cross-role workflow monitor rail and track status/timing for profile/date-scoped pending orders (`Implemented`, dev-site UAT verified).

What is missing:
- Full cashier/picker/dispatch lifecycle integration and relay-enabled proof for the same order (next phases / relay testing).
- Printer-specific QR/barcode output visual validation on target hardware/browser.
- Scanner-first cashier intake from raw QR payload. Current proven cashier retrieval path is barcode/Sales Order lookup, not QR JSON parsing.
- Full SA-specific visibility (Phase 2).
- Server/relay authorization (Phase 3).

Audit note:
- SA attribution on Sales Order will use document `owner` for now (`Accepted`).
- SA-stage `sales_partner` capture is deferred (`Deferred`).

### Cashier (`cline-Cashier`)
Status: `Partial` but most complete operational path

What exists:
- Relay-enabled local-first payment commit path (`Implemented` foundation).
- Direct cloud fallback disabled when relay-enabled commit fails (`Implemented`).
- SO selection and SO -> SI conversion support exists (`Implemented`).
- Workflow monitor rail can surface pending order status/timing (read-only) for profile/date scope (`Implemented`, dev-site UAT verified).
- Dedicated token slip retrieval validation now proves the current cashier intake behavior on cloud dev:
  - raw QR payload lookup is not supported by current cashier search
  - barcode/Sales Order lookup works
  - retrieved order loads into invoice successfully

What is missing:
- Prefer/guide cashier flow toward SO-first in role-specific UI (Phase 2).
- Server-side role enforcement for payment/submit actions (Phase 3).

### Picker (`cline-Picker`)
Status: `Partial` (core local-first workflow + cloud parity for fresh events proven through `codex-4.1-picked-dispatch-relay`)

What exists:
- Relay pick queue and pick update APIs (`Implemented` backend foundation).
- Shared-shell fulfillment workspace UI is implemented on `codex-4-picker-dispatch` and live-validated on dev site + OptiPlex relay (`Partial`, core local-first path proven):
  - relay queue + sale detail panel in POS Awesome
  - line list with editable picked quantities
  - ordered UOM + conversion factor + derived stock qty shown
  - picker status actions routed through relay `/relay/pick/update`
- Relay now persists line-level picker results in local sale line payloads (`payload.picker`) during pick updates (`Implemented`, live UAT verified after local relay restart).
- Live UAT proof (2026-02-24, headed Cypress on OptiPlex):
  - line-wise decimal `picked_qty` edit persisted (`0.5`)
  - UOM/conversion metadata persisted in `payload.picker`
  - sale advanced to `PICKED_READY_FOR_RELEASE`

What is missing:
- Picker-focused UX polish/guardrails in shared shell (pick-ticket print/reprint, reason presets, clearer exception prompts).
- Simplify the default picker UI path (current line-wise workspace is functional but can feel too busy); keep line list and editable `picked_qty`, but make order-level actions the primary path.
- Committed/repeatable Cypress picker spec coverage in branch history (helper spec used in UAT was local-only; committed coverage exists now on `codex-4.1-picked-dispatch-relay`, live rerun/standardization still in progress).
- Relay auth/role authorization (Phase 3).

Recommended picker flow (same POS shell, relay-backed):
- Default picker landing panel shows a relay-backed pick queue (paid, not yet released, pick-pending/in-progress/exception).
- Picker opens an order detail panel (read-only customer/order/payment summary, editable pick actions only).
- Normal case (fast path): picker reviews the line list, leaves default `picked_qty = ordered qty`, and uses order-level actions (`Start/Save`, `Mark Picked Ready`).
- Line-wise edits are available when needed (exceptions, shortages, wire/length quantities, measurement corrections) and do not mutate the billed invoice lines.
- Picker records exceptions through relay endpoints without changing the billed invoice; exception handling routes to supervisor/cashier flow as needed.
- Picker UI respects order UOM and conversion factor (shows picked qty in order UOM plus computed stock qty equivalent; important for wire/length items).
- Relay updates local sale / line state immediately for offline continuity and queues sync events.
- Ticket monitor rail remains visible for cross-role context; picker actions may later deep-link from rail row -> pick detail panel.

### Dispatch (`cline-Dispatch`)
Status: `Partial` (core local-first workflow + cloud parity for fresh events proven through `codex-4.1-picked-dispatch-relay`)

What exists:
- Relay dispatch release API and state transitions (`Implemented` backend foundation).
- Shared-shell fulfillment workspace UI is implemented on `codex-4-picker-dispatch` and live-validated on dev site + OptiPlex relay (`Partial`, core local-first path proven):
  - release-ready queue filtering in POS Awesome
  - relay sale detail/status visibility
  - relay `/relay/dispatch/release` action with partial/exception override toggle
- Live UAT proof (2026-02-24, headed Cypress on OptiPlex):
  - dispatch released a picker-ready local sale
  - relay sale `dispatch_status = RELEASED`
  - local `RELEASED` dispatch event created
  - sale disappeared from relay pick queue

What is missing:
- Dispatch hold/reason/override UX refinement and explicit supervisor pathways.
- Committed/repeatable Cypress dispatch spec coverage exists on `codex-4.1-picked-dispatch-relay`; live rerun/standardization and hold/reason variants are still pending.
- Server/relay authorization (Phase 3).

Recommended dispatch flow (same POS shell, relay-backed):
- Default dispatch landing panel shows release-ready orders (picked/paid, not released) and held/exception items requiring resolution.
- Normal case (fast path): dispatch confirms release with one explicit action after verifying picked/paid status.
- Edge case: hold/reason/override path is used when pick is partial/exception or supervisor approval is required.
- Relay records dispatch release event locally and updates local sale release status immediately.
- Sync to cloud happens through relay outbox/event sync without blocking the local release action when offline policy allows.

### Supervisor (`cline-Supervisor`)
Status: `Planned` / `Partial`

What exists:
- Conceptual role and some backend paths that could be used for exception handling.

What is missing:
- Explicit supervisor-only override workflows.
- Auditable approval actions and reason capture.
- Relay/server-side supervisor authorization enforcement.

Recommended supervisor behavior in shared shell:
- Supervisor can view the same operator panels but gets explicit override buttons only on exception paths.
- Every override requires a reason and should be written to relay/backend audit logs.

## Backend and Relay Authorization Expectations (Target State)
### Backend (ERPNext/Frappe)
- Validate role on sensitive POS APIs where role-specific action matters.
- Do not assume UI blocks are sufficient.
- Tie SA token creation API to allowed roles (`SA`, optional `Supervisor`).

### Relay (Flask)
- Authenticate mutating requests.
- Authorize action by trusted role/identity.
- Reject spoofed role payloads from browser.
- Log role/user/device on all mutating workflow transitions.
- Preserve offline-first behavior for authorized role actions by writing local state/events first, then syncing via outbox.

Status: `Partial` (Phase 3 baseline implemented on `codex-4.1-picked-dispatch-relay`; hardening/coverage still pending)

Current live UAT note (2026-02-25, `codex-4.1-picked-dispatch-relay`):
- Relay-local picker and dispatch transitions are proven in the shared shell.
- Fresh relay outbox fulfillment events now sync to cloud:
  - `PICK_EVENT` -> `update_relay_picking_status` (`done`)
  - `RELEASE_EVENT` -> `release_relay_dispatch` (`done`)
- Cloud `POS Relay Workflow State` proof captured for tested invoice (`ACC-SINV-2026-00260`):
  - `picking_status = Picked`
  - `dispatch_status = Released`
- Historical pre-fix outbox rows may still remain queued with old `500`/`417` errors and should be treated as legacy artifacts.

## Phase Mapping for Missing Items
- Phase 1:
  - SA token as submitted Sales Order (online-first)
  - QR/barcode token slip
  - preserve cashier SO -> SI preference
- Phase 1B (immediately after Phase 1 core):
  - ticket sidebar workflow monitor rail (default `POS Profile + business date` scope, cross-role visibility)
  - workflow timing timestamps (`order_taken_at`, `paid_at`, `pick_started_at`, `picked_at`, `status_changed_at`)
  - monitor API for pending order board + `Mine` filter
- Phase 2:
  - Full role-based UI visibility and operator flows (Cashier/Picker/Dispatch/Supervisor UX)
  - Navbar role display
- Phase 3:
  - Relay auth and server-side role authorization
- Phase 4:
  - SA relay-first/offline token creation with cloud SO sync
- Phase 5:
  - UAT evidence, deployment hardening, observability polish

## Audit and Attribution Notes
- `Accepted`: Use Frappe `owner` on Sales Order as SA attribution for now.
- `Deferred`: Add explicit visible `Sales Associate` field on Sales Order for reporting convenience.
- `Deferred`: Capture `sales_partner` at SA stage (currently sales partner exists in cashier payment screen flow).

## Open Questions to Revisit (Later Phases)
- Whether supervisors can perform cashier fallback when staffing is constrained.
- Whether picker/dispatch terminals should see customer PII or only token/order identifiers.
- Whether token QR payload should be signed before scanner-based workflows are introduced.

## See also
- `00-ai-agent-start-here.md`
- `02-master-implementation-plan.md`
- `03-offline-edge-relay-and-windows-service-spec.md`
- `phases/phase-1-sa-sales-order-token-online-first.md`
- `phases/phase-2-cashier-picker-dispatch-ui-and-enforcement.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
