# POS Relay for OptiPlex (Windows)

This folder contains a lightweight relay service designed to run on your always-on Windows machine (OptiPlex 3080).

## What it provides

- Setup UI for Frappe Cloud connection and local relay options.
- Real-time queue dashboard (updates every few seconds).
- Relay queue persistence in a local SQLite database.
- Basic Windows bootstrap helper to create firewall rule and startup task.

## Quick start (Windows)

1. Install Python 3.10+.
2. Open terminal in this folder.
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Start relay:
   - `python -m relay.app`
5. Open browser:
   - `http://127.0.0.1:8787`

## Bootstrap actions (from the UI)

From the **System Setup** page, click **Run Windows Bootstrap**.

It will:

- Create inbound firewall rule for your relay port on private profile.
- Create a startup task that launches relay on user logon.

## Important notes

- This is a practical v1 admin + queue monitor relay scaffold.
- Keep your fixed LAN IP reserved in router for stable POS connectivity.
- Use this with your profile-gated workflow in the main POS app.

