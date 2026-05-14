# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe.utils import cint, cstr, now_datetime, nowdate



from posawesome.posawesome.api.pos.relay.state import (
    _relay_workflow_doctype_exists,
    _relay_workflow_has_field,
)



def _normalize_monitor_display_status(row):
    token_status = cstr((row or {}).get("token_status") or "")
    picking_status = cstr((row or {}).get("picking_status") or "")
    dispatch_status = cstr((row or {}).get("dispatch_status") or "")

    if dispatch_status == "Released":
        return "Dispatched"
    if dispatch_status == "On Hold" or picking_status == "Exception":
        return "On Hold"
    if token_status != "Paid":
        return "Unpaid"
    if picking_status == "In Progress":
        return "Picking"
    if picking_status == "Picked":
        return "Picked"
    return "Paid"

def get_relay_workflow_monitor_board(
    pos_profile=None,
    business_date=None,
    scope_mode=None,
    pos_opening_shift=None,
    mine_only=0,
    include_released=0,
    limit_page_length=200,
):
    if not _relay_workflow_doctype_exists():
        return {"summary": {"pending_count": 0, "server_time": str(now_datetime())}, "rows": []}

    state_fields = [
        "name",
        "sales_invoice",
        "pos_profile",
        "token_id",
        "token_status",
        "picking_status",
        "dispatch_status",
        "exceptions_note",
        "released_by",
        "released_at",
        "modified",
    ]
    for maybe_field in (
        "sales_order",
        "business_date",
        "pos_opening_shift",
        "status_changed_at",
        "order_taken_at",
        "paid_at",
        "pick_started_at",
        "picked_at",
        "dispatch_exception_state",
        "cashier_adjustment_required",
        "dispatch_proof",
        "dispatch_proof_payload",
    ):
        if _relay_workflow_has_field(maybe_field):
            state_fields.append(maybe_field)

    scope_mode = cstr(scope_mode or "business_date").strip().lower()
    if scope_mode not in ("business_date", "opening_shift"):
        scope_mode = "business_date"
    target_business_date = cstr(business_date or nowdate()).strip() or nowdate()

    filters = {}
    if pos_profile:
        filters["pos_profile"] = pos_profile
    if (
        scope_mode == "opening_shift"
        and _relay_workflow_has_field("pos_opening_shift")
        and pos_opening_shift
    ):
        filters["pos_opening_shift"] = pos_opening_shift
    if not cint(include_released):
        filters["dispatch_status"] = ["!=", "Released"]

    state_rows = frappe.get_all(
        "POS Relay Workflow State",
        filters=filters,
        fields=state_fields,
        order_by="modified asc",
        limit_page_length=max(1, cint(limit_page_length) or 200),
    )

    so_names = sorted(
        {cstr((row.get("sales_order") or "")).strip() for row in state_rows if row.get("sales_order")}
    )
    si_names = sorted(
        {cstr((row.get("sales_invoice") or "")).strip() for row in state_rows if row.get("sales_invoice")}
    )

    so_map = {}
    if so_names:
        for doc in frappe.get_all(
            "Sales Order",
            filters={"name": ["in", so_names]},
            fields=[
                "name",
                "customer",
                "customer_name",
                "grand_total",
                "currency",
                "owner",
                "transaction_date",
                "creation",
                "modified",
            ],
            limit_page_length=len(so_names),
        ):
            so_map[doc.name] = doc

    si_map = {}
    if si_names:
        for doc in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", si_names]},
            fields=[
                "name",
                "customer",
                "customer_name",
                "grand_total",
                "currency",
                "owner",
                "posting_date",
                "posting_time",
                "creation",
                "modified",
                "posa_pos_opening_shift",
            ],
            limit_page_length=len(si_names),
        ):
            si_map[doc.name] = doc

    user_ids = set()
    for so in so_map.values():
        if so.get("owner"):
            user_ids.add(so.get("owner"))
    for si in si_map.values():
        if si.get("owner"):
            user_ids.add(si.get("owner"))

    user_map = {}
    if user_ids:
        for user in frappe.get_all(
            "User",
            filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name", "first_name", "last_name"],
            limit_page_length=len(user_ids),
        ):
            full_name = cstr(user.get("full_name") or "").strip()
            if not full_name:
                full_name = " ".join(
                    [cstr(user.get("first_name") or "").strip(), cstr(user.get("last_name") or "").strip()]
                ).strip()
            user_map[user.name] = full_name or user.name

    mine_only = cint(mine_only)
    current_user = frappe.session.user

    rows = []
    status_counts = {}

    def _derived_business_date(row_obj, so_doc_obj=None, si_doc_obj=None):
        if row_obj and row_obj.get("business_date"):
            return cstr(row_obj.get("business_date"))
        if so_doc_obj and so_doc_obj.get("transaction_date"):
            return cstr(so_doc_obj.get("transaction_date"))
        if si_doc_obj and si_doc_obj.get("posting_date"):
            return cstr(si_doc_obj.get("posting_date"))
        raw_dt = (row_obj or {}).get("order_taken_at") or (row_obj or {}).get("modified")
        if raw_dt:
            raw_text = cstr(raw_dt)
            if " " in raw_text:
                return raw_text.split(" ", 1)[0]
            if "T" in raw_text:
                return raw_text.split("T", 1)[0]
        return ""

    for row in state_rows:
        so_doc = so_map.get(row.get("sales_order")) if row.get("sales_order") else None
        si_doc = si_map.get(row.get("sales_invoice")) if row.get("sales_invoice") else None

        row_business_date = _derived_business_date(row, so_doc, si_doc)
        if scope_mode == "business_date" and target_business_date:
            if row_business_date and row_business_date != target_business_date:
                continue

        sales_associate_user = cstr((so_doc or {}).get("owner") or "").strip()
        if not sales_associate_user and si_doc and row.get("token_status") != "Paid":
            sales_associate_user = cstr(si_doc.get("owner") or "").strip()

        if mine_only and sales_associate_user != current_user:
            continue

        sales_associate_name = user_map.get(sales_associate_user, sales_associate_user)
        customer_name = (
            (so_doc or {}).get("customer_name")
            or (si_doc or {}).get("customer_name")
            or ""
        )
        grand_total = (so_doc or {}).get("grand_total")
        if grand_total in (None, ""):
            grand_total = (si_doc or {}).get("grand_total")
        currency = (so_doc or {}).get("currency") or (si_doc or {}).get("currency") or ""

        order_taken_at = row.get("order_taken_at") or (so_doc or {}).get("creation") or (si_doc or {}).get("creation")
        status_changed_at = row.get("status_changed_at") or row.get("modified")
        effective_shift = row.get("pos_opening_shift") or (si_doc or {}).get("posa_pos_opening_shift") or ""

        monitor_row = {
            "workflow_state": row.get("name"),
            "sales_order": row.get("sales_order") or "",
            "sales_invoice": row.get("sales_invoice") or "",
            "token_id": row.get("token_id") or "",
            "customer_name": customer_name,
            "grand_total": grand_total,
            "currency": currency,
            "sales_associate_user": sales_associate_user,
            "sales_associate_name": sales_associate_name,
            "business_date": row_business_date or target_business_date,
            "pos_opening_shift": effective_shift,
            "token_status": row.get("token_status"),
            "picking_status": row.get("picking_status"),
            "dispatch_status": row.get("dispatch_status"),
            "display_status": _normalize_monitor_display_status(row),
            "order_taken_at": order_taken_at,
            "paid_at": row.get("paid_at"),
            "pick_started_at": row.get("pick_started_at"),
            "picked_at": row.get("picked_at"),
            "released_at": row.get("released_at"),
            "status_changed_at": status_changed_at,
            "dispatch_exception_state": row.get("dispatch_exception_state") or "NONE",
            "cashier_adjustment_required": cint(row.get("cashier_adjustment_required") or 0),
            "dispatch_proof": row.get("dispatch_proof")
            or row.get("dispatch_proof_payload")
            or {},
        }
        rows.append(monitor_row)
        status_counts[monitor_row["display_status"]] = status_counts.get(monitor_row["display_status"], 0) + 1

    def _sort_key(item):
        return cstr(item.get("status_changed_at") or item.get("order_taken_at") or "")

    rows.sort(key=_sort_key)

    return {
        "summary": {
            "pending_count": len(rows),
            "status_counts": status_counts,
            "server_time": str(now_datetime()),
            "scope_mode": scope_mode,
            "business_date": target_business_date if scope_mode == "business_date" else "",
            "pos_profile": pos_profile or "",
        },
        "rows": rows,
    }
