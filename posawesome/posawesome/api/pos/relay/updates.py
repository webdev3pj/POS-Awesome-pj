# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe.utils import cint, cstr, now_datetime



from posawesome.posawesome.api.pos.relay.constants import (
    RELAY_DISPATCH_STATUSES,
    RELAY_PICKING_STATUSES,
    RELAY_TOKEN_STATUSES,
)

from posawesome.posawesome.api.pos.relay.meta import _relay_workflow_has_field, _set_state_field_if_exists



def _apply_relay_workflow_state_updates(
    state_doc,
    token_status=None,
    picking_status=None,
    dispatch_status=None,
    exceptions_note=None,
    is_offline_recorded=None,
    last_sync_status=None,
    sync_error=None,
    pos_profile=None,
    token_id=None,
    sales_invoice=None,
    sales_order=None,
    pos_opening_shift=None,
    business_date=None,
    set_order_taken_at=False,
):
    if not state_doc:
        return None

    now_ts = now_datetime()
    prev_token_status = cstr(state_doc.get("token_status") or "")
    prev_picking_status = cstr(state_doc.get("picking_status") or "")
    prev_dispatch_status = cstr(state_doc.get("dispatch_status") or "")
    status_changed = False

    if pos_profile:
        state_doc.pos_profile = pos_profile

    if token_id:
        state_doc.token_id = cstr(token_id)

    if sales_invoice:
        state_doc.sales_invoice = sales_invoice

    _set_state_field_if_exists(state_doc, "sales_order", sales_order)
    _set_state_field_if_exists(state_doc, "pos_opening_shift", pos_opening_shift)
    _set_state_field_if_exists(state_doc, "business_date", cstr(business_date) if business_date else None)

    if set_order_taken_at and _relay_workflow_has_field("order_taken_at") and not state_doc.get("order_taken_at"):
        state_doc.set("order_taken_at", now_ts)

    if token_status in RELAY_TOKEN_STATUSES and token_status != prev_token_status:
        state_doc.token_status = token_status
        status_changed = True
        if token_status == "Paid" and _relay_workflow_has_field("paid_at") and not state_doc.get("paid_at"):
            state_doc.set("paid_at", now_ts)

    if picking_status in RELAY_PICKING_STATUSES and picking_status != prev_picking_status:
        state_doc.picking_status = picking_status
        status_changed = True
        if (
            picking_status == "In Progress"
            and _relay_workflow_has_field("pick_started_at")
            and not state_doc.get("pick_started_at")
        ):
            state_doc.set("pick_started_at", now_ts)
        if picking_status == "Picked" and _relay_workflow_has_field("picked_at"):
            state_doc.set("picked_at", now_ts)

    if dispatch_status in RELAY_DISPATCH_STATUSES and dispatch_status != prev_dispatch_status:
        state_doc.dispatch_status = dispatch_status
        status_changed = True
        if dispatch_status == "Released":
            if state_doc.get("released_by") in (None, ""):
                state_doc.released_by = frappe.session.user
            if not state_doc.get("released_at"):
                state_doc.released_at = now_ts

    if exceptions_note is not None:
        state_doc.exceptions_note = exceptions_note

    if is_offline_recorded is not None:
        state_doc.is_offline_recorded = cint(is_offline_recorded)

    if last_sync_status is not None:
        state_doc.last_sync_status = last_sync_status

    if sync_error is not None:
        state_doc.sync_error = sync_error

    if _relay_workflow_has_field("status_changed_at"):
        if status_changed:
            state_doc.set("status_changed_at", now_ts)
        elif state_doc.is_new() and not state_doc.get("status_changed_at"):
            state_doc.set("status_changed_at", now_ts)

    state_doc.flags.ignore_permissions = True
    state_doc.save()
    return state_doc
