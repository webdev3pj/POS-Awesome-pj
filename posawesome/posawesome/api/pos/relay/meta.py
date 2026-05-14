# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe.utils import cint, cstr



def _relay_workflow_doctype_exists():
    return bool(frappe.db.exists("DocType", "POS Relay Workflow State"))

def _is_relay_workflow_enabled(pos_profile):
    if not pos_profile:
        return False

    return cint(
        frappe.get_cached_value("POS Profile", pos_profile, "custom_have_token") or 0
    ) == 1

def _resolve_relay_workflow_pos_profile(invoice_doc, *candidates):
    invoice_profile = cstr((invoice_doc.get("pos_profile") if invoice_doc else "") or "").strip()
    if invoice_profile:
        return invoice_profile

    for candidate in candidates:
        value = cstr(candidate or "").strip()
        if value:
            return value

    if invoice_doc and _relay_workflow_doctype_exists():
        try:
            state_name = frappe.db.exists("POS Relay Workflow State", {"sales_invoice": invoice_doc.name})
            if state_name:
                return cstr(
                    frappe.db.get_value("POS Relay Workflow State", state_name, "pos_profile") or ""
                ).strip()
        except Exception:
            pass

    return ""

def _relay_workflow_meta():
    if not _relay_workflow_doctype_exists():
        return None
    try:
        return frappe.get_meta("POS Relay Workflow State")
    except Exception:
        return None

def _relay_workflow_has_field(fieldname):
    meta = _relay_workflow_meta()
    return bool(meta and meta.has_field(fieldname))

def _set_state_field_if_exists(state_doc, fieldname, value):
    if value is None:
        return
    if _relay_workflow_has_field(fieldname):
        state_doc.set(fieldname, value)

def _get_relay_invoice_by_local_sale_ref(local_sale_ref):
    local_sale_ref = cstr(local_sale_ref or "").strip()
    if not local_sale_ref or not _relay_workflow_has_field("local_sale_ref"):
        return None

    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"local_sale_ref": local_sale_ref}
    )
    if not state_name:
        return None

    sales_invoice = cstr(
        frappe.db.get_value("POS Relay Workflow State", state_name, "sales_invoice")
        or ""
    ).strip()
    if sales_invoice and frappe.db.exists("Sales Invoice", sales_invoice):
        return frappe.get_doc("Sales Invoice", sales_invoice)
    return None

def _set_relay_state_local_sale_ref(state_doc, local_sale_ref):
    local_sale_ref = cstr(local_sale_ref or "").strip()
    if not state_doc or not local_sale_ref or not _relay_workflow_has_field("local_sale_ref"):
        return state_doc

    state_doc.set("local_sale_ref", local_sale_ref)
    state_doc.flags.ignore_permissions = True
    state_doc.save()
    return state_doc

def _get_invoice_linked_sales_order_name(invoice_doc):
    if not invoice_doc:
        return ""
    for row in (invoice_doc.get("items") or []):
        so_name = cstr(
            (row.get("sales_order") if hasattr(row, "get") else getattr(row, "sales_order", ""))
            or ""
        ).strip()
        if so_name:
            return so_name
    return ""
