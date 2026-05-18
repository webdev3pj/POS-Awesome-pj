# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate, nowdate

from posawesome.posawesome.api.pos.quotation.lookup import require_quotation_permission
from posawesome.posawesome.api.pos.sales_order.lookup import _age_days_from_date


def get_quotation_reprice_preview(quotation_name, pos_profile, role):
    quotation_name = cstr(quotation_name or "").strip()
    pos_profile = cstr(pos_profile or "").strip()
    if not quotation_name:
        frappe.throw(_("Quotation name is required"))
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    require_quotation_permission(pos_profile, role)

    doc = frappe.get_doc("Quotation", quotation_name)
    doc.flags.ignore_permissions = True
    repriced_lines = []
    old_total = 0.0
    new_total = 0.0
    for row in (doc.items or []):
        qty = flt(row.qty or 0)
        old_rate = flt(row.rate or 0)
        old_amount = flt(row.amount or (qty * old_rate))
        latest_rate = latest_item_rate_for_profile(
            row.item_code, pos_profile, company=doc.company, customer=doc.party_name, currency=doc.currency
        )
        if latest_rate <= 0:
            latest_rate = old_rate
        new_amount = flt(qty * latest_rate)
        old_total += old_amount
        new_total += new_amount
        repriced_lines.append(
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": qty,
                "uom": row.uom,
                "old_rate": old_rate,
                "new_rate": latest_rate,
                "delta_rate": flt(latest_rate - old_rate),
                "old_amount": old_amount,
                "new_amount": new_amount,
                "delta_amount": flt(new_amount - old_amount),
            }
        )

    valid_till = cstr(doc.get("valid_till") or "")
    is_expired = 1 if (valid_till and getdate(valid_till) < getdate(nowdate())) else 0
    return {
        "quote_name": doc.name,
        "valid_till": valid_till,
        "is_expired": is_expired,
        "age_days": _age_days_from_date(doc.get("transaction_date")),
        "old_total": flt(old_total),
        "new_total": flt(new_total),
        "delta_total": flt(new_total - old_total),
        "repriced_lines": repriced_lines,
    }


def latest_item_rate_for_profile(item_code, pos_profile, company=None, customer=None, currency=None):
    item_code = cstr(item_code or "").strip()
    if not item_code:
        return 0
    price_list = cstr(frappe.get_cached_value("POS Profile", pos_profile, "selling_price_list") or "").strip()
    if not price_list:
        return 0

    filters = {
        "item_code": item_code,
        "price_list": price_list,
        "selling": 1,
    }
    if currency:
        filters["currency"] = currency
    row = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["price_list_rate", "valid_from", "creation"],
        order_by="valid_from desc, creation desc",
        limit_page_length=1,
    )
    if row:
        return flt(row[0].get("price_list_rate") or 0)
    return 0
