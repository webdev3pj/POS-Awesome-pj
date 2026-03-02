# Trainer Quickstart (Manager Copy)

## Goal
Train each employee role in under 30 minutes with one practical transaction.

## Materials
1. Role manual for each employee:
   - `sales-associate-manual.md`
   - `cashier-manual.md`
   - `picker-manual.md`
   - `dispatch-manual.md`
   - `supervisor-manual.md`
2. Test customer
3. One test item
4. Access to POS with correct role users

## 30-Minute Training Flow
1. SA creates token and prints slip.
2. Cashier retrieves token by order ID and submits invoice.
3. Picker opens same order and marks picked-ready (or exception demo).
4. Dispatch releases with proof.
5. Supervisor reviews one exception case.

## Trainer Checklist
1. Confirm each trainee can log in and sees only expected role controls.
2. Confirm each trainee can complete their own step without help.
3. Confirm handoff from one role to next is clear.
4. Confirm relay status is visible and understood.
5. Confirm trainee knows escalation path for failures.

## Escalation Script (Simple)
If an employee is blocked, they should report:
1. Role
2. Order ID (`SAL-ORD-*`) or local sale ref (`LSR-*`)
3. Exact error message
4. Time of failure

## Pass Criteria for Staff Readiness
1. SA can create and print token correctly.
2. Cashier can retrieve and submit without confusion.
3. Picker can update quantities and exceptions correctly.
4. Dispatch can release only with proof.
5. Supervisor can resolve exception path with notes.
