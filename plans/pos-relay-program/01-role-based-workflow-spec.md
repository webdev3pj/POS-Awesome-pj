# 01 - Role-Based Workflow Specification (Detailed)

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

### `Navbar.vue`
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Relay/cloud status chips | Visible | Visible | Visible | Visible | Visible | `Implemented` |
| Read-only current role display | Visible | Visible | Visible | Visible | Visible | `Planned` (Phase 2) |
| Role-specific shortcuts/actions | Minimal | Cashier-focused | Pick-focused | Dispatch-focused | Supervisor-focused | `Planned` (Phase 2) |

### `Invoice.vue` (cart/token screen)
| Capability | SA | Cashier | Picker | Dispatch | Supervisor | Status |
|---|---|---|---|---|---|---|
| Add/remove items | Yes | Yes | Limited/No | No | Optional | `Partial` |
| Select/update customer | Yes | Yes | Read-only | Read-only | Yes | `Partial` |
| `Save/New` token/order | Yes | Optional | No | No | Optional | `Partial` (currently invoice-based) |
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
| Open POS shift/session | Yes | Yes | Yes | Yes | Yes | `Implemented` | `Partial` |
| Create token/order | Yes | Optional | No | No | Optional | `Partial` | `Planned` (SO-first API) |
| Print token slip | Yes | Optional | No | No | Optional | `Partial` (text token today) | `N/A` |
| Render QR/barcode token slip | Yes | Optional | No | No | Optional | `Planned` (Phase 1) | `N/A` |
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
- SA can currently save and get a token popup, but token is derived from draft Sales Invoice (`Partial`, wrong audit model).

What is missing:
- SA token must create submitted Sales Order (Phase 1).
- Token slip QR/barcode printing (Phase 1).
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
