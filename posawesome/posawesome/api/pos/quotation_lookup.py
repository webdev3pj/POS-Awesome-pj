# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, getdate, nowdate

from posawesome.posawesome.api.pos.sales_order_lookup import (
    _age_days_from_date,
    _profile_so_policy,
    _resolve_allow_stale,
)


def require_quotation_permission(pos_profile, role):
    role = cstr(role or "").strip()
    if role not in ("cline-Sales Associate", "cline-Cashier"):
        return
    if not pos_profile:
        frappe.throw(_("POS Profile is required for quotation permission checks."))
    if role == "cline-Sales Associate":
        allowed = _get_profile_check_value(pos_profile, "posa_allow_sa_quotation", default=1)
        if not allowed:
            frappe.throw(_("Sales Associate quotation is disabled in POS Profile {0}.").format(pos_profile))
    if role == "cline-Cashier":
        allowed = _get_profile_check_value(pos_profile, "posa_allow_cashier_quotation", default=1)
        if not allowed:
            frappe.throw(_("Cashier quotation is disabled in POS Profile {0}.").format(pos_profile))


def search_pos_quotations(
    company=None,
    currency=None,
    pos_profile=None,
    quote_name=None,
    allow_stale=None,
    history_days=None,
):
    pos_profile = cstr(pos_profile or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    company = cstr(company or frappe.get_cached_value("POS Profile", pos_profile, "company") or "").strip()
    currency = cstr(currency or frappe.get_cached_value("POS Profile", pos_profile, "currency") or "").strip()

    so_policy = _profile_so_policy(pos_profile)
    validity_days = max(
        1, cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_quotation_validity_days") or 7)
    )
    max_age_days = max(validity_days, cint(so_policy["max_age_days"] or 1))
    allow_stale = _resolve_allow_stale(allow_stale, so_policy["allow_stale"])
    if history_days in (None, ""):
        history_days = max(cint(so_policy["history_days"] or 30), max_age_days)
    history_days = max(max_age_days, cint(history_days or 30))

    lookback_days = history_days if allow_stale else max_age_days
    filters = {
        "docstatus": 1,
        "company": company,
        "transaction_date": [">=", add_days(nowdate(), -lookback_days)],
    }
    if currency:
        filters["currency"] = currency
    if quote_name:
        filters["name"] = ["like", f"%{quote_name}%"]

    rows = frappe.get_list(
        "Quotation",
        filters=filters,
        fields=["name", "transaction_date", "valid_till"],
        limit_page_length=0,
        order_by="transaction_date desc, creation desc",
    )
    out = []
    for row in rows:
        age_days = _age_days_from_date(row.get("transaction_date"))
        is_stale = 1 if age_days > max_age_days else 0
        if not allow_stale and is_stale:
            continue
        doc = frappe.get_doc("Quotation", row.get("name")).as_dict()
        valid_till = cstr(doc.get("valid_till") or row.get("valid_till") or "")
        is_expired = 1 if (valid_till and getdate(valid_till) < getdate(nowdate())) else 0
        doc["quote_name"] = doc.get("name")
        doc["order_age_days"] = age_days
        doc["age_days"] = age_days
        doc["is_stale"] = is_stale
        doc["is_expired"] = is_expired
        doc["stale_policy_allow"] = 1 if allow_stale else 0
        doc["stale_policy_max_age_days"] = max_age_days
        doc["stale_policy_history_days"] = history_days
        out.append(doc)
    return out


def _get_profile_check_value(pos_profile, fieldname, default=1):
    value = frappe.get_cached_value("POS Profile", pos_profile, fieldname)
    if value in (None, ""):
        return cint(default)
    return cint(value)
