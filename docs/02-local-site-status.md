# Local Site Status

Last updated: `2026-04-07`

## What Exists

A local Forge bench and site were created on this machine to mirror the PJ dev environment:

- bench: `v14_dev_local`
- site: `devpjjamaica.localhost`
- local frontend port: `37003`

The site was later restored from the backup set in:

- `C:\Users\WORK\Documents\erpnext work\backupfiles`

## What Is Good

- the site record exists
- the database was restored
- the encryption key was restored
- `CODEX BOT NICK` login was proven against the restored site once the key issue was fixed

## What Is Not Good

The local frontend is not fully configured now.

Known failure mode:

- `http://localhost:37003/login` and `/app` were returning `500`
- the backend stack reported `ModuleNotFoundError: No module named 'posawesome'`

That means the data snapshot may be usable, but the local app/runtime state is not equivalent to production or the cloud dev site.

## Minimum Recovery Path

To make the local site usable again:

1. repopulate the bench `apps/` folder with all non-core apps
2. ensure this repo is the source for `posawesome` on branch `codex-7`
3. ensure `whitelabel` comes from the PJ fork on `fix/app-install`
4. ensure `portland_jewellers_custom` comes from `webdev3pj/portland_jewellers_custom` on `shrikant`
5. rebuild `sites/apps.txt`
6. run `bench --site devpjjamaica.localhost migrate`
7. rebuild assets and restart backend, frontend, queue, scheduler, and websocket

## Operational Rule

Do not assume local frontend behavior proves anything until the above recovery is complete.

For current functional validation, prefer:

- `https://devpjjamaica.v.frappe.cloud`
- or production, depending on change risk
