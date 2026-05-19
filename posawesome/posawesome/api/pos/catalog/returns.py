# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import copy



import frappe

from frappe import _

from frappe.utils import cstr



def search_invoices_for_return(invoice_name, company, pos_opening_shift=None):
    pos_opening_shift = cstr(pos_opening_shift or "").strip()
    if not pos_opening_shift:
        frappe.throw(_("POS Opening Shift is required to search return invoices."))

    invoices_list = frappe.get_all(
        "Sales Invoice",
        filters={
            "name": ["like", f"%{invoice_name}%"],
            "company": company,
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 1,
            "is_return": 0,
        },
        fields=["name"],
        order_by="customer",
    )

    data = []

    for invoice in invoices_list:
        original = frappe.get_doc("Sales Invoice", invoice["name"])
        original.flags.ignore_permissions = True

        # Get all return invoices for this invoice
        return_invoices = frappe.get_all(
            "Sales Invoice",
            filters={"return_against": original.name, "docstatus": 1},
            fields=["name"]
        )

        # Build map: item_code -> total returned qty
        returned_qty_map = {}
        for ret in return_invoices:
            ret_doc = frappe.get_doc("Sales Invoice", ret.name)
            ret_doc.flags.ignore_permissions = True
            for item in ret_doc.items:
                returned_qty_map[item.item_code] = returned_qty_map.get(item.item_code, 0) + abs(item.qty)

        has_returnable_items = False
        updated_items = []

        for item in original.items:
            returned_qty = returned_qty_map.get(item.item_code, 0)
            remaining_qty = item.qty - returned_qty

            # Copy item
            new_item = copy.deepcopy(item)

            if remaining_qty > 0:
                # Mark item for return (negate qty & recalc amounts)
                new_item.qty = -remaining_qty
                new_item.stock_qty = -(item.stock_qty / item.qty) * remaining_qty if item.qty else 0
                new_item.amount = -(item.amount / item.qty) * remaining_qty if item.qty else 0
                has_returnable_items = True
            else:
                new_item.qty = 0
                new_item.stock_qty = 0
                new_item.amount = 0

            updated_items.append(new_item)

        if has_returnable_items:
            original.set("items", updated_items)
            data.append(original)

    return data
