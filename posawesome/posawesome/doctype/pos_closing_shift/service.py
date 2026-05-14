import json
import time

import frappe
from frappe.utils import flt


def get_pos_invoices(pos_opening_shift):
    submit_printed_invoices(pos_opening_shift)
    data = frappe.db.sql(
        """
        select
            name
        from
            `tabSales Invoice`
        where
            docstatus = 1 and posa_pos_opening_shift = %s
        """,
        (pos_opening_shift),
        as_dict=1,
    )
    return [frappe.get_doc("Sales Invoice", row.name).as_dict() for row in data]


def get_payments_entries(pos_opening_shift):
    return frappe.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "reference_no": pos_opening_shift,
            "payment_type": "Receive",
        },
        fields=[
            "name",
            "mode_of_payment",
            "paid_amount",
            "reference_no",
            "posting_date",
            "party",
        ],
    )


def make_closing_shift_from_opening(opening_shift):
    opening_shift = json.loads(opening_shift)
    submit_printed_invoices(opening_shift.get("name"))
    closing_shift = _new_closing_shift(opening_shift)

    pos_transactions = []
    taxes = []
    payments = _opening_payments(opening_shift)
    pos_payments_table = []

    for invoice in get_pos_invoices(opening_shift.get("name")):
        _add_invoice_to_closing_shift(
            closing_shift, invoice, opening_shift, pos_transactions, taxes, payments
        )

    for payment_entry in get_payments_entries(opening_shift.get("name")):
        _add_payment_entry_to_closing_shift(
            payment_entry, payments, pos_payments_table
        )

    closing_shift.set("pos_transactions", pos_transactions)
    closing_shift.set("payment_reconciliation", payments)
    closing_shift.set("taxes", taxes)
    closing_shift.set("pos_payments", pos_payments_table)
    return closing_shift


def submit_closing_shift(closing_shift):
    closing_shift_payload = json.loads(closing_shift)
    closing_shift_doc = save_closing_shift_with_retry(closing_shift_payload)
    closing_shift_doc.submit()
    return closing_shift_doc.name


def save_closing_shift_with_retry(closing_shift_payload, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            closing_shift_doc = frappe.get_doc(closing_shift_payload)
            closing_shift_doc.flags.ignore_permissions = True
            closing_shift_doc.save()
            return closing_shift_doc
        except frappe.QueryDeadlockError as exc:
            last_error = exc
            frappe.db.rollback()
            if attempt >= attempts - 1:
                break
            time.sleep(0.2 * (attempt + 1))
    raise last_error


def submit_printed_invoices(pos_opening_shift):
    invoices_list = frappe.get_all(
        "Sales Invoice",
        filters={
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 0,
            "posa_is_printed": 1,
        },
    )
    for invoice in invoices_list:
        invoice_doc = frappe.get_doc("Sales Invoice", invoice.name)
        invoice_doc.submit()


def _new_closing_shift(opening_shift):
    closing_shift = frappe.new_doc("POS Closing Shift")
    closing_shift.pos_opening_shift = opening_shift.get("name")
    closing_shift.period_start_date = opening_shift.get("period_start_date")
    closing_shift.period_end_date = frappe.utils.get_datetime()
    closing_shift.pos_profile = opening_shift.get("pos_profile")
    closing_shift.user = opening_shift.get("user")
    closing_shift.company = opening_shift.get("company")
    closing_shift.grand_total = 0
    closing_shift.net_total = 0
    closing_shift.total_quantity = 0
    return closing_shift


def _opening_payments(opening_shift):
    return [
        frappe._dict(
            {
                "mode_of_payment": detail.get("mode_of_payment"),
                "opening_amount": detail.get("amount") or 0,
                "expected_amount": detail.get("amount") or 0,
            }
        )
        for detail in opening_shift.get("balance_details")
    ]


def _add_invoice_to_closing_shift(
    closing_shift, invoice, opening_shift, pos_transactions, taxes, payments
):
    pos_transactions.append(
        frappe._dict(
            {
                "sales_invoice": invoice.name,
                "posting_date": invoice.posting_date,
                "grand_total": invoice.grand_total,
                "customer": invoice.customer,
            }
        )
    )
    closing_shift.grand_total += flt(invoice.grand_total)
    closing_shift.net_total += flt(invoice.net_total)
    closing_shift.total_quantity += flt(invoice.total_qty)
    _add_invoice_taxes(invoice, taxes)
    _add_invoice_payments(invoice, opening_shift, payments)


def _add_invoice_taxes(invoice, taxes):
    for tax in invoice.taxes:
        existing_tax = [
            row
            for row in taxes
            if row.account_head == tax.account_head and row.rate == tax.rate
        ]
        if existing_tax:
            existing_tax[0].amount += flt(tax.tax_amount)
        else:
            taxes.append(
                frappe._dict(
                    {
                        "account_head": tax.account_head,
                        "rate": tax.rate,
                        "amount": tax.tax_amount,
                    }
                )
            )


def _add_invoice_payments(invoice, opening_shift, payments):
    for payment in invoice.payments:
        existing_pay = [
            row for row in payments if row.mode_of_payment == payment.mode_of_payment
        ]
        if not existing_pay:
            payments.append(
                frappe._dict(
                    {
                        "mode_of_payment": payment.mode_of_payment,
                        "opening_amount": 0,
                        "expected_amount": payment.amount,
                    }
                )
            )
            continue

        amount = _invoice_payment_amount(invoice, opening_shift, payment)
        existing_pay[0].expected_amount += flt(amount)


def _invoice_payment_amount(invoice, opening_shift, payment):
    cash_mode_of_payment = frappe.get_value(
        "POS Profile",
        opening_shift.get("pos_profile"),
        "posa_cash_mode_of_payment",
    )
    cash_mode_of_payment = cash_mode_of_payment or "Cash"
    if payment.mode_of_payment == cash_mode_of_payment:
        return payment.amount - invoice.change_amount
    return payment.amount


def _add_payment_entry_to_closing_shift(payment_entry, payments, pos_payments_table):
    pos_payments_table.append(
        frappe._dict(
            {
                "payment_entry": payment_entry.name,
                "mode_of_payment": payment_entry.mode_of_payment,
                "paid_amount": payment_entry.paid_amount,
                "posting_date": payment_entry.posting_date,
                "customer": payment_entry.party,
            }
        )
    )
    existing_pay = [
        row for row in payments if row.mode_of_payment == payment_entry.mode_of_payment
    ]
    if existing_pay:
        existing_pay[0].expected_amount += flt(payment_entry.paid_amount)
    else:
        payments.append(
            frappe._dict(
                {
                    "mode_of_payment": payment_entry.mode_of_payment,
                    "opening_amount": 0,
                    "expected_amount": payment_entry.paid_amount,
                }
            )
        )
