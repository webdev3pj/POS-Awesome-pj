# Copyright (c) 2025, Youssef Restom and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe import _

class SalesPartnerCommissionBulkPayOut(Document):
    def before_submit(self):
        if not self.mode_of_payment:
            frappe.throw(_("Mode of Payment is required before submitting."))

    def on_submit(self):
        for row in self.items:
            if row.reference_sales_invoice:
                frappe.db.set_value(
                    "Sales Invoice",
                    row.reference_sales_invoice,
                    "custom_partner_commission_paid",
                    1
                )