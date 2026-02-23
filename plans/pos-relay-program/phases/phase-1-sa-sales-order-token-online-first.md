# Phase 1 - SA Sales Order Token (Online-First)

## TL;DR (Business Owner)
- This phase makes SA create a `Sales Order` token instead of consuming a `Sales Invoice` number.
- It protects invoice numbering for audit purposes because only cashier creates the invoice.
- It also includes the first version of the ticket sidebar monitor and timing fields.
- SA should be able to start a POS session without opening cash; cashier still owns cash opening/closing.
- POS Profile-specific Sales Order series and cashier `Select S.O` age filtering are now implemented and verified in cashier dev-site UAT.

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Document Currency
- This phase doc is still active, but many checkbox notes were written during the initial implementation pass on `kilo-codex-v3`.
- Treat the task breakdown as the phase design/checklist history.
- Treat verification status as current only when confirmed in:
  - `../CHANGELOG_PROGRESS.md`
  - `../uat/2026-02-22-dev-site-sa-watch-mode-cypress.md`
  - `../uat/2026-02-23-dev-site-cashier-watch-mode-cypress.md`

## Purpose
Convert the Sales Associate token flow from draft `Sales Invoice`-based token generation to a submitted `Sales Order`-based token flow (online-first), preserving invoice-series audit integrity.

## In Scope
- SA token creation as submitted `Sales Order`
- Token slip print with QR + barcode + required fields
- Cashier-preferred `SO -> SI` flow preserved
- Workflow state support for SO-first token lifecycle
- Best-effort relay token sync using SO token id
- Phase 1B: ticket sidebar workflow monitor rail (default `POS Profile + business date` scope, read-only) and workflow timing timestamps
- SA no-cash POS session bootstrap (cash opening remains cashier-only)

## Out of Scope
- SA relay-first/offline token creation (Phase 4)
- Relay authentication and server-side role authorization (Phase 3)
- Full role UI completion for all roles (Phase 2)
- SA-stage `sales_partner` capture (deferred)

## Completed So Far
### Relevant existing capabilities to reuse
- POS supports `Sales Order` search and selection (`Select S.O`).
- POS supports `Sales Order -> Sales Invoice` conversion for payment.
- Relay token create endpoint exists.
- Opening dialog role derivation exists.
- SA payment blocking exists and is live-tested in dev-site UAT.

### Current gap this phase closes
- Current token popup/print is tied to `new_invoice()` / draft `Sales Invoice` and derives token from SI name suffix.

## Historical Checklist Annotation Note
- Many task lines below retain original implementation-time annotations such as `local working tree` and `pending UAT`.
- Use `../CHANGELOG_PROGRESS.md` and the UAT docs for the latest verification status.
- Treat the checklist below as phase build history + remaining tasks, not a real-time branch snapshot.

## Implementation Tasks
### Backend (`posawesome/posawesome/api/posapp.py`)
- [x] Add whitelisted API to create and submit `Sales Order` from POS cart payload (SA token path). *(local working tree; pending UAT)*
- [x] Return token slip metadata (SO name, token last4, customer, SA user, totals, timestamps). *(local working tree; pending UAT)*
- [x] Add/extend relay workflow state helper to support `sales_order` linkage and timing field updates. *(local working tree; pending migration/UAT)*
- [x] Add monitor board API for ticket sidebar (`get_relay_workflow_monitor_board`). *(Phase 1B, local working tree)*
- [x] Add non-cash session bootstrap API for SA/non-cash roles (`bootstrap_pos_session`). *(Phase 1B, local working tree; pending UAT)*
- [x] When cashier later creates SI, attach SI to existing SO-linked workflow state (without breaking invoice-first legacy records). *(helper fallback/update path implemented locally; verify in UAT)*

### DocType (`POS Relay Workflow State`)
- [x] Add `sales_order` Link field to `Sales Order`. *(local working tree; migrate required)*
- [x] Allow SO-first record creation (do not require `sales_invoice` at initial creation). *(local working tree; migrate required)*
- [x] Preserve `sales_invoice` for cashier completion stage. *(local working tree)*
- [x] Add monitor timing fields (`order_taken_at`, `paid_at`, `pick_started_at`, `picked_at`, `status_changed_at`) and scope metadata (`business_date`, optional `pos_opening_shift`). *(Phase 1B, local working tree; migrate required)*

### Frontend (`Invoice.vue`)
- [x] Route SA `Save/New` to new SO token API instead of invoice draft token path. *(local working tree; pending UAT)*
- [ ] Keep non-SA `Save/New` behavior unchanged unless explicitly scoped.
- [x] Show token dialog based on SO response metadata. *(local working tree; pending UAT)*
- [x] Implement token slip print with required fields and symbol rendering. *(QR/barcode via browser-loaded libs; pending browser/printer UAT)*
- [x] Use canonical token id = full `Sales Order.name`; display last4 for human fallback. *(local working tree)*
- [x] Keep cart reset behavior only after successful SO create/token dialog flow begins. *(local working tree)*

### Frontend (`Payments.vue`, `SalesOrders.vue`)
- [ ] Preserve SO -> SI preference for cashier.
- [ ] Ensure token id carries through SO-loaded flow into relay commit payload where relevant.
- [ ] Keep direct invoice fallback path available.
- [x] Emit workflow monitor refresh after payment success (cloud and relay commit success callbacks). *(Phase 1B, local working tree)*

### Frontend (`Pos.vue`, `WorkflowTicketRail.vue`) - Phase 1B
- [x] Add ticket-style left sidebar icon/rail visible in POS shell. *(local working tree; pending UAT)*
- [x] Show collapsed pending count badge and expandable panel. *(local working tree; pending UAT)*
- [x] Poll monitor API and support `All (date)` / `Mine` filter. *(local working tree; pending UAT/load testing)*
- [x] Show customer, SA name, order taken time, current status, time in status, and grand total. *(local working tree; pending UAT)*
- [x] Default monitor scope to `POS Profile + business date` so rows appear before cashier shift open. *(local working tree; pending UAT)*
- [x] Support SA no-cash POS session entry and virtual/no-opening-shift session payload handling. *(local working tree; pending UAT/migration)*
- [ ] Validate mobile overlay behavior and responsiveness on target devices.

### Backend hook (`posawesome/posawesome/api/invoice.py`)
- [x] Guard against duplicate SO creation on SI submit when invoice already originates from SO. *(local working tree; pending regression verification)*

### Relay integration (minimal Phase 1)
- [x] Best-effort relay token sync after SA SO creation using `/relay/token/create`. *(local working tree; pending UAT)*
- [x] Include optional source metadata in payload where harmless (`source_doctype`, `source_name`). *(local working tree)*

### Documentation updates during implementation
- [x] Add Phase 1B ticket sidebar workflow monitor requirement to core docs. *(local working tree)*
- [x] Document SA no-cash session + profile/date monitor scope and SO series config/filtering plan in plans docs. *(historical annotation; later branch work implemented the SO series feature)*
- [ ] Update `../01-role-based-workflow-spec.md` statuses from `Partial` -> `Implemented` for Phase 1 items after UAT confirmation.
- [ ] Log commit IDs and verification notes in `../CHANGELOG_PROGRESS.md` after commit.

## Tests and Verification
### Automated (Cypress, post-deploy)
- [ ] SA login (OTP)
- [ ] SA cannot use `PAY`
- [ ] SA creates SO token using first available item
- [ ] Token dialog shows SO-backed token details
- [ ] Slip print content contains required text/QR/barcode placeholders
- [ ] Ticket sidebar count increases after SA token creation and row shows required fields/timer (profile/date scope, no cashier shift required)
- [ ] SA can enter POS without opening cash amounts table (non-cash session bootstrap)

### Manual / UAT (dev site)
- [ ] Confirm submitted `Sales Order` created (not SI) when SA creates token
- [ ] Confirm SO `owner` is correct SA user
- [ ] Confirm no SI number consumed at SA stage
- [ ] Confirm cashier can `Select S.O` and pay to create SI
- [ ] Confirm relay token sync is non-blocking if relay token create fails
- [ ] Confirm ticket sidebar row appears immediately (or within polling interval) using `PJ7 CASHIER` + business date scope (even before cashier shift open)
- [ ] Confirm `Mine` filter shows SA-owned order rows
- [ ] Confirm row status/timer updates after cashier payment and pick/dispatch transitions

## Known Risks
- Regressing existing cashier `Save/New` or `Held` invoice flows while branching SA behavior.
- Breaking workflow state assumptions if SO-first and SI-first records are mixed incorrectly.
- Barcode/QR rendering issues across browsers/printers.

## Deferred Items
- Capture `sales_partner` during SA token creation stage.
- Add explicit visible Sales Order field for SA attribution (owner is accepted for now).
- SA relay-first/offline token creation (Phase 4).
- Ticket sidebar row actions (open/approve/transition) beyond read-only monitor.

## Exit Criteria
- SA token is a submitted `Sales Order`.
- Token slip prints required fields (customer, SA, date/time, total, QR, barcode, token last4).
- SI is created only at cashier payment step in the preferred flow.
- Cashier SO -> SI flow remains operational.
- Ticket sidebar monitor rail is visible to all roles and tracks profile/date-scoped pending orders with timing.
- Phase 1 docs updated with verification evidence and remaining defects.

## Cross-References
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
