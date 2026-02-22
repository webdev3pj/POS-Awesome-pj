# POS Relay for OptiPlex (Windows)

This folder contains a lightweight relay service designed to run on your always-on Windows machine (OptiPlex 3080).

## What it provides

- Setup UI for Frappe Cloud connection and local relay options.
- Real-time queue dashboard (updates every few seconds).
- Real-time outbox counters for local-first sync state.
- Relay queue persistence in a local SQLite database.
- Local-first offline entities (tokens, cashier sessions, local sales, pick/release state).
- Basic Windows bootstrap helper to create firewall rule and startup task.

## One-click install/start (Windows)

1. Open folder [`relay/`](relay/README.md).
2. Double-click [`start_relay.bat`](relay/start_relay.bat).

What this one-click script does automatically:

- Detects Python (`py`/`python`).
- Attempts Python install via `winget` if Python is missing.
- Creates virtual environment.
- Downloads/installs all dependencies from [`requirements.txt`](relay/requirements.txt).
- Runs relay self-test using [`relay.selftest`](relay/relay/selftest.py).
- Opens browser at `http://127.0.0.1:8787`.
- Starts relay app from [`relay.app`](relay/relay/app.py).

If anything fails, the script stops with an error message.

## Bootstrap actions (from the UI)

From the **System Setup** page, click **Run Windows Bootstrap**.

It will:

- Create inbound firewall rule for your relay port on private profile.
- Create a startup task that launches relay on user logon.

## Quick verification

After start, verify:

- Dashboard: `http://127.0.0.1:8787`
- Queue page: `http://127.0.0.1:8787/queue`
- Health JSON: `http://127.0.0.1:8787/health`
- Outbox JSON: `http://127.0.0.1:8787/api/outbox`

## v2 local-first API endpoints (offline continuity)

- `POST /relay/token/create`
- `GET /relay/token/<token_id>`
- `POST /relay/token/<token_id>/void`
- `POST /relay/session/open`
- `POST /relay/session/close`
- `POST /relay/customer/upsert`
- `GET /relay/items/search`
- `POST /relay/items/refresh`
- `POST /relay/items/refresh-from-cloud`
- `POST /relay/commit-invoice` (requires `idempotency_key`)
- `GET /relay/pick-queue`
- `POST /relay/pick/update`
- `POST /relay/dispatch/release`

## Important notes

- This is a practical v1 admin + queue monitor relay scaffold.
- v2 extends scaffold with local-first durable workflow support.
- Keep your fixed LAN IP reserved in router for stable POS connectivity.
- Use this with your profile-gated workflow in the main POS app.

