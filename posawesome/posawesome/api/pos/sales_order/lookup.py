# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import add_days, cint, cstr, getdate, nowdate


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
    items_by_order = _get_sales_order_items_for_lookup(
        [name for name in order_names if name not in invoiced_orders]
    )

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
        doc["items"] = items_by_order.get(order["name"], [])
        doc["order_age_days"] = age_days
        doc["is_stale"] = is_stale
        doc["stale_policy_allow"] = 1 if allow_stale else 0
        doc["stale_policy_max_age_days"] = days_back
        doc["stale_policy_history_days"] = history_days
        data.append(doc)
    return data


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


def _get_sales_order_items_for_lookup(sales_orders):
    sales_orders = [cstr(name).strip() for name in (sales_orders or []) if cstr(name).strip()]
    if not sales_orders:
        return {}

    fields = [
        "parent",
        "name",
        "item_code",
        "item_name",
        "qty",
        "uom",
        "rate",
        "amount",
        "conversion_factor",
    ]
    for fieldname in (
        "serial_no",
        "batch_no",
        "discount_percentage",
        "discount_amount",
        "price_list_rate",
        "warehouse",
        "delivery_warehouse",
        "posa_notes",
        "posa_delivery_date",
    ):
        if _doctype_has_column("Sales Order Item", fieldname):
            fields.append(fieldname)

    rows = frappe.get_all(
        "Sales Order Item",
        filters={"parent": ["in", sales_orders]},
        fields=fields,
        order_by="parent asc, idx asc",
        limit_page_length=0,
        ignore_permissions=True,
    )
    items_by_order = {}
    for row in rows:
        item = frappe._dict(row)
        item["doctype"] = "Sales Order Item"
        items_by_order.setdefault(item.parent, []).append(item)
    return items_by_order


def _age_days_from_date(raw_date):
    try:
        d = getdate(raw_date)
        return max(0, (getdate(nowdate()) - d).days)
    except Exception:
        return 0


def _resolve_pos_profile_for_lookup(pos_profile, company):
    pos_profile = cstr(pos_profile or "").strip()
    if pos_profile:
        return pos_profile

    active_shift = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": frappe.session.user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
            "company": company,
        },
        fields=["pos_profile"],
        order_by="period_start_date desc",
        limit_page_length=1,
    )
    if active_shift:
        return cstr(active_shift[0].get("pos_profile") or "").strip()
    return ""


def _profile_so_policy(pos_profile):
    max_age_days = 1
    allow_stale = 0
    history_days = 30
    naming_series = ""
    if pos_profile:
        max_age_days = max(
            0,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_sales_order_lookup_max_age_days"
                )
                or 1
            ),
        )
        allow_stale = 1 if cint(
            frappe.get_cached_value(
                "POS Profile", pos_profile, "posa_allow_stale_sales_order_fetch"
            )
            or 0
        ) else 0
        history_days = max(
            max_age_days,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_stale_sales_order_history_days"
                )
                or 30
            ),
        )
        naming_series = cstr(
            frappe.get_cached_value("POS Profile", pos_profile, "posa_sales_order_naming_series")
            or ""
        ).strip()
    return {
        "max_age_days": max_age_days,
        "allow_stale": allow_stale,
        "history_days": history_days,
        "naming_series": naming_series,
    }


def _resolve_allow_stale(arg_allow_stale, default_allow_stale):
    if arg_allow_stale in (None, ""):
        return 1 if cint(default_allow_stale) else 0
    return 1 if cint(arg_allow_stale) else 0


def _doctype_has_column(doctype, fieldname):
    return frappe.get_meta(doctype).has_field(fieldname) and frappe.db.has_column(
        doctype, fieldname
    )
