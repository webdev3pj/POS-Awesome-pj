# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
from frappe.utils import cstr
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice

from posawesome.posawesome.api.pos.invoice.document import (
    apply_pos_opening_shift,
    apply_pos_profile_naming_series,
    apply_pos_profile_tax_inclusive,
)


def make_or_get_sales_invoice_from_order(sales_order, pos_profile=None, pos_opening_shift=None):
    existing_invoice = _get_draft_invoice_for_sales_order(
        sales_order, pos_profile=pos_profile, pos_opening_shift=pos_opening_shift
    )
    if existing_invoice:
        invoice_doc = frappe.get_doc("Sales Invoice", existing_invoice)
        invoice_doc.flags.ignore_permissions = True
        return invoice_doc.as_dict()

    sales_invoice = make_sales_invoice(sales_order, ignore_permissions=True)
    if pos_profile:
        sales_invoice.pos_profile = pos_profile
    apply_pos_opening_shift(sales_invoice, pos_opening_shift)
    apply_pos_profile_naming_series(sales_invoice)
    apply_pos_profile_tax_inclusive(sales_invoice)
    return sales_invoice.as_dict()


def update_invoice_from_order_data(data):
    if isinstance(data, str):
        data = json.loads(data)
    data = data or {}

    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.flags.ignore_permissions = True
        invoice_doc.update(data)
    else:
        data.pop("name", None)
        invoice_doc = frappe.get_doc(data)

    apply_pos_opening_shift(invoice_doc)
    apply_pos_profile_naming_series(invoice_doc)
    apply_pos_profile_tax_inclusive(invoice_doc)
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.save()
    return invoice_doc


def _get_draft_invoice_for_sales_order(sales_order, pos_profile=None, pos_opening_shift=None):
    sales_order = cstr(sales_order or "").strip()
    if not sales_order:
        return ""

    conditions = [
        "si.docstatus = 0",
        "ifnull(si.is_pos, 0) = 1",
        "sii.sales_order = %s",
    ]
    values = [sales_order]

    pos_profile = cstr(pos_profile or "").strip()
    if pos_profile:
        conditions.append("si.pos_profile = %s")
        values.append(pos_profile)

    pos_opening_shift = cstr(pos_opening_shift or "").strip()
    if pos_opening_shift and frappe.db.has_column("Sales Invoice", "posa_pos_opening_shift"):
        conditions.append("si.posa_pos_opening_shift = %s")
        values.append(pos_opening_shift)

    rows = frappe.db.sql(
        """
        select distinct si.name
        from `tabSales Invoice` si
        inner join `tabSales Invoice Item` sii on sii.parent = si.name
        where {conditions}
        order by si.modified desc
        limit 1
        """.format(conditions=" and ".join(conditions)),
        values,
        as_dict=True,
    )
    return rows[0].name if rows else ""
