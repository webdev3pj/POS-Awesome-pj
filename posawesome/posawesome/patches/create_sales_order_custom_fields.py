# -*- coding: utf-8 -*-
# Copyright (c) 2026, PJ Jamaica and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute():
    """Create custom fields for Sales Order token workflow."""
    create_sales_order_custom_fields()


def create_sales_order_custom_fields():
    """Create custom fields on Sales Order for POS Token workflow."""
    
    custom_fields = [
        {
            "dt": "Sales Order",
            "fieldname": "custom_sales_associate",
            "label": "Sales Associate (User)",
            "fieldtype": "Link",
            "options": "User",
            "insert_after": "customer",
            "read_only": 1,
            "in_standard_filter": 1,
            "description": "The user who created this order (Sales Associate)"
        },
        {
            "dt": "Sales Order",
            "fieldname": "custom_order_type",
            "label": "Order Type",
            "fieldtype": "Select",
            "options": "POS Token Order\nRegular Order\nDelivery Order",
            "default": "Regular Order",
            "insert_after": "custom_sales_associate",
            "in_list_view": 1,
            "in_standard_filter": 1,
            "description": "Type of order for filtering"
        },
        {
            "dt": "Sales Order",
            "fieldname": "custom_pos_opening_shift",
            "label": "POS Opening Shift",
            "fieldtype": "Link",
            "options": "POS Opening Shift",
            "insert_after": "custom_order_type",
            "read_only": 1,
            "description": "Links to cashier's shift when order is paid"
        },
        {
            "dt": "Sales Order",
            "fieldname": "custom_token_qr_code",
            "label": "Token QR Code",
            "fieldtype": "Attach Image",
            "insert_after": "custom_pos_opening_shift",
            "read_only": 1,
            "hidden": 1
        }
    ]
    
    for field in custom_fields:
        field_name = f"{field['dt']}-{field['fieldname']}"
        
        # Check if field already exists
        if frappe.db.exists("Custom Field", field_name):
            print(f"Custom field {field_name} already exists, skipping...")
            continue
        
        # Create the custom field
        try:
            custom_field = frappe.get_doc({
                "doctype": "Custom Field",
                "name": field_name,
                **field
            })
            custom_field.insert(ignore_permissions=True)
            print(f"Created custom field: {field_name}")
        except Exception as e:
            print(f"Error creating {field_name}: {str(e)}")
    
    frappe.db.commit()
    print("Sales Order custom fields setup complete!")
