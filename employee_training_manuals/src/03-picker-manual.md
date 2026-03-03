# Picker Manual (Stupid Simple)

## Role sanity (must be true)
- Your only operational role is `cline-Picker`.
- If you see "multiple operational roles", stop and call supervisor/admin.

## Your job
- Pick paid orders line by line.
- Save real picked quantity.
- Mark ready for dispatch or flag exception.

![Picker screen](../images/picker-ui.png)

## When to do what
1. Start of shift:
- Open Picker Queue.
- Start from oldest `Pending` or `In Progress`.

2. During shift:
- Open queue row.
- Enter picked qty per line.
- Click `Start/Save Picking`.
- Click `Mark Picked Ready` when complete, else `Flag Exception`.

3. End of shift:
- No open partial pick without notes.

## Every visible button/field on picker screen
1. Refresh icon: refresh queue and detail.
2. `DETAILED` / `SIMPLE`: view mode toggle.
3. `Search LSR / SO / customer`: queue search.
4. Filter chips `All`, `Pending`, `In Progress`, `Exception`, `Picked Ready`: status filter.
5. Queue row card: load order detail.
6. `MARK ALL PICKED`: set picked qty equal to ordered qty for all lines.
7. `START/SAVE PICKING`: save line edits as in-progress.
8. `MARK PICKED READY`: send to dispatch-ready state.
9. `FLAG EXCEPTION`: set pick exception status.
10. Line table:
- `Picked Qty` input: actual picked qty.
- `Status` column: per-line pick status.
- `Ord Qty`, `UOM`, `Conv`, `Ord Stock`, `Picked Stock`: reference fields.
11. `Picker notes`: reason/context for exceptions and partials.
12. Pick History: audit trail of pick actions.
13. Dispatch + Sync panel: read-only state visibility.

## Edge cases you must follow
1. If only `Picked Ready` or `Exception` rows are left, do not force-edit blindly. Review notes and escalate to supervisor if unclear.
2. Never mark ready if any line is wrong or missing.
3. Picker never takes payment and never releases goods.
