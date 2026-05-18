# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate

from posawesome.posawesome.api.pos.quotation.lookup import require_quotation_permission


def convert_quotation_to_sales_order_token(
    quotation_name,
    pos_profile,
    confirm_reprice,
    role,
    reprice_preview_fn,
    create_sales_order_token_fn,
    order_name=None,
):
    quotation_name = cstr(quotation_name or "").strip()
    pos_profile = cstr(pos_profile or "").strip()
    order_name = cstr(order_name or "").strip()
    if not quotation_name:
        frappe.throw(_("Quotation name is required"))
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    require_quotation_permission(pos_profile, role)

    doc = frappe.get_doc("Quotation", quotation_name)
    doc.flags.ignore_permissions = True
    validity_days = max(
        1, cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_quotation_validity_days") or 7)
    )
    valid_till = cstr(doc.get("valid_till") or add_days(doc.get("transaction_date") or nowdate(), validity_days))
    if valid_till and getdate(valid_till) < getdate(nowdate()):
        frappe.throw(_("Quotation {0} is expired and cannot be converted.").format(quotation_name))

    preview = reprice_preview_fn(quotation_name=quotation_name, pos_profile=pos_profile)
    if flt(preview.get("delta_total")) != 0 and not cint(confirm_reprice):
        frappe.throw(_("Price changed since quotation. Confirmation is required for conversion."))

    so_items = _build_sales_order_items_from_quotation(doc, preview)
    token = create_sales_order_token_fn(
        {
            "pos_profile": pos_profile,
            "company": cstr(doc.get("company") or ""),
            "customer": cstr(doc.get("customer") or doc.get("party_name") or ""),
            "currency": cstr(doc.get("currency") or ""),
            "posting_date": cstr(nowdate()),
            "order_name": order_name,
            "posa_order_name": order_name,
            "items": so_items,
            "discount_amount": flt(doc.get("discount_amount") or 0),
            "additional_discount_percentage": flt(doc.get("additional_discount_percentage") or 0),
        }
    )
    token["quote_name"] = quotation_name
    token["quote_valid_till"] = valid_till
    token["quote_reprice_preview"] = preview
    return token


def _build_sales_order_items_from_quotation(doc, preview):
    line_rate_map = {}
    for i, row in enumerate(preview.get("repriced_lines") or []):
        line_rate_map[(cstr(row.get("item_code") or ""), i)] = flt(row.get("new_rate") or 0)

    so_items = []
    for i, row in enumerate(doc.items or []):
        item_code = cstr(row.item_code or "").strip()
        new_rate = line_rate_map.get((item_code, i), flt(row.rate or 0))
        so_items.append(
            {
                "item_code": item_code,
                "item_name": row.item_name,
                "qty": flt(row.qty or 0),
                "uom": row.uom,
                "rate": new_rate,
                "amount": flt(flt(row.qty or 0) * new_rate),
                "conversion_factor": flt(row.conversion_factor or 1) or 1,
                "discount_percentage": flt(row.discount_percentage or 0),
                "discount_amount": flt(row.discount_amount or 0),
                "price_list_rate": flt(row.price_list_rate or new_rate),
                "warehouse": row.get("warehouse") if hasattr(row, "get") else None,
                "posa_delivery_date": cstr(row.get("delivery_date") if hasattr(row, "get") else "") or "",
            }
        )
    return so_items
