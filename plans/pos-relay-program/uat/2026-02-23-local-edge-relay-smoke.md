# 2026-02-23 Local Edge Relay Smoke (codex-3-edge-relay)

## TL;DR (Business Owner)
- We created a new branch for relay-focused hardening: `codex-3-edge-relay`.
- The Edge Relay core SA/Cashier endpoints were tested locally and are working in a real local HTTP smoke run.
- A local test reliability issue was fixed: relay acceptance tests were failing only because they reused an old local SQLite DB schema.
- Tomorrow’s deploy can focus on real end-to-end relay behavior from the live dev site instead of basic relay endpoint debugging.

## Scope
- Local relay validation only (not Frappe Cloud browser-to-relay live integration yet)
- Focused on SA/Cashier relay core:
  - cashier session open
  - token create
  - invoice commit (local-first)

## What Was Tested
### 1. Relay acceptance test suite (local)
- Command (from `relay/`):
  - `python -m unittest tests.test_offline_workflow -v`
- Result:
  - `PASS` (`5/5`) after test isolation fix

### 2. Real local HTTP smoke (temporary local relay server)
- Started relay app locally using a temporary DB/config path (no shared `relay/data/relay.db`)
- Hit these endpoints over HTTP:
  - `GET /health`
  - `POST /relay/session/open`
  - `POST /relay/token/create`
  - `POST /relay/commit-invoice`
- Result:
  - `PASS`
  - `commit-invoice` returned `SALE_COMMITTED_LOCAL`
  - `local_sale_ref` generated successfully

## Issue Found (and Fixed)
### Problem
- Local relay tests were failing with:
  - `sqlite3.OperationalError: table relay_cashier_sessions has no column named role`
- Cause:
  - Tests were using the persistent local DB (`relay/data/relay.db`) from previous runs/schema versions.

### Fix
- Updated `relay/tests/test_offline_workflow.py` to:
  - create a temporary DB/config directory per test case
  - patch relay storage paths to that temp directory
  - disable background sync loop during tests

## Why This Matters for Tomorrow
- Relay endpoint logic is now locally verified and testable repeatedly.
- Tomorrow’s deploy/test can focus on:
  - connecting the live POS to a real relay URL
  - validating SA + Cashier flow through relay in the actual environment
  - tuning relay configuration and submit outcomes

## Next Actions (Tomorrow)
1. Deploy `codex-3-edge-relay`
2. Start local Edge Relay service on your machine (or relay host)
3. Configure `PJ7 CASHIER` relay URL (LAN/tunnel as needed)
4. Re-run SA + Cashier Cypress flow against live dev site with relay enabled
5. Confirm cashier submit reaches relay commit success path (not just UI validation)
