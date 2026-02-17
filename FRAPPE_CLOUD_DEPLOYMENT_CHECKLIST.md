# Frappe Cloud Deployment Checklist - Manual Configurations Required

**Last Updated**: January 21, 2026  
**Latest Commit**: e874cdc

---

## ⚠️ IMPORTANT NOTES

1. **Why Manual Configuration?**: Frappe Cloud deployments via GitHub do NOT automatically apply custom fields and permissions from fixture files. These must be manually configured in the UI until you set up a local environment and run `bench migrate`.

2. **One-Time Setup**: These configurations only need to be done ONCE per Frappe Cloud instance. Future deployments will retain these settings.

3. **Local Environment**: Once you set up local Frappe development, run `bench export-fixtures` to capture all manual changes, then commit to make them permanent.

---

## 📋 DEPLOYMENT CHECKLIST

### After Each GitHub Deploy to Frappe Cloud:

- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Verify custom fields exist (see Section A)
- [ ] Verify permissions are correct (see Section B)
- [ ] Test token flow end-to-end
- [ ] Test commission calculation

---

## A. CUSTOM FIELDS TO CREATE

### A1. Sales Invoice Custom Fields

**Go to**: Customize Form → Sales Invoice

#### Field 1: POS Token Link
```
Label: POS Token
Field Name: custom_pos_token
Type: Link
Options: POS Token
Insert After: custom_partner_commission_paid
Read Only: ☑ (checked)
In List View: ☐ (unchecked)
```
**Purpose**: Links the invoice back to the token that was paid

---

#### Field 2: Sales Associate
```
Label: Sales Associate (User)
Field Name: custom_sales_associate
Type: Link
Options: User
Insert After: custom_pos_token
Read Only: ☑ (checked)
In List View: ☐ (unchecked)
Description: The user who created the token/order
```
**Purpose**: Tracks which Sales Associate created the order for commission attribution

---

**Click "Update" to save**

### A2. Customer Custom Fields (Already Should Exist)

**Go to**: Customize Form → Customer

#### Field 1: Default Sales Person
```
Field Name: custom_default_sales_person
Label: Default Sales Person
Type: Link
Options: Sales Person
```
**Purpose**: Tracks the primary sales person for this customer

---

#### Field 2: Created By Sales Associate
```
Field Name: custom_created_by_sales_associate
Label: Created By Sales Associate
Type: Link
Options: User
```
**Purpose**: Records which Sales Associate first created this customer

---

### A3. Sales Person Custom Fields (Already Should Exist)

**Go to**: Customize Form → Sales Person

#### Field 1: Linked User
```
Field Name: custom_user
Label: User
Type: Link
Options: User
```
**Purpose**: Links Sales Person to a User account (bypasses broken Employee doctype)

---

### A4. POS Profile Custom Fields (Already Should Exist)

**Go to**: Customize Form → POS Profile

#### Field 1: Commission Enabled
```
Field Name: custom_commission_enabled
Label: Commission Enabled
Type: Check
Default: 0
```
**Purpose**: Master switch to enable/disable commission calculation

---

#### Field 2: Sales Person Grand Total Limit
```
Field Name: custom_sales_person_grand_total_limit
Label: Sales Person Grand Total Limit
Type: Currency
Options: currency
```
**Purpose**: Minimum invoice amount required for commission eligibility

---

#### Field 3: Sales Partner Grand Total Limit (Future Use)
```
Field Name: custom_sales_partner_grand_total_limit
Label: Sales Partner Grand Total Limit
Type: Currency
Options: currency
```
**Purpose**: Minimum invoice amount for partner commission (not currently used)

---

## B. ROLE PERMISSIONS TO CONFIGURE

### B1. POS Cashier - Sales Invoice Permissions

**Go to**: Role Permission Manager

**Select Document Type**: Sales Invoice

**Find/Add Row for Role**: POS Cashier

**Enable the following permissions**:
- ☑ Read (Level 0)
- ☑ Write (Level 0)
- ☑ Create (Level 0)
- ☑ Submit (Level 0)
- ☑ Cancel (Level 0)
- ☑ Print (Level 0)
- ☑ Email (Level 0)
- ☑ Share (Level 0)

**Click "Update"**

**Why**: Without these permissions, cashiers cannot submit invoices, causing "Permission Denied" errors.

---

### B2. Role Profile Assignments (Should Already Exist)

**Go to**: Role Profile

#### POS Cashier Profile
- POS Admin PJB
- PJ SETTINGS READ
- POS Cashier

#### POS Sales Associate Profile
- POS Admin PJB
- PJ SETTINGS READ
- POS Sales Associate

---

## C. POS PROFILE CONFIGURATION

**Go to**: POS Profile → [Your Profile Name]

### Commission Settings Section

```
☑ Commission Enabled (custom_commission_enabled)
Sales Person Grand Total Limit: 1000.00 (or your threshold)
```

**Purpose**: Controls when commission is calculated. Commission only applies if:
1. This checkbox is enabled
2. Invoice grand total >= the limit amount

---

## D. SALES PERSON SETUP

For each Sales Associate user, create a corresponding Sales Person record:

**Go to**: Sales Person → New

```
Sales Person Name: [Sales Associate Name]
Parent Sales Person: All Sales Persons
Is Group: ☐ (unchecked)
Enabled: ☑ (checked)
User: [Link to the Sales Associate's User account] ← custom_user field
Commission Rate: 0.5 (or appropriate %)
```

**Example**:
```
Sales Person Name: em_sales_associate2 Test
User: em_sales_associate2@pjjamaica.com
Commission Rate: 1.0
```

**Why**: The commission system links Sales Associates (Users) to Sales Persons via the `custom_user` field to determine commission rates.

---

## E. VERIFICATION CHECKLIST

After completing all configurations:

### ✅ Custom Fields Verification

**Sales Invoice**:
- [ ] custom_pos_token field exists
- [ ] custom_sales_associate field exists

**Customer**:
- [ ] custom_default_sales_person field exists
- [ ] custom_created_by_sales_associate field exists

**Sales Person**:
- [ ] custom_user field exists

**POS Profile**:
- [ ] custom_commission_enabled field exists
- [ ] custom_sales_person_grand_total_limit field exists

### ✅ Permissions Verification

- [ ] POS Cashier can create Sales Invoice
- [ ] POS Cashier can submit Sales Invoice
- [ ] POS Cashier can cancel Sales Invoice

### ✅ Data Setup Verification

- [ ] Each Sales Associate has a corresponding Sales Person record
- [ ] Each Sales Person has custom_user field populated
- [ ] Each Sales Person has commission_rate set
- [ ] POS Profile has commission enabled
- [ ] POS Profile has grand total limit set

---

## F. TESTING PROCEDURE

### Test 1: Token Creation
1. Login as Sales Associate 1
2. Create a new customer
3. Verify `custom_created_by_sales_associate` is populated
4. Add items to cart (total > commission limit)
5. Generate token
6. Verify token status = "Pending"

### Test 2: Token Payment & Commission
1. Login as Cashier
2. Scan token QR code
3. Click "COLLECT PAYMENT"
4. Complete payment
5. **Verify**:
   - Token status changed to "Paid"
   - Token `linked_invoice` field populated
   - Sales Invoice created and submitted
   - Sales Invoice `custom_pos_token` = token name
   - Sales Invoice `custom_sales_associate` = Sales Associate email
   - Sales Invoice → Sales Team table has entry
   - Commission rate matches Sales Person master
   - Amount eligible for commission = net total

### Test 3: Multiple Rates
1. Create Sales Person 1 with 0.5% rate
2. Create Sales Person 2 with 1.0% rate
3. Each creates a token
4. Process both tokens
5. Verify each invoice has correct commission rate

---

## G. TROUBLESHOOTING

### Issue: "Permission Denied" when cashier submits invoice

**Solution**: Add Sales Invoice permissions to POS Cashier role (Section B1)

---

### Issue: Commission not calculated

**Check**:
1. POS Profile → Commission Enabled is checked
2. Invoice grand total >= Sales Person Grand Total Limit
3. Sales Person has `custom_user` field populated
4. Sales Person has `commission_rate` set
5. Sales Person is enabled
6. Token has `sales_associate` field populated

---

### Issue: Token status stays "Pending"

**Check**:
1. Custom fields are created (Section A)
2. Code is deployed (latest commit: e874cdc)
3. Browser cache is cleared
4. Check browser console for JavaScript errors
5. Check Frappe Error Log for backend errors

---

### Issue: Custom fields not appearing

**Solution**: 
1. Go to Customize Form
2. Select the doctype
3. Add the fields manually as per Section A
4. Click Update

---

## H. FUTURE: MAKING CONFIGURATIONS PERMANENT

Once you set up a local Frappe development environment:

```bash
# 1. Install Frappe locally
bench get-app posawesome https://github.com/webdev3pj/POS-Awesome-pj.git --branch production_deploy

# 2. Create new site
bench new-site your-site.local

# 3. Install app
bench --site your-site.local install-app posawesome

# 4. Manually create all custom fields in UI (as per Section A)

# 5. Export fixtures
bench --site your-site.local export-fixtures

# 6. Commit changes
cd apps/posawesome
git add fixtures/
git commit -m "Export custom fields to fixtures"
git push origin production_deploy

# 7. Future deployments will automatically have these fields
```

---

## I. QUICK REFERENCE: FIELD NAMES

For developers/scripts:

### Sales Invoice
- `custom_pos_token` (Link → POS Token)
- `custom_sales_associate` (Link → User)

### Customer
- `custom_default_sales_person` (Link → Sales Person)
- `custom_created_by_sales_associate` (Link → User)

### Sales Person
- `custom_user` (Link → User)

### POS Profile
- `custom_commission_enabled` (Check)
- `custom_sales_person_grand_total_limit` (Currency)
- `custom_sales_partner_grand_total_limit` (Currency)

### POS Token (Standard fields, no custom)
- `sales_associate` (Link → User)
- `sales_person` (Link → Sales Person)
- `linked_invoice` (Link → Sales Invoice)
- `status` (Select: Pending/Paid/Cancelled)
- `paid_datetime` (Datetime)
- `cashier` (Link → User)

---

## J. COMMIT HISTORY

- `c5de406` - Initial Sales Associate commission tracking
- `6f6cf7b` - Added POS Cashier permissions to fixtures
- `e874cdc` - Fixed token commission and status update (CURRENT)

---

## K. SUPPORT CONTACTS

- GitHub Repo: https://github.com/webdev3pj/POS-Awesome-pj
- Branch: production_deploy

---

**IMPORTANT**: Print this document or save it where your developer can easily access it. Every new Frappe Cloud deployment or environment setup will require these manual configurations until you complete the local environment setup and fixture export (Section H).

---

**Last Verified**: January 21, 2026  
**Tested On**: Frappe Cloud (devpjjamaica.v.frappe.cloud)  
**App**: POS Awesome (Custom Fork)
