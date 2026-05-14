import frappe

from posawesome.posawesome.api.pos.payments.entry import (
    create_payment_entry,
    get_bank_cash_account,
    set_paid_amount_and_received_amount,
)
from posawesome.posawesome.api.pos.payments.lookup import (
    get_available_pos_profiles as _get_available_pos_profiles,
    get_outstanding_invoices as _get_outstanding_invoices,
    get_unallocated_payments as _get_unallocated_payments,
)
from posawesome.posawesome.api.pos.payments.reconciliation import (
    process_pos_payment as _process_pos_payment,
)


@frappe.whitelist()
def get_outstanding_invoices(company, currency, customer=None, pos_profile_name=None):
    return _get_outstanding_invoices(company, currency, customer, pos_profile_name)


@frappe.whitelist()
def get_unallocated_payments(customer, company, currency, mode_of_payment=None):
    return _get_unallocated_payments(customer, company, currency, mode_of_payment)


@frappe.whitelist()
def process_pos_payment(payload):
    return _process_pos_payment(payload)


@frappe.whitelist()
def get_available_pos_profiles(company, currency):
    return _get_available_pos_profiles(company, currency)
