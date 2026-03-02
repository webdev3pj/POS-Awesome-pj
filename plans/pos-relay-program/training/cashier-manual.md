# Cashier Manual

## Your Mission
Receive customer token/order, collect payment, and submit the final Sales Invoice.

## Before You Start
1. Log in with cashier user.
2. Confirm top status chips:
   - `Relay Online (LAN)` is preferred.
   - `Cloud Online` should normally be green.
3. Confirm payment modes are visible on payment screen (Cash/Card/Cheque/Bank Transfer as configured).

## Main Workflow
1. Click `Select S.O`.
2. Enter token/order ID and click `Search`.
3. Select the correct row and load it into POS.
4. Click `PAY`.
5. Enter paid amount in correct payment mode(s).
6. Click `Submit` (or `Submit & Print` if used).
7. Confirm success message and invoice reference.

## Token Retrieval Priority
1. Use Sales Order/token ID from printed slip.
2. If not found, retry with exact Sales Order number.
3. If still not found, ask SA to confirm token print/order ID.

## Relay and Fallback Rules
1. If relay is up, submit should go through relay path.
2. If relay is down and cloud is up, a fallback prompt may appear.
3. Follow store policy before selecting cloud fallback.
4. If both relay and cloud are down, do not force payment submit; escalate.

## What You Must Not Do
1. Do not change picker/dispatch statuses.
2. Do not use supervisor override actions.

## If Something Goes Wrong
1. Payment modes missing:
   - Refresh once.
   - Reload Sales Order.
   - Escalate if still missing.
2. Submit fails:
   - Note error text and time.
   - Do not repeatedly click submit.
   - Escalate with order ID.
3. Customer asks for change after payment:
   - Use approved cashier correction process.
   - In fulfillment mismatch cases, coordinate with supervisor.

## End of Shift
1. Confirm submitted invoices are complete.
2. Escalate pending payment failures before logout.
