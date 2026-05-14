import frappe
from frappe.utils import add_days


def add_loyalty_point(invoice_doc):
    for offer in invoice_doc.posa_offers:
        if offer.offer != "Loyalty Point":
            continue
        original_offer = frappe.get_doc("POS Offer", offer.offer_name)
        if original_offer.loyalty_points <= 0:
            continue
        loyalty_program = frappe.get_value(
            "Customer", invoice_doc.customer, "loyalty_program"
        )
        if not loyalty_program:
            loyalty_program = original_offer.loyalty_program
        frappe.get_doc(
            {
                "doctype": "Loyalty Point Entry",
                "loyalty_program": loyalty_program,
                "loyalty_program_tier": original_offer.name,
                "customer": invoice_doc.customer,
                "invoice_type": "Sales Invoice",
                "invoice": invoice_doc.name,
                "loyalty_points": original_offer.loyalty_points,
                "expiry_date": add_days(invoice_doc.posting_date, 10000),
                "posting_date": invoice_doc.posting_date,
                "company": invoice_doc.company,
            }
        ).insert(ignore_permissions=True)
