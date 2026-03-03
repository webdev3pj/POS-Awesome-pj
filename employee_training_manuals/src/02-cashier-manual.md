# Cashier Manual (Stupid Simple)

## Role sanity (must be true)
- Your only operational role is `cline-Cashier`.
- If you see "multiple operational roles", stop and call supervisor/admin.

## Your job
- Open cash session.
- Pull Sales Order from token with `Select S.O`.
- Collect payment.
- Submit invoice.

![Cashier main screen](../images/cashier-ui.png)

![Select Sales Order dialog](../images/select-sales-order.png)

![Payment screen](../images/payment-screen.png)

## When to do what
1. Start of shift:
- Open POS as cashier.
- Complete opening cash amounts if opening dialog appears.
- Enter POS with `Submit`.

2. During shift:
- Click `Select S.O`.
- Choose correct order row.
- Click `PAY`.
- Enter payment and click `Submit` or `Submit & Print`.

3. End of shift:
- Finish pending payments.
- Close shift as per store process.

## Every visible button/field (main cashier screen)
1. `Search Items`: manual item search.
2. `Customer`: buyer.
3. `Type`: document type selector.
4. `Select S.O`: open Sales Order list from token flow.
5. `Held`: open held draft bills.
6. `Save Quote`: save quote (if enabled).
7. `Select Quote`: load quote (if enabled).
8. `Return`: start return flow.
9. `Cancel`: clear current cart.
10. `Save/New`: save/reset draft bill.
11. `PAY`: open payment panel.
12. `Print Draft`: print draft copy.
13. Left ticket icon: open Order Monitor.
14. Order Monitor `All` / `Mine` / refresh: workflow visibility controls.

## Every visible button/field (Select Sales Orders dialog)
1. `Order ID`: type token/order id filter.
2. `SEARCH`: run lookup.
3. Row checkbox: choose order to load.
4. Columns: Customer, Date, Order, Amount, Age, Freshness.
5. Pagination controls: change page/rows per page.
6. `CLOSE`: close dialog without loading.

## Every visible button/field (Payment screen)
1. `Paid Amount`: total paid so far.
2. `To Be Paid`: remaining balance.
3. Payment amount rows (`Cash`, `Credit Card`, `Cheque`, `Bank Transfer`): enter per mode.
4. Payment mode buttons (`CASH`, `CREDIT CARD`, etc.): auto-fill selected mode.
5. Totals fields (`Net Total`, `Tax and Charges`, `Total Amount`, `Grand Total`, `Rounded Total`): verify totals.
6. `Additional Notes`: optional payment note.
7. `Use Customer Credit`: apply credit if allowed.
8. `Submit`: post invoice.
9. `Submit & Print`: post and print.
10. `Cancel Payment`: exit payment panel.

## Edge cases you must follow
1. If `Select S.O` shows no rows, check age filter policy and token/order id, then escalate if still empty.
2. If token workflow is disabled for profile, use normal item sale and pay flow.
3. If relay/cloud warning appears during submit, follow prompt and call supervisor if not resolved.
4. Cashier never releases goods. Dispatch/supervisor handles release.
