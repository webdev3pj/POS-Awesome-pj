# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe import _

from frappe.utils import cint, cstr



from posawesome.posawesome.api.pos.session.roles import require_operational_role_for_action

from posawesome.posawesome.api.pos.relay.state import (
    RELAY_PICKING_STATUSES,
    _get_relay_state_doc,
    _is_relay_workflow_enabled,
    _relay_workflow_doctype_exists,
    _resolve_relay_workflow_pos_profile,
    _upsert_relay_workflow_state,
)



def update_relay_picking_status(sales_invoice, picking_status, exceptions_note=None, pos_profile=None, pos_profile_id=None):
    require_operational_role_for_action(
        ("cline-Picker", "cline-Supervisor"),
        "update relay picking status",
        allow_relay_sync=True,
    )

    if picking_status not in RELAY_PICKING_STATUSES:
        frappe.throw(_("Invalid picking status: {0}").format(picking_status))

    if not _relay_workflow_doctype_exists():
        frappe.throw(_("Relay workflow state DocType is missing. Please run migration."))

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if effective_pos_profile and not cstr(invoice_doc.get("pos_profile") or "").strip():
        invoice_doc.pos_profile = effective_pos_profile

    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    current_state = _get_relay_state_doc(invoice_doc)
    if current_state.dispatch_status == "Released":
        next_dispatch_status = "Released"
    elif picking_status == "Exception":
        next_dispatch_status = "On Hold"
    else:
        next_dispatch_status = "Pending"

    state_doc = _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Paid" if invoice_doc.docstatus == 1 else "Draft",
        picking_status=picking_status,
        dispatch_status=next_dispatch_status,
        exceptions_note=exceptions_note,
    )
    return state_doc.as_dict() if state_doc else {}

def release_relay_dispatch(sales_invoice, allow_exception_release=0, pos_profile=None, pos_profile_id=None):
    require_operational_role_for_action(
        ("cline-Dispatch", "cline-Supervisor"),
        "release relay dispatch",
        allow_relay_sync=True,
    )

    if not _relay_workflow_doctype_exists():
        frappe.throw(_("Relay workflow state DocType is missing. Please run migration."))

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if effective_pos_profile and not cstr(invoice_doc.get("pos_profile") or "").strip():
        invoice_doc.pos_profile = effective_pos_profile

    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    if invoice_doc.docstatus != 1:
        frappe.throw(_("Only submitted Sales Invoices can be released for dispatch."))

    state_doc = _upsert_relay_workflow_state(invoice_doc, token_status="Paid")
    if not state_doc:
        frappe.throw(_("Unable to create relay workflow state."))

    if state_doc.dispatch_status == "Released":
        return state_doc.as_dict()

    allow_exception_release = cint(allow_exception_release)
    can_release = state_doc.picking_status == "Picked" or (
        allow_exception_release and state_doc.picking_status == "Exception"
    )

    if not can_release:
        frappe.throw(
            _(
                "Dispatch release requires Picking status 'Picked'. Use supervisor override for exceptions."
            )
        )

    state_doc = _upsert_relay_workflow_state(invoice_doc, dispatch_status="Released")
    return state_doc.as_dict() if state_doc else {}
