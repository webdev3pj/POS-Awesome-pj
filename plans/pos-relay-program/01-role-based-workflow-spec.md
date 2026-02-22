# 01 - Role-Based Workflow Specification (Detailed)

## TL;DR (Business Owner)
- This file defines exactly what each role should be able to see and do in POS.
- SA can build orders/tokens and monitor status, but must not take payment or manage cash shifts.
- Cashier owns payment and cash opening/closing.
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
Define the intended role-based POS workflow in operational detail and map each rule to implementation status on `kilo-codex-v3`.

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
- Final authorization must be server-side and relay-side (`Planned`, Phase 3).

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

## Component Visibility Matrix (Intended Behavior)
Status tags in the last column reflect current branch state.

### `OpeningDialog.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Derived role display | Visible | Visible | Visible | Visible | Visible | `Implemented` |
| Role self-selection | No | No | No | No | No | `Implemented` |
| Block no/multi role when relay token workflow enabled | Yes | Yes | Yes | Yes | Yes | `Implemented` |
| Start POS without cash opening table (non-cash roles) | Yes | No | Yes | Yes | Yes | `Implemented` (local working tree, pending UAT) |
| Require cash opening amounts/table (cashier only) | No | Yes | No | No | No | `Implemented` (local working tree, pending UAT) |

### `Navbar.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Relay/cloud status chips | Visible | Visible | Visible | Visible | Visible | `Implemented` |
| Read-only current role display | Visible | Visible | Visible | Visible | Visible | `Planned` (Phase 2) |
| Role-specific shortcuts/actions | Minimal | Cashier-focused | Pick-focused | Dispatch-focused | Supervisor-focused | `Planned` (Phase 2) |

### `WorkflowTicketRail.vue` (left sidebar ticket monitor)
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| See collapsed ticket icon + pending count | Visible | Visible | Visible | Visible | Visible | `Implemented` (local working tree, pending UAT) |
| Expand monitor panel for profile/date scope (opening shift optional metadata) | Yes | Yes | Yes | Yes | Yes | `Implemented` (local working tree, pending UAT) |
| View customer, SA name, order taken time, current status, time in status, grand total | Yes | Yes | Yes | Yes | Yes | `Implemented` (local working tree, pending UAT) |
| Filter rows by `Mine` (SA owner) | Yes | Yes | Yes | Yes | Yes | `Implemented` (local working tree, pending UAT) |
| See dispatched rows by default | No | No | No | No | No | `Implemented` (default hidden; API excludes released rows) |
| Row actions (open/approve/transition) | No | No | No | No | No | `Deferred` (read-only v1, Phase 2+) |

### `Invoice.vue` (cart/token screen)
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Add/remove items | Yes | Yes | Limited/No | No | Optional | `Partial` |
| Select/update customer | Yes | Yes | Read-only | Read-only | Yes | `Partial` |
| `Save/New` token/order | Yes | Optional | No | No | Optional | `Partial` (SO path implemented locally; pending UAT/migration) |
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
| Create/update customer via relay fallback | Yes | Yes | No | No | Yes | `Partial` (local working tree additions need validation) |

### `ItemsSelector.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Search items online | Yes | Yes | Limited | No | Yes | `Implemented` |
| Search items via relay cache fallback | Yes | Yes | Limited | No | Yes | `Partial` (local working tree additions need validation) |

## Allowed / Blocked Action Matrix (UI + Backend + Relay)
### Action matrix
| Action | SA | Cashier | Picker | Dispatch | Supervisor | UI Status | Server/Relay Status |
|---|---|---|---|---|---|---|---|
| Start POS session (non-cash roles allowed without opening cash) | Yes | Yes | Yes | Yes | Yes | `Implemented` (local working tree, pending UAT) | `Partial` |
| Open cash shift / enter opening amounts | No | Yes | No | No | No | `Implemented` (local working tree, pending UAT) | `Partial` |
| Close cash shift | No | Yes | No | No | Conditional | `Partial` (SA hidden/blocked locally; broader role rules pending) | `Partial` |
| View ticket monitor rail (read-only) | Yes | Yes | Yes | Yes | Yes | `Implemented` (local working tree) | `N/A` |
| Create token/order | Yes | Optional | No | No | Optional | `Partial` | `Planned` (SO-first API) |
| Print token slip | Yes | Optional | No | No | Optional | `Partial` (text token today) | `N/A` |
| Render QR/barcode token slip | Yes | Optional | No | No | Optional | `Partial` (local working tree; pending browser/printer UAT) | `N/A` |
| Take payment | No | Yes | No | No | Conditional | `Partial` | `Planned` (Phase 3 auth) |
| Submit SI | No | Yes | No | No | Conditional | `Partial` | `Partial` |
| Void token | No | No | No | No | Yes | `Planned` | `Partial` (relay endpoint exists; auth missing) |
| Pick update | No | No | Yes | No | Yes | `Partial` | `Partial` |
| Dispatch release | No | No | No | Yes | Yes | `Partial` | `Partial` |
| Override exceptions | No | No | No | Limited | Yes | `Planned` | `Planned` |

## Current Implementation Notes by Role
### Sales Associate (`cline-Sales Associate`)
Status: `Partial`

What exists:
- Role derivation and storage in opening dialog (`Implemented`).
- SA payment block in UI exists in local working tree changes (`Partial` until committed/UAT).
- SA SO token API + frontend save path is being implemented locally (`Partial`, requires UAT and migration).
- SA can see cross-role workflow monitor rail and track status/timing for profile/date-scoped pending orders (`Implemented` in local working tree, pending UAT).

What is missing:
- SA token must create submitted Sales Order (Phase 1).
- Token slip QR/barcode printing (Phase 1, local implementation pending UAT).
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
- Workflow monitor rail can surface pending order status/timing (read-only) for profile/date scope (`Implemented` local working tree, pending UAT).

What is missing:
- Prefer/guide cashier flow toward SO-first in role-specific UI (Phase 2).
- Server-side role enforcement for payment/submit actions (Phase 3).

### Picker (`cline-Picker`)
Status: `Partial`

What exists:
- Relay pick queue and pick update APIs (`Implemented` backend foundation).

What is missing:
- Picker-focused UI screen/visibility and guardrails (Phase 2).
- Relay auth/role authorization (Phase 3).

### Dispatch (`cline-Dispatch`)
Status: `Partial`

What exists:
- Relay dispatch release API and state transitions (`Implemented` backend foundation).

What is missing:
- Dispatch operator UI and visibility (Phase 2).
- Server/relay authorization (Phase 3).

### Supervisor (`cline-Supervisor`)
Status: `Planned` / `Partial`

What exists:
- Conceptual role and some backend paths that could be used for exception handling.

What is missing:
- Explicit supervisor-only override workflows.
- Auditable approval actions and reason capture.
- Relay/server-side supervisor authorization enforcement.

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

Status: `Planned` (Phase 3)

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
