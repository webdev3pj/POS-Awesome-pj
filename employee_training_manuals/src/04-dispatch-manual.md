# Dispatch Manual (Very Simple)

## What your job is

Your job is:
- Verify picked-ready orders.
- Capture release proof.
- Release goods correctly.

![Dispatch screen](../images/dispatch-ui.png)

## When you do work

- Start of shift: open dispatch queue and check oldest rows.
- During shift: release only after proof fields are complete.
- End of shift: no release without proof; hand off unresolved mismatches.

## Exact buttons and fields you need

1. Refresh icon
- What it does: reloads queue and detail.
- When to click: at shift start and between orders.

2. `Detailed` / `Simple`
- What they do: switch view level.
- When to click: keep `Detailed` for release work.

3. Search box
- What it does: filters by LSR, SO, customer.
- When to click: find one order fast.

4. Filter chips `All`, `Dispatch Ready`
- What they do: queue filter.
- When to click: use `Dispatch Ready` for releasable orders.

5. Queue row click
- What it does: opens detail panel for selected order.
- When to click: before any release action.

6. Dispatch proof fields
- `Acknowledged By (required)`: name of receiver.
- `Proof Mode (required)`: `Counter pickup`, `Delivery handover`, or `Other`.
- `Reference No (optional)`: receipt, route, package ref.
- `Proof Notes (optional)`: extra handover notes.

7. `Release Goods`
- What it does: final dispatch release.
- When to click: only when proof is complete and row is ready.

8. `Flag Mismatch`
- What it does: sends row to mismatch flow.
- When to click: picked goods do not match what should be released.

9. `Allow partial/exception release` checkbox
- What it does: allows release from exception state.
- When to click: only with supervisor policy approval.

10. Dispatch mismatch fields
- `Reason Code`
- `Reason Details`
- `Requires cashier adjustment`
- Use them before `Flag Mismatch`.

11. `Dispatch notes`
- What it does: saves context for dispatch action.
- When to use: whenever mismatch or special handover happened.

12. Order Monitor ticket icon and panel controls
- What they do: quick global queue visibility.
- When to click: for cross-role coordination.

## Step-by-step

1. Click `Dispatch Ready` filter.
2. Open one row.
3. Fill dispatch proof.
4. Re-check customer/order details.
5. Click `Release Goods`.
6. Confirm status is `RELEASED`.
7. If mismatch, use mismatch fields and click `Flag Mismatch`.

## Do not do these

- Do not release without proof.
- Do not edit picker data silently.
- Do not collect payment.

## If something breaks

1. Refresh.
2. Reopen row.
3. If still blocked, report LSR + message to supervisor.

