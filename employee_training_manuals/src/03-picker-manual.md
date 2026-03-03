# Picker Manual (Very Simple)

## What your job is

Your job is:
- Pick items after payment.
- Record real picked quantity.
- Mark order ready for dispatch.

![Picker screen](../images/picker-ui.png)

## When you do work

- Start of shift: open picker queue.
- During shift: pick by queue priority.
- End of shift: leave no row half-done without notes.

## Exact buttons you need to know

1. Refresh icon (top right of queue card)
- What it does: reloads queue and selected detail.
- When to click: at start and before each next order.

2. `Detailed` / `Simple`
- What they do: switch queue/detail view density.
- When to click: use `Detailed` for normal operations.

3. Search box `Search LSR / SO / customer`
- What it does: filters queue rows.
- When to click: find one specific order quickly.

4. Filter chips: `All`, `Pending`, `In Progress`, `Exception`, `Picked Ready`
- What they do: filter queue by pick status.
- When to click: use `Pending` to focus new picks.

5. Queue row click
- What it does: opens order detail.
- When to click: always click exact row before updating.

6. `Mark All Picked`
- What it does: sets picked qty equal to ordered qty for all lines.
- When to click: everything is fully available and fully picked.

7. `Start/Save Picking`
- What it does: saves picked qty updates in progress state.
- When to click: after entering picked qty lines.

8. `Mark Picked Ready`
- What it does: marks order ready for dispatch.
- When to click: all lines are complete and no exception remains.

9. `Flag Exception`
- What it does: marks pick exception state.
- When to click: short pick, damaged item, or missing stock.

10. `Picked Qty` input field (line table)
- What it does: stores actual picked quantity.
- When to use: every time actual qty is not equal to ordered qty.

11. `Picker notes`
- What it does: stores reason/context for updates.
- When to use: always fill notes for partial/exception picks.

12. Order Monitor ticket icon
- What it does: opens global order monitor panel.
- When to click: check where order sits in full workflow.

## Step-by-step

1. Click queue row.
2. Check line items and quantities.
3. Update `Picked Qty`.
4. Add `Picker notes` if needed.
5. Click `Start/Save Picking`.
6. If complete: click `Mark Picked Ready`.
7. If issue: click `Flag Exception` and notify supervisor.

## Do not do these

- Do not collect payment.
- Do not release goods.
- Do not clear exception without proper reason.

## If something breaks

1. Refresh once.
2. Re-open the same LSR row.
3. If still broken, report LSR to supervisor.

