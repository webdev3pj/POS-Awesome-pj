# Picker Manual

## Your Mission
Pick items accurately from paid orders and update picking status in POS.

## Before You Start
1. Log in with picker user.
2. Confirm fulfillment workspace is visible.
3. Confirm relay is online (`Relay Online (LAN)` chip).

## Main Workflow
1. Select a queue row in Picker workspace.
2. Review line items, ordered qty, UOM, and conversion factor.
3. Click `Start/Save Picking` as needed.
4. For normal case:
   - keep picked qty equal to ordered qty.
5. For exceptions:
   - edit line picked qty as actually picked.
   - add picker notes.
6. When done:
   - click `Mark Picked Ready`.

## Key Rule for Quantities
- Picked qty should be entered in order UOM.
- System also tracks stock conversion in the background.

## Exception Handling
1. If item unavailable or short:
   - keep accurate picked qty
   - record notes
   - use exception path (`Flag Exception` when required by flow)
2. Do not release goods from picker role.

## What You Must Not Do
1. Do not take payment.
2. Do not release final dispatch.
3. Do not override supervisor-only exceptions.

## If Something Goes Wrong
1. Queue row not updating:
   - refresh once and re-open same row.
2. Relay chip is down:
   - inform supervisor/IT immediately.
3. Wrong order selected:
   - stop editing and switch to correct row before saving.

## End of Shift
1. Ensure no half-updated rows are left without notes.
2. Hand over exception rows to supervisor/dispatch clearly.
