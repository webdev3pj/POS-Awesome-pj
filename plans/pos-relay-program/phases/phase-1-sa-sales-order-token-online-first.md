# Phase 1 - SA Sales Order Token (Online-First)

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Purpose
Convert the Sales Associate token flow from draft `Sales Invoice`-based token generation to a submitted `Sales Order`-based token flow (online-first), preserving invoice-series audit integrity.

## In Scope
- SA token creation as submitted `Sales Order`
- Token slip print with QR + barcode + required fields
- Cashier-preferred `SO -> SI` flow preserved
- Workflow state support for SO-first token lifecycle
- Best-effort relay token sync using SO token id

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
- SA payment blocking exists in local UI changes (verify/commit and preserve).

### Current gap this phase closes
- Current token popup/print is tied to `new_invoice()` / draft `Sales Invoice` and derives token from SI name suffix.

## Implementation Tasks
### Backend (`posawesome/posawesome/api/posapp.py`)
- [ ] Add whitelisted API to create and submit `Sales Order` from POS cart payload (SA token path).
- [ ] Return token slip metadata (SO name, token last4, customer, SA user, totals, timestamps).
- [ ] Add/extend relay workflow state helper to support `sales_order` linkage.
- [ ] When cashier later creates SI, attach SI to existing SO-linked workflow state (without breaking invoice-first legacy records).

### DocType (`POS Relay Workflow State`)
- [ ] Add `sales_order` Link field to `Sales Order`.
- [ ] Allow SO-first record creation (do not require `sales_invoice` at initial creation).
- [ ] Preserve `sales_invoice` for cashier completion stage.

### Frontend (`Invoice.vue`)
- [ ] Route SA `Save/New` to new SO token API instead of invoice draft token path.
- [ ] Keep non-SA `Save/New` behavior unchanged unless explicitly scoped.
- [ ] Show token dialog based on SO response metadata.
- [ ] Implement token slip print with required fields and symbol rendering.
- [ ] Use canonical token id = full `Sales Order.name`; display last4 for human fallback.
- [ ] Keep cart reset behavior only after successful SO create/token dialog flow begins.

### Frontend (`Payments.vue`, `SalesOrders.vue`)
- [ ] Preserve SO -> SI preference for cashier.
- [ ] Ensure token id carries through SO-loaded flow into relay commit payload where relevant.
- [ ] Keep direct invoice fallback path available.

### Backend hook (`posawesome/posawesome/api/invoice.py`)
- [ ] Guard against duplicate SO creation on SI submit when invoice already originates from SO.

### Relay integration (minimal Phase 1)
- [ ] Best-effort relay token sync after SA SO creation using `/relay/token/create`.
- [ ] Include optional source metadata in payload where harmless (`source_doctype`, `source_name`).

### Documentation updates during implementation
- [ ] Update `../01-role-based-workflow-spec.md` statuses from `Partial` -> `Implemented` for Phase 1 items.
- [ ] Log commit IDs and verification notes in `../CHANGELOG_PROGRESS.md`.

## Tests and Verification
### Automated (Cypress, post-deploy)
- [ ] SA login (OTP)
- [ ] SA cannot use `PAY`
- [ ] SA creates SO token using first available item
- [ ] Token dialog shows SO-backed token details
- [ ] Slip print content contains required text/QR/barcode placeholders

### Manual / UAT (dev site)
- [ ] Confirm submitted `Sales Order` created (not SI) when SA creates token
- [ ] Confirm SO `owner` is correct SA user
- [ ] Confirm no SI number consumed at SA stage
- [ ] Confirm cashier can `Select S.O` and pay to create SI
- [ ] Confirm relay token sync is non-blocking if relay token create fails

## Known Risks
- Regressing existing cashier `Save/New` or `Held` invoice flows while branching SA behavior.
- Breaking workflow state assumptions if SO-first and SI-first records are mixed incorrectly.
- Barcode/QR rendering issues across browsers/printers.

## Deferred Items
- Capture `sales_partner` during SA token creation stage.
- Add explicit visible Sales Order field for SA attribution (owner is accepted for now).
- SA relay-first/offline token creation (Phase 4).

## Exit Criteria
- SA token is a submitted `Sales Order`.
- Token slip prints required fields (customer, SA, date/time, total, QR, barcode, token last4).
- SI is created only at cashier payment step in the preferred flow.
- Cashier SO -> SI flow remains operational.
- Phase 1 docs updated with verification evidence and remaining defects.

## Cross-References
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`
