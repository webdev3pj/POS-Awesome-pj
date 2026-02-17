# -*- coding: utf-8 -*-
# Copyright (c) 2026, PJ Jamaica and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_url
import qrcode
import base64
from io import BytesIO


@frappe.whitelist()
def create_sales_order_token(customer, items, pos_profile):
    """
    Create a Sales Order for token workflow (Sales Associate).
    
    This replaces the POS Token doctype with standard Sales Order.
    Commission is calculated here and will automatically copy to Sales Invoice.
    
    Args:
        customer: Customer name
        items: JSON string of items [{"item_code": "...", "qty": 1, "rate": 100, ...}]
        pos_profile: POS Profile name
    
    Returns:
        {
            "order_name": "SO-PJK-2026-00001",
            "grand_total": 2700.00,
            "qr_code": "data:image/png;base64,...",
            "commission_applied": True/False,
            "commission_amount": 13.50
        }
    """
    import json
    
    # Parse items
    if isinstance(items, str):
        items = json.loads(items)
    
    # Get POS Profile
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    
    # Create Sales Order
    sales_order = frappe.get_doc({
        "doctype": "Sales Order",
        "customer": customer,
        "transaction_date": nowdate(),
        "delivery_date": nowdate(),
        "company": pos_profile_doc.company,
        "currency": pos_profile_doc.currency,
        "selling_price_list": pos_profile_doc.selling_price_list,
        "custom_sales_associate": frappe.session.user,
        "custom_order_type": "POS Token Order",
        "custom_pos_opening_shift": None,  # Sales Associate doesn't need shift
    })
    
    # Add items
    for item in items:
        sales_order.append("items", {
            "item_code": item.get("item_code"),
            "item_name": item.get("item_name"),
            "description": item.get("description"),
            "qty": flt(item.get("qty", 1)),
            "rate": flt(item.get("rate", 0)),
            "warehouse": item.get("warehouse") or pos_profile_doc.warehouse,
            "uom": item.get("uom"),
            "conversion_factor": flt(item.get("conversion_factor", 1)),
            "delivery_date": nowdate(),
        })
    
    # Calculate taxes and totals
    sales_order.flags.ignore_permissions = True
    sales_order.run_method("set_missing_values")
    sales_order.run_method("calculate_taxes_and_totals")
    
    # Apply commission if eligible
    commission_info = apply_commission_to_sales_order(sales_order, pos_profile_doc)
    
    # Save and submit
    sales_order.save(ignore_permissions=True)
    sales_order.submit()
    
    # Generate QR code
    qr_code_data = generate_qr_code_for_order(sales_order.name)
    
    # Return order details
    return {
        "order_name": sales_order.name,
        "grand_total": sales_order.grand_total,
        "qr_code": qr_code_data,
        "commission_applied": commission_info.get("applied", False),
        "commission_amount": commission_info.get("amount", 0),
        "commission_rate": commission_info.get("rate", 0),
        "sales_associate": sales_order.custom_sales_associate
    }


def apply_commission_to_sales_order(sales_order, pos_profile_doc):
    """
    Apply Sales Associate commission to Sales Order.
    
    Commission eligibility:
    1. custom_commission_enabled = 1 in POS Profile
    2. grand_total >= custom_sales_person_grand_total_limit
    3. Sales Person linked to Sales Associate via custom_user
    
    The sales_team table will automatically copy to Sales Invoice via make_sales_invoice().
    
    Args:
        sales_order: Sales Order document
        pos_profile_doc: POS Profile document
    
    Returns:
        {
            "applied": True/False,
            "amount": 13.50,
            "rate": 0.5,
            "sales_person": "SP-001"
        }
    """
    try:
        commission_enabled = pos_profile_doc.get("custom_commission_enabled", 0)
        sales_person_limit = flt(pos_profile_doc.get("custom_sales_person_grand_total_limit", 0))
        grand_total = flt(sales_order.grand_total)
        sales_associate = sales_order.custom_sales_associate
        
        # Check eligibility
        if not commission_enabled:
            frappe.log_error(
                title="Commission Not Enabled",
                message=f"Commission not enabled in POS Profile {pos_profile_doc.name}"
            )
            return {"applied": False, "amount": 0, "rate": 0}
        
        if grand_total < sales_person_limit:
            frappe.log_error(
                title="Below Commission Threshold",
                message=f"Order {sales_order.name}: Grand total {grand_total} < limit {sales_person_limit}"
            )
            return {"applied": False, "amount": 0, "rate": 0}
        
        # Get Sales Person linked to this Sales Associate
        sales_person = frappe.db.get_value(
            "Sales Person",
            {"custom_user": sales_associate, "enabled": 1},
            ["name", "commission_rate"],
            as_dict=True
        )
        
        if not sales_person:
            frappe.log_error(
                title="No Sales Person Found",
                message=f"No Sales Person linked to user {sales_associate}"
            )
            return {"applied": False, "amount": 0, "rate": 0}
        
        commission_rate = flt(sales_person.commission_rate) or 0.5
        
        # Clear existing sales_team entries
        sales_order.sales_team = []
        
        # Add sales team entry
        sales_order.append("sales_team", {
            "sales_person": sales_person.name,
            "allocated_percentage": 100,
            "commission_rate": commission_rate
        })
        
        # Calculate commission amount
        commission_amount = (grand_total * commission_rate) / 100
        
        return {
            "applied": True,
            "amount": commission_amount,
            "rate": commission_rate,
            "sales_person": sales_person.name
        }
        
    except Exception as e:
        frappe.log_error(
            title="Commission Calculation Error",
            message=f"Failed to apply commission to {sales_order.name}: {str(e)}"
        )
        return {"applied": False, "amount": 0, "rate": 0}


def generate_qr_code_for_order(order_name):
    """
    Generate QR code for Sales Order.
    
    Args:
        order_name: Sales Order name (e.g., "SO-PJK-2026-00001")
    
    Returns:
        Base64 encoded QR code image data URI
    """
    try:
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(order_name)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
        
    except Exception as e:
        frappe.log_error(
            title="QR Code Generation Error",
            message=f"Failed to generate QR for {order_name}: {str(e)}"
        )
        return None


@frappe.whitelist()
def get_pending_orders(sales_associate=None, pos_profile=None):
    """
    Get pending Sales Orders (not yet billed).
    
    For Sales Associate: Shows their own orders
    For Cashier: Shows all pending orders for the shift
    
    Args:
        sales_associate: Filter by Sales Associate user (optional)
        pos_profile: Filter by POS Profile (optional)
    
    Returns:
        List of pending orders with details
    """
    filters = {
        "docstatus": 1,
        "status": ["in", ["To Deliver and Bill", "To Bill"]],
        "per_billed": ["<", 100],
        "custom_order_type": "POS Token Order"
    }
    
    if sales_associate:
        filters["custom_sales_associate"] = sales_associate
    
    orders = frappe.get_list(
        "Sales Order",
        filters=filters,
        fields=[
            "name",
            "customer",
            "customer_name",
            "transaction_date",
            "grand_total",
            "currency",
            "custom_sales_associate",
            "status",
            "per_billed",
            "creation"
        ],
        order_by="creation desc",
        limit=100
    )
    
    return orders


@frappe.whitelist()
def get_sales_order_for_cashier(order_name):
    """
    Retrieve Sales Order for cashier to process.
    
    Validates:
    - Order exists
    - Not fully billed
    - Is a POS Token Order
    
    Args:
        order_name: Sales Order name from QR scan
    
    Returns:
        Full Sales Order document
    """
    try:
        # Get order
        order = frappe.get_doc("Sales Order", order_name)
        
        # Validate
        if order.docstatus != 1:
            frappe.throw(_("Order {0} is not submitted").format(order_name))
        
        if order.per_billed >= 100:
            frappe.throw(_("Order {0} is already fully billed").format(order_name))
        
        if order.custom_order_type != "POS Token Order":
            frappe.throw(_("Order {0} is not a POS Token Order").format(order_name))
        
        return order
        
    except Exception as e:
        frappe.throw(_("Failed to retrieve order {0}: {1}").format(order_name, str(e)))


@frappe.whitelist()
def cancel_sales_order_token(order_name, reason=None):
    """
    Cancel a Sales Order (Sales Associate or Manager).
    
    Args:
        order_name: Sales Order name
        reason: Cancellation reason (optional)
    
    Returns:
        Success message
    """
    try:
        order = frappe.get_doc("Sales Order", order_name)
        
        # Check if already billed
        if order.per_billed > 0:
            frappe.throw(_("Cannot cancel order {0}. It has been partially/fully billed.").format(order_name))
        
        # Add cancellation reason if provided
        if reason:
            order.add_comment("Comment", f"Cancellation reason: {reason}")
        
        # Cancel
        order.flags.ignore_permissions = True
        order.cancel()
        
        return {
            "success": True,
            "message": f"Order {order_name} cancelled successfully"
        }
        
    except Exception as e:
        frappe.throw(_("Failed to cancel order {0}: {1}").format(order_name, str(e)))
