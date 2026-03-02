# Dispatch Manual

## Your Mission
Monitor ready orders, verify release conditions, and release goods with proof.

## Before You Start
1. Log in with dispatch user.
2. Confirm fulfillment workspace is visible.
3. Confirm relay online chip is green.

## Main Workflow
1. Open dispatch queue.
2. Select order row.
3. Verify:
   - order details/customer
   - pick status
   - notes and timeline
4. Fill release proof fields (required).
5. Click `Release Goods`.
6. Confirm status changes to released.

## Dispatch Proof Requirement
Release is only valid when proof is captured.

Minimum fields required in current workflow:
1. Acknowledged-by name
2. Proof mode (counter/delivery/other)
3. Line snapshot is captured by the system on release

## Mismatch Flow
If dispatch detects mismatch:
1. Use mismatch/exception route.
2. Return order to picker exception flow.
3. Mark whether cashier adjustment is needed.
4. Inform supervisor when required.

## What You Must Not Do
1. Do not collect payment.
2. Do not silently edit picker data without notes.
3. Do not release without proof.

## If Something Goes Wrong
1. Release button disabled:
   - check proof fields are filled
   - check row is in correct status
2. Release remains pending:
   - refresh and re-open row
   - if still pending, escalate with local sale reference (`LSR-*`)
3. Relay down:
   - stop release actions and escalate to supervisor/IT.

## End of Shift
1. Ensure all released rows show release details.
2. Escalate unresolved exception rows to supervisor.
