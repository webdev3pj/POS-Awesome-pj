# posawesome/posawesome/api.py

import frappe
from frappe import _

@frappe.whitelist()
def pay_commission(sales_invoice):
    if not sales_invoice:
        frappe.throw(_("Sales Invoice is required."))

    # Update the commission_paid check field
    frappe.db.set_value("Sales Invoice", sales_invoice, "custom_commisstion_paid", 1)
    frappe.db.commit()

@frappe.whitelist()
def pay_partner_commission(sales_invoice):
    if not sales_invoice:
        frappe.throw(_("Sales Invoice is required."))

    # Update the commission_paid check field
    frappe.db.set_value("Sales Invoice", sales_invoice, "custom_partner_commission_paid", 1)
    frappe.db.commit()
