# Sales Order Token System - Deployment & Testing Guide

**Branch**: `feature/sales-order-token`  
**Latest Commit**: `d8de92c`  
**Date**: January 22, 2026  
**Status**: ✅ READY FOR TESTING

---

## 🎯 What's Been Built

### Phase 1: Backend (Complete) ✅
- Custom fields for Sales Order
- Commission calculation API
- QR code generation
- Order creation & retrieval APIs
- Pending orders query

### Phase 2: Frontend (Complete) ✅
- "Generate Order" button for Sales Associate
- Order dialog with QR code
- Pending Orders sidebar
- Cashier scan input for Sales Orders
- Load order into cart functionality

---

## 📋 Deployment Steps for Frappe Cloud

### Step 1: Deploy Branch

1. **Go to your Frappe Cloud dashboard**
2. **Navigate to your dev site**
3. **Go to Deploy tab** (or Site Settings)
4. **Select branch**: `feature/sales-order-token`
5. **Click "Deploy"**
6. **Wait for deployment** (usually 5-10 minutes)

---

### Step 2: Create Custom Fields (IMPORTANT!)

After deployment, you **MUST manually create** these custom fields:

#### A. Sales Order Custom Fields

**Go to**: Customize Form → Sales Order

**Add these 4 fields:**

1. **Sales Associate**
```
Field Name: custom_sales_associate
Label: Sales Associate (User)
Type: Link
Options: User
Insert After: customer
☑ Read Only
☑ In Standard Filter
```

2. **Order Type**
```
Field Name: custom_order_type
Label: Order Type
Type: Select
Options: 
  POS Token Order
  Regular Order
  Delivery Order
Default: Regular Order
Insert After: custom_sales_associate
☑ In List View
☑ In Standard Filter
```

3. **POS Opening Shift**
```
Field Name: custom_pos_opening_shift
Label: POS Opening Shift
Type: Link
Options: POS Opening Shift
Insert After: custom_order_type
☑ Read Only
```

4. **Token QR Code**
```
Field Name: custom_token_qr_code
Label: Token QR Code
Type: Attach Image
Insert After: custom_pos_opening_shift
☑ Read Only
☑ Hidden
```

**Click "Update"** to save

---

#### B. Sales Invoice Custom Fields (If Not Already Created)

**Go to**: Customize Form → Sales Invoice

1. **POS Token** (if not exists)
```
Field Name: custom_pos_token
Label: POS Token
Type: Link
Options: POS Token
☑ Read Only
```

2. **Sales Associate** (if not exists)
```
Field Name: custom_sales_associate
Label: Sales Associate (User)
Type: Link
Options: User
☑ Read Only
```

---

### Step 3: Configure POS Profile

**Go to**: POS Profile → [Your Profile]

**Ensure these are set:**
```
☑ Commission Enabled (custom_commission_enabled)
Sales Person Grand Total Limit: 1000 (or your threshold)
```

---

### Step 4: Setup Sales Person Records

For each Sales Associate, ensure they have a Sales Person record:

**Go to**: Sales Person → New/Edit

```
Sales Person Name: [Name]
☑ Enabled
User: [Link to Sales Associate user] ← custom_user field
Commission Rate: 0.5 (or 1.0, etc.)
```

---

### Step 5: Role Permissions

**Ensure these permissions exist:**

#### Sales Associate Role:
```
Sales Order:
  ☑ Create
  ☑ Read
  ☑ Submit
  ☑ Print
  ☐ Cancel (no)
  
Sales Invoice:
  ☐ All permissions (no)
```

#### Cashier Role:
```
Sales Order:
  ☑ Read
  ☑ Print
  ☑ Cancel (optional)
  ☐ Create (no)
  
Sales Invoice:
  ☑ Create
  ☑ Read
  ☑ Write
  ☑ Submit
  ☑ Cancel
  ☑ Print
```

---

## 🧪 Testing Guide

### Test 1: Sales Associate Creates Order

**Login as**: Sales Associate (e.g., `em_sales_associate2@pjjamaica.com`)

**Steps:**
1. Open POS Awesome
2. Search and select customer
3. Add items to cart (total > $1,000 for commission)
4. Click **"GENERATE ORDER"** button (purple, large)
5. Wait for order creation
6. **Verify Dialog Shows:**
   - Order number (SO-PJK-2026-XXXXX)
   - QR code image
   - Total amount
   - Commission applied: Yes/No
   - Commission rate and amount

7. Click "Print Order" (opens Sales Order print view)
8. Click "Done" to close dialog
9. Cart should be cleared
10. **Check Pending Orders Sidebar:**
    - Purple icon on right side
    - Click to expand
    - Should show your new order

**Expected Result:**
- ✅ Sales Order created and submitted
- ✅ Commission in sales_team table
- ✅ QR code generated
- ✅ Order visible in sidebar

---

### Test 2: Cashier Processes Order

**Login as**: Cashier (e.g., `em_cashier@pjjamaica.com`)

**Steps:**
1. Open POS Awesome
2. Open shift (if required)
3. Click **"Cashier - Scan Order"** button or icon
4. **Scan QR code** or type order number (e.g., `SO-PJK-2026-00001`)
5. Press Enter
6. **Verify:**
   - Order loads into cart
   - Customer auto-selected
   - Items displayed with correct quantities
   - Prices locked from order
   - Total amount matches

7. **(Optional) Modify quantities** if customer changes mind
8. Click **"Pay"** button
9. Select payment method
10. Click **"Submit"**

**Expected Result:**
- ✅ Sales Invoice created from Sales Order
- ✅ Commission auto-copied to invoice
- ✅ Sales Team table populated
- ✅ Invoice submitted successfully
- ✅ Sales Order status → "Completed"
- ✅ Receipt printed

---

### Test 3: Commission Verification

**Go to**: Sales Invoice → [The created invoice]

**Verify:**
1. **Sales Team Table** has entry:
   - Sales Person: [Linked to Sales Associate]
   - Commission Rate: 0.5% or 1.0%
   - Allocated Percentage: 100

2. **Amount Eligible for Commission**: Matches grand total

3. **Custom Fields**:
   - `custom_sales_associate`: Shows Sales Associate email
   - `custom_pos_token`: Empty (not using old token)

---

### Test 4: Pending Orders Sidebar

**Login as**: Sales Associate

**Steps:**
1. Create 2-3 orders without paying
2. Look at right side of screen
3. Click purple receipt icon
4. **Verify:**
   - Sidebar expands
   - Shows all your pending orders
   - Displays customer names
   - Shows order amounts
   - Shows order dates
   - Total pending value calculated

5. Click on an order
6. **Verify**: Shows order details popup

---

### Test 5: Backward Compatibility (Optional)

If you still have old POS Tokens:

**Login as**: Cashier

**Steps:**
1. Click "Cashier - Scan Order"
2. Enter old token number (not SO-XXX format)
3. **Verify**: System still retrieves old token
4. Process payment normally

---

## 🔍 Troubleshooting

### Issue 1: "Generate Order" button not showing

**Check:**
- User has "POS Sales Associate" role
- Logged in as Sales Associate user
- Clear browser cache (Ctrl+Shift+Delete)

---

### Issue 2: Custom fields missing

**Solution:**
- Go back to Step 2 and create fields manually
- Make sure field names match exactly (with `custom_` prefix)
- Click "Update" to save

---

### Issue 3: Commission not calculating

**Check:**
1. POS Profile → `custom_commission_enabled` is checked
2. Order total >= `custom_sales_person_grand_total_limit`
3. Sales Person has `custom_user` linked to Sales Associate
4. Sales Person has `commission_rate` set
5. Sales Person is enabled

---

### Issue 4: Cashier can't scan order

**Check:**
- Order number format: `SO-PJK-2026-00001` (starts with SO-)
- Order exists and is submitted
- Order not already fully billed
- Cashier has Read permission on Sales Order

---

### Issue 5: Order doesn't load into cart

**Check browser console** (F12 → Console):
- Look for JavaScript errors
- Check network tab for failed API calls
- Verify `load_sales_order` event is working

**Try:**
- Clear cache and refresh
- Check if items exist in system
- Verify warehouse settings

---

## 📊 What to Verify During Testing

### Backend Validation:
- [ ] Sales Order created with correct doctype
- [ ] Custom fields populated correctly
- [ ] Commission added to sales_team table
- [ ] QR code generated and stored
- [ ] Order status correct

### Frontend Validation:
- [ ] Generate Order button visible for SA
- [ ] Order dialog displays correctly
- [ ] QR code image renders
- [ ] Pending Orders sidebar works
- [ ] Cashier scan input accepts SO-XXX
- [ ] Cart loads order items
- [ ] Payment processing works

### Commission Flow:
- [ ] Commission calculated at order creation
- [ ] Rate fetched from Sales Person master
- [ ] Threshold check works
- [ ] Commission copies to Sales Invoice
- [ ] Amount calculates correctly

---

## 🐛 Known Issues & Limitations

### Current Limitations:
1. **Print Format**: Order prints as standard Sales Order (no custom QR format yet)
   - Workaround: Print directly from Sales Order document

2. **Sales Associate Can't Cancel**: Only manager can cancel orders
   - Workaround: Request cancellation from manager

3. **No Partial Billing UI**: Can bill order multiple times, but no UI indicator
   - Works: System tracks `per_billed` percentage

### Future Enhancements (Not Yet Built):
- [ ] Custom print format with QR code
- [ ] Order cancellation request workflow
- [ ] Edit order after creation (amendment)
- [ ] Multiple payment splitting UI
- [ ] Order history dashboard

---

## 📝 Testing Checklist

Before marking as complete, verify:

- [ ] Deployed `feature/sales-order-token` branch
- [ ] Created all 4 custom fields on Sales Order
- [ ] Created 2 custom fields on Sales Invoice (if missing)
- [ ] Configured POS Profile commission settings
- [ ] Created Sales Person records for all Sales Associates
- [ ] Set up role permissions
- [ ] Tested Sales Associate order creation
- [ ] Tested Cashier order retrieval
- [ ] Verified commission calculation
- [ ] Checked pending orders sidebar
- [ ] Tested with multiple orders
- [ ] Verified Sales Invoice generation
- [ ] Checked Sales Order status updates

---

## 📞 Support

**If you encounter issues:**

1. **Check browser console** (F12) for JavaScript errors
2. **Check ERPNext Error Log**: Home → Error Log
3. **Check backend logs** on Frappe Cloud (if accessible)
4. **Test API directly** in console:
   ```javascript
   frappe.call({
       method: 'posawesome.posawesome.api.sales_order_token.get_pending_orders',
       args: { sales_associate: frappe.session.user },
       callback: (r) => console.log(r.message)
   });
   ```

5. **Report back** with:
   - What you were doing
   - Error message
   - Screenshot of console/error log
   - User role being tested

---

## ✅ Success Criteria

System is working if:
1. ✅ Sales Associate can create orders (no payment)
2. ✅ Orders show in pending sidebar
3. ✅ Cashier can scan and load orders
4. ✅ Payment processing creates invoices
5. ✅ Commission appears in invoices
6. ✅ Sales Order status updates to "Completed"
7. ✅ No JavaScript errors in console
8. ✅ Both roles work without errors

---

## 🚀 Next Steps After Testing

Once testing is successful:

### Short-term:
1. **Report any bugs** you find
2. **Request refinements** (UI tweaks, workflow changes)
3. **Test edge cases** (cancellations, returns, etc.)

### Medium-term:
1. **Build custom print format** with QR code
2. **Add order amendment workflow**
3. **Create reports** for pending orders

### Long-term:
1. **Migrate old tokens** to Sales Orders (if needed)
2. **Deprecate POS Token doctype**
3. **Train all users** on new system

---

**Ready to test! Deploy the branch and follow the steps above.** 🎉

Let me know how it goes!
