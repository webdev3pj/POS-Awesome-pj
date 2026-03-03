# POS Process Overview (All Roles)

## One-line flow
Sales Associate creates token -> Cashier collects payment -> Picker picks -> Dispatch releases -> Supervisor handles exceptions/overrides.

## Role sanity map (one operational role per person)
1. Sales Associate: `cline-Sales Associate`
2. Cashier: `cline-Cashier`
3. Picker: `cline-Picker`
4. Dispatch: `cline-Dispatch`
5. Supervisor: `cline-Supervisor`

## Who does what
1. Sales Associate:
- Builds cart and creates token/order.
- Never enters cash shift money.

2. Cashier:
- Opens cash session and takes payment.
- Owns payment completion and shift cash accountability.

3. Picker:
- Updates line-level picked qty.
- Marks picked-ready or pick-exception.

4. Dispatch:
- Captures release proof.
- Releases goods or flags mismatch.

5. Supervisor:
- Resolves exception/mismatch path.
- Can approve controlled partial/exception release.

## Handoff checkpoints
1. SA -> Cashier:
- Token exists and customer handoff complete.

2. Cashier -> Picker:
- Invoice/payment submitted.
- Fulfillment row visible.

3. Picker -> Dispatch:
- Picked-ready or exception documented.

4. Dispatch -> Customer:
- Release proof captured and status released.

5. Any role -> Supervisor:
- Blocked action, mismatch, stale row, or policy exception.

## Fixed edge-case rules (important)
1. SA must never see or enter opening cash amount fields.
2. Dispatch/Supervisor release needs proof fields filled before release.
3. If mismatch action does not persist, escalate immediately with LSR.
4. If user sees "multiple operational roles", stop and correct role assignment first.
5. Legacy relay behavior may differ on old endpoints; operational flow uses current UI endpoints and supervisor escalation if blocked.

## Quick visual references
![Cashier payment reference](../images/payment-screen.png)

![Picker fulfillment reference](../images/picker-ui.png)

![Dispatch reference](../images/dispatch-ui.png)

## Escalation template (all staff)
1. Your role.
2. Order reference (`SO` or `LSR`).
3. Exact error text shown.
4. Time of issue.
