# POS Role-Based Workflow Implementation

> Note (2026-02-22): This document is useful context, but the active branch-accurate role rules and phased execution status now live in `plans/pos-relay-program/01-role-based-workflow-spec.md` and `plans/pos-relay-program/02-master-implementation-plan.md`.

## Overview

This document describes the implementation of a role-based offline-first workflow for POS Awesome with Edge Relay. Each user is assigned exactly one role, enabling specific workflows while maintaining full offline capability through the Edge Relay.

---

## Role Definitions

All roles use the `cline-` prefix for identification in the system:

| Role ID | Display Name | Description |
|---------|---------------|--------------|
| `cline-Sales Associate` | Sales Associate (SA) | Builds customer cart and generates QR tokens |
| `cline-Cashier` | Cashier | Converts tokens to paid sales |
| `cline-Picker` | Picker | Physically picks goods for paid sales |
| `cline-Dispatch` | Dispatch / Gatekeeper | Verifies and releases goods at gate |
| `cline-Supervisor` | Supervisor | Handles exceptions and approvals |

---

## Core Workflow States

### Token Status Flow
```
TOKEN_OPEN → TOKEN_PAID → (consumed)
TOKEN_OPEN → TOKEN_VOID → (supervisor voided)
TOKEN_OPEN → TOKEN_EXPIRED → (auto-expired)
```

### Sale Status Flow
```
SALE_COMMITTED_LOCAL
    ↓
PAID_PENDING_PICK (after payment)
    ↓
PICK_IN_PROGRESS (picker started)
    ↓
PICKED_READY_FOR_RELEASE (picker completed)
    ↓
RELEASED (dispatcher released)
```

### Pick Exception Flow
```
PICK_EXCEPTION (shortage/substitute)
    ↓
SUPERVISOR_APPROVED (supervisor resolved)
    ↓
PICKED_READY_FOR_RELEASE (or partial release)
```

---

## Role Permissions Matrix

| Feature | Sales Associate | Cashier | Picker | Dispatch | Supervisor |
|---------|-----------------|---------|--------|----------|------------|
| Search/Create Customer | ✅ | ✅ | ❌ | ❌ | ❌ |
| Build Cart | ✅ | ✅* | ❌ | ❌ | ❌ |
| Create Token (QR) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Scan Token | ❌ | ✅ | ❌ | ❌ | ❌ |
| Edit Cart (pre-payment) | ❌ | ✅ | ❌ | ❌ | ✅** |
| Take Payment | ❌ | ✅ | ❌ | ❌ | ❌ |
| View Pick Queue | ❌ | ❌ | ✅ | ❌ | ✅ |
| Mark Items Picked | ❌ | ❌ | ✅ | ❌ | ❌ |
| View Dispatch Queue | ❌ | ❌ | ❌ | ✅ | ✅ |
| Release Goods | ❌ | ❌ | ❌ | ✅ | ❌ |
| Void Token | ❌ | ❌ | ❌ | ❌ | ✅ |
| Resolve Pick Exception | ❌ | ❌ | ❌ | ❌ | ✅ |
| Approve Overrides | ❌ | ❌ | ❌ | ❌ | ✅ |

*\* Cashier can edit cart before payment*  
*\*\* Supervisor can edit cart with reason and auth*

---

## API Endpoints

### Session Management

#### Open Session
```
POST /relay/session/open
{
    "pos_profile_id": "POS-001",
    "cashier_user_id": "user@company.com",
    "device_id": "device-001",
    "role": "cline-Cashier"  // New field
}
```

#### Close Session
```
POST /relay/session/close
{
    "session_id": "SESS-ABC123",
    "close_note": "End of shift"
}
```

### Token Operations

#### Create Token (Sales Associate)
```
POST /relay/token/create
{
    "pos_profile_id": "POS-001",
    "customer_id": "CUST-001",
    "customer_name": "John Doe",
    "items": [
        {"item_code": "ITEM-001", "qty": 2, "rate": 100.00}
    ],
    "created_by": "user@company.com",
    "role": "cline-Sales Associate"
}
```

Response:
```json
{
    "ok": true,
    "token": {
        "token_id": "A1B2C3D4E5",
        "status": "TOKEN_OPEN",
        "expires_at": "2026-02-22T04:23:00Z",
        "items": [...]
    }
}
```

#### Get Token
```
GET /relay/token/{token_id}
```

#### Void Token (Supervisor)
```
POST /relay/token/{token_id}/void
{
    "supervisor_user_id": "supervisor@company.com",
    "reason": "Customer requested cancellation",
    "role": "cline-Supervisor"
}
```

### Payment Operations

#### Commit Invoice (Cashier)
```
POST /relay/commit-invoice
{
    "idempotency_key": "unique-key-123",
    "token_id": "A1B2C3D4E5",
    "pos_profile_id": "POS-001",
    "cashier_user_id": "user@company.com",
    "cashier_session_id": "SESS-ABC123",
    "device_id": "device-001",
    "invoice": {
        "customer": "CUST-001",
        "items": [...],
        "grand_total": 200.00
    },
    "role": "cline-Cashier"
}
```

Response:
```json
{
    "ok": true,
    "local_sale_ref": "LSR-POS-20260222012345-ABC123",
    "sale_status": "SALE_COMMITTED_LOCAL",
    "pick_status": "PAID_PENDING_PICK",
    "dispatch_status": "PENDING"
}
```

### Pick Operations

#### Get Pick Queue
```
GET /relay/pick-queue?pos_profile_id=POS-001
```

#### Update Pick Status (Picker)
```
POST /relay/pick/update
{
    "local_sale_ref": "LSR-POS-20260222012345-ABC123",
    "picking_status": "PICKED_READY_FOR_RELEASE",
    "picker_user_id": "picker@company.com",
    "notes": "All items picked",
    "role": "cline-Picker"
}
```

Valid picking_status values:
- `PAID_PENDING_PICK` - Initial state
- `PICK_IN_PROGRESS` - Picker started picking
- `PICK_EXCEPTION` - Shortage/substitute needed
- `PICKED_READY_FOR_RELEASE` - Picking complete

### Dispatch Operations

#### Release Sale (Dispatch)
```
POST /relay/dispatch/release
{
    "local_sale_ref": "LSR-POS-20260222012345-ABC123",
    "dispatcher_user_id": "dispatcher@company.com",
    "notes": "Customer picked up",
    "release_method": "pickup",
    "role": "cline-Dispatch"
}
```

Response:
```json
{
    "ok": true,
    "local_sale_ref": "LSR-POS-20260222012345-ABC123",
    "dispatch_status": "RELEASED",
    "released_at": "2026-02-22T02:30:00Z"
}
```

### Supervisor Operations

#### Resolve Pick Exception
```
POST /relay/pick/update
{
    "local_sale_ref": "LSR-POS-20260222012345-ABC123",
    "picking_status": "PICKED_READY_FOR_RELEASE",
    "supervisor_user_id": "supervisor@company.com",
    "resolution": "approved_partial",
    "notes": "Approved 3 of 5 items, backorder 2",
    "role": "cline-Supervisor"
}
```

---

## Offline-First Rules

All operations MUST work offline when Edge Relay is reachable on store LAN:

1. **Shared State**: All data (tokens, sales, pick status, release status) lives on Edge Relay
2. **Device Independence**: Any device/user can continue from where another left off
3. **Idempotency**: All critical operations use idempotency keys to prevent duplicates
4. **Atomic Commits**: Token consumption is atomic - prevents double-payment

### Double-Payment Prevention

The relay implements:
1. **Token Status Lock**: `TOKEN_OPEN` → `TOKEN_PAID` is atomic
2. **Idempotency Keys**: Same `idempotency_key` returns same result
3. **Race Condition Handling**: First commit wins, second returns `TOKEN_ALREADY_PAID`

```
Cashier A (offline)              Cashier B (offline)
     |                                 |
     |-- commit (token_id=X) ------->|
     |                                 |-- commit (token_id=X)
     |<-- local_sale_ref=LSR-001 -----|   (fails: TOKEN_ALREADY_PAID)
     |                                 |
```

---

## Database Schema

### relay_cashier_sessions (Updated)
```sql
CREATE TABLE relay_cashier_sessions (
    session_id TEXT PRIMARY KEY,
    pos_profile_id TEXT NOT NULL,
    cashier_user_id TEXT NOT NULL,
    role TEXT,  -- NEW: cline-Sales Associate, cline-Cashier, etc.
    device_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    close_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### relay_tokens (Updated)
```sql
CREATE TABLE relay_tokens (
    token_id TEXT PRIMARY KEY,
    pos_profile_id TEXT NOT NULL,
    cashier_user_id TEXT,
    created_by_role TEXT,  -- NEW: role that created the token
    customer_id TEXT,
    customer_name TEXT,
    status TEXT NOT NULL DEFAULT 'TOKEN_OPEN',
    expires_at TEXT,
    void_reason TEXT,
    voided_by TEXT,
    voided_by_role TEXT,  -- NEW
    consumed_sale_ref TEXT,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### relay_local_sales (Updated)
```sql
CREATE TABLE relay_local_sales (
    local_sale_ref TEXT PRIMARY KEY,
    token_id TEXT,
    pos_profile_id TEXT NOT NULL,
    cashier_user_id TEXT,
    cashier_role TEXT,  -- NEW
    cashier_session_id TEXT,
    device_id TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    sale_status TEXT NOT NULL DEFAULT 'SALE_COMMITTED_LOCAL',
    pick_status TEXT NOT NULL DEFAULT 'PAID_PENDING_PICK',
    dispatch_status TEXT NOT NULL DEFAULT 'PENDING',
    paid INTEGER NOT NULL DEFAULT 1,
    ...
);
```

### relay_pick_events (Updated)
```sql
CREATE TABLE relay_pick_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    local_sale_ref TEXT NOT NULL,
    picker_user_id TEXT,
    picker_role TEXT,  -- NEW
    event_type TEXT NOT NULL,
    notes TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(local_sale_ref) REFERENCES relay_local_sales(local_sale_ref)
);
```

### relay_dispatch_events (Updated)
```sql
CREATE TABLE relay_dispatch_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    local_sale_ref TEXT NOT NULL,
    dispatcher_user_id TEXT,
    dispatcher_role TEXT,  -- NEW
    event_type TEXT NOT NULL,
    notes TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(local_sale_ref) REFERENCES relay_local_sales(local_sale_ref)
);
```

---

## Implementation Checklist

### Phase 1: Create Roles ✅ COMPLETE
- [x] Add 5 new roles to `fixtures/role.json`:
  - `cline-Sales Associate`
  - `cline-Cashier`
  - `cline-Picker`
  - `cline-Dispatch`
  - `cline-Supervisor`

### Phase 2: Update POS UI ✅ COMPLETE
- [x] Add role selector in `OpeningDialog.vue`
- [x] Store selected role in `localStorage` (key: `pos_current_role`)
- [x] Role selector displays with human-readable names (removes "cline-" prefix)
- [ ] Add role display in `Navbar.vue` (TODO: Show current role in header)
- [ ] Implement role-based UI visibility (TODO: Hide/show features based on role)

### Phase 3: Update Edge Relay ✅ COMPLETE
- [x] Add `role` field to session management APIs (`open_cashier_session`)
- [x] `role` stored in `relay_cashier_sessions` table
- [ ] Add `created_by_role` to token creation (TODO)
- [ ] Add role validation for supervisor-only operations (TODO)

### Phase 4: Testing
- [ ] Test offline token creation
- [ ] Test offline payment with double-payment prevention
- [ ] Test pick status updates offline
- [ ] Test dispatch release offline
- [ ] Test supervisor void token
- [ ] Test supervisor pick exception resolution

---

## Security Considerations

1. **Role Assignment**: Each user must have exactly ONE role assigned
2. **Supervisor Auth**: Supervisor actions require supervisor_user_id verification
3. **Audit Trail**: All supervisor actions recorded with who/when/why
4. **Idempotency**: Prevents duplicate operations in offline mode

---

## Related Documents

- [POS Token and Edge Relay](./POS_token_and_edge_relay.md)
- [Offline Continuity Checklist](../../plans/kilo-codex-v2-offline-continuity-checklist.md)
