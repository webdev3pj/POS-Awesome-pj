# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json

import frappe

from frappe import _



def _as_dict(value):
    if isinstance(value, str):
        return frappe._dict(json.loads(value or "{}"))
    return frappe._dict(value or {})


def _first_existing(doctype, candidates):
    for candidate in candidates:
        candidate = (candidate or "").strip()
        if candidate and frappe.db.exists(doctype, candidate):
            return candidate
    return ""


def create_customer(
    customer_id,
    customer_name,
    company,
    pos_profile_doc,
    tax_id=None,
    mobile_no=None,
    email_id=None,
    referral_code=None,
    birthday=None,
    customer_group=None,
    territory=None,
    customer_type=None,
    gender=None,
    method="create",
):
    pos_profile = _as_dict(pos_profile_doc)
    customer_name = (customer_name or customer_id or "").strip()
    customer_group = _first_existing(
        "Customer Group",
        [
            customer_group,
            pos_profile.get("customer_group"),
            frappe.db.get_single_value("Selling Settings", "customer_group"),
            "All Customer Groups",
        ],
    )
    territory = _first_existing(
        "Territory",
        [
            territory,
            pos_profile.get("territory"),
            frappe.defaults.get_user_default("Territory"),
            frappe.db.get_single_value("Selling Settings", "territory"),
            "All Territories",
        ],
    )

    if not customer_name:
        frappe.throw(_("Customer name is required."))
    if not customer_group:
        frappe.throw(_("Customer Group is required to create Customer."))
    if not territory:
        frappe.throw(_("Territory is required to create Customer."))

    if method == "create":
        is_exist = frappe.db.exists("Customer", {"customer_name": customer_name})
        if pos_profile.get("posa_allow_duplicate_customer_names") or not is_exist:
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "posa_referral_company": company,
                    "tax_id": tax_id,
                    "mobile_no": mobile_no,
                    "email_id": email_id,
                    "posa_referral_code": referral_code,
                    "posa_birthday": birthday,
                    "customer_type": customer_type,
                    "gender": gender,
                    "customer_group": customer_group,
                    "territory": territory,
                }
            )
            customer.flags.ignore_permissions = True
            customer.save()
            return customer
        else:
            frappe.throw(_("Customer already exists"))

    elif method == "update":
        customer_doc = frappe.get_doc("Customer", customer_id)
        customer_doc.flags.ignore_permissions = True
        customer_doc.customer_name = customer_name
        customer_doc.posa_referral_company = company
        customer_doc.tax_id = tax_id
        customer_doc.posa_referral_code = referral_code
        customer_doc.posa_birthday = birthday
        customer_doc.customer_type = customer_type
        customer_doc.territory = territory
        customer_doc.customer_group = customer_group
        customer_doc.gender = gender
        customer_doc.save()
        if mobile_no != customer_doc.mobile_no:
            set_customer_info(customer_doc.name, "mobile_no", mobile_no)
        if email_id != customer_doc.email_id:
            set_customer_info(customer_doc.name, "email_id", email_id)
        return customer_doc

def set_customer_info(customer, fieldname, value=""):
    if fieldname == "loyalty_program":
        frappe.db.set_value("Customer", customer, "loyalty_program", value)

    contact = (
        frappe.get_cached_value("Customer", customer, "customer_primary_contact") or ""
    )

    if contact:
        contact_doc = frappe.get_doc("Contact", contact)
        contact_doc.flags.ignore_permissions = True
        if fieldname == "email_id":
            contact_doc.set("email_ids", [{"email_id": value, "is_primary": 1}])
            frappe.db.set_value("Customer", customer, "email_id", value)
        elif fieldname == "mobile_no":
            contact_doc.set("phone_nos", [{"phone": value, "is_primary_mobile_no": 1}])
            frappe.db.set_value("Customer", customer, "mobile_no", value)
        contact_doc.save()

    else:
        contact_doc = frappe.new_doc("Contact")
        contact_doc.first_name = customer
        contact_doc.is_primary_contact = 1
        contact_doc.is_billing_contact = 1
        if fieldname == "mobile_no":
            contact_doc.add_phone(value, is_primary_mobile_no=1, is_primary_phone=1)

        if fieldname == "email_id":
            contact_doc.add_email(value, is_primary=1)

        contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})

        contact_doc.flags.ignore_mandatory = True
        contact_doc.flags.ignore_permissions = True
        contact_doc.save()
        frappe.set_value(
            "Customer", customer, "customer_primary_contact", contact_doc.name
        )
