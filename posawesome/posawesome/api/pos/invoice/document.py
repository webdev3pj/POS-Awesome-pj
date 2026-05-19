# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json



import frappe

from frappe import _

from frappe.utils import cstr, flt, getdate



from posawesome.posawesome.api.pos.invoice.taxes import add_taxes_from_tax_template

from posawesome.posawesome.api.pos.relay.state import _upsert_relay_workflow_state



SYSTEM_FIELDS_FROM_CLIENT = {
    "creation",
    "modified",
    "modified_by",
    "owner",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
    "__last_sync_on",
    "__unsaved",
}


def apply_pos_profile_naming_series(invoice_doc):
    pos_profile = invoice_doc.get("pos_profile") if hasattr(invoice_doc, "get") else ""
    if not isinstance(pos_profile, str):
        pos_profile = ""
    pos_profile = cstr(pos_profile).strip()

    has_field = getattr(getattr(invoice_doc, "meta", None), "has_field", None)
    if not pos_profile or not callable(has_field) or not has_field("naming_series"):
        return

    naming_series = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "naming_series") or ""
    ).strip()
    if naming_series:
        invoice_doc.naming_series = naming_series


def strip_client_system_fields(value):
    if isinstance(value, dict):
        for fieldname in SYSTEM_FIELDS_FROM_CLIENT:
            value.pop(fieldname, None)
        for child in value.values():
            strip_client_system_fields(child)
    elif isinstance(value, list):
        for child in value:
            strip_client_system_fields(child)
    return value



def update_invoice(data):
    data = json.loads(data)
    strip_client_system_fields(data)

    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.flags.ignore_permissions = True
        invoice_doc.update(data)
    else:
        invoice_doc = frappe.get_doc(data)

    apply_pos_profile_naming_series(invoice_doc)
    invoice_doc.set_missing_values()
    apply_pos_profile_naming_series(invoice_doc)
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True

    # Handle returns
    if invoice_doc.is_return and invoice_doc.return_against:
        ref_doc = frappe.get_doc("Sales Invoice", invoice_doc.return_against)
        ref_doc.flags.ignore_permissions = True

        if not ref_doc.update_stock:
            invoice_doc.update_stock = 0

        if len(invoice_doc.payments) == 0:
            invoice_doc.payments = ref_doc.payments

        for return_item in invoice_doc.items:
            match_found = False
            for original_item in ref_doc.items:
                if return_item.item_code == original_item.item_code:
                    return_item.sales_invoice = ref_doc.name
                    return_item.sales_invoice_item = original_item.name
                    return_item.rate = original_item.rate
                    return_item.uom = original_item.uom
                    return_item.income_account = original_item.income_account
                    return_item.cost_center = original_item.cost_center
                    return_item.warehouse = original_item.warehouse
                    match_found = True
                    break
            if not match_found:
                frappe.throw(
                    _("Row # {0}: Returned Item {1} does not exist in Sales Invoice {2}").format(
                        return_item.idx, return_item.item_code, ref_doc.name
                    )
                )

    # Validate zero-rated items
    allow_zero_rated_items = frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_allow_zero_rated_items"
    )

    for item in invoice_doc.items:
        if not item.rate or item.rate == 0:
            if allow_zero_rated_items:
                item.price_list_rate = 0.00
                item.is_free_item = 1
            else:
                frappe.throw(
                    _("Rate cannot be zero for item {0}").format(item.item_code)
                )
        else:
            item.is_free_item = 0

        add_taxes_from_tax_template(item, invoice_doc)

    # Tax inclusion flag
    if frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_tax_inclusive"
    ):
        if invoice_doc.get("taxes"):
            for tax in invoice_doc.taxes:
                tax.included_in_print_rate = 1

    # Set posting time if backdated
    today_date = getdate()
    if (
        invoice_doc.get("posting_date")
        and getdate(invoice_doc.posting_date) != today_date
    ):
        invoice_doc.set_posting_time = 1

    # Enforce payment reset
    if invoice_doc.is_return:
        invoice_doc.paid_amount = 0.0
        invoice_doc.write_off_amount = 0.0
        for payment in invoice_doc.payments:
            payment.amount = 0.0

        # ✅ Show message (not throw) if no payment selected
        has_payment = any(flt(p.amount) > 0 for p in invoice_doc.payments)
        if not has_payment:
            frappe.msgprint(_("Please select a Mode of Payment before submitting the document."))

    invoice_doc.save()

    _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Draft" if invoice_doc.docstatus == 0 else None,
    )

    return invoice_doc
