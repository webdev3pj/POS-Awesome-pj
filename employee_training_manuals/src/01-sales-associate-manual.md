# Sales Associate Manual (Stupid Simple)

## Role sanity (must be true)
- Your only operational role is `cline-Sales Associate`.
- If you see "multiple operational roles", stop and call supervisor/admin.

## Your job
- Build cart.
- Create Sales Order token with `Save/New`.
- Send customer to cashier.

## You NEVER do
- Do not enter opening cash.
- Do not take payment.
- Do not release goods.
- Do not do dispatch mismatch or supervisor override work.

![Sales Associate screen](../images/sa-ui.png)

## When to do what
1. Start of shift:
- Open POS.
- If role dialog appears, confirm role is Sales Associate.
- Pick POS Profile and press `Submit`.

2. During shift:
- Search and add items.
- Confirm customer.
- Click `Save/New` to create token.
- Tell customer to go to cashier with token/order reference.

3. End of shift:
- Make sure no customer is left without token.
- Escalate blocked orders to supervisor.

## Every visible button/field on this screen
1. `Search Items`: find items by name/code/barcode.
2. Item row in left table: adds item to cart.
3. `Customer`: set buyer.
4. `Type`: sale document mode (normally Invoice flow).
5. `Items Group`: filter item list by category.
6. `LIST` / `CARD`: switch item display style.
7. `COUPONS`: open coupon section if used.
8. `OFFERS`: shows applied offers count.
9. `Held`: open held drafts.
10. `Save Quote`: save quotation (if enabled).
11. `Select Quote`: load a saved quotation.
12. `Return`: start return flow (normally cashier/supervisor process).
13. `Cancel`: clear current cart.
14. `Save/New`: create token/order and reset screen.
15. `PAY`: SA must not finalize payment. If shown, do not use.
16. Left ticket icon: open Order Monitor panel.
17. Order Monitor `All` / `Mine` / refresh: filter and refresh workflow rows.

## Edge cases you must follow
1. If you ever see `Opening Amount`, you are in wrong role/session. Stop and call supervisor.
2. If `Save/New` does not show token dialog, wait 5 seconds and retry once, then escalate.
3. If `PAY` is enabled for SA, do not use it. Hand off to cashier.
