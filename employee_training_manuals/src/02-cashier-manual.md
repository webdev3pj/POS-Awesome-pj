# Cashier Manual (Stupid Simple)

## Your job
- Open cash shift.
- Load Sales Order from token.
- Take payment.
- Submit invoice.

![Cashier main screen](../images/cashier-ui.png)

![Select Sales Order dialog](../images/select-sales-order.png)

![Payment screen](../images/payment-screen.png)

## When you do what
1. Start of shift:
- Open POS.
- Cashier opening dialog appears.
- Enter opening amount per payment mode.
- Click `Submit`.

2. During shift:
- Click `Select S.O`.
- Find and load customer order.
- Click `PAY`.
- Enter payment.
- Click `Submit` (or `Submit & Print`).

3. End of shift:
- Clear pending invoices.
- Close shift by store process.

## Opening dialog fields/buttons (cashier)
1. `Company`:
- Company for this POS session.

2. `POS Profile`:
- Profile for terminal/workflow.

3. Opening amount table (`Mode of Payment`, `Opening Amount`):
- Enter starting cash/amounts for accountability.

4. `Cancel`:
- Exit without opening shift.

5. `Submit`:
- Create opening shift and enter POS.

## Main screen buttons/fields
1. `Search Items`:
- Item search.

2. `Customer`:
- Set buyer/customer.

3. `Select S.O`:
- Open Sales Order picker (normal token flow).

4. `Held`:
- Open held drafts.

5. `Save Quote` / `Select Quote`:
- Quote flow if enabled by profile.

6. `Return`:
- Return process.

7. `Cancel`:
- Clear current cart.

8. `Save/New`:
- Save/reset invoice draft flow.

9. `PAY`:
- Open payment panel.

10. `Print Draft`:
- Print draft if needed.

11. Left ticket icon + monitor panel controls:
- Live workflow visibility (`All (date)`, `Mine`, refresh).

## Select Sales Orders dialog fields/buttons
1. `Order ID`:
- Type token/SO number.

2. `Search`:
- Run lookup.

3. Row checkbox:
- Select one order.

4. Table columns:
- Customer, Date, Order, Amount, Age, Freshness.

5. Bottom `Close`:
- Exit dialog without loading.

## Payment screen fields/buttons
1. Payment rows (`Cash`, `Credit Card`, `Cheque`, `Bank Transfer`, etc.):
- Enter amount or click mode button to set full amount.

2. Payment mode buttons (`CASH`, `CREDIT CARD`, etc.):
- Fill the selected mode with full payable amount quickly.

3. Totals fields:
- `Paid Amount`, `To Be Paid`, `Net Total`, `Tax and Charges`, `Total Amount`, `Grand Total`, etc.

4. `Additional Notes`:
- Optional payment note.

5. `Use Customer Credit` toggle:
- Apply available customer credit if allowed.

6. `Submit`:
- Submit paid invoice.

7. `Submit & Print`:
- Submit + print immediately.

8. `Cancel Payment`:
- Back to invoice screen.

## Non-negotiable rules
- Cashier owns opening/closing cash accountability.
- Do not release goods from fulfillment screen.
