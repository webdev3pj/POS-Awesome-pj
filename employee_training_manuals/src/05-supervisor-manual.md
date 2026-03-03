# Supervisor Manual (Very Simple)

## What your job is

Your job is:
- Resolve exception rows.
- Approve or reject partial/exception release.
- Keep clean notes and audit trail.

![Supervisor screen](../images/supervisor-ui.png)

## When you do work

- Start of shift: check exception queue first.
- During shift: support picker/dispatch when blocked.
- End of shift: no open exception without clear note.

## Exact buttons and controls you need

You can see both picker and dispatch controls.

1. Refresh icon
- Reloads queue and detail.

2. `Detailed` / `Simple`
- Switches detail depth.

3. Search box and filter chips
- `All`, `Pending`, `In Progress`, `Exception`, `Picked Ready`, `Dispatch Ready`.

4. Picker action buttons
- `Mark All Picked`
- `Start/Save Picking`
- `Mark Picked Ready`
- `Flag Exception`

5. Dispatch action buttons
- `Release Goods`
- `Flag Mismatch`
- `Allow partial/exception release` (checkbox)

6. Dispatch proof and mismatch fields
- `Acknowledged By (required)`
- `Proof Mode (required)`
- `Reference No (optional)`
- `Proof Notes (optional)`
- `Reason Code`
- `Reason Details`
- `Requires cashier adjustment`

7. Notes fields
- `Picker notes`
- `Dispatch notes`

8. Order Monitor ticket icon and panel controls
- Monitor all pending rows and handoff progress.

## Supervisor decision rules (simple)

1. Full pick, no mismatch:
- allow normal dispatch release.

2. Pick exception, but release is still acceptable by policy:
- check `Allow partial/exception release`, then release with full notes.

3. Financial mismatch:
- require cashier adjustment first.

4. Missing proof:
- do not release.

## Step-by-step for exception row

1. Filter `Exception`.
2. Open row.
3. Read line qty and notes.
4. Decide: return to picker or allow controlled release.
5. Record clear note and reason.
6. Confirm final status in detail panel.

## Do not do these

- Do not approve exception with no reason.
- Do not ignore mismatch details.
- Do not leave row unresolved with no handoff note.

## If something breaks

1. Refresh and re-open row.
2. Record LSR and error text.
3. Escalate to IT/Codex support path.

