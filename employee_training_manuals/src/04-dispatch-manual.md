# Dispatch Manual (Stupid Simple)

## Role sanity (must be true)
- Your only operational role is `cline-Dispatch`.
- If you see "multiple operational roles", stop and call supervisor/admin.

## Your job
- Verify picked-ready rows.
- Capture release proof.
- Release goods or flag mismatch.

![Dispatch screen](../images/dispatch-ui.png)

## When to do what
1. Start of shift:
- Open dispatch queue.
- Prioritize oldest and SLA-high rows.

2. During shift:
- Open row.
- Fill proof fields.
- Click `RELEASE GOODS`.
- If mismatch: fill mismatch reason and click `FLAG MISMATCH`.

3. End of shift:
- No row released without proof.
- Escalate unresolved mismatches.

## Every visible button/field on dispatch screen
1. Refresh icon: refresh queue/detail.
2. `DETAILED` / `SIMPLE`: view mode.
3. Queue search `Search LSR / SO / customer`.
4. Filter chips (`All`, `Dispatch Ready`, `Pending`, etc.).
5. Queue metrics cards (`Ready`, `Picking`, `Exceptions`, `Avg Wait`, `Oldest Open`, `Over SLA`).
6. Queue row card: load selected order.
7. `RELEASE GOODS`: final release action.
8. `FLAG MISMATCH`: return row to mismatch/exception flow.
9. `Allow partial/exception release`: allows release of exception rows (policy controlled).
10. Release proof fields:
- `Acknowledged By (required)`
- `Proof Mode (required)`
- `Reference No (optional)`
- `Proof Notes (optional)`
11. Mismatch fields:
- `Reason Code`
- `Reason Details`
- `Requires cashier adjustment`
12. `Dispatch notes`: audit notes.
13. Dispatch + Sync history: event/outbox visibility.

## Edge cases you must follow
1. `RELEASE GOODS` stays disabled until required proof fields are filled.
2. If `FLAG MISMATCH` does not update status within a few seconds, escalate to supervisor immediately.
3. Dispatch never takes payment and never edits opening cash.
