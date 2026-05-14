import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from erpnext.accounts.party import get_party_account
from posawesome.posawesome.api.m_pesa import submit_mpesa_payment
from posawesome.posawesome.api.pos.payments.entry import create_payment_entry


def process_pos_payment(payload):
    data = frappe._dict(json.loads(payload))
    _validate_payload(data)

    allow_make_new_payments = data.pos_profile.get("posa_allow_make_new_payments")
    allow_reconcile_payments = data.pos_profile.get("posa_allow_reconcile_payments")
    allow_mpesa_reconcile_payments = data.pos_profile.get(
        "posa_allow_mpesa_reconcile_payments"
    )

    new_payments_entry = []
    all_payments_entry = []
    errors = []
    reconcile_doc = None

    if allow_mpesa_reconcile_payments:
        _process_mpesa_payments(data, new_payments_entry, all_payments_entry, errors)

    if allow_make_new_payments:
        _process_new_payments(data, new_payments_entry, all_payments_entry, errors)

    if len(data.selected_invoices) > 0 and data.total_selected_invoices > 0:
        if allow_reconcile_payments:
            all_payments_entry.extend(data.selected_payments or [])
        if all_payments_entry:
            reconcile_doc = _reconcile_payments(data, all_payments_entry)

    msg = _build_result_message(
        new_payments_entry, all_payments_entry, data.selected_invoices, errors
    )
    if msg:
        frappe.msgprint(msg)

    return {
        "new_payments_entry": new_payments_entry,
        "all_payments_entry": all_payments_entry,
        "errors": errors,
        "reconcile_doc": reconcile_doc,
    }


def _validate_payload(data):
    if not data.pos_profile.get("posa_use_pos_awesome_payments"):
        frappe.throw(_("POS Awesome Payments is not enabled for this POS Profile"))
    for field, label in (
        ("customer", _("Customer is required")),
        ("company", _("Company is required")),
        ("currency", _("Currency is required")),
        ("pos_profile_name", _("POS Profile is required")),
        ("pos_opening_shift_name", _("POS Opening Shift is required")),
    ):
        if not data.get(field):
            frappe.throw(label)


def _process_mpesa_payments(data, new_payments_entry, all_payments_entry, errors):
    if not (len(data.selected_mpesa_payments) > 0 and data.total_selected_mpesa_payments > 0):
        return
    for mpesa_payment in data.selected_mpesa_payments:
        try:
            new_mpesa_payment = submit_mpesa_payment(mpesa_payment.get("name"), data.customer)
            new_payments_entry.append(new_mpesa_payment)
            all_payments_entry.append(new_mpesa_payment)
        except Exception as exc:
            errors.append(exc)


def _process_new_payments(data, new_payments_entry, all_payments_entry, errors):
    if not (len(data.payment_methods) > 0 and data.total_payment_methods > 0):
        return
    today = nowdate()
    for payment_method in data.payment_methods:
        try:
            if not payment_method.get("amount"):
                continue
            new_payment_entry = create_payment_entry(
                company=data.company,
                customer=data.customer,
                currency=data.currency,
                amount=flt(payment_method.get("amount")),
                mode_of_payment=payment_method.get("mode_of_payment"),
                posting_date=today,
                reference_no=data.pos_opening_shift_name,
                reference_date=today,
                cost_center=data.pos_profile.get("cost_center"),
                submit=1,
            )
            new_payments_entry.append(new_payment_entry)
            all_payments_entry.append(new_payment_entry)
        except Exception as exc:
            errors.append(exc)


def _reconcile_payments(data, all_payments_entry):
    all_payments_entry = sorted(
        all_payments_entry,
        key=lambda k: getdate(str(k.get("posting_date"))),
        reverse=True,
    )
    all_invoices_list = sorted(
        data.selected_invoices,
        key=lambda k: getdate(k.get("posting_date")),
        reverse=True,
    )
    reconcile_doc = frappe.new_doc("Payment Reconciliation")
    reconcile_doc.party_type = "Customer"
    reconcile_doc.party = data.customer
    reconcile_doc.company = data.company
    reconcile_doc.receivable_payable_account = get_party_account(
        "Customer", data.customer, data.company
    )
    reconcile_doc.get_unreconciled_entries()
    reconcile_doc.allocate_entries(
        {
            "invoices": [_invoice_allocation(invoice) for invoice in all_invoices_list],
            "payments": [_payment_allocation(payment) for payment in all_payments_entry],
        }
    )
    reconcile_doc.reconcile()
    return reconcile_doc


def _invoice_allocation(invoice):
    return {
        "invoice_type": "Sales Invoice",
        "invoice_number": invoice.get("name"),
        "invoice_date": invoice.get("posting_date"),
        "amount": invoice.get("grand_total"),
        "outstanding_amount": invoice.get("outstanding_amount"),
        "currency": invoice.get("currency"),
        "exchange_rate": 0,
    }


def _payment_allocation(payment):
    return {
        "reference_type": "Payment Entry",
        "reference_name": payment.get("name"),
        "posting_date": payment.get("posting_date"),
        "amount": payment.get("unallocated_amount"),
        "unallocated_amount": payment.get("unallocated_amount"),
        "difference_amount": 0,
        "currency": payment.get("currency"),
        "exchange_rate": 0,
    }


def _build_result_message(new_payments_entry, all_payments_entry, selected_invoices, errors):
    msg = ""
    if new_payments_entry:
        msg += _html_table(
            "New Payments",
            ("Payment Entry", "Amount"),
            [(p.get("name"), p.get("unallocated_amount")) for p in new_payments_entry],
        )
    if all_payments_entry and selected_invoices:
        msg += _html_table(
            "Reconciled Payments",
            ("Payment Entry", "Amount"),
            [(p.get("name"), p.get("unallocated_amount")) for p in all_payments_entry],
        )
    if selected_invoices:
        msg += _html_table(
            "Reconciled Invoices",
            ("Invoice", "Amount"),
            [(i.get("name"), i.get("outstanding_amount")) for i in selected_invoices],
        )
    if errors:
        msg += _html_table("Errors", ("Error",), [(error,) for error in errors])
    return msg


def _html_table(title, headers, rows):
    msg = f"<h4>{title}</h4><table class='table table-bordered'><thead><tr>"
    msg += "".join(f"<th>{header}</th>" for header in headers)
    msg += "</tr></thead><tbody>"
    for row in rows:
        msg += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    msg += "</tbody></table>"
    return msg
