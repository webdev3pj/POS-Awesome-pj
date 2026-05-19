# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json



import frappe

from frappe import _

from frappe.utils import cstr

from frappe.utils.background_jobs import enqueue

from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

from erpnext.stock.doctype.batch.batch import set_batch_nos



from posawesome.posawesome.api.pos.invoice.batch import set_batch_nos_for_bundels

from posawesome.posawesome.api.pos.invoice.credit import redeeming_customer_credit

from posawesome.posawesome.api.pos.invoice.document import (
    apply_pos_profile_tax_inclusive,
    strip_client_system_fields,
)

from posawesome.posawesome.api.pos.relay.state import _is_relay_workflow_enabled, _upsert_relay_workflow_state

from posawesome.posawesome.api.pos.session.roles import require_operational_role_for_action



def submit_invoice(invoice, data):
    data = json.loads(data or "{}")
    if not isinstance(data, dict):
        data = {}

    invoice = json.loads(invoice or "{}")
    if not isinstance(invoice, dict):
        invoice = {}
    strip_client_system_fields(invoice)

    invoice_doc = frappe.get_doc("Sales Invoice", invoice.get("name"))
    invoice_doc.flags.ignore_permissions = True
    invoice_doc.update(invoice)

    _set_invoice_cashier_attribution(invoice_doc, data=data, invoice_payload=invoice)

    if _is_relay_workflow_enabled(cstr(invoice_doc.get("pos_profile") or "").strip()):
        require_operational_role_for_action(
            ("cline-Cashier", "cline-Supervisor"),
            "submit invoices",
            allow_relay_sync=True,
        )

    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]
    if len(mop_cash_list) > 0:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {
            "account": frappe.get_value(
                "Company", invoice_doc.company, "default_cash_account"
            )
        }

    # creating advance payment
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "mode_of_payment": "Cash",
                "paid_to": cash_account["account"],
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": invoice_doc.get("customer"),
                "paid_amount": invoice_doc.get("credit_change"),
                "received_amount": invoice_doc.get("credit_change"),
                "company": invoice_doc.get("company"),
            }
        )

        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # calculating cash
    total_cash = 0
    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

    is_payment_entry = 0
    if data.get("redeemed_customer_credit"):
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])
                advance.flags.ignore_permissions = True

                advance_payment = {
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                }

                invoice_doc.append("advances", advance_payment)
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
        set_batch_nos(invoice_doc, "warehouse", throw=True)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    apply_pos_profile_tax_inclusive(invoice_doc)
    invoice_doc.save()

    if data.get("due_date"):
        frappe.db.set_value(
            "Sales Invoice",
            invoice_doc.name,
            "due_date",
            data.get("due_date"),
            update_modified=False,
        )

    has_sales_order = any(cstr(item.get("sales_order") or "").strip() for item in invoice_doc.items)
    allow_background_submission = frappe.get_value(
        "POS Profile",
        invoice_doc.pos_profile,
        "posa_allow_submissions_in_background_job",
    )

    if allow_background_submission and not has_sales_order:
        invoices_list = frappe.get_all(
            "Sales Invoice",
            filters={
                "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                "docstatus": 0,
                "posa_is_printed": 1,
            },
        )
        for invoice in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": invoice.name,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        invoice_doc.submit()
        redeeming_customer_credit(
            invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
        )
        _upsert_relay_workflow_state(
            invoice_doc,
            token_status="Paid",
            picking_status="Not Started",
            dispatch_status="Pending",
        )

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}

def _set_invoice_cashier_attribution(invoice_doc, data=None, invoice_payload=None):
    if not invoice_doc:
        return ""

    data = data or {}
    invoice_payload = invoice_payload or {}
    invoice_meta = None
    try:
        invoice_meta = frappe.get_meta("Sales Invoice")
    except Exception:
        invoice_meta = None

    def _read(mapping, key):
        if isinstance(mapping, dict):
            return cstr(mapping.get(key) or "").strip()
        return ""

    cashier_user = ""
    for candidate in (
        _read(data, "cashier_user_id"),
        _read(data, "cashier"),
        _read(invoice_payload, "cashier_user_id"),
        _read(invoice_payload, "cashier"),
        cstr(invoice_doc.get("custom_cashier") or "").strip(),
        cstr(invoice_doc.get("cashier_user_id") or "").strip(),
        cstr(invoice_doc.get("owner") or "").strip(),
        cstr(frappe.session.user or "").strip(),
    ):
        if candidate:
            cashier_user = candidate
            break

    if not cashier_user or not invoice_meta:
        return cashier_user

    for fieldname in ("custom_cashier", "cashier_user_id", "cashier"):
        if invoice_meta.has_field(fieldname):
            invoice_doc.set(fieldname, cashier_user)
            break

    cashier_name = cstr(
        frappe.get_cached_value("User", cashier_user, "full_name") or cashier_user
    ).strip()
    for name_field in ("custom_cashier_name", "cashier_name"):
        if cashier_name and invoice_meta.has_field(name_field):
            invoice_doc.set(name_field, cashier_name)
            break

    return cashier_user

def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    invoice_doc = kwargs.get("invoice_doc")
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc("Sales Invoice", invoice)
    invoice_doc.flags.ignore_permissions = True
    invoice_doc.submit()
    redeeming_customer_credit(
        invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
    )
    _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Paid",
        picking_status="Not Started",
        dispatch_status="Pending",
    )
