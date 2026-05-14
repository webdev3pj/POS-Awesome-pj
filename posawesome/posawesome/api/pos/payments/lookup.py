import frappe

from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_outstanding_invoices as _get_outstanding_invoices


def get_outstanding_invoices(company, currency, customer=None, pos_profile_name=None):
    if not customer:
        filters = {
            "company": company,
            "outstanding_amount": (">", 0),
            "docstatus": 1,
            "is_return": 0,
            "currency": currency,
        }
        if pos_profile_name:
            filters.update({"pos_profile": pos_profile_name})
        return frappe.get_all(
            "Sales Invoice",
            filters=filters,
            fields=[
                "name",
                "customer",
                "customer_name",
                "outstanding_amount",
                "grand_total",
                "due_date",
                "posting_date",
                "currency",
                "pos_profile",
            ],
            order_by="due_date asc",
        )

    precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2
    outstanding_invoices = _get_outstanding_invoices(
        party_type="Customer",
        party=customer,
        account=get_party_account("Customer", customer, company),
    )
    invoices_list = []
    customer_name = frappe.get_cached_value("Customer", customer, "customer_name")
    for invoice in outstanding_invoices:
        if invoice.get("currency") != currency:
            continue
        if pos_profile_name and frappe.get_cached_value(
            "Sales Invoice", invoice.get("voucher_no"), "pos_profile"
        ) != pos_profile_name:
            continue
        outstanding_amount = invoice.outstanding_amount
        if outstanding_amount <= 0.5 / (10**precision):
            continue
        invoices_list.append(
            {
                "name": invoice.get("voucher_no"),
                "customer": customer,
                "customer_name": customer_name,
                "outstanding_amount": invoice.get("outstanding_amount"),
                "grand_total": invoice.get("invoice_amount"),
                "due_date": invoice.get("due_date"),
                "posting_date": invoice.get("posting_date"),
                "currency": invoice.get("currency"),
                "pos_profile": pos_profile_name,
            }
        )
    return invoices_list


def get_unallocated_payments(customer, company, currency, mode_of_payment=None):
    filters = {
        "party": customer,
        "company": company,
        "docstatus": 1,
        "party_type": "Customer",
        "payment_type": "Receive",
        "unallocated_amount": [">", 0],
        "paid_from_account_currency": currency,
    }
    if mode_of_payment:
        filters.update({"mode_of_payment": mode_of_payment})
    return frappe.get_all(
        "Payment Entry",
        filters=filters,
        fields=[
            "name",
            "paid_amount",
            "party_name as customer_name",
            "received_amount",
            "posting_date",
            "unallocated_amount",
            "mode_of_payment",
            "paid_from_account_currency as currency",
        ],
        order_by="posting_date asc",
    )


def get_available_pos_profiles(company, currency):
    return frappe.get_list(
        "POS Profile",
        filters={"disabled": 0, "company": company, "currency": currency},
        page_length=1000,
        pluck="name",
    )
