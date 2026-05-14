# Manual POS Testing Checklist

Use this checklist on dev before moving the POS changes to production. Record every Sales Order, Sales Invoice, POS Profile, user, and screenshot/video evidence so failures can be reproduced.

## Test Evidence Template

| Field | Value |
| --- | --- |
| Site / URL | |
| Branch / Commit | |
| Tester | |
| Test Date | |
| Default POS Profile, token workflow OFF | |
| Token POS Profile, token workflow ON | |
| Sales Associate User | |
| Cashier User | |
| Supervisor/Admin User | |

## Pre-Test Setup

| # | Check | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Confirm app is built and latest code is deployed on dev. | POS loads latest bundle without old cached behavior. | | |
| 2 | Clear browser cache or open POS in private window. | No stale JS bundle affects testing. | | |
| 3 | Confirm one normal POS Profile has `Enable Token Workflow` / `custom_have_token` OFF. | This profile behaves like default POS. | | |
| 4 | Confirm one token POS Profile has `Enable Token Workflow` / `custom_have_token` ON. | This profile uses Sales Associate / Cashier workflow. | | |
| 5 | Confirm token profile has payment modes configured: Cash, Bank Transfer, Credit Card, or the modes used by store. | Cashier payment screen shows the modes. | | |
| 6 | Confirm Sales Associate user has exactly one operational role, for example `cline-Sales Associate`. | User has no cashier/supervisor role conflict. | | |
| 7 | Confirm Cashier user has exactly one operational role, for example `cline-Cashier`. | Cashier can open cash shift and process payment. | | |
| 8 | Confirm both users have a default POS Profile assigned where required. | Token workflow auto-selects the correct profile. | | |
| 9 | Confirm users have required ERPNext/POS permissions and no permission errors on POS Profile, POS Opening Shift, Sales Order, or Sales Invoice. | API calls do not return 403. | | |
| 10 | Confirm test items have price, stock if stock validation applies, warehouse, taxes, and UOM configured. | Item can be added and invoiced. | | |

## Flow 1: Default POS Regression, Token Workflow OFF

Goal: prove that a normal POS Profile still behaves like production/default POS when token workflow is disabled.

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Login as a normal cashier/user assigned to the token-OFF POS Profile. | Login succeeds. | | |
| 2 | Open POS. | Standard POS opening behavior appears. | | |
| 3 | If the old production behavior allowed profile selection, verify it still works for token-OFF profile. | User can select the intended normal profile. | | |
| 4 | Start/open POS session with opening balances if required. | POS session opens without token workflow restrictions. | | |
| 5 | Add one normal item to cart. | Item appears with correct price, tax, and quantity. | | |
| 6 | Do not enter Order Name. | No mandatory token Order Name blocks normal invoice flow. | | |
| 7 | Click Pay. | Payment screen opens normally. | | |
| 8 | Confirm configured payment modes are visible. | Cash/Card/Bank Transfer or configured modes appear. | | |
| 9 | Complete payment. | Sales Invoice submits successfully. | | |
| 10 | Open the created Sales Invoice in backend. | Invoice is submitted, linked to correct POS Profile and opening shift. | | |
| 11 | Confirm no relay-down warning blocks submit. | Default POS sale is not blocked by relay behavior. | | |
| 12 | Close shift if applicable. | Closing shift flow works normally. | | |

Evidence to capture: POS Profile, Sales Invoice ID, payment mode screenshot, submitted invoice screenshot.

## Flow 2: Sales Associate Token Flow

Goal: prove Sales Associate can create an order/token without cash opening and without payment access.

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Login as Sales Associate user. | Login succeeds. | | |
| 2 | Open POS. | No cash opening shift dialog appears for Sales Associate. | | |
| 3 | Confirm POS Profile is auto-selected from user default. | No profile switch is required or allowed in token workflow. | | |
| 4 | Confirm Sales Associate sees Save Order button. | Save Order is visible. | | |
| 5 | Confirm payment/invoice actions are not available to Sales Associate. | Sales Associate cannot complete payment. | | |
| 6 | Confirm Print Quotation button visibility follows POS Profile setting. | Button is shown only if allowed. | | |
| 7 | Add one item to cart. | Item appears correctly. | | |
| 8 | Leave Order Name blank and click Save Order. | Mandatory validation blocks save and asks for Order Name. | | |
| 9 | Enter a unique Order Name, for example `QA SA 001`. | Order Name remains visible in cart. | | |
| 10 | Click Save Order. | Sales Order is created. | | |
| 11 | Confirm token dialog appears. | Dialog shows token, date/time, and Order Name. | | |
| 12 | Confirm token is based on last 5 digits of Sales Order number. | Token matches Sales Order suffix. | | |
| 13 | Click print token if available. | Print action opens/prints token without error. | | |
| 14 | Open Sales Order in backend. | Sales Order is submitted, has correct customer/items/order name/profile. | | |
| 15 | Refresh POS and search/reopen if needed. | Created order remains available for cashier retrieval. | | |

Evidence to capture: no-opening-dialog screenshot/video, auto-selected POS Profile, mandatory Order Name validation, token dialog, Sales Order ID.

## Flow 3: Cashier Retrieve Sales Order And Pay

Goal: prove Cashier can retrieve a Sales Associate order by name/token and complete exactly one invoice.

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Login as Cashier user. | Login succeeds. | | |
| 2 | Open POS. | Cashier sees POS Opening Shift dialog if no open shift exists. | | |
| 3 | Confirm Cashier cannot switch away from assigned/default profile in token workflow. | Profile switching is not available for token workflow. | | |
| 4 | Start opening shift with balances. | Shift opens successfully. | | |
| 5 | Search Sales Order by exact Order Name from Flow 2. | Matching unpaid Sales Order appears quickly. | | |
| 6 | Search Sales Order by token / Sales Order suffix. | Same unpaid Sales Order appears. | | |
| 7 | Select the Sales Order. | POS clearly shows which Sales Order is selected. | | |
| 8 | Confirm cart matches Sales Order items, quantities, rates, taxes, customer, and discounts. | No mismatch from original order. | | |
| 9 | Click Pay once. | Draft Sales Invoice is created or reused for selected SO. | | |
| 10 | Confirm payment modes are visible. | Cash/Card/Bank Transfer or configured modes appear. | | |
| 11 | Complete payment. | Sales Invoice submits successfully. | | |
| 12 | Open Sales Invoice in backend. | Invoice links to the selected Sales Order items. | | |
| 13 | Search the same Sales Order again. | Paid/fully billed Sales Order should not appear for payment. | | |
| 14 | Click Pay again without reselecting the SO. | No duplicate Sales Invoice is created. | | |
| 15 | Reselect the same SO if it still appears, then click Pay. | System must not create another SI for already paid/fully billed SO. | | |

Evidence to capture: Sales Order search by name, search by token, selected SO UI, Sales Invoice ID, backend link between SI and SO.

## Flow 4: Duplicate And Permission Guard Tests

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | As Sales Associate, try to access payment flow. | Blocked or payment actions unavailable. | | |
| 2 | As Sales Associate, try to open cash shift. | Cash opening is cashier-only or unavailable. | | |
| 3 | As Cashier, select an unpaid SO and click Pay repeatedly before submit. | Existing draft SI is reused; no duplicate draft invoices. | | |
| 4 | As Cashier, try to delete an invoice/SO from POS list if delete is not allowed. | No unhandled permission error is shown. | | |
| 5 | As Cashier, pay an SO, then refresh and search again. | Paid SO is hidden from unpaid list. | | |
| 6 | As Cashier, attempt to retrieve a stale/old SO outside POS Profile policy. | Behavior follows POS Profile stale SO settings. | | |
| 7 | As a user with multiple `cline-*` roles, open token workflow POS. | Clear role error appears; ambiguous role is blocked. | | |
| 8 | As user without default POS Profile, open token workflow POS. | Clear default profile error appears. | | |

## Flow 5: Quotation And Print Quote

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | On token profile, turn Print Quotation setting ON if available. | Print Quote button appears for allowed role. | | |
| 2 | Turn Print Quotation setting OFF if available. | Print Quote button is hidden. | | |
| 3 | As Sales Associate, create quotation if role/profile allows it. | Quotation is created with correct customer/items. | | |
| 4 | Search quotation by quotation number. | Quotation appears if valid and allowed by policy. | | |
| 5 | Convert quotation to Sales Order token. | Sales Order token is created and dialog appears. | | |
| 6 | As Cashier, retrieve converted Sales Order and pay. | Invoice submits once and links to SO. | | |

Evidence to capture: button visibility for ON/OFF, Quotation ID, converted Sales Order ID, Sales Invoice ID.

## Flow 6: Relay And Connectivity Behavior

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Use token-OFF default POS Profile with relay unavailable. | Sale can still submit normally. | | |
| 2 | Use token-ON POS Profile with relay unavailable. | Behavior follows relay/POS Profile configuration. | | |
| 3 | Confirm no confirmation prompt says: `Edge Relay is down/unreachable, but cloud is reachable. Submit directly to cloud for this sale?` | This prompt should not appear. | | |
| 4 | If relay-down message appears, record exact POS Profile and action. | Message should be explainable by token profile relay setting. | | |
| 5 | Open browser console during payment. | No blocking JS errors related to relay submit flow. | | |

## Flow 7: Closing Shift

| # | Step | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | As Cashier, complete at least one paid invoice. | Invoice is submitted under current POS Opening Shift. | | |
| 2 | Open close shift flow. | POS transactions and payments load. | | |
| 3 | Confirm payment reconciliation values. | Expected amount includes opening cash, invoices, and payment entries. | | |
| 4 | Submit closing shift. | Closing shift submits without deadlock/permission error. | | |
| 5 | Open POS Opening Shift in backend. | Opening shift is marked closed and linked to closing shift. | | |

## Browser Console Checks

Run these checks during each flow.

| # | Check | Expected Result | Pass/Fail | Notes |
| --- | --- | --- | --- | --- |
| 1 | Browser console has no `403 FORBIDDEN` on POS Profile, POS Opening Shift, Sales Order, Sales Invoice APIs. | No permission failures. | | |
| 2 | Browser console has no `Sales Invoice None not found`. | Pay flow has valid invoice name. | | |
| 3 | Browser console has no repeated recursion/modal focus error during normal actions. | Dialogs open/close normally. | | |
| 4 | Network tab shows successful calls for save order, search orders, create invoice, submit invoice. | API responses are 200 unless validation is expected. | | |

## Final Sign-Off

| Area | Pass/Fail | Evidence |
| --- | --- | --- |
| Default POS token-OFF sale works like normal POS | | |
| Sales Associate creates token order | | |
| Cashier retrieves and pays token order | | |
| No duplicate Sales Invoice is created | | |
| Paid Sales Order is hidden from cashier unpaid list | | |
| Payment modes show correctly | | |
| Print Quotation visibility follows setting | | |
| Relay does not block default POS profile | | |
| Cashier closing shift works | | |
| No critical browser console errors | | |

## Minimum Video Demo Sequence

Record this if a short demo is needed:

1. Sales Associate login.
2. POS opens without cash opening dialog.
3. POS Profile auto-selected.
4. Add item.
5. Show blank Order Name validation.
6. Enter Order Name and Save Order.
7. Show token dialog and token print option.
8. Cashier login.
9. Cashier opening shift.
10. Search Sales Order by Order Name/token.
11. Select Sales Order and show selected state.
12. Pay using configured payment mode.
13. Show submitted Sales Invoice.
14. Search same Sales Order again and show it is not available for payment.
