# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe.utils import cstr, nowdate



from posawesome.posawesome.api.pos.relay.meta import (
    _get_invoice_linked_sales_order_name,
    _is_relay_workflow_enabled,
    _relay_workflow_doctype_exists,
    _relay_workflow_has_field,
)

from posawesome.posawesome.api.pos.relay.updates import _apply_relay_workflow_state_updates



def _get_relay_state_doc(invoice_doc):
    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"sales_invoice": invoice_doc.name}
    )
    if state_name:
        return frappe.get_doc("POS Relay Workflow State", state_name)

    linked_sales_order = _get_invoice_linked_sales_order_name(invoice_doc)
    if linked_sales_order and _relay_workflow_has_field("sales_order"):
        state_name = frappe.db.exists(
            "POS Relay Workflow State", {"sales_order": linked_sales_order}
        )
        if state_name:
            return frappe.get_doc("POS Relay Workflow State", state_name)

    payload = {
        "doctype": "POS Relay Workflow State",
        "sales_invoice": invoice_doc.name,
        "pos_profile": invoice_doc.pos_profile,
        "token_id": cstr(linked_sales_order or invoice_doc.name),
        "token_status": "Draft",
        "picking_status": "Not Started",
        "dispatch_status": "Pending",
        "last_sync_status": "Not Applicable",
    }
    if linked_sales_order and _relay_workflow_has_field("sales_order"):
        payload["sales_order"] = linked_sales_order
    if _relay_workflow_has_field("pos_opening_shift") and invoice_doc.get("posa_pos_opening_shift"):
        payload["pos_opening_shift"] = invoice_doc.get("posa_pos_opening_shift")
    if _relay_workflow_has_field("business_date"):
        payload["business_date"] = cstr(invoice_doc.get("posting_date") or nowdate())
    return frappe.get_doc(payload)

def _upsert_relay_workflow_state(
    invoice_doc,
    token_status=None,
    picking_status=None,
    dispatch_status=None,
    exceptions_note=None,
    is_offline_recorded=None,
    last_sync_status=None,
    sync_error=None,
):
    if not invoice_doc or not invoice_doc.get("name") or not invoice_doc.get("pos_profile"):
        return None

    if not _relay_workflow_doctype_exists():
        return None

    if not _is_relay_workflow_enabled(invoice_doc.pos_profile):
        return None

    state_doc = _get_relay_state_doc(invoice_doc)
    linked_sales_order = _get_invoice_linked_sales_order_name(invoice_doc)
    pos_opening_shift = invoice_doc.get("posa_pos_opening_shift")
    token_id = linked_sales_order or cstr(invoice_doc.name)[-5:]
    business_date = cstr(invoice_doc.get("posting_date") or nowdate())
    if linked_sales_order:
        try:
            so_txn_date = frappe.get_cached_value("Sales Order", linked_sales_order, "transaction_date")
            if so_txn_date:
                business_date = cstr(so_txn_date)
        except Exception:
            pass

    return _apply_relay_workflow_state_updates(
        state_doc,
        token_status=token_status,
        picking_status=picking_status,
        dispatch_status=dispatch_status,
        exceptions_note=exceptions_note,
        is_offline_recorded=is_offline_recorded,
        last_sync_status=last_sync_status,
        sync_error=sync_error,
        pos_profile=invoice_doc.pos_profile,
        token_id=token_id,
        sales_invoice=invoice_doc.name,
        sales_order=linked_sales_order,
        pos_opening_shift=pos_opening_shift,
        business_date=business_date,
    )
