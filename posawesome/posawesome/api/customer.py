# Copyright (c) 2021, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from posawesome.posawesome.doctype.referral_code.referral_code import (
    create_referral_code,
)


def get_sales_person_for_user(user=None):
    """
    Get the Sales Person linked to a User via Employee
    Returns sales_person name or None
    """
    if not user:
        user = frappe.session.user
    
    # Find Employee linked to this User
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return None
    
    # Find Sales Person linked to this Employee
    sales_person = frappe.db.get_value(
        "Sales Person", 
        {"employee": employee, "enabled": 1}, 
        "name"
    )
    
    return sales_person


def after_insert(doc, method):
    create_customer_referral_code(doc)
    create_gift_coupon(doc)
    set_default_sales_person(doc)


def validate(doc, method):
    validate_referral_code(doc)


def set_default_sales_person(doc):
    """
    Set the default sales person for newly created customers.
    The creator (if linked to a Sales Person) becomes the default for commission purposes.
    """
    # Only set if not already set
    if doc.get("custom_default_sales_person"):
        return
    
    # Get the sales person linked to the current user (creator)
    sales_person = get_sales_person_for_user()
    
    if sales_person:
        frappe.db.set_value(
            "Customer", 
            doc.name, 
            "custom_default_sales_person", 
            sales_person,
            update_modified=False
        )


def create_customer_referral_code(doc):
    if doc.posa_referral_company:
        company = frappe.get_cached_doc("Company", doc.posa_referral_company)
        if not company.posa_auto_referral:
            return
        create_referral_code(
            doc.posa_referral_company,
            doc.name,
            company.posa_customer_offer,
            company.posa_primary_offer,
            company.posa_referral_campaign,
        )


def create_gift_coupon(doc):
    if doc.posa_referral_code:
        coupon = frappe.new_doc("POS Coupon")
        coupon.customer = doc.name
        coupon.referral_code = doc.posa_referral_code
        coupon.create_coupon_from_referral()


def validate_referral_code(doc):
    referral_code = doc.posa_referral_code
    exist = None
    if referral_code:
        exist = frappe.db.exists("Referral Code", referral_code)
        if not exist:
            exist = frappe.db.exists("Referral Code", {"referral_code": referral_code})
        if not exist:
            frappe.throw(_("This Referral Code {0} not exists").format(referral_code))
