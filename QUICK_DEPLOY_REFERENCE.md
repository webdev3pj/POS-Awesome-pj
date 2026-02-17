# Quick Reference - Manual Configurations After Deploy

## ⚡ MUST DO AFTER EACH DEPLOYMENT

### 1️⃣ Clear Browser Cache
```
Ctrl + Shift + Delete → Clear cache
```

### 2️⃣ Create Custom Fields (ONE TIME ONLY)

**Sales Invoice** (Customize Form):
- `custom_pos_token` → Link → POS Token → Read Only
- `custom_sales_associate` → Link → User → Read Only

**Customer** (should exist):
- `custom_default_sales_person` → Link → Sales Person
- `custom_created_by_sales_associate` → Link → User

**Sales Person** (should exist):
- `custom_user` → Link → User

**POS Profile** (should exist):
- `custom_commission_enabled` → Check
- `custom_sales_person_grand_total_limit` → Currency

### 3️⃣ Set Permissions (ONE TIME ONLY)

**Role Permission Manager** → Sales Invoice → POS Cashier:
- ☑ Read, Write, Create, Submit, Cancel, Print, Email, Share

### 4️⃣ Configure POS Profile

- ☑ Commission Enabled
- Sales Person Grand Total Limit: 1000.00

### 5️⃣ Setup Sales Persons

For each Sales Associate:
- Create Sales Person record
- Set `custom_user` = Sales Associate email
- Set `commission_rate` = 0.5 (or appropriate %)

---

## 🧪 QUICK TEST

1. Sales Associate creates token (> $1,000)
2. Cashier scans QR & pays
3. **Verify**:
   - ✓ Token status = "Paid"
   - ✓ Sales Invoice → Sales Team has commission
   - ✓ Commission rate matches Sales Person master

---

## 🆘 COMMON ISSUES

| Issue | Solution |
|-------|----------|
| Permission Denied | Add POS Cashier permissions to Sales Invoice |
| No commission | Check POS Profile settings & Sales Person setup |
| Token stays Pending | Clear cache, check custom fields exist |

---

**Full Documentation**: `/app/FRAPPE_CLOUD_DEPLOYMENT_CHECKLIST.md`
