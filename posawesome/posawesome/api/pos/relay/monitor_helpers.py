from frappe.utils import cstr
import frappe

from posawesome.posawesome.api.pos.relay.state import _relay_workflow_has_field


def monitor_state_fields():
    fields = [
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
            fields.append(maybe_field)
    return fields


def get_sales_order_map(state_rows):
    so_names = sorted(
        {cstr(row.get("sales_order") or "").strip() for row in state_rows if row.get("sales_order")}
    )
    if not so_names:
        return {}
    return {
        doc.name: doc
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
        )
    }


def get_sales_invoice_map(state_rows):
    si_names = sorted(
        {cstr(row.get("sales_invoice") or "").strip() for row in state_rows if row.get("sales_invoice")}
    )
    if not si_names:
        return {}
    return {
        doc.name: doc
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
        )
    }


def get_user_display_map(so_map, si_map):
    user_ids = {
        doc.get("owner")
        for doc in list(so_map.values()) + list(si_map.values())
        if doc.get("owner")
    }
    if not user_ids:
        return {}

    user_map = {}
    for user in frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)]},
        fields=["name", "full_name", "first_name", "last_name"],
        limit_page_length=len(user_ids),
    ):
        full_name = cstr(user.get("full_name") or "").strip()
        if not full_name:
            full_name = " ".join(
                [
                    cstr(user.get("first_name") or "").strip(),
                    cstr(user.get("last_name") or "").strip(),
                ]
            ).strip()
        user_map[user.name] = full_name or user.name
    return user_map


def derived_business_date(row_obj, so_doc_obj=None, si_doc_obj=None):
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
