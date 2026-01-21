# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Awesome and contributors
# For license information, please see license.txt

"""
Token-Based POS System API

This module provides API endpoints for the token-based order processing system
designed for hardware stores with separate order counters and cashier stations.

Key Features:
- Stores Sales Associate (user who created the token)
- Stores Sales Person (for commission calculation)
- Stores Sales Partner (for partner commission)
- QR code generation for easy token lookup
"""

from __future__ import unicode_literals
import json
import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, flt
import qrcode
import io
import base64


@frappe.whitelist()
def create_token(pos_profile, customer, items, pos_opening_shift=None, sales_person=None, sales_partner=None):
    """
    Create a new POS Token from cart items
    
    Args:
        pos_profile: POS Profile name
        customer: Customer ID
        items: JSON string of cart items
        pos_opening_shift: Optional POS Opening Shift reference
        sales_person: Optional Sales Person for commission
        sales_partner: Optional Sales Partner for commission
    
    Returns:
        dict: Token document with QR code data
    """
    items = json.loads(items) if isinstance(items, str) else items
    
    if not items or len(items) == 0:
        frappe.throw(_("Cannot create token without items"))
    
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    customer_doc = frappe.get_doc("Customer", customer)
    
    # Get sales associate name
    sales_associate = frappe.session.user
    sales_associate_name = frappe.db.get_value("User", sales_associate, "full_name") or sales_associate
    
    # Create token document
    token_doc = frappe.get_doc({
        "doctype": "POS Token",
        "customer": customer,
        "customer_name": customer_doc.customer_name,
        "company": pos_profile_doc.company,
        "pos_profile": pos_profile,
        "pos_opening_shift": pos_opening_shift,
        "sales_associate": sales_associate,
        "sales_associate_name": sales_associate_name,
        "sales_person": sales_person,
        "sales_partner": sales_partner,
        "status": "Pending"
    })
    
    # Add items to token
    for item in items:
        token_doc.append("items", {
            "item_code": item.get("item_code"),
            "item_name": item.get("item_name"),
            "qty": flt(item.get("qty", 1)),
            "rate": flt(item.get("rate", 0)),
            "amount": flt(item.get("qty", 1)) * flt(item.get("rate", 0)),
            "uom": item.get("uom") or item.get("stock_uom"),
            "batch_no": item.get("batch_no"),
            "serial_no": item.get("serial_no"),
            "warehouse": item.get("warehouse") or pos_profile_doc.warehouse
        })
    
    token_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Generate QR code data
    qr_data = generate_token_qr_data(token_doc.name, token_doc.token_number)
    
    return {
        "name": token_doc.name,
        "token_number": token_doc.token_number,
        "customer": token_doc.customer,
        "customer_name": token_doc.customer_name,
        "total_amount": token_doc.total_amount,
        "total_qty": token_doc.total_qty,
        "token_datetime": str(token_doc.token_datetime),
        "sales_associate": token_doc.sales_associate,
        "sales_associate_name": token_doc.sales_associate_name,
        "sales_person": token_doc.sales_person,
        "sales_person_name": token_doc.sales_person_name,
        "sales_partner": token_doc.sales_partner,
        "qr_code": qr_data,
        "items": [
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.uom
            }
            for item in token_doc.items
        ]
    }


def generate_token_qr_data(token_name, token_number):
    """
    Generate QR code as base64 string for token
    
    Args:
        token_name: Document name of the token
        token_number: Human-readable token number
    
    Returns:
        str: Base64 encoded QR code image
    """
    # QR code contains the token name for easy lookup
    qr_content = json.dumps({
        "type": "pos_token",
        "name": token_name,
        "token": token_number
    })
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@frappe.whitelist()
def get_token(token_identifier):
    """
    Get token details by name or token number (for QR scan)
    
    Args:
        token_identifier: Token document name or token_number or QR JSON data
    
    Returns:
        dict: Complete token information including sales team data
    """
    token_name = None
    
    # Try to parse as QR JSON data
    try:
        qr_data = json.loads(token_identifier)
        if isinstance(qr_data, dict) and qr_data.get("type") == "pos_token":
            token_name = qr_data.get("name")
    except (json.JSONDecodeError, TypeError):
        pass
    
    # If not QR data, try direct lookup
    if not token_name:
        # Check if it's a token name
        if frappe.db.exists("POS Token", token_identifier):
            token_name = token_identifier
        else:
            # Try to find by token_number
            token_name = frappe.db.get_value(
                "POS Token", 
                {"token_number": token_identifier}, 
                "name"
            )
    
    if not token_name:
        frappe.throw(_("Token not found: {0}").format(token_identifier))
    
    token_doc = frappe.get_doc("POS Token", token_name)
    
    # Generate fresh QR code
    qr_data = generate_token_qr_data(token_doc.name, token_doc.token_number)
    
    return {
        "name": token_doc.name,
        "token_number": token_doc.token_number,
        "status": token_doc.status,
        "customer": token_doc.customer,
        "customer_name": token_doc.customer_name,
        "company": token_doc.company,
        "pos_profile": token_doc.pos_profile,
        "pos_opening_shift": token_doc.pos_opening_shift,
        "sales_associate": token_doc.sales_associate,
        "sales_associate_name": token_doc.sales_associate_name,
        "sales_person": token_doc.sales_person,
        "sales_person_name": token_doc.sales_person_name,
        "sales_partner": token_doc.sales_partner,
        "cashier": token_doc.cashier,
        "total_qty": token_doc.total_qty,
        "total_amount": token_doc.total_amount,
        "token_datetime": str(token_doc.token_datetime),
        "paid_datetime": str(token_doc.paid_datetime) if token_doc.paid_datetime else None,
        "linked_invoice": token_doc.linked_invoice,
        "qr_code": qr_data,
        "items": [
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.uom,
                "batch_no": item.batch_no,
                "serial_no": item.serial_no,
                "warehouse": item.warehouse
            }
            for item in token_doc.items
        ]
    }


@frappe.whitelist()
def get_pending_tokens(pos_profile=None, pos_opening_shift=None):
    """
    Get list of all pending tokens
    
    Args:
        pos_profile: Optional filter by POS Profile
        pos_opening_shift: Optional filter by POS Opening Shift
    
    Returns:
        list: List of pending token summaries including sales associate info
    """
    filters = {"status": "Pending"}
    
    if pos_profile:
        filters["pos_profile"] = pos_profile
    
    if pos_opening_shift:
        filters["pos_opening_shift"] = pos_opening_shift
    
    tokens = frappe.get_all(
        "POS Token",
        filters=filters,
        fields=[
            "name", "token_number", "customer", "customer_name",
            "total_qty", "total_amount", "token_datetime",
            "sales_associate", "sales_associate_name", 
            "sales_person", "sales_person_name",
            "sales_partner", "pos_profile"
        ],
        order_by="token_datetime desc"
    )
    
    return tokens


@frappe.whitelist()
def process_token_payment(token_name, payments, pos_opening_shift=None):
    """
    Process payment for a token and create Sales Invoice
    
    This method:
    1. Creates Sales Invoice from token items
    2. Applies sales_person from token to invoice (for commission)
    3. Applies sales_partner from token (if set)
    4. Marks token as paid
    
    Args:
        token_name: Token document name
        payments: JSON string of payment methods and amounts
        pos_opening_shift: POS Opening Shift for the cashier
    
    Returns:
        dict: Created invoice details
    """
    payments = json.loads(payments) if isinstance(payments, str) else payments
    
    token_doc = frappe.get_doc("POS Token", token_name)
    
    if token_doc.status != "Pending":
        frappe.throw(_("Token {0} is already {1}").format(
            token_doc.token_number, token_doc.status
        ))
    
    pos_profile_doc = frappe.get_doc("POS Profile", token_doc.pos_profile)
    
    # Create Sales Invoice
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": token_doc.customer,
        "company": token_doc.company,
        "pos_profile": token_doc.pos_profile,
        "is_pos": 1,
        "update_stock": 1,
        "posa_pos_opening_shift": pos_opening_shift or token_doc.pos_opening_shift,
        "posting_date": nowdate(),
        "due_date": nowdate(),
        "set_warehouse": pos_profile_doc.warehouse,
        "selling_price_list": pos_profile_doc.selling_price_list,
        "currency": pos_profile_doc.currency
    })
    
    # Add items from token
    for item in token_doc.items:
        invoice.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "rate": item.rate,
            "uom": item.uom,
            "batch_no": item.batch_no,
            "serial_no": item.serial_no,
            "warehouse": item.warehouse or pos_profile_doc.warehouse
        })
    
    # Add sales team from token (for commission calculation)
    if token_doc.sales_person:
        invoice.append("sales_team", {
            "sales_person": token_doc.sales_person,
            "allocated_percentage": 100
        })
    
    # Add sales partner from token (if set)
    if token_doc.sales_partner:
        invoice.sales_partner = token_doc.sales_partner
        # Get commission rate from Sales Partner
        partner_commission = frappe.db.get_value(
            "Sales Partner", token_doc.sales_partner, "commission_rate"
        )
        if partner_commission:
            invoice.commission_rate = partner_commission
    
    # Add payments
    for payment in payments:
        invoice.append("payments", {
            "mode_of_payment": payment.get("mode_of_payment"),
            "amount": flt(payment.get("amount", 0))
        })
    
    invoice.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    
    invoice.set_missing_values()
    invoice.save()
    invoice.submit()
    
    # Update token status
    token_doc.mark_as_paid(invoice.name, frappe.session.user)
    
    frappe.db.commit()
    
    return {
        "invoice_name": invoice.name,
        "token_name": token_doc.name,
        "token_number": token_doc.token_number,
        "status": "Paid",
        "grand_total": invoice.grand_total,
        "paid_amount": invoice.paid_amount,
        "sales_person": token_doc.sales_person,
        "sales_partner": token_doc.sales_partner
    }


@frappe.whitelist()
def cancel_token(token_name, reason=None):
    """
    Cancel a pending token
    
    Args:
        token_name: Token document name
        reason: Optional cancellation reason
    
    Returns:
        dict: Updated token status
    """
    token_doc = frappe.get_doc("POS Token", token_name)
    
    if token_doc.status != "Pending":
        frappe.throw(_("Cannot cancel token with status: {0}").format(token_doc.status))
    
    token_doc.status = "Cancelled"
    token_doc.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    return {
        "name": token_doc.name,
        "token_number": token_doc.token_number,
        "status": token_doc.status
    }


@frappe.whitelist()
def get_token_receipt_data(token_name):
    """
    Get formatted data for printing token receipt
    
    Args:
        token_name: Token document name
    
    Returns:
        dict: Formatted receipt data with QR code and sales info
    """
    token_doc = frappe.get_doc("POS Token", token_name)
    company_doc = frappe.get_doc("Company", token_doc.company)
    
    qr_data = generate_token_qr_data(token_doc.name, token_doc.token_number)
    
    return {
        "token_number": token_doc.token_number,
        "customer_name": token_doc.customer_name,
        "token_datetime": token_doc.token_datetime,
        "total_qty": token_doc.total_qty,
        "total_amount": token_doc.total_amount,
        "company_name": company_doc.company_name,
        "company_address": company_doc.address or "",
        "sales_associate_name": token_doc.sales_associate_name,
        "sales_person_name": token_doc.sales_person_name,
        "qr_code": qr_data,
        "items": [
            {
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount
            }
            for item in token_doc.items
        ],
        "message": "Please proceed to cashier with this receipt"
    }


@frappe.whitelist()
def search_tokens(search_term, status=None, limit=20):
    """
    Search tokens by token number, customer name, sales associate, or customer ID
    
    Args:
        search_term: Search string
        status: Optional status filter
        limit: Maximum results to return
    
    Returns:
        list: Matching tokens
    """
    filters = []
    
    if status:
        filters.append(["status", "=", status])
    
    # Build OR conditions for search
    or_filters = [
        ["token_number", "like", f"%{search_term}%"],
        ["customer", "like", f"%{search_term}%"],
        ["customer_name", "like", f"%{search_term}%"],
        ["sales_associate_name", "like", f"%{search_term}%"]
    ]
    
    tokens = frappe.get_all(
        "POS Token",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", "token_number", "customer", "customer_name",
            "total_qty", "total_amount", "token_datetime",
            "status", "sales_associate", "sales_associate_name",
            "sales_person", "sales_person_name", "pos_profile"
        ],
        order_by="token_datetime desc",
        limit=limit
    )
    
    return tokens


@frappe.whitelist()
def get_token_stats(pos_profile=None, date=None):
    """
    Get token statistics for dashboard
    
    Args:
        pos_profile: Optional filter by POS Profile
        date: Optional date filter (defaults to today)
    
    Returns:
        dict: Token statistics
    """
    if not date:
        date = nowdate()
    
    filters = {
        "creation": [">=", date],
        "creation": ["<", frappe.utils.add_days(date, 1)]
    }
    
    if pos_profile:
        filters["pos_profile"] = pos_profile
    
    # Get counts by status
    pending_count = frappe.db.count("POS Token", {**filters, "status": "Pending"})
    paid_count = frappe.db.count("POS Token", {**filters, "status": "Paid"})
    cancelled_count = frappe.db.count("POS Token", {**filters, "status": "Cancelled"})
    
    # Get total amount for paid tokens
    paid_tokens = frappe.get_all(
        "POS Token",
        filters={**filters, "status": "Paid"},
        fields=["total_amount"]
    )
    total_paid_amount = sum(t.get("total_amount", 0) for t in paid_tokens)
    
    return {
        "date": date,
        "pending": pending_count,
        "paid": paid_count,
        "cancelled": cancelled_count,
        "total": pending_count + paid_count + cancelled_count,
        "total_paid_amount": total_paid_amount
    }
