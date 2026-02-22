# kilo-codex-v2 Offline Continuity Execution Checklist

## Scope lock
- Feature applies only when `custom_have_token = 1` on POS Profile.
- For `custom_have_token = 0`, behavior remains unchanged.
- Goal is local-first continuity across SA, Cashier, Picker, Dispatch while cloud is down.

## Work packages

### WP1 Relay storage model
- [ ] Add tables for token, token_lines, cashier_sessions, local_sales, local_sale_lines.
- [ ] Add tables for idempotency_records, pick_events, dispatch_events, outbox_events.
- [ ] Add unique indexes:
  - token_id
  - idempotency_key
  - one consumed commit per token
- [ ] Add migration-safe init path for existing relay DB.

### WP2 Token lifecycle APIs
- [ ] `POST /relay/token/create`
- [ ] `GET /relay/token/<token_id>`
- [ ] `POST /relay/token/<token_id>/void`
- [ ] Enforce token expiry and terminal states:
  - TOKEN_OPEN
  - TOKEN_EXPIRED
  - TOKEN_VOID
  - TOKEN_PAID

### WP3 Cashier sessions
- [ ] `POST /relay/session/open` with pos_profile_id cashier_user_id device_id
- [ ] `POST /relay/session/close` with offline-safe close
- [ ] Allow concurrent OPEN sessions for same POS Profile and different cashiers/devices.
- [ ] Queue SESSION_OPEN and SESSION_CLOSE outbox events.

### WP4 Commit invoice atomic path
- [ ] `POST /relay/commit-invoice` requiring idempotency_key.
- [ ] Implement atomic token consume lock.
- [ ] Prevent double-pay returning TOKEN_ALREADY_PAID.
- [ ] Replay same idempotency_key returns same local_sale_ref.
- [ ] Persist local sale with status SALE_COMMITTED_LOCAL and SALE_SYNC_PENDING.
- [ ] Return stable local_sale_ref in response.

### WP5 Picking and dispatch local-first
- [ ] `GET /relay/pick-queue` from locally paid sales.
- [ ] `POST /relay/pick/update` supporting:
  - PAID_PENDING_PICK
  - PICK_IN_PROGRESS
  - PICK_EXCEPTION
  - PICKED_READY_FOR_RELEASE
- [ ] `POST /relay/dispatch/release` enforcing paid plus picked-ready gate.
- [ ] Record immutable release user and release timestamp.

### WP6 Offline customer and item continuity
- [ ] `POST /relay/customer/upsert` local-first with outbox sync.
- [ ] `GET /relay/items/search` from local cache.
- [ ] Add cache refresh mechanism when cloud is reachable.

### WP7 Sync reliability and idempotent cloud reconciliation
- [ ] Expand durable outbox event types:
  - CUSTOMER_UPSERT
  - TOKEN_CREATED
  - SALE_COMMITTED
  - PICK_EVENT
  - RELEASE_EVENT
  - SESSION_OPEN
  - SESSION_CLOSE
- [ ] Add retry policy with bounded backoff and structured failure logging.
- [ ] Attach unique relay event id for cloud idempotency.
- [ ] On timeout, implement lookup before recreate to avoid duplicates.

### WP8 POS UI behavior for enabled profiles
- [ ] Add explicit mode banner states:
  - OFFLINE MODE Relay Active
  - RELAY DOWN Offline continuity unavailable
- [ ] Block relay-dependent actions when relay is down and profile is enabled.
- [ ] Route token and commit flows to new relay endpoints.
- [ ] Display local_sale_ref clearly after Pay and Finalize.
- [ ] Keep disabled-profile UX exactly unchanged.

### WP9 Acceptance tests evidence
- [ ] Test 1 multi-device offline continuity across SA Cashier Picker Dispatch.
- [ ] Test 2 multi-cashier same profile concurrent sessions.
- [ ] Test 3 double-pay prevention.
- [ ] Test 4 idempotency replay returns same local_sale_ref.
- [ ] Test 5 outage recovery sync no duplicate SI mapping.

## Definition of done
- [ ] All acceptance tests pass with recorded logs/screenshots.
- [ ] No regression for disabled profiles.
- [ ] Updated handoff markdown and regenerated PDF.
- [ ] Changes committed and pushed to branch `kilo-codex-v2`.
