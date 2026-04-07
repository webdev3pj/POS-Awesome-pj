# PJ Environment Map

Last updated: `2026-04-07`

## Purpose

This file gives a new agent enough context to work on this POS Awesome fork without needing the older knowledge repos first.

## Frappe Cloud Dev

Primary targets:

- Frappe Cloud URL: `https://cloud.frappe.io`
- Bench apps page used for checks: `https://cloud.frappe.io/dashboard/groups/bench-26423/apps`
- ERP dev site: `https://devpjjamaica.v.frappe.cloud`

Local-only credential files in this repo root:

- `C:\vs code repos\POS-Awesome-pj\.env.frappe-cloud.local`
- `C:\vs code repos\POS-Awesome-pj\.env.devpjjamaica.local`

These are intentionally gitignored.

## Current Dev-Bench Alignment

Observed on the Frappe Cloud dev bench:

- POS Awesome repo: `webdev3pj/POS-Awesome-pj`
- POS Awesome branch: `codex-7`
- installed commit when last checked: `8b5b1ef`
- next available update when last checked: `8532899`

Related app branches on the dev bench:

- `frappe`: `version-14`
- `erpnext`: `version-14`
- `payments`: `version-14`
- `insights`: `main`
- `active_users`: `main`
- `whitelabel`: `fix/app-install`
- `portland_jewellers_custom`: `shrikant`

## Local Forge Dev Site

Existing local Forge bench:

- bench: `v14_dev_local`
- site: `devpjjamaica.localhost`
- frontend port: `37003`
- Forge route: `http://127.0.0.1:8000/forge/benches/v14_dev_local`

Current known local admin access:

- user: `Administrator`
- password: `admin`

## Local Site Warning

The local site exists and has been restored from backup, but it is not currently trustworthy for frontend testing.

Reason:

- the local bench runtime dropped back to only core apps in the container `apps/` tree
- the site then started failing with `ModuleNotFoundError: No module named 'posawesome'`

Treat the local site as a partially restored shell until the custom apps are reinstalled and the assets are rebuilt.

## Where To Look Next

If local work is needed, fix the bench first:

1. restore `posawesome` on branch `codex-7`
2. restore `whitelabel` from the PJ fork on `fix/app-install`
3. restore `portland_jewellers_custom` from the `webdev3pj` fork on `shrikant`
4. rerun `migrate`
5. rebuild assets
6. verify `/login` and `/app` from a real browser
