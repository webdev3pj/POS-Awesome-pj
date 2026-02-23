# Phase 4 - SA Relay-First Offline Token Creation

## TL;DR (Business Owner)
- This phase lets SA continue creating orders/tokens when the cloud is down (using the local relay first).
- It happens after the online SA flow is proven stable.
- The relay then syncs those SA orders back to cloud Sales Orders later.

## See also
- `../README.md`
- `../00-ai-agent-start-here.md`
- `../01-role-based-workflow-spec.md`
- `../02-master-implementation-plan.md`
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../CHANGELOG_PROGRESS.md`

## Document Currency
- This is a current planning doc for a deferred phase (Phase 4).
- SA online-first `Sales Order` token flow is already implemented; this phase covers the later relay-first/offline extension only.

## Purpose
Enable Sales Associates to create tokens/orders when cloud ERPNext is unavailable, using relay-first local persistence and later sync to cloud `Sales Order`.

## In Scope
- SA local token/order creation through relay when cloud is down
- Relay storage and sync design for SO creation events
- POS UX for offline SA token confirmation and later cloud reconciliation
- Conflict handling and retry semantics for SO sync

## Out of Scope
- Cashier payment commit redesign (existing relay commit path already covers cashier local-first)
- Unrelated POS feature work

## Completed So Far
- Relay token storage exists (`relay_tokens`, `relay_token_lines`).
- Relay outbox and sync worker foundation exists.
- SA online token concept now exists as a submitted `Sales Order` flow (implemented in branch history and dev-site UAT verified); this phase extends that to relay-first/offline creation.

## Implementation Tasks
- [ ] Define local relay representation for SA order payload (extend token model vs add dedicated local SO model/event payload).
- [ ] Add relay endpoint(s) for SA relay-first token/order creation with trusted auth/role checks (depends on Phase 3).
- [ ] Add outbox event type and sync worker mapping to create cloud `Sales Order`.
- [ ] Define reconciliation behavior when cloud SO creation succeeds (store cloud SO name/reference and update token metadata).
- [ ] Define conflict behavior (duplicate token, item/price changes, customer mismatch, validation failures).
- [ ] Add POS offline SA UI flow and messaging (cloud down but relay available).
- [ ] Add recovery UI for pending/failed SA cloud SO sync records.
- [ ] Update docs and runbooks for offline SA procedures.

## Tests and Verification
- [ ] Simulated cloud outage with relay reachable: SA can create token/order locally.
- [ ] Later cloud recovery: relay sync creates cloud SO and links reference.
- [ ] Duplicate retry/idempotency behavior does not create duplicate SOs.
- [ ] Operator messaging is clear during pending sync and failure states.

## Known Risks
- Cloud SO validation failures may block sync for locally accepted SA tokens.
- Pricing/promotions divergence if cloud rules change during outage.
- UX confusion if local token exists but cloud SO reference is delayed.

## Deferred Items
- Advanced conflict resolution UI beyond initial retry/review workflow.

## Exit Criteria
- SA can continue token creation while cloud ERPNext is unavailable (with relay online).
- Cloud SO sync and reconciliation are reliable and auditable.
- Offline SA runbook exists and is validated.

## Cross-References
- `../03-offline-edge-relay-and-windows-service-spec.md`
- `../02-master-implementation-plan.md`
- `../CHANGELOG_PROGRESS.md`
