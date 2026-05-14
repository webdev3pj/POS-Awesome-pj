# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe

from frappe import _

from frappe.utils import cint, cstr, flt



from posawesome.posawesome.api.pos.relay.state import (
    _is_relay_workflow_enabled,
    _relay_workflow_doctype_exists,
    _resolve_relay_workflow_pos_profile,
    _upsert_relay_workflow_state,
)



def get_relay_workflow_state(sales_invoice):
    if not _relay_workflow_doctype_exists():
        return {}

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    if not _is_relay_workflow_enabled(invoice_doc.pos_profile):
        return {}

    state_doc = _upsert_relay_workflow_state(invoice_doc)
    return state_doc.as_dict() if state_doc else {}

def get_relay_fulfillment_detail(sales_invoice, pos_profile=None, pos_profile_id=None):
    if not _relay_workflow_doctype_exists():
        return {}

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    state_doc = _upsert_relay_workflow_state(invoice_doc, token_status="Paid")
    state = state_doc.as_dict() if state_doc else {}
    sale = {
        "local_sale_ref": invoice_doc.name,
        "token_id": state.get("token_id") or invoice_doc.name,
        "pos_profile_id": effective_pos_profile or invoice_doc.pos_profile,
        "customer_id": invoice_doc.customer,
        "customer_name": invoice_doc.customer_name,
        "currency": invoice_doc.currency,
        "grand_total": invoice_doc.grand_total,
        "paid": 1 if invoice_doc.docstatus == 1 else 0,
        "pick_status": _cloud_pick_to_relay_status(state.get("picking_status")),
        "dispatch_status": cstr(state.get("dispatch_status") or "Pending").upper(),
        "released_at": state.get("released_at"),
        "dispatch_proof": state.get("dispatch_proof") or state.get("dispatch_proof_payload") or {},
        "dispatch_proof_payload": state.get("dispatch_proof_payload") or state.get("dispatch_proof") or {},
        "cashier_adjustment_required": cint(state.get("cashier_adjustment_required") or 0),
        "created_at": invoice_doc.creation,
        "updated_at": state.get("modified") or invoice_doc.modified,
    }
    lines = []
    for row in invoice_doc.items:
        conversion_factor = flt(row.get("conversion_factor") or 1) or 1
        qty = flt(row.get("qty") or 0)
        stock_qty = flt(row.get("stock_qty") or (qty * conversion_factor))
        lines.append(
            {
                "id": row.idx,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": qty,
                "uom": row.uom,
                "rate": row.rate,
                "amount": row.amount,
                "pick_status": sale["pick_status"],
                "payload": {
                    "stock_uom": row.stock_uom,
                    "stock_qty": stock_qty,
                    "conversion_factor": conversion_factor,
                },
            }
        )
    return {
        "ok": True,
        "sale": sale,
        "lines": lines,
        "pick_events": [],
        "dispatch_events": [],
        "outbox_events": [],
        "workflow_state": state,
    }

def _cloud_pick_to_relay_status(picking_status):
    status = cstr(picking_status or "").strip()
    if status == "In Progress":
        return "PICK_IN_PROGRESS"
    if status == "Picked":
        return "PICKED_READY_FOR_RELEASE"
    if status == "Exception":
        return "PICK_EXCEPTION"
    return "PAID_PENDING_PICK"

def get_relay_pick_queue(pos_profile=None, picking_status=None, dispatch_status=None, limit_page_length=50):
    if not _relay_workflow_doctype_exists():
        return []

    filters = {"token_status": "Paid"}
    if pos_profile:
        filters["pos_profile"] = pos_profile
    if picking_status:
        filters["picking_status"] = picking_status
    if dispatch_status:
        filters["dispatch_status"] = dispatch_status
    else:
        filters["dispatch_status"] = ["!=", "Released"]

    return frappe.get_all(
        "POS Relay Workflow State",
        filters=filters,
        fields=[
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
        ],
        order_by="modified asc",
        limit_page_length=cint(limit_page_length) or 50,
    )
