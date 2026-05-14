# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe.utils import cstr, nowdate



from posawesome.posawesome.api.pos.relay.constants import RELAY_TOKEN_STATUSES

from posawesome.posawesome.api.pos.relay.meta import (
    _is_relay_workflow_enabled,
    _relay_workflow_doctype_exists,
    _relay_workflow_has_field,
)

from posawesome.posawesome.api.pos.relay.updates import _apply_relay_workflow_state_updates



def _get_relay_state_doc_for_sales_order(
    sales_order_name, pos_profile=None, pos_opening_shift=None, business_date=None
):
    if not sales_order_name or not _relay_workflow_has_field("sales_order"):
        return None

    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"sales_order": sales_order_name}
    )
    if state_name:
        return frappe.get_doc("POS Relay Workflow State", state_name)

    payload = {
        "doctype": "POS Relay Workflow State",
        "token_id": cstr(sales_order_name),
        "token_status": "Draft",
        "picking_status": "Not Started",
        "dispatch_status": "Pending",
        "last_sync_status": "Not Applicable",
    }
    if pos_profile:
        payload["pos_profile"] = pos_profile
    if _relay_workflow_has_field("sales_order"):
        payload["sales_order"] = sales_order_name
    if _relay_workflow_has_field("pos_opening_shift") and pos_opening_shift:
        payload["pos_opening_shift"] = pos_opening_shift
    if _relay_workflow_has_field("business_date") and business_date:
        payload["business_date"] = cstr(business_date)
    return frappe.get_doc(payload)

def _upsert_relay_workflow_state_for_sales_order(
    sales_order_doc,
    pos_profile=None,
    pos_opening_shift=None,
    token_status="Draft",
):
    if not sales_order_doc or not sales_order_doc.get("name"):
        return None
    if not _relay_workflow_doctype_exists():
        return None
    if pos_profile and not _is_relay_workflow_enabled(pos_profile):
        return None

    so_business_date = cstr(sales_order_doc.get("transaction_date") or nowdate())
    state_doc = _get_relay_state_doc_for_sales_order(
        sales_order_doc.name,
        pos_profile=pos_profile,
        pos_opening_shift=pos_opening_shift,
        business_date=so_business_date,
    )
    if not state_doc:
        return None

    return _apply_relay_workflow_state_updates(
        state_doc,
        pos_profile=pos_profile,
        token_id=sales_order_doc.name,
        sales_order=sales_order_doc.name,
        pos_opening_shift=pos_opening_shift,
        business_date=so_business_date,
        token_status=token_status if token_status in RELAY_TOKEN_STATUSES else None,
        picking_status="Not Started",
        dispatch_status="Pending",
        set_order_taken_at=True,
    )
