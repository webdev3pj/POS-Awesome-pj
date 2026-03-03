# Picker Manual (Stupid Simple)

## Your job
- Pick paid orders.
- Record actual picked quantity per line.
- Mark ready for dispatch, or flag exception.

![Picker screen](../images/picker-ui.png)

## When you do what
1. Start of shift:
- Open picker queue.
- Focus `Pending` / `In Progress` rows.

2. During shift:
- Open one queue row.
- Update picked qty/status.
- Save picking.
- Mark ready when complete.

3. End of shift:
- No order left half-done without notes.

## Every button/field on picker screen
1. Refresh icon (top-right of queue card):
- Reload queue and detail.

2. `DETAILED` / `SIMPLE`:
- Change detail density.
- Use `DETAILED` for normal work.

3. Search field `Search LSR / SO / customer`:
- Filter queue quickly.

4. Filter chips: `All`, `Pending`, `In Progress`, `Exception`, `Picked Ready`:
- Queue filter by status.

5. Queue row:
- Click row to load full order detail.

6. `MARK ALL PICKED`:
- Set all line picked qty = ordered qty.

7. `START/SAVE PICKING`:
- Save current line edits in progress.

8. `MARK PICKED READY`:
- Mark ready for dispatch.
- Use only when all lines are properly picked.

9. `FLAG EXCEPTION`:
- Send row to exception state when mismatch/short pick/damage.

10. Line table fields:
- `Picked Qty` input: enter actual quantity.
- `Status` dropdown: line status (`NOT_PICKED`, `PICKED`, `PARTIAL`, `EXCEPTION`).

11. `Picker notes`:
- Explain partial pick or exception reason.

12. Left ticket icon + monitor controls:
- Cross-role visibility of pending workflow.

## Non-negotiable rules
- Picker does not collect payment.
- Picker does not release goods.
