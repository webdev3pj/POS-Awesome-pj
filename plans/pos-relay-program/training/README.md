# POS Role Training Pack (Employee Manuals)

## Purpose
This folder is the staff-facing training material for daily POS operation.

Use these manuals for onboarding and refresher training:
1. `sales-associate-manual.md`
2. `cashier-manual.md`
3. `picker-manual.md`
4. `dispatch-manual.md`
5. `supervisor-manual.md`
6. `trainer-quickstart.md`

## Scope
These manuals are based on the current shared POS Awesome workflow with edge relay:
- SA creates Sales Order token
- Cashier retrieves token and submits invoice
- Picker updates picking progress
- Dispatch releases goods with proof
- Supervisor handles exception paths

## Important Notes
- This pack is for operations training, not developer implementation details.
- Relay/cloud status chips shown in POS are part of daily checks.
- For technical setup, use:
  - `../runbooks/new-shop-one-click-setup.md`
  - `../runbooks/shop-pc-lan-relay-setup-non-technical.md`
  - `../runbooks/optiplex-edge-relay-next-session.md`
