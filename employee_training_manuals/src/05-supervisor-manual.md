# Supervisor Manual (Stupid Simple)

## Your job
- Run fulfillment exceptions safely.
- Approve controlled partial/exception releases.
- Keep clear notes and auditability.

![Supervisor screen](../images/supervisor-ui.png)

## When you do what
1. Start of shift:
- Check `Exception` and SLA-high rows first.

2. During shift:
- Review picker/dispatch details.
- Decide: return to picker, mismatch route, or controlled release.

3. End of shift:
- No unresolved exception without documented next action.

## Every button/field on supervisor screen
Supervisor sees both picker and dispatch controls.

1. Refresh icon:
- Reload queue/detail.

2. `DETAILED` / `SIMPLE`:
- `DETAILED` for full context.

3. Search + filter chips (`All`, `Pending`, `In Progress`, `Exception`, `Picked Ready`, `Dispatch Ready`):
- Find workload and exception states.

4. Picker action buttons:
- `MARK ALL PICKED`
- `START/SAVE PICKING`
- `MARK PICKED READY`
- `FLAG EXCEPTION`

5. Dispatch action buttons:
- `RELEASE GOODS`
- `FLAG MISMATCH`
- `Allow partial/exception release` checkbox

6. Dispatch Release Proof fields:
- `Acknowledged By (required)`
- `Proof Mode (required)`
- `Reference No (optional)`
- `Proof Notes (optional)`

7. Dispatch Mismatch fields:
- `Reason Code`
- `Reason Details`
- `Requires cashier adjustment`

8. Notes fields:
- `Picker notes`
- `Dispatch notes`

9. Left ticket icon + monitor controls:
- Cross-role pending-order visibility.

## Simple decision rules
1. Full good pick:
- Normal `RELEASE GOODS` with proof.

2. Pick exception but acceptable release:
- Enable `Allow partial/exception release`, then release with full notes.

3. Financial mismatch:
- Flag mismatch and require cashier adjustment.

4. Missing proof:
- No release.

## Non-negotiable rules
- No override without reason and notes.
- No release without proof capture.
