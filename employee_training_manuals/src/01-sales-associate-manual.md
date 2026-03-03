# Sales Associate Manual (Stupid Simple)

## Your job
- Build the customer cart.
- Create the Sales Order token.
- Hand the customer to Cashier.

## You NEVER do
- You do not enter opening cash amounts.
- You do not close shifts.
- You do not take payment.
- You do not release goods.

![Sales Associate screen](../images/sa-ui.png)

## When you do what
1. Start of shift:
- Open POS.
- If the start dialog appears, you only pick `Company` and `POS Profile`, then click `Submit`.
- SA starts a non-cash session. No opening amount entry.

2. During shift:
- Select customer.
- Add items.
- Confirm total with customer.
- Click `Save/New` to create token.

3. End of shift:
- Make sure no waiting customer is missing a token.
- Escalate blocked orders to supervisor.

## Every button/field you use (SA)
1. `Search Items` field:
- Type item name/code.

2. Item list row:
- Click row to add item to cart.

3. `Customer` field (right panel top):
- Set the customer for the sale.

4. `Type` field:
- Usually `Invoice`/`Order` mode control.
- SA should keep normal order-taking flow for token handoff.

5. `Held`:
- Open held drafts (only if your store process uses this).

6. `Save Quote`:
- Save current cart as quote (if enabled in profile).

7. `Select Quote`:
- Load an existing quote (if enabled).

8. `Return`:
- Return flow (usually cashier/supervisor process).

9. `Cancel`:
- Clear current invoice/cart.

10. `Save/New`:
- Main SA action. Creates Sales Order token and resets for next customer.

11. `Print Draft`:
- Print draft copy only when store policy requires it.

12. Left ticket icon (Order Monitor):
- Open monitor panel to view pending order flow.

13. In monitor panel: `All (date)`, `Mine`, refresh icon:
- `All (date)`: all pending orders for profile/date.
- `Mine`: only orders linked to your user.
- Refresh: reload monitor list.

## Important sanity rule
- If anyone asks SA to enter opening shift money, that is wrong.
- Opening cash is cashier-only.
