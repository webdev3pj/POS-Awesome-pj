# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Awesome and contributors
# For license information, please see license.txt

"""
Sales Person Commission Helper Functions

This module provides helper functions for sales person commission calculation
in the token-based POS workflow.
"""

from __future__ import unicode_literals
import frappe
from frappe import _


@frappe.whitelist()
def get_sales_person_for_user(user=None):
    """
    Get the Sales Person linked to a User via Employee
    
    The link chain is: User -> Employee -> Sales Person
    
    Args:
        user: User ID (defaults to current user)
    
    Returns:
        dict: Sales Person info or None
    """
    if not user:
        user = frappe.session.user
    
    # First, find the Employee linked to this User
    employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)
    
    if not employee:
        return None
    
    # Now find the Sales Person linked to this Employee
    sales_person = frappe.db.get_value(
        "Sales Person", 
        {"employee": employee.name, "enabled": 1}, 
        ["name", "sales_person_name", "commission_rate"],
        as_dict=True
    )
    
    if sales_person:
        return {
            "sales_person": sales_person.name,
            "sales_person_name": sales_person.sales_person_name,
            "commission_rate": sales_person.commission_rate or 0.5,
            "employee": employee.name,
            "employee_name": employee.employee_name
        }
    
    return None


@frappe.whitelist()
def get_customer_sales_info(customer):
    """
    Get the customer's default sales person and check for ownership conflicts
    
    Args:
        customer: Customer ID
    
    Returns:
        dict: Customer sales info including default sales person and warnings
    """
    if not customer:
        return {"error": "Customer ID required"}
    
    customer_doc = frappe.get_doc("Customer", customer)
    default_sales_person = customer_doc.get("custom_default_sales_person")
    
    # Get current user's sales person
    current_user_sales_person = get_sales_person_for_user()
    
    result = {
        "customer": customer,
        "customer_name": customer_doc.customer_name,
        "default_sales_person": default_sales_person,
        "default_sales_person_name": None,
        "current_user_sales_person": current_user_sales_person.get("sales_person") if current_user_sales_person else None,
        "current_user_sales_person_name": current_user_sales_person.get("sales_person_name") if current_user_sales_person else None,
        "ownership_warning": None,
        "is_own_customer": True
    }
    
    # Get the default sales person's name
    if default_sales_person:
        result["default_sales_person_name"] = frappe.db.get_value(
            "Sales Person", default_sales_person, "sales_person_name"
        )
        
        # Check for ownership conflict
        if current_user_sales_person:
            if default_sales_person != current_user_sales_person.get("sales_person"):
                result["ownership_warning"] = _(
                    "This customer belongs to {0}. Commission will be credited to you for this transaction."
                ).format(result["default_sales_person_name"])
                result["is_own_customer"] = False
    
    return result


@frappe.whitelist()
def set_customer_default_sales_person(customer, sales_person=None):
    """
    Set the default sales person for a customer
    
    Args:
        customer: Customer ID
        sales_person: Sales Person ID (if None, uses current user's sales person)
    
    Returns:
        dict: Updated customer info
    """
    if not customer:
        frappe.throw(_("Customer ID required"))
    
    # If no sales person provided, get current user's sales person
    if not sales_person:
        user_sales_person = get_sales_person_for_user()
        if user_sales_person:
            sales_person = user_sales_person.get("sales_person")
    
    if not sales_person:
        return {"success": False, "message": _("No Sales Person found for current user")}
    
    # Update customer
    frappe.db.set_value("Customer", customer, "custom_default_sales_person", sales_person)
    frappe.db.commit()
    
    return {
        "success": True,
        "customer": customer,
        "default_sales_person": sales_person,
        "message": _("Default Sales Person set successfully")
    }


@frappe.whitelist()
def get_commission_eligibility(pos_profile, grand_total):
    """
    Check if a transaction is eligible for commission based on the grand total threshold
    
    Args:
        pos_profile: POS Profile name
        grand_total: Transaction grand total
    
    Returns:
        dict: Commission eligibility info
    """
    from frappe.utils import flt
    
    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    
    commission_enabled = pos_profile_doc.get("custom_commission_enabled", 0)
    sales_person_limit = flt(pos_profile_doc.get("custom_sales_person_grand_total_limit", 0))
    sales_partner_limit = flt(pos_profile_doc.get("custom_sales_partner_grand_total_limit", 0))
    grand_total = flt(grand_total)
    
    return {
        "commission_enabled": commission_enabled,
        "sales_person_eligible": commission_enabled and grand_total >= sales_person_limit,
        "sales_partner_eligible": commission_enabled and grand_total >= sales_partner_limit,
        "sales_person_limit": sales_person_limit,
        "sales_partner_limit": sales_partner_limit,
        "grand_total": grand_total
    }
