# Dispatch Manual (Stupid Simple)

## Your job
- Verify picked-ready orders.
- Capture release proof.
- Release goods, or flag mismatch.

![Dispatch screen](../images/dispatch-ui.png)

## When you do what
1. Start of shift:
- Open dispatch queue.
- Prioritize `Dispatch Ready` and SLA-high rows.

2. During shift:
- Open row.
- Fill proof fields.
- Release goods.
- If mismatch: flag mismatch with reason.

3. End of shift:
- No release without proof.
- Hand over unresolved mismatches.

## Every button/field on dispatch screen
1. Refresh icon:
- Reload queue and details.

2. `DETAILED` / `SIMPLE`:
- `DETAILED` recommended.

3. Search field `Search LSR / SO / customer`:
- Filter queue.

4. Filter chips (`All`, `Dispatch Ready`, etc.):
- Focus correct rows.

5. Queue row:
- Load order in detail pane.

6. Queue metrics cards (`Ready`, `Picking`, `Exceptions`, `Avg Wait`, `Oldest Open`, `Over SLA`):
- Prioritization dashboard.

7. `RELEASE GOODS`:
- Final dispatch action.
- Enabled only when release gate passes.

8. `FLAG MISMATCH`:
- Return row to picker exception flow.

9. `Allow partial/exception release` checkbox:
- Allow release from exception states per supervisor policy.

10. Dispatch Release Proof fields:
- `Acknowledged By (required)`
- `Proof Mode (required)`
- `Reference No (optional)`
- `Proof Notes (optional)`

11. Dispatch Mismatch fields:
- `Reason Code`
- `Reason Details`
- `Requires cashier adjustment`

12. `Dispatch notes`:
- Add action notes for audit.

13. Left ticket icon + monitor controls:
- Read-only workflow visibility.

## Non-negotiable rules
- Never release goods without proof.
- Never bypass mismatch reason capture.
- Dispatch does not take payment.
