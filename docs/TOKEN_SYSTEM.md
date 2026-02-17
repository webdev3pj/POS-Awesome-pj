# POS Token Workflow System

## Overview

This document describes the token-based workflow system for POS Awesome, designed for hardware stores with multiple order counters and a central cashier station.

## Key Features

1. **Sales Associate Workflow**
   - Takes orders and creates customers
   - Generates tokens (QR codes) for orders
   - Cannot process payments or create final invoices
   - Can hold/save draft orders

2. **Cashier Workflow**
   - Scans QR codes to retrieve orders
   - Can modify items before payment
   - Processes payments and creates final invoices
   - Has a sidebar to view all pending tokens

## Commission System

### Customer Ownership

When a Sales Associate creates a new customer, they automatically become the "default sales person" for that customer:
- The `custom_default_sales_person` field on the Customer stores this link
- This is used for commission attribution

### Commission Flow

1. **Token Creation**: The Sales Associate's linked Sales Person is automatically captured in the token
2. **Customer Ownership Check**: When a customer is selected, the system checks if they belong to another Sales Associate
3. **Warning Display**: If serving another associate's customer, a warning message is shown
4. **Transaction Attribution**: The Sales Associate who processes the transaction (creates the token) receives the commission

### Commission Calculation

Commission is calculated based on:
- `custom_commission_enabled` flag in POS Profile
- `custom_sales_person_grand_total_limit` - minimum transaction amount for commission
- The Sales Person linked to the User via Employee → Sales Person chain

### User → Sales Person Link

The system links Users to Sales Persons through this chain:
```
User (user_id) → Employee (employee) → Sales Person
```

## Technical Implementation

### New API Endpoints

- `posawesome.posawesome.api.posapp.get_customer_sales_info` - Get customer ownership info
- `posawesome.posawesome.api.sales_commission.get_sales_person_for_user` - Get Sales Person for a user
- `posawesome.posawesome.api.sales_commission.get_customer_sales_info` - Full customer sales info with warning
- `posawesome.posawesome.api.sales_commission.set_customer_default_sales_person` - Set customer's default sales person

### Custom Fields

- `Customer.custom_default_sales_person` - Link to default Sales Person

### Modified Files

- `Invoice.vue` - Customer ownership warning display
- `Payments.vue` - Pre-populate sales person from token
- `token.py` - Auto-capture sales person when creating token
- `customer.py` - Auto-set default sales person on customer creation
- `posapp.py` - Helper functions for sales person lookup

## Configuration

### Enable Token Workflow

1. Go to POS Profile
2. Enable "Token Workflow" checkbox (`posa_enable_token_workflow`)
3. Enable "Commission Enabled" checkbox (`custom_commission_enabled`)
4. Set minimum grand total for commission (`custom_sales_person_grand_total_limit`)

### Setup User → Sales Person Link

1. Create an Employee record with `user_id` set to the User
2. Create a Sales Person record with `employee` linked to the Employee
3. Set `enabled = 1` on the Sales Person

## Roles

- **POS Sales Associate**: Can create tokens, view pending tokens, cannot process payments
- **POS Cashier**: Can scan tokens, modify orders, process payments, view pending tokens sidebar

## Data Flow

```
Sales Associate creates token
       ↓
Token stores: customer, items, sales_associate, sales_person
       ↓
Cashier scans QR code
       ↓
System loads token data, pre-populates sales_person
       ↓
Cashier processes payment
       ↓
Sales Invoice created with sales_team from token
       ↓
Commission calculated based on sales_team
```
