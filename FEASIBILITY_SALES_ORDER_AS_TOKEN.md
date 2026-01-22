# Feasibility Assessment: Sales Order as Token System

**Date**: January 22, 2026  
**Status**: Feasibility Analysis (No Code Changes)

---

## Executive Summary

**Verdict**: ✅ **HIGHLY FEASIBLE & RECOMMENDED**

Using Sales Order as the "token" is **architecturally superior** to both the custom Token and draft Invoice approaches:

1. ✅ **Proper accounting separation**: Order (intent) vs Invoice (transaction)
2. ✅ **Standard ERPNext workflow**: Sales Order → Sales Invoice is core functionality
3. ✅ **No draft invoices**: Maintains clean accounting records
4. ✅ **Built into POS Awesome**: Conversion functions already exist
5. ✅ **Audit-friendly**: Clear paper trail of order → payment → invoice

---

## Why Sales Order is the Right Choice

### Accounting Best Practices

```
❌ WRONG: Draft Sales Invoice
   - Invoices should only exist when payment is collected
   - Draft invoices pollute accounting reports
   - Confusing for auditors

✅ RIGHT: Sales Order → Sales Invoice
   - Sales Order = Customer's intent to purchase
   - Sales Invoice = Actual transaction with payment
   - Clean separation of concerns
```

### Standard ERPNext Flow

```
Sales Order (docstatus=1, status="To Deliver and Bill")
    ↓
Customer brings order to cashier
    ↓
Cashier creates Sales Invoice from Sales Order
    ↓
Collects payment & submits invoice
    ↓
Sales Order status → "Completed"
```

This is **exactly how ERPNext is designed to work**!

---

## Detailed Workflow Design

### 🔵 SALES ASSOCIATE WORKFLOW

#### Step 1: Create Customer
```
Action: Look up or create customer
Fields:
  - custom_created_by_sales_associate = current user
  - custom_default_sales_person = linked Sales Person
```

#### Step 2: Add Items to Cart
```
Action: Select items, quantities, prices
Same as current POS Awesome flow
```

#### Step 3: Create Sales Order (Instead of Token)
```
Doctype: Sales Order
Status: Submitted (docstatus=1)
Key Fields:
  - customer
  - items[] (from cart)
  - sales_team[] 
      └─ sales_person (linked to Sales Associate)
      └─ commission_rate (from Sales Person master)
  - custom_sales_associate = current user
  - delivery_date = today (or future)
  - posa_pos_opening_shift = current shift
  - custom_order_type = "POS Token Order" (to differentiate)

API Call:
  posawesome.posawesome.api.posapp.create_sales_order_for_token()
  
Backend Logic:
  1. Validate items availability
  2. Calculate totals
  3. Check commission eligibility
  4. Add sales_team entry if eligible
  5. Submit Sales Order (docstatus=1)
  6. Return Sales Order name
```

#### Step 4: Print Order Receipt with QR Code
```
Print Format: "POS Token Order Receipt"
Contents:
  - Customer name
  - Order number (SO-PJK-2026-00001)
  - Items list with prices
  - Total amount
  - Sales Associate name
  - Date/Time
  - QR Code containing: SO-PJK-2026-00001
  - Instructions: "Bring this to cashier for payment"

QR Code Generation:
  - Same as current token
  - Contains Sales Order name
```

#### Step 5: Hand Receipt to Customer
```
Customer takes receipt to cashier counter
Sales Order status: "To Deliver and Bill"
```

---

### 🟢 CASHIER WORKFLOW

#### Step 1: Scan QR Code
```
Action: Scan QR code on receipt
QR Contains: "SO-PJK-2026-00001"

UI: Cashier Mode (existing component)
New Button: "Scan Order" (instead of "Scan Token")
```

#### Step 2: Retrieve Sales Order
```
API Call:
  posawesome.posawesome.api.posapp.get_sales_order_for_cashier(order_name)

Backend:
  1. Fetch Sales Order document
  2. Verify status = "To Deliver and Bill"
  3. Check if already billed (prevent double billing)
  4. Return order details

Response:
  {
    "order_name": "SO-PJK-2026-00001",
    "customer": "Customer Name",
    "items": [...],
    "grand_total": 2700.00,
    "sales_team": [{...}],  // Commission info
    "sales_associate": "em_sales_associate2@pjjamaica.com"
  }
```

#### Step 3: Load Order into POS
```
UI Action:
  1. Load order items into cart
  2. Display customer info
  3. Show order total
  4. Cashier can:
     ✓ Review items
     ✓ Modify quantities (if policy allows)
     ✓ Add/remove items (if policy allows)
     ✗ Cannot change prices (locked from order)
```

#### Step 4: Collect Payment
```
Action: Click "Collect Payment"

Same as current POS flow:
  - Select payment method(s)
  - Enter amounts
  - Calculate change
```

#### Step 5: Create Sales Invoice from Order
```
API Call:
  posawesome.posawesome.api.posapp.create_invoice_from_sales_order()

Backend Logic:
  1. Create Sales Invoice from Sales Order (standard ERPNext function)
  2. Copy all fields:
     - items[]
     - customer
     - sales_team[] (with commission)
     - custom_sales_associate
  3. Add payment entries
  4. Set custom_sales_order = order name (for reference)
  5. Submit invoice (docstatus=1)
  6. Update Sales Order:
     - Link invoice in Sales Order Item table
     - Status → "Completed" (if fully billed)
  7. Return invoice details

Standard ERPNext Function:
  erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice()
```

#### Step 6: Print Invoice & Complete
```
Print: Sales Invoice (standard POS receipt)
Result:
  - Customer receives invoice
  - Sales Order marked as completed
  - Commission tracked in invoice
```

---

## Technical Implementation Details

### Custom Fields Required

#### Sales Order Doctype
```
1. custom_sales_associate (Link → User)
   - Tracks who created the order
   - Read only
   
2. custom_order_type (Select)
   - Options: "POS Token Order", "Regular Order", "Delivery Order"
   - Default: "Regular Order"
   - Used to filter token-style orders

3. custom_pos_opening_shift (Link → POS Opening Shift)
   - Links order to shift for reporting
```

#### Sales Invoice Doctype
```
1. custom_sales_order (Link → Sales Order)
   - Already may exist (standard linking)
   - Used to track which order was paid
   
2. custom_sales_associate (Link → User)
   - Copied from Sales Order
   - For commission reporting
```

---

### API Endpoints Needed

#### For Sales Associate

```python
@frappe.whitelist()
def create_sales_order_for_token(customer, items, pos_profile):
    """
    Create and submit a Sales Order for token workflow
    
    Args:
        customer: Customer name
        items: List of items with qty, rate
        pos_profile: Current POS Profile
    
    Returns:
        {
            "order_name": "SO-PJK-2026-00001",
            "grand_total": 2700.00,
            "qr_code": "base64_image",
            "print_html": "receipt_html"
        }
    """
    # 1. Create Sales Order doc
    # 2. Add items
    # 3. Check commission eligibility
    # 4. Add sales_team entry
    # 5. Submit order
    # 6. Generate QR code
    # 7. Return order details
```

#### For Cashier

```python
@frappe.whitelist()
def get_sales_order_for_cashier(order_name):
    """
    Retrieve Sales Order for cashier to process
    
    Args:
        order_name: Sales Order name from QR scan
    
    Returns:
        Full Sales Order document with validation
    
    Validations:
        - Order exists
        - Not already fully billed
        - Status is "To Deliver and Bill"
    """
    # 1. Fetch Sales Order
    # 2. Validate status
    # 3. Check for existing invoices
    # 4. Return order data
```

```python
@frappe.whitelist()
def create_invoice_from_sales_order(order_name, payments):
    """
    Create Sales Invoice from Sales Order with payments
    
    Uses standard ERPNext function:
    erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice()
    
    Args:
        order_name: Sales Order name
        payments: Payment details (same as current flow)
    
    Returns:
        {
            "invoice_name": "SINV-PJK-2026-00009",
            "status": "Submitted"
        }
    """
    # 1. Call standard make_sales_invoice()
    # 2. Add payment entries
    # 3. Copy custom fields
    # 4. Submit invoice
    # 5. Update Sales Order status
    # 6. Return invoice details
```

---

## Comparison: Current Token vs Sales Order

| Aspect | Current (POS Token) | Proposed (Sales Order) |
|--------|---------------------|------------------------|
| **Doctype** | Custom "POS Token" | Standard "Sales Order" |
| **Accounting** | Non-standard | Standard ERPNext flow |
| **Status Tracking** | Custom (Pending/Paid) | Standard (To Bill/Completed) |
| **Data Duplication** | High (Token + Invoice) | Low (Order → Invoice) |
| **ERPNext Integration** | Poor | Excellent |
| **Reports** | Custom needed | Standard reports work |
| **Audit Trail** | Clear | Clearer (standard) |
| **Commission** | Custom fields | Standard sales_team |
| **Modification** | Complex | Standard ERPNext |
| **Future Updates** | May break | Forward compatible |
| **Learning Curve** | High (custom) | Low (standard) |

**Winner: Sales Order (10/10 vs Token 3/10)**

---

## Role Permissions

### Sales Associate Role

**Sales Order Permissions:**
- ✓ Create
- ✓ Read
- ✓ Write (before submit)
- ✓ Submit
- ✗ Cancel
- ✓ Print

**Why Submit?**: 
- Submitted order = confirmed order
- Prevents accidental modification
- Sales Associate can't cancel after customer takes receipt

### Cashier Role

**Sales Order Permissions:**
- ✓ Read
- ✗ Write (locked after submit)
- ✗ Submit
- ✗ Cancel

**Sales Invoice Permissions:**
- ✓ Create
- ✓ Read
- ✓ Write
- ✓ Submit
- ✓ Cancel
- ✓ Print

**Why**: Cashier creates invoice FROM order, doesn't modify order

---

## Commission Calculation Flow

### During Order Creation (Sales Associate)

```python
# In create_sales_order_for_token()

# 1. Get POS Profile settings
commission_enabled = pos_profile.custom_commission_enabled
threshold = pos_profile.custom_sales_person_grand_total_limit

# 2. Check eligibility
if commission_enabled and order.grand_total >= threshold:
    
    # 3. Get Sales Person linked to Sales Associate
    sales_person = frappe.db.get_value(
        "Sales Person",
        {"custom_user": sales_associate},
        ["name", "commission_rate"],
        as_dict=True
    )
    
    # 4. Add to sales_team
    order.append("sales_team", {
        "sales_person": sales_person.name,
        "allocated_percentage": 100,
        "commission_rate": sales_person.commission_rate
    })

# 5. Submit order (commission data saved)
```

### During Invoice Creation (Cashier)

```python
# In create_invoice_from_sales_order()

# Standard ERPNext function automatically copies sales_team from Order to Invoice
invoice = make_sales_invoice(order_name)

# Sales team table is automatically populated!
# Commission shows in invoice without extra code
```

**Key Point**: Commission is calculated ONCE (at order creation) and automatically flows to invoice!

---

## Order Modification Scenarios

### Scenario 1: Customer Changes Mind (Add Items)

**Option A: Modify Order (Requires Amendment)**
```
1. Cashier cancels original order
2. Creates amended order with new items
3. Processes payment
```
❌ Complex, not recommended

**Option B: Create New Invoice with Different Items**
```
1. Cashier creates Sales Invoice (not from order)
2. Adds items customer actually wants
3. Leaves original order unfulfilled
4. Marks order as "Cancelled" or "On Hold"
```
✓ Simpler, standard practice

**Recommended**: Option B
- Most businesses allow cashier to override order
- Original order stays as record of what was requested
- Invoice reflects what was actually sold

### Scenario 2: Customer Changes Quantity

**Implementation**:
```javascript
// In cashier UI
if (order_item.qty !== cart_item.qty) {
    show_warning("Quantity changed from " + order_item.qty + " to " + cart_item.qty);
    // Allow or prevent based on policy
}

// Backend creates invoice with actual quantities
// Order remains unchanged (audit trail)
```

### Scenario 3: Customer Cancels Order

**Sales Associate**:
- Can submit cancellation request
- Manager approves

**Cashier**:
- Cannot cancel order (needs manager)
- Can create credit note if already billed

---

## Status Tracking

### Sales Order Status Field (Standard ERPNext)

```
"Draft" → Order being created (docstatus=0)
  ↓
"To Deliver and Bill" → Submitted, awaiting payment (docstatus=1)
  ↓
"To Bill" → Partially delivered
  ↓
"To Deliver" → Partially billed
  ↓
"Completed" → Fully billed and delivered (docstatus=1)
  ↓
"Cancelled" → Cancelled (docstatus=2)
```

### For Token Workflow

```
Sales Associate creates order:
  status = "To Deliver and Bill"
  per_billed = 0
  per_delivered = 0

Cashier creates invoice:
  status = "Completed" (if fully billed)
  per_billed = 100
  per_delivered = 100 (if update_stock=1)
```

### Dashboard Filtering

**Sales Associate View**:
```sql
-- Show "my pending orders"
SELECT * FROM `tabSales Order`
WHERE custom_sales_associate = current_user
AND status = "To Deliver and Bill"
AND docstatus = 1
ORDER BY creation DESC
```

**Cashier View**:
```sql
-- Show "orders awaiting payment"
SELECT * FROM `tabSales Order`
WHERE posa_pos_opening_shift = current_shift
AND status = "To Deliver and Bill"
AND per_billed < 100
AND docstatus = 1
ORDER BY creation DESC
```

---

## QR Code Implementation

### Print Format: "POS Token Order Receipt"

**Jinja Template**:
```html
<div style="text-align: center;">
    <h2>Order Receipt</h2>
    <p>Please bring this to cashier for payment</p>
    
    <h3>{{ doc.name }}</h3>
    
    <table>
        <tr><th>Customer:</th><td>{{ doc.customer_name }}</td></tr>
        <tr><th>Sales Associate:</th><td>{{ doc.custom_sales_associate }}</td></tr>
        <tr><th>Date:</th><td>{{ doc.transaction_date }}</td></tr>
    </table>
    
    <h3>Items</h3>
    <table>
        {% for item in doc.items %}
        <tr>
            <td>{{ item.item_name }}</td>
            <td>{{ item.qty }}</td>
            <td>{{ item.amount }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Total: {{ doc.currency }} {{ doc.grand_total }}</h2>
    
    <!-- QR Code -->
    <img src="{{ qr_code_base64(doc.name) }}" style="width: 200px; height: 200px;">
    
    <p>Order Number: {{ doc.name }}</p>
</div>
```

**QR Code Function** (existing in token.py):
```python
def generate_qr_code(data):
    """Generate QR code for order number"""
    # Same as current implementation
    # Returns base64 encoded image
```

---

## Migration Path

### Phase 1: Assessment (This document)
✅ Complete

### Phase 2: Proof of Concept (1 week)
- Create Sales Order from Sales Associate UI
- Generate QR code
- Scan and retrieve order in Cashier UI
- Convert to Sales Invoice
- Test commission flow

### Phase 3: Full Implementation (2 weeks)
- Update all UI components
- Add custom fields
- Create API endpoints
- Update print formats
- Role permission configuration

### Phase 4: Data Migration (1 week)
- Migrate existing tokens → Sales Orders (historical)
- Update reports
- Train users

### Phase 5: Deprecate Token (1 week)
- Mark POS Token as archived
- Remove from UI
- Keep data for audit

**Total Timeline: 5 weeks**

---

## Advantages Over Current System

### 1. **Accounting Compliance** ✅
- No draft invoices
- Clean separation: Order vs Invoice
- Audit-friendly

### 2. **Standard ERPNext** ✅
- Uses core functionality
- All reports work
- Future-proof

### 3. **Less Custom Code** ✅
- ~70% less custom code
- Leverage standard functions
- Easier maintenance

### 4. **Better Performance** ✅
- No data duplication
- Standard indexes
- Optimized queries

### 5. **Flexibility** ✅
- Cashier can modify orders
- Standard amendment process
- Delivery scheduling possible

### 6. **Reporting** ✅
- Standard Sales Order reports
- Commission reports work
- Integration with ERPNext BI

---

## Potential Challenges

### Challenge 1: Sales Associate Can't Submit Orders

**Issue**: Standard ERPNext may require manager approval for Sales Orders

**Solution**: 
```python
# Override submit permissions
order_doc.flags.ignore_permissions = True
order_doc.submit()
```
OR
- Grant "Submit" permission to Sales Associate role
- This is safe for POS workflow

---

### Challenge 2: Order Modification by Cashier

**Issue**: Submitted orders can't be edited directly

**Solutions**:
1. Create new invoice with different items (recommended)
2. Allow amendment (complex)
3. Don't allow modification (rigid)

**Recommendation**: Option 1

---

### Challenge 3: Partial Payments

**Issue**: Customer pays deposit, comes back later

**Solution**: 
- Create partial Sales Invoice
- Sales Order remains "To Bill" status
- Second visit creates another invoice for balance
- Standard ERPNext behavior!

---

### Challenge 4: User Confusion

**Issue**: Users familiar with "Token" terminology

**Solution**:
- Keep using "Token" in UI labels
- Backend uses Sales Order
- Print format says "Order Receipt" with QR code
- Training: "Token is now an Order"

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sales Order permissions complex | Medium | Medium | Custom permission logic |
| Users confused by change | High | Low | Good training + UI labels |
| Cashier can't modify orders | Low | Medium | Allow invoice override |
| Commission not copied | Low | High | Test thoroughly |
| Migration data loss | Low | High | Backup + staged rollout |
| Standard updates break it | Very Low | Low | Uses standard functions |

**Overall Risk**: 🟢 Low (Much lower than custom Token system)

---

## Recommendation

### ✅ STRONGLY RECOMMEND: Proceed with Sales Order Approach

**Why**:
1. Architecturally correct (Order → Invoice)
2. No draft invoices (accounting best practice)
3. Uses 90% standard ERPNext functionality
4. Future-proof and maintainable
5. All standard reports work
6. Lower technical debt
7. Easier for new developers

**Next Steps**:
1. Review this document with stakeholders
2. Get approval for approach
3. Build proof of concept (1 week)
4. If successful, proceed with full implementation

---

## Flows Summary

### 📘 Sales Associate Flow (5 steps)
```
1. Create/select customer
   ↓
2. Add items to cart
   ↓
3. Click "Create Order" (instead of "Create Token")
   → Sales Order submitted with commission
   ↓
4. Print order receipt with QR code
   ↓
5. Hand receipt to customer
```

### 📗 Cashier Flow (5 steps)
```
1. Scan QR code → Get order number
   ↓
2. Retrieve Sales Order
   → Load items into cart
   ↓
3. Review/modify items (if needed)
   ↓
4. Click "Collect Payment"
   → Add payment methods
   ↓
5. Submit
   → Creates Sales Invoice from Sales Order
   → Order status → "Completed"
   → Commission tracked in invoice
```

---

**Conclusion**: This approach is **feasible, recommended, and superior** to both the custom Token system and draft Invoice approach. It aligns with ERPNext best practices and provides a clean, maintainable solution.

**Ready for implementation once approved.** ✅
