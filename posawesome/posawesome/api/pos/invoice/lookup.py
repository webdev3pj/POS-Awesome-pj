# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import time



import frappe

from frappe import _



def get_draft_invoices(pos_opening_shift):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 0,
            "posa_is_printed": 0,
        },
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc("Sales Invoice", invoice["name"]))
    return data

def _delete_sales_invoice_with_retry(sales_invoice, force=0, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            frappe.delete_doc("Sales Invoice", sales_invoice, force=force)
            return
        except frappe.QueryDeadlockError as exc:
            last_error = exc
            frappe.db.rollback()
            if attempt >= attempts - 1:
                break
            time.sleep(0.2 * (attempt + 1))
    raise last_error

def delete_invoice(invoice):
    if frappe.get_value("Sales Invoice", invoice, "posa_is_printed"):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))
    _delete_sales_invoice_with_retry(invoice, force=1)
    return _("Invoice {0} Deleted").format(invoice)

def get_sales_invoice_child_table(sales_invoice, sales_invoice_item=None):
    parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)

    if sales_invoice_item:
        # fetch specific item row
        return frappe.get_doc(
            "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
        )
    else:
        # fetch all child rows for that invoice
        return frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": parent_doc.name},
            fields=["*"]
        )
