# -*- coding: utf-8 -*-

import copy
import json

import frappe
from frappe import _
from frappe.utils import cstr

from posawesome.posawesome.api.posapp import (
    _get_relay_invoice_by_local_sale_ref,
    _is_relay_workflow_enabled,
    _set_relay_state_local_sale_ref,
    _upsert_relay_workflow_state,
    create_sales_order_token,
    submit_invoice,
    update_invoice,
)
from posawesome.posawesome.api.pos.relay.sync_utils import (
    as_dict,
    invoice_response,
    normalize_doc_payload,
    resolve_local_sale_ref,
    resolve_local_token_id,
    sales_order_response,
)


class RelaySyncService:
    def sync_sales_order_token(self, data, local_token_id=None):
        token_payload = as_dict(data)
        local_token_id = resolve_local_token_id(local_token_id, token_payload)
        if not local_token_id:
            frappe.throw(_("Relay local token ID is required."))

        existing_sales_order = self._get_sales_order_by_local_token_id(local_token_id)
        if existing_sales_order:
            return self._sales_order_response(existing_sales_order, local_token_id)

        token_payload = self._prepare_sales_order_token_payload(token_payload)
        result = create_sales_order_token(json.dumps(token_payload))
        sales_order_name = cstr(result.get("sales_order_name") or result.get("token_id") or "").strip()
        if not sales_order_name:
            frappe.throw(_("Unable to create Sales Order from relay token."))

        state_name = None
        workflow_state = result.get("workflow_state")
        if isinstance(workflow_state, dict):
            state_name = cstr(workflow_state.get("name") or "").strip()
        if not state_name:
            state_name = frappe.db.exists(
                "POS Relay Workflow State", {"sales_order": sales_order_name}
            )
        if state_name and self._relay_workflow_has_field("local_token_id"):
            state_doc = frappe.get_doc("POS Relay Workflow State", state_name)
            state_doc.local_token_id = local_token_id
            state_doc.is_offline_recorded = 1
            state_doc.last_sync_status = "Synced"
            state_doc.flags.ignore_permissions = True
            state_doc.save()

        return sales_order_response(frappe.get_doc("Sales Order", sales_order_name), local_token_id)

    def submit_offline_invoice(self, invoice, data=None, local_ref=None):
        invoice_payload = as_dict(invoice)
        data_payload = as_dict(data)
        local_sale_ref = resolve_local_sale_ref(local_ref, invoice_payload, data_payload)

        if not local_sale_ref:
            frappe.throw(_("Relay local sale reference is required."))

        existing_invoice = _get_relay_invoice_by_local_sale_ref(local_sale_ref)
        if existing_invoice:
            if existing_invoice.docstatus == 0:
                return self._submit_existing_invoice(
                    existing_invoice, invoice_payload, data_payload, local_sale_ref
                )
            return invoice_response(existing_invoice, local_sale_ref)

        pos_profile = cstr(invoice_payload.get("pos_profile") or "").strip()
        if pos_profile and not _is_relay_workflow_enabled(pos_profile):
            frappe.throw(
                _("Relay workflow is not enabled for POS Profile {0}").format(pos_profile)
            )

        invoice_payload = self._prepare_invoice_payload(invoice_payload)
        data_payload["local_sale_ref"] = local_sale_ref

        draft_invoice = update_invoice(json.dumps(invoice_payload))
        state_doc = _upsert_relay_workflow_state(
            draft_invoice,
            token_status="Draft",
            picking_status="Not Started",
            dispatch_status="Pending",
            is_offline_recorded=1,
            last_sync_status="Pending",
        )
        _set_relay_state_local_sale_ref(state_doc, local_sale_ref)

        return self._submit_existing_invoice(
            draft_invoice, invoice_payload, data_payload, local_sale_ref
        )

    def _submit_existing_invoice(
        self, invoice_doc, invoice_payload, data_payload, local_sale_ref
    ):
        submit_payload = self._prepare_invoice_payload(invoice_payload)
        submit_payload["name"] = invoice_doc.name
        result = submit_invoice(json.dumps(submit_payload), json.dumps(data_payload))

        submitted_invoice = frappe.get_doc("Sales Invoice", result.get("name") or invoice_doc.name)
        state_doc = _upsert_relay_workflow_state(
            submitted_invoice,
            token_status="Paid",
            picking_status="Not Started",
            dispatch_status="Pending",
            is_offline_recorded=1,
            last_sync_status="Synced",
            sync_error="",
        )
        _set_relay_state_local_sale_ref(state_doc, local_sale_ref)
        return invoice_response(submitted_invoice, local_sale_ref)

    def _prepare_invoice_payload(self, invoice_payload):
        prepared = copy.deepcopy(invoice_payload or {})
        prepared["doctype"] = "Sales Invoice"

        invoice_name = cstr(prepared.get("name") or "").strip()
        if invoice_name and not frappe.db.exists("Sales Invoice", invoice_name):
            prepared.pop("name", None)
        if not invoice_name:
            prepared.pop("name", None)

        for fieldname in ("docstatus", "owner", "creation", "modified", "modified_by"):
            prepared.pop(fieldname, None)

        return normalize_doc_payload(prepared, "Sales Invoice")

    def _prepare_sales_order_token_payload(self, token_payload):
        prepared = copy.deepcopy(token_payload or {})
        pos_profile = cstr(
            prepared.get("pos_profile") or prepared.get("pos_profile_id") or ""
        ).strip()
        if pos_profile:
            prepared["pos_profile"] = pos_profile
            prepared["pos_profile_id"] = pos_profile
            if not prepared.get("company"):
                prepared["company"] = frappe.get_cached_value(
                    "POS Profile", pos_profile, "company"
                )
            if not prepared.get("currency"):
                prepared["currency"] = frappe.get_cached_value(
                    "POS Profile", pos_profile, "currency"
                )
        if not prepared.get("customer") and prepared.get("customer_id"):
            prepared["customer"] = prepared.get("customer_id")
        return prepared

    def _get_sales_order_by_local_token_id(self, local_token_id):
        local_token_id = cstr(local_token_id or "").strip()
        if not local_token_id or not self._relay_workflow_has_field("local_token_id"):
            return None
        state_name = frappe.db.exists(
            "POS Relay Workflow State", {"local_token_id": local_token_id}
        )
        if not state_name:
            return None
        sales_order = cstr(
            frappe.db.get_value("POS Relay Workflow State", state_name, "sales_order")
            or ""
        ).strip()
        if sales_order and frappe.db.exists("Sales Order", sales_order):
            return frappe.get_doc("Sales Order", sales_order)
        return None

    def _relay_workflow_has_field(self, fieldname):
        if not frappe.db.exists("DocType", "POS Relay Workflow State"):
            return False
        return frappe.get_meta("POS Relay Workflow State").has_field(fieldname)


@frappe.whitelist()
def sync_sales_order_token(data, local_token_id=None):
    return RelaySyncService().sync_sales_order_token(
        data=data, local_token_id=local_token_id
    )


@frappe.whitelist()
def submit_relay_offline_invoice(invoice, data=None, local_ref=None):
    return RelaySyncService().submit_offline_invoice(
        invoice=invoice, data=data, local_ref=local_ref
    )
