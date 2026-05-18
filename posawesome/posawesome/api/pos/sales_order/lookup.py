# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, nowdate

from posawesome.posawesome.api.pos.sales_order.policy import (
    age_days_from_date as _age_days_from_date,
    doctype_has_column as _doctype_has_column,
    profile_so_policy as _profile_so_policy,
    resolve_allow_stale as _resolve_allow_stale,
    resolve_pos_profile_for_lookup as _resolve_pos_profile_for_lookup,
)


def search_sales_orders(
    company,
    currency,
    order_name=None,
    pos_profile=None,
    days_back=None,
    allow_stale=None,
    history_days=None,
):
    pos_profile = _resolve_pos_profile_for_lookup(pos_profile, company)
    policy = _profile_so_policy(pos_profile)

    try:
        if days_back in (None, ""):
            days_back = policy["max_age_days"]
        days_back = max(0, cint(days_back or 1))
    except Exception:
        days_back = max(0, cint(policy["max_age_days"] or 1))

    allow_stale = _resolve_allow_stale(allow_stale, policy["allow_stale"])
    try:
        if history_days in (None, ""):
            history_days = policy["history_days"]
        history_days = max(days_back, cint(history_days or policy["history_days"] or 30))
    except Exception:
        history_days = max(days_back, cint(policy["history_days"] or 30))

    lookback_days = history_days if allow_stale else days_back
    filters = {
        "billing_status": ["in", ["Not Billed", "Partly Billed"]],
        "docstatus": 1,
        "company": company,
        "currency": currency,
        "transaction_date": [">=", add_days(nowdate(), -lookback_days)],
    }
    if policy["naming_series"]:
        filters["naming_series"] = policy["naming_series"]

    order_name = cstr(order_name or "").strip()
    or_filters = None
    if order_name:
        if _doctype_has_column("Sales Order", "posa_order_name"):
            or_filters = [
                ["Sales Order", "name", "like", f"%{order_name}%"],
                ["Sales Order", "posa_order_name", "like", f"%{order_name}%"],
            ]
        else:
            filters["name"] = ["like", f"%{order_name}%"]

    fields = _sales_order_lookup_fields()
    orders_list = frappe.get_list(
        "Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        limit_page_length=50,
        order_by="transaction_date desc, creation desc",
    )
    order_names = [order["name"] for order in orders_list]
    invoiced_orders = _get_sales_orders_with_submitted_invoice(order_names)

    data = []
    for order in orders_list:
        if order["name"] in invoiced_orders:
            continue
        age_days = _age_days_from_date(order.get("transaction_date"))
        is_stale = 1 if age_days > days_back else 0
        if not allow_stale and is_stale:
            continue
        doc = frappe._dict(order)
        doc["doctype"] = "Sales Order"
        doc["order_age_days"] = age_days
        doc["is_stale"] = is_stale
        doc["stale_policy_allow"] = 1 if allow_stale else 0
        doc["stale_policy_max_age_days"] = days_back
        doc["stale_policy_history_days"] = history_days
        data.append(doc)
    return data


def get_sales_order_for_pos(sales_order):
    sales_order = cstr(sales_order or "").strip()
    if not sales_order:
        frappe.throw(_("Sales Order is required"))
    return frappe.get_doc("Sales Order", sales_order).as_dict()


def _sales_order_lookup_fields():
    fields = [
        "name",
        "transaction_date",
        "customer",
        "customer_name",
        "grand_total",
        "currency",
        "billing_status",
        "status",
    ]
    for fieldname in (
        "posa_order_name",
        "posa_notes",
        "posa_offers",
        "posa_coupons",
        "discount_amount",
        "additional_discount_percentage",
    ):
        if _doctype_has_column("Sales Order", fieldname):
            fields.append(fieldname)
    return fields


def _get_sales_orders_with_submitted_invoice(sales_orders):
    sales_orders = [cstr(name).strip() for name in (sales_orders or []) if cstr(name).strip()]
    if not sales_orders:
        return set()

    rows = frappe.db.sql(
        """
        select distinct sii.sales_order
        from `tabSales Invoice` si
        inner join `tabSales Invoice Item` sii on sii.parent = si.name
        where si.docstatus = 1
            and sii.sales_order in %(sales_orders)s
        """,
        {"sales_orders": tuple(sales_orders)},
        as_dict=True,
    )
    return {row.sales_order for row in rows}

