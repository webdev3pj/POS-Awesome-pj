# 03 - Offline Edge Relay and Windows Service Specification

## TL;DR (Business Owner)
- This file explains what the local relay stores, how it syncs later, and how it runs on the Windows store machine.
- The relay is what protects store operations when the cloud is down, especially for cashier commits.
- The new POS sidebar monitor is not a relay screen yet; it reads ERPNext workflow state first (v1).
- LAN-only relay mode (browser-LAN health as submit gate) and cashier prompted cloud fallback are now implemented and live-validated on the OptiPlex/dev site.
- SA offline-first order creation is planned later (Phase 4), after the online SA flow is stable.
- Windows service/runbook details stay here so deployment and support are repeatable.

## See also
- `README.md`
- `00-ai-agent-start-here.md`
- `runbooks/optiplex-edge-relay-next-session.md`
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`
- `runbooks/shop-pc-lan-relay-setup-non-technical.md`
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `phases/phase-4-sa-relay-first-offline-token-creation.md`
- `phases/phase-5-uat-deployment-observability-hardening.md`
- `CHANGELOG_PROGRESS.md`

## Document Currency
- This is the current offline/relay reference for the active branch family and is aligned with relay-focused work through `codex-4-picker-dispatch` (inherits `codex-3-edge-relay` LAN-only/fallback work and adds picker/dispatch relay-local workflow validation).
- Some sections describe target-state service packaging/security that is still planned (especially Phase 3/Phase 4+ items).
- For the latest verified relay behavior, use:
  - `CHANGELOG_PROGRESS.md`
  - `uat/2026-02-23-local-edge-relay-smoke.md`
  - `uat/2026-02-24-optiplex-lan-https-relay-sa-cashier-e2e-demo.md`
  - `uat/2026-02-24-optiplex-picker-dispatch-shared-shell-relay-local-first.md`
  - `runbooks/optiplex-edge-relay-next-session.md`
- Historical baseline note:
  - branch baseline `424c79a` documented the LAN/private-cloud constraint before the LAN-only mode implementation.
- Current implemented state on `codex-3-edge-relay` (verified 2026-02-24):
  - LAN-only relay mode (`browser-LAN` health as submit gate)
  - prompted cloud fallback when relay is down but cloud is up
  - OptiPlex LAN HTTPS reverse-proxy (Caddy) + shop-PC certificate trust setup guidance
- Current implemented state on `codex-4-picker-dispatch` (verified 2026-02-24 on OptiPlex/dev site):
  - shared-shell picker/dispatch actions persist locally through relay (`/relay/pick/update`, `/relay/dispatch/release`)
  - line-wise picker quantities persist into `relay_local_sale_lines.payload.picker` with UOM/conversion metadata
  - dispatch release updates local relay sale status and appends local dispatch event
  - relay outbox correctly queues `PICK_EVENT` / `RELEASE_EVENT`, but cloud sync for these events is currently failing with `500` in the dev backend

## Purpose
Define the offline continuity design and operations model for the Edge Relay, including:
- what is stored locally,
- how local-first commit and sync work,
- retry/idempotency semantics,
- and how the relay is operated on Windows (OptiPlex deployment model).

This is the offline-only reference and should be kept synchronized with `relay/relay/storage.py`, `relay/relay/app.py`, `relay/README.md`, and `relay/SETUP_CHECKLIST_OPTIPLEX.md`.

For a step-by-step relay-host startup/test sequence (especially when a new AI session starts on the OptiPlex with no prior chat context), use:
- `runbooks/optiplex-edge-relay-next-session.md`
- `runbooks/optiplex-fresh-codex-zero-context-handoff.md`

## Offline Scope and Goals
### Goals
- Keep store operations moving during cloud/API outages.
- Prevent duplicate payment commits (idempotency).
- Preserve an auditable local event trail for pick/dispatch and sync outcomes.
- Provide operators/administrators visibility into queue/outbox/transactions.

### Non-goals (current phases)
- Full offline SA token -> cloud SO sync (deferred to Phase 4).
- Full enterprise-grade Windows Service packaging in current branch (current bootstrap is startup task + batch launcher).

## Workflow Monitor Data Source (v1 and Future)
### v1 source of truth (Phase 1B)
- The ticket sidebar workflow monitor rail uses ERPNext `POS Relay Workflow State` records as the display source.
- This gives cross-role visibility in the POS UI for profile/date-scoped pending orders and timing metrics while the SA online-first Sales Order flow is stabilized.
- Timing fields expected on the ERPNext workflow state for monitoring:
  - `order_taken_at`
  - `paid_at`
  - `pick_started_at`
  - `picked_at`
  - `released_at`
  - `status_changed_at`

### Future offline implication (Phase 4+)
- When SA relay-first/offline token creation is introduced, the original local creation timestamp must be preserved so `order_taken_at` remains meaningful after cloud sync.
- When business-date monitor scoping is active, relay/cloud sync must preserve the original order business date so dashboard timing remains accurate across outages.
- WebSocket/push updates are deferred; v1 monitor uses polling + local event-trigger refresh.

## Relay Topology
- POS browser (store devices) talks to local relay over LAN.
- Relay stores data in local SQLite.
- Relay sync worker pushes events to ERPNext/Frappe Cloud when reachable.
- ERPNext cloud may also need to reach relay `/health` for backend diagnostics using a public/tunnel URL (`public_base_url`).
- POS workflow monitor rail (Phase 1B) reads an ERPNext API and polls for near-real-time updates; it is not a relay-native screen yet.

## Frappe Cloud + Private LAN Relay Constraint (Important)
### Historical baseline behavior (before LAN-only mode, e.g. `424c79a`)
- Relay-enabled cashier submit logic depended on relay connectivity status checked by an ERPNext/Frappe backend API (`get_relay_connectivity_status`).
- On Frappe Cloud, that backend check runs from the cloud network, not from the store LAN.
- A private LAN relay URL such as `http://192.168.50.168:8787` is not routable from Frappe Cloud, so the backend reported relay unreachable and the POS could block relay-backed submit.

### Current implemented behavior (LAN-only mode on `codex-3-edge-relay`)
- POS can use `browser-LAN` relay health (for example `https://192.168.50.168/health`) as the effective submit gate when POS Profile mode is set to LAN-only.
- Cloud-side relay reachability is still useful for diagnostics, but it is not the submit blocker in LAN-only mode.
- Cashier can be prompted to fall back to direct cloud submit when relay is down but cloud is up (POS Profile toggle controlled).

### Browser transport note (HTTPS -> HTTP)
- The Frappe Cloud POS page is served over HTTPS.
- Direct browser `fetch()` from `https://<site>.frappe.cloud` to `http://192.168.x.x:8787` may be blocked by browser mixed-content policy.

### Deployment patterns for Frappe Cloud + OptiPlex relay
#### Option A (implemented and validated for shop LAN use)
- Use LAN HTTPS on the OptiPlex (for example `https://192.168.50.168`) and configure POS Profile LAN-only mode.
- Set that LAN HTTPS URL in:
  - POS Profile `Edge Relay URL` (`custom_edge_relay_url`) on the cloud site
  - relay `public_base_url` in relay setup/config
- Browser/LAN reachability and certificate trust on shop PCs is required.
- Cloud backend diagnostics may still fail to reach a private LAN IP and should be treated as diagnostic-only in LAN-only mode.

#### Option B (still valid if cloud-reachable diagnostics are required)
- Use a public HTTPS URL (tunnel or reverse proxy) that forwards to the OptiPlex relay.
- Set the same public URL in:
  - POS Profile `Edge Relay URL` (`custom_edge_relay_url`)
  - relay `public_base_url`
- Use when backend/cloud-side relay checks must pass from outside the store LAN.

## Relay Configuration Files and Paths
Defined in `relay/relay/storage.py`:
- `relay/data/relay.db`: SQLite database
- `relay/data/relay_config.json`: relay configuration

Default config keys (current code):
- `frappe_base_url`
- `api_key`
- `api_secret`
- `relay_host` (default `0.0.0.0`)
- `relay_port` (default `8787`)
- `public_base_url`
- `site_name`
- `offline_mode`
- `poll_seconds`
- `allowed_subnet`

### Config location reminders (cloud + relay)
- Cloud site (frontend/admin): POS Profile field `Edge Relay URL` (`custom_edge_relay_url`)
- Cloud site fallback (server config): `posa_edge_relay_url` in `site_config.json`
- Relay host (OptiPlex): relay config key `public_base_url` in `relay/data/relay_config.json` (or relay setup UI)
- Local-only Cypress secrets (for relay-host testing if Cypress runs there): repo root `.env` with `CYPRESS_baseUrl`, `CYPRESS_username`, `CYPRESS_password`, `CYPRESS_totpUri` (ignored by git)

## What Relay Stores Locally (Table-by-Table)
Source of truth: `relay/relay/storage.py` `init_db()`.

### Monitor note (important)
- Phase 1B does **not** add a new relay storage table for the sidebar monitor.
- The v1 monitor is ERPNext workflow-state driven so all roles can view the same normalized state in the POS UI while Phase 1 is stabilized.
- Relay dashboards/APIs remain the primary local operational source when cloud diagnostics are unavailable.

### `relay_queue` (legacy compatibility queue)
Status: `Implemented`, retained for backward compatibility.

Purpose:
- Legacy generic queue table kept to avoid breaking older relay scaffolding flows.

Key fields:
- `id`
- `event_type`
- `payload`
- `status`
- `retries`
- `last_error`
- `created_at`, `updated_at`

Notes:
- v2/v3 flows primarily use `relay_outbox` for local-first sync semantics.

### `relay_tokens`
Purpose:
- Store token headers created at SA/draft stage and updated through token lifecycle.

Key fields:
- `token_id` (PK)
- `pos_profile_id`
- `cashier_user_id` (naming legacy; may carry token creator in current payloads)
- `customer_id`, `customer_name`
- `status` (`TOKEN_OPEN`, `TOKEN_PAID`, `TOKEN_VOID`, etc.)
- `expires_at`
- void fields: `void_reason`, `voided_by`
- consume fields: `consumed_sale_ref`, `consumed_at`
- `created_at`, `updated_at`

Semantics:
- Token creation is idempotent for retried/open states.
- Paid/void tokens should not be recreated.

### `relay_token_lines`
Purpose:
- Store line items for a token.

Key fields:
- `id`
- `token_id` (FK to `relay_tokens`)
- `item_code`, `item_name`
- `qty`, `uom`, `rate`, `amount`
- `payload` (raw serialized line)
- `created_at`

Semantics:
- Rewritten on idempotent token-create retry if token is reset to open.

### `relay_cashier_sessions`
Purpose:
- Track cashier session lifecycle at relay.

Key fields:
- `session_id` (PK)
- `pos_profile_id`
- `cashier_user_id`
- `role` (current field exists; trust hardening still pending)
- `device_id`
- `status` (`OPEN`, closed states)
- `opened_at`, `closed_at`
- `close_note`
- `created_at`, `updated_at`

Semantics:
- Used by relay commit path to tie commits to a cashier session.
- Role is stored but not yet enforced as trusted authorization.

### `relay_local_sales`
Purpose:
- Primary local-first committed sale header record after successful relay commit.

Key fields:
- `local_sale_ref` (PK, `LSR-*` style)
- `token_id`
- `pos_profile_id`
- `cashier_user_id`, `cashier_session_id`, `device_id`
- `idempotency_key` (UNIQUE)
- sale state fields:
  - `sale_status`
  - `pick_status`
  - `dispatch_status`
  - `paid`
- amount/customer fields:
  - `total`, `net_total`
  - `customer_id`, `customer_name`
- payload fields:
  - `invoice_payload`
  - `data_payload`
- cloud sync fields:
  - `cloud_invoice_name`
  - `cloud_sync_status`
  - `cloud_sync_error`
- release audit fields:
  - `released_by`, `released_at`
- `created_at`, `updated_at`

Semantics:
- Created atomically on relay commit.
- Serves as the local operational record for pick/dispatch workflows.
- `idempotency_key` prevents duplicate local sales on retries/double clicks.

### `relay_local_sale_lines`
Purpose:
- Store per-line details for each local committed sale.

Key fields:
- `id`
- `local_sale_ref` (FK)
- `item_code`, `item_name`
- `qty`, `uom`, `rate`, `amount`
- `line_status`, `pick_status`
- `payload`
- `created_at`, `updated_at`

Semantics:
- Supports pick queue and line-level operational views.
- `codex-4-picker-dispatch` extends line payload usage by persisting picker results inside `payload.picker` (for example `picked_qty`, `picked_uom`, `ordered_uom`, `conversion_factor`, `picked_stock_qty`, `pick_status`) so fulfillment edits survive refresh/offline sessions.

### `relay_idempotency`
Purpose:
- Persist request/reply mapping for idempotent commit replay behavior.

Key fields:
- `idempotency_key` (PK)
- `token_id`
- `local_sale_ref`
- `request_hash`
- `response_payload`
- `created_at`, `updated_at`

Semantics:
- Same idempotency key returns the original commit response instead of duplicating a sale.

### `relay_pick_events`
Purpose:
- Append-only pick workflow events.

Key fields:
- `id`
- `local_sale_ref` (FK)
- `picker_user_id`
- `event_type`
- `notes`
- `payload`
- `created_at`

Semantics:
- Operational audit log for picker actions and exceptions.

### `relay_dispatch_events`
Purpose:
- Append-only dispatch/release workflow events.

Key fields:
- `id`
- `local_sale_ref` (FK)
- `dispatcher_user_id`
- `event_type`
- `notes`
- `payload`
- `created_at`

Semantics:
- Operational audit log for gate release actions.

### `relay_customers`
Purpose:
- Local customer cache and relay-local customer fallback records.

Key fields:
- `customer_id` (PK)
- `customer_name`
- `mobile_no`, `email_id`, `tax_id`
- `payload` (full JSON)
- `updated_at`, `created_at`

Semantics:
- Supports offline/failed-cloud customer search or local fallback customer handling.

### `relay_items_cache`
Purpose:
- Local item search cache for offline continuity and faster lookups.

Key fields:
- `item_code` (PK)
- `item_name`
- `stock_uom`
- `barcode`
- `rate`
- `payload` (full JSON)
- `updated_at`, `created_at`

Semantics:
- Refreshed via relay endpoints from cloud or explicit refresh workflows.

### `relay_outbox`
Purpose:
- Durable queue of cloud sync events for eventual consistency.

Key fields:
- `event_id` (PK)
- `event_type`
- `idempotency_key`
- `local_ref`
- `payload`
- `status`
- `retries`
- `next_attempt_at`
- `last_error`
- `cloud_ref`
- `created_at`, `updated_at`

Semantics:
- Drives sync worker retries and backoff.
- `next_attempt_at` schedules future retry attempts.
- This is the primary queue/outbox for the current local-first SA/Cashier relay commit workflow (v2 behavior).

## Indices and Performance Notes
Current indices in `init_db()`:
- `idx_relay_tokens_profile_status`
- `idx_relay_sessions_profile_status`
- `idx_relay_sales_profile_pick_dispatch`
- `idx_relay_outbox_status_next_attempt`

These support common dashboard/query paths and worker polling filters.

## Storage Semantics (How the Relay Behaves)
### Local-first commit
- Relay commit endpoint stores local sale and lines before cloud sync.
- Payment success can be acknowledged locally (with `local_sale_ref`) while cloud sync is deferred.

### Idempotency
- Commit requests require `idempotency_key`.
- Replays return original response instead of duplicating a committed local sale.

### Token consumption and double-pay prevention
- Token lifecycle is updated during commit.
- Duplicate token payment attempts are rejected or replayed via idempotency semantics.

### Eventual consistency
- Local operation success and cloud sync success are separate states.
- Operators must use outbox/transaction views to monitor backlog and failures.
- This separation is now directly observed in live Picker/Dispatch UAT: local relay pick/release updates succeeded while outbox sync to cloud retried due backend `500` errors.

## Sync Event Types and Cloud Mapping (Current Known Behavior)
Examples present in branch:
- `SALE_COMMITTED` -> cloud sync path exists (`Implemented` foundation; live dev-site relay-first cashier UAT verified)
- `PICK_EVENT` -> local enqueue/outbox path verified (`Implemented` local-first foundation); dev backend sync endpoint currently returns `500` (`Partial` cloud parity)
- `RELEASE_EVENT` -> local enqueue/outbox path verified (`Implemented` local-first foundation); dev backend sync endpoint currently returns `500` (`Partial` cloud parity)
- `TOKEN_CREATED`, `SESSION_OPEN`, `SESSION_CLOSE` -> currently intentional no-op cloud ack in worker (`Partial parity`)

## What Is NOT Stored on Relay (Current Model)
- Full ERPNext database records beyond cached/serialized payloads required for local workflows.
- Final authoritative cloud accounting state (relay stores local snapshots and sync references, not ERPNext as source of truth).
- Secure authenticated identity guarantees (current role/user payload trust is incomplete; Phase 3 addresses this).

## Failure and Conflict Handling
### Cloud unreachable
- Relay continues local commit for supported relay-enabled cashier flows.
- Outbox accumulates events for later sync.

### Relay unreachable (from POS)
- In LAN-only mode:
  - if cloud is up and POS Profile fallback toggle is enabled, cashier is prompted and may submit directly to cloud
  - if cloud is down (or fallback toggle is disabled), cashier submit is blocked
- In non-LAN-only/older behavior, cloud relay diagnostics may still block relay-backed submit when the relay URL is private LAN only.

### Duplicate submit / double-click
- Idempotency should return same `local_sale_ref`.

### Partial sync failure
- Outbox records retries, last error, and next attempt.
- Dashboard/outbox endpoints provide visibility.

## Relay HTTP/Operational Endpoints (Selected)
### Health and diagnostics
- `/health`
- `/queue`
- `/api/queue`
- `/api/outbox`
- `/api/metrics`
- `/api/transactions`
- `/api/transactions/<local_sale_ref>`
- `/api/erpnext-access-check`

### Queue/Outbox observability note
- `/queue` and `/api/queue` expose the legacy compatibility queue (`relay_queue` table).
- SA/Cashier local-first relay commit flow is primarily observable via:
  - relay dashboard `/` (Outbox Counters + Transaction Timeline)
  - `/api/outbox`
  - `/api/transactions`
  - `/api/transactions/<local_sale_ref>`

### Relay workflow endpoints
- `/relay/token/create`
- `/relay/token/<token_id>`
- `/relay/token/<token_id>/void`
- `/relay/session/open`
- `/relay/session/current`
- `/relay/session/close`
- `/relay/customer/upsert`
- `/relay/customer/search`
- `/relay/items/search`
- `/relay/items/refresh`
- `/relay/items/refresh-from-cloud`
- `/relay/commit-invoice`
- `/relay/pick-queue`
- `/relay/pick/update`
- `/relay/dispatch/release`

## Windows Operation Model (Current Branch Reality)
### Current startup model (`Implemented`)
The current branch documents and supports a practical Windows launcher workflow, not a full Windows Service binary install by default:
- `relay/start_relay.bat` performs install/bootstrap/start tasks.
- UI bootstrap creates:
  - inbound firewall rule,
  - Windows startup task (launch on user logon).

### Current documented daily usage
- Start relay via `start_relay.bat`.
- Check status at `/health`.
- Monitor queue/outbox via dashboard and JSON endpoints.

## Windows Service Specification (Program Target / Ops Guidance)
This section is the operational spec for a maintainable Windows deployment, whether implemented via Scheduled Task, NSSM, or native service wrapper later.

### Installation and Update Requirements
- Fixed install location on always-on machine (OptiPlex).
- Python runtime and venv pinned/managed.
- Dependency install from `relay/requirements.txt`.
- Safe restart procedure after code update.
- Version/commit recorded in a local text file or dashboard field (recommended future enhancement).

### Run Identity
- Prefer a dedicated Windows user account for relay runtime (future hardening target).
- Minimum file permissions to relay folder and `relay/data/`.
- Do not run with unnecessary admin rights outside bootstrap steps.

### Startup and Recovery
- Startup mode: automatic on boot or user logon (current implementation uses startup task on logon).
- Recovery: restart on failure (if wrapped as service) or scheduled task relaunch policy.
- Document manual restart command and recovery procedure.

### Firewall and Network
- Allow inbound on relay port (default `8787`) on private profile.
- Restrict LAN reachability to expected subnet (`allowed_subnet` config where enforced/used).
- Reserve DHCP lease / static assignment for stable LAN URL.

### Logging and Diagnostics
Current branch:
- Browser dashboard + JSON endpoints provide operational visibility.
- Errors surfaced through outbox rows and API responses.

Recommended operational additions (future):
- File-based rotating logs.
- Windows Event Log integration for service lifecycle events.

### Backup and Restore (Relay Data)
Minimum backup artifacts:
- `relay/data/relay.db`
- `relay/data/relay_config.json`

Backup rules:
- Prefer scheduled backups outside peak hours.
- Validate restore procedure on a spare machine/dev environment.
- Document backup retention and privacy handling (contains customer/order payloads).

Restore procedure (high level):
1. Stop relay process.
2. Restore `relay.db` and `relay_config.json`.
3. Start relay.
4. Verify `/health`, `/api/outbox`, `/api/transactions`.
5. Confirm outbox resumes retry behavior safely.

## `public_base_url` and Cloud Reachability (Critical)
### Why it matters
ERPNext/Frappe Cloud cannot reach LAN-only relay addresses for backend diagnostics.

### Required setup
- Configure a public/tunnel HTTPS relay URL in relay setup (`public_base_url`).
- Set POS Profile `custom_edge_relay_url` to a URL ERPNext can reach for server-side checks (or document split LAN/public strategy carefully).
- Validate via `/api/erpnext-access-check`.

### Common failure mode
- Relay works on LAN for POS browsers but appears unreachable to ERPNext cloud because only `192.168.x.x` URL is configured.

## Monitoring and Operations Checklist (Condensed)
- Relay `/health` returns healthy.
- Dashboard counters update.
- `/api/outbox` backlog is understood and monitored.
- Team understands `/queue` (legacy queue) vs `relay_outbox` (current local-first cashier/SA event sync path).
- `/api/transactions` shows recent local sales.
- `public_base_url` reachability check passes after network changes.
- Windows startup/firewall settings remain intact after OS updates.

## Phase Mapping (Offline-Focused)
- Phase 3: relay auth and authorization hardening.
- Phase 4: SA relay-first/offline token creation and SO cloud sync.
- Phase 5: observability, runbooks, backup/restore/UAT hardening.

## See also
- `01-role-based-workflow-spec.md`
- `02-master-implementation-plan.md`
- `phases/phase-3-relay-auth-and-server-side-role-enforcement.md`
- `phases/phase-4-sa-relay-first-offline-token-creation.md`
- `phases/phase-5-uat-deployment-observability-hardening.md`
